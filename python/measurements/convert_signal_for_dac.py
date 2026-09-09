
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path



class Config:
    FILENAME = Path("data/signal_even_harmonics.bin")
    FILENAME_2 = Path("data/signal_odd_harmonics.bin")
    DAC_RES_BITS = 12
    DAC_VCC = 3.3


class DAC:
    def __init__(self, resolution_bits, vcc):
        self.Res_bits = resolution_bits
        self.Vcc = vcc

    @property
    def Lsb(self):
        return self.Vcc/(2**self.Res_bits)

    @property
    def Max_value(self):
        return 2 ** self.Res_bits - 1


class CovertSignalForDAC:
    def __init__(self, dac: DAC, filename: Path):
        self.dac = dac
        self.filename = filename
        self.loaded_signal = None
        self.dac_signal = None

    def load_signal(self):
        self.loaded_signal = np.fromfile(self.filename, dtype=np.float32)

    def convert_to_dac_signal(self, amp, offset):
        max_value = min(amp, self.dac.Max_value)
        self.dac_signal = np.round(self.loaded_signal * max_value + offset).astype(np.uint16)
        np.clip(self.dac_signal, a_min=0, a_max=self.dac.Max_value, out=self.dac_signal)

    def plot(self):
        plt.figure(figsize=(10, 5))
        plt.plot(list(range(len(self.dac_signal))), self.dac_signal)
        plt.title(f"{self.filename}")
        plt.xlabel("Próbka")
        plt.ylabel("Amplituda")
        plt.grid(True)
        plt.show()

    def save(self):
        self.dac_signal.astype(np.float32).tofile("data\\dac_" + str(self.filename.parts[-1]))

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
    if Config.FILENAME.exists():
        loaded_signal = np.fromfile(Config.FILENAME, dtype=np.float32)
        # loaded_signal = np.loadtxt(FILENAME, delimiter=",")

        # 6. Przeskalowanie wczytanych wartości (0.0 - 1.0) na 12-bitowy DAC (0 - 4095)
        dac_values = np.round(loaded_signal * dac.Max_value).astype(np.uint16)

        # 7. Wygenerowanie tablicy w stylu C
        print(f"const uint16_t dac_lut[{len(dac_values)}] = {{")
        for i in range(0, len(dac_values), 10):  # Drukuj 10 wartości na wiersz dla czytelności
            row = dac_values[i:i + 10]
            print("    " + ", ".join(f"{val}" for val in row) + ",")
        print("};")
        print("\n")

        # 8. Rysowanie wykresu na podstawie wczytanych i przeskalowanych danych
        plt.plot(list(range(len(dac_values))), dac_values)
        plt.title("Odtworzony sygnał 12-bit (wczytany z pliku binarnego)")
        plt.xlabel("Próbka")
        plt.ylabel("Amplituda (0 - 4095)")
        plt.grid(True)
        plt.show()
    else:
        print("Błąd: Plik binarny nie istnieje!")

    CovertSignalForDAC(filename=Config.FILENAME, dac=dac).convert_and_save(dac.Max_value/2)
    CovertSignalForDAC(filename=Config.FILENAME_2, dac=dac).convert_and_save(dac.Max_value/2, 2000)