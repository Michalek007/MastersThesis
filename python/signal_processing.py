from measurements.fft import FFT
from calculations.converter import ADC
from calculations.helmholtz_coil import DAC, CurrentSource, HelmholtzCoil
from calculations.sensors import Sensor, AD8429, ALT021, DRV425, DRV5055, HMC1001

from pathlib import Path
import struct
import matplotlib.pyplot as plt
import numpy as np


class Config:
    SAMPLING_RATE = 10e3
    FREQ = 50
    PERIOD = 1/FREQ
    SAMPLES_PER_PERIOD = SAMPLING_RATE*PERIOD
    TIME_STEP = 1/SAMPLING_RATE
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    DATA_FILE = "data/uart_capture.bin"


class DataReader:
    def __init__(self, filename: Path):
        self.filename = filename
        self.count = None
        self.values = None
        self.x = None

    def read(self):
        with open(self.filename, "rb") as f:
            raw = f.read()

        self.count = len(raw) // 2
        self.values = struct.unpack(f">{self.count}H", raw)
        self.x = [i for i in range(self.count)]

        print(f"Loaded {self.count} samples")

    def plot(self, periods=10):
        plt.figure()
        plt.plot(self.x[0:int(Config.SAMPLES_PER_PERIOD*periods)], self.values[0:int(Config.SAMPLES_PER_PERIOD*periods)])
        plt.title("Raw data")
        plt.xlabel("Sample index")
        plt.ylabel("Value")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_scatter(self, periods=10):
        plt.figure()
        plt.scatter(self.x[0:int(Config.SAMPLES_PER_PERIOD*periods)], self.values[0:int(Config.SAMPLES_PER_PERIOD*periods)], s=0.5)
        plt.title("Raw data")
        plt.xlabel("Sample index")
        plt.ylabel("Value")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_histogram(self, bins=100):
        plt.figure()
        plt.hist(self.values, bins=bins)
        plt.xlabel("Value")
        plt.ylabel("Frequency")
        plt.title("Histogram of Variable Values")
        plt.show()

    def fft(self):
        fft = FFT(signal=self.values, sampling_rate=Config.SAMPLING_RATE)
        fft.calculate()
        fft.plot_fft()


class SignalProcessing:
    def __init__(self, dac_values, adc: ADC, sensor: Sensor, ad8429: AD8429):
        self.dac_values = np.array(dac_values)
        self.n_samples = len(dac_values)
        self.t = [i * Config.TIME_STEP for i in range(self.n_samples)]
        self.adc = adc
        self.sensor = sensor
        self.ad8429 = ad8429
        self.fft = FFT(signal=self.dac_values, sampling_rate=Config.SAMPLING_RATE)
        self.fft.calculate()

    def plot(self, title, y_scale = 1, periods: int = 5, y_label = "Amplitude", offset=0):
        plt.figure()
        plt.plot(self.t[0:int(Config.SAMPLES_PER_PERIOD*periods)], (self.dac_values[0:int(Config.SAMPLES_PER_PERIOD*periods)]+offset) * y_scale)
        plt.title(title)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_v_adc(self):
        self.plot(title="Napięcie od czasu przetwornika A/C", y_scale=adc.Lsb, y_label="Napięcie [V]")
        self.fft.plot_fft(y_scale=adc.Lsb)

    def plot_magnetic_field(self):
        offset = np.average(self.dac_values)
        factor = adc.Lsb / self.ad8429.G / self.sensor.S * 1e6
        self.plot(title="Pole magnetyczne od czasu", y_scale=factor, y_label="Pole magnetycze [uT]", offset=-offset)
        fft = FFT(signal=self.dac_values-offset, sampling_rate=Config.SAMPLING_RATE)
        fft.calculate()
        fft.plot_fft(y_scale=factor)


if __name__ == '__main__':
    data_reader = DataReader(filename=Path(Config.DATA_FILE))
    data_reader.read()
    data_reader.plot_scatter(periods=2)
    data_reader.plot_histogram()
    data_reader.plot(periods=1)
    data_reader.fft()

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2)
    alt021 = ALT021(vcc=Config.SENSOR_VCC)

    sp_alt021 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429_g2)
    sp_alt021.plot_v_adc()
    sp_alt021.plot_magnetic_field()