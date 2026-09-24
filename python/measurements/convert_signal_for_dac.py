from calculations.converter import DAC

import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path


class Config:
    FILENAME = Path("data/signal_even_harmonics.bin")
    FILENAME_2 = Path("data/signal_odd_harmonics.bin")
    DAC_RES_BITS = 12
    DAC_VCC = 3.3


class CovertSignalForDAC:
    def __init__(self, dac: DAC, filename: Path, out_file: Path = None):
        self.dac = dac
        self.filename = filename
        self.loaded_signal = None
        self.dac_signal = None
        self.out_file = out_file
        if not self.out_file:
            self.out_file = Path(self.filename.parts[-2] + "/dac_" + self.filename.parts[-1])

    def load_signal(self):
        self.loaded_signal = np.fromfile(self.filename, dtype=np.float32)

    def convert_to_dac_signal(self, amp, offset):
        # max_value = min(amp, self.dac.Max_value)
        self.loaded_signal -= np.min(self.loaded_signal)
        self.dac_signal = np.round(self.loaded_signal * amp + offset).astype(np.uint16)
        self.dac_signal += self.dac.Min_value
        np.clip(self.dac_signal, a_min=0, a_max=self.dac.Max_value, out=self.dac_signal)

    def plot(self):
        plt.figure(figsize=(10, 5))
        plt.plot(list(range(len(self.dac_signal))), self.dac_signal)
        plt.title(f"{self.filename}")
        plt.xlabel("Próbka")
        plt.ylabel("Amplituda")
        plt.grid(True)
        plt.show()

        plt.figure(figsize=(10, 5))
        plt.plot(list(range(len(self.dac_signal))), self.dac_signal*self.dac.Lsb)
        plt.title(f"{self.filename}")
        plt.xlabel("Czas")
        plt.ylabel("Napięcie [V]")
        plt.grid(True)
        # plt.show()
        plt.savefig(f'graphs/{self.out_file.parts[-1].split(".")[0]}.png', dpi=500)

    def save(self):
        self.dac_signal.astype(np.uint16).tofile(self.out_file)

    def print_c_array(self):
        print(f"const uint16_t dac_lut[{len(self.dac_signal)}] = {{")
        for i in range(0, len(self.dac_signal), 10):
            row = self.dac_signal[i:i + 10]
            print("    " + ", ".join(f"{val}" for val in row) + ",")
        print("};")
        print("\n")

    def convert_and_save(self, amp, offset=0):
        self.load_signal()
        self.convert_to_dac_signal(amp, offset)
        self.plot()
        self.print_c_array()
        self.save()


if __name__ == '__main__':
    dac = DAC(vcc=Config.DAC_VCC, resolution_bits=Config.DAC_RES_BITS)
    CovertSignalForDAC(filename=Config.FILENAME, dac=dac).convert_and_save(dac.Max_value/2)
    CovertSignalForDAC(filename=Config.FILENAME_2, dac=dac).convert_and_save(dac.Max_value/2, 2000)
    CovertSignalForDAC(filename=Path('data/sine.bin'), dac=dac).convert_and_save(dac.Value(0.1))
    CovertSignalForDAC(filename=Path('data/sine.bin'), out_file=Path('data/dac_small_sine.bin'), dac=dac).convert_and_save(20)
    CovertSignalForDAC(filename=Path('data/dc.bin'), dac=dac).convert_and_save(2048)
    CovertSignalForDAC(filename=Path('data/sine.bin'), out_file=Path('data/dac_sine_100.bin'), dac=dac).convert_and_save(50, offset=dac.Value(0.5))
