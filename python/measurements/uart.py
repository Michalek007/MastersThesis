from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from calculations.converter import ADC

import serial
import struct
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime
from enum import Enum
import numpy as np
import time


class Waveform(Enum):
    SINE = 0
    SINE_ODD_HARMONICS = 1
    SQUARE_WAVE = 2
    LAST_SENT = 3


class Config:
    SERIAL_PORT = "COM3"
    BAUDRATE = 230400
    SAMPLING_RATE = 10e3
    FREQ = 50
    SAMPLES_PER_PERIOD = 10e3/FREQ
    TIME_STEP = 1/SAMPLING_RATE
    BATCH_SIZE = 400  # data sent in one burst [bytes]
    RECORD_SECONDS = 5
    OUT_FILE = Path(f"data/uart_capture_{datetime.now().strftime('%Y%m%d_%H%M')}.bin")
    VCC = 3.3
    V_REF = VCC/2


class UART:
    def __init__(self, serial_port, baudrate, out_file, batch_size=400, timeout=0.1):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.out_file = out_file
        self.batch_size = batch_size
        self.timeout = timeout
        self.serial: serial.Serial

    def connect(self):
        self.serial = serial.Serial(
            port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        print(f"Opened {self.serial_port} @ {self.baudrate} baud")

    def close(self):
        self.serial.close()

    def capture(self, record_seconds, waveform: Waveform):
        print(f"Recording for {record_seconds} seconds...")

        buffer = bytearray()
        with open(self.out_file, "wb") as f:
            start_packet = bytes([ord("S"), record_seconds, waveform.value])
            self.serial.write(start_packet)
            data = 1
            while data:
                data = self.serial.read(self.batch_size - len(buffer))
                if data:
                    buffer.extend(data)

                if len(buffer) == self.batch_size:
                    f.write(buffer)
                    buffer.clear()
        print("Capture complete.")

    def send_waveform(self, filename):
        start_packet = bytes([ord("R"), 0, 0])
        self.serial.write(start_packet)
        # time.sleep(0.1)

        batch_size = 2000
        with open(filename, "rb") as f:
            self.serial.write(f.read(batch_size))
            self.serial.flush()

            # while True:
            #     chunk = f.read(batch_size)
            #     if not chunk:
            #         break  # End of file reached


class DataReader:
    def __init__(self, filename: Path, adc: ADC = None):
        self.filename = filename
        self.count = None
        self.values = None
        self.x = None

        self.adc = adc
        self.v_adc = None
        self.t = None

    def read(self):
        with open(self.filename, "rb") as f:
            raw = f.read()

        self.count = len(raw) // 2
        self.values = struct.unpack(f">{self.count}H", raw)
        # self.values = rc_filter_numpy(self.values)
        self.x = [i for i in range(self.count)]

        if self.adc:
            self.v_adc = [i * self.adc.Lsb for i in self.values]
            self.t = [i * Config.TIME_STEP for i in range(self.count)]

        if self.count == 0:
            raise ValueError("Error: loaded 0 samples!")
        print(f"Loaded {self.count} samples")

    def plot(self, periods=10, scale_to_v=False):
        y = self.values if not scale_to_v else self.v_adc
        x = self.x if not scale_to_v else self.t
        plt.figure()
        plt.plot(x[0:int(Config.SAMPLES_PER_PERIOD*periods)], y[0:int(Config.SAMPLES_PER_PERIOD*periods)])
        plt.title("Raw data" if not scale_to_v else "VADC")
        plt.xlabel("Sample index" if not scale_to_v else "Time [s]")
        plt.ylabel("Value" if not scale_to_v else "Voltage [V]")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_scatter(self, periods=10, scale_to_v=False):
        y = self.values if not scale_to_v else self.v_adc
        x = self.x if not scale_to_v else self.t
        plt.figure()
        plt.scatter(x[0:int(Config.SAMPLES_PER_PERIOD*periods)], y[0:int(Config.SAMPLES_PER_PERIOD*periods)], s=0.5)
        plt.title("Raw data" if not scale_to_v else "VADC")
        plt.xlabel("Sample index" if not scale_to_v else "Time [s]")
        plt.ylabel("Value" if not scale_to_v else "Voltage [V]")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_histogram(self, bins=100, scale_to_v=False):
        plt.figure()
        plt.hist(self.values if not scale_to_v else self.v_adc, bins=bins)
        plt.xlabel("Value")
        plt.ylabel("Frequency")
        plt.title("Histogram of Variable Values")
        plt.show()

    def fft(self, scale_to_v=False):
        fft = FFT(signal=self.values if not scale_to_v else self.v_adc, sampling_rate=Config.SAMPLING_RATE, remove_offset=False)
        fft.calculate()
        fft.plot_fft(x_lim=2500)
        fft.get_harmonic_amplitudes(f0=50, num_harmonics=5, search_window_hz=2.0)
        fft.print_harmonic_amplitudes()

    def analyse_signal(self, scale_to_v=False):
        signal_analyser = SignalAnalyzer(signal=self.values if not scale_to_v else self.v_adc)
        signal_analyser.print_parameters()


def rc_filter_numpy(data, fs=10_000, R=1000, C=22e-9):
    """
    Pure NumPy implementation of a 1st-order RC low-pass filter.
    """
    dt = 1.0 / fs
    RC = R * C
    alpha = dt / (RC + dt)

    filtered = np.zeros_like(data, dtype=float)
    filtered[0] = data[0]

    # Calculate difference equation iteratively
    for i in range(1, len(data)):
        filtered[i] = alpha * data[i] + (1.0 - alpha) * filtered[i - 1]

    return filtered


if __name__ == "__main__":
    uart = UART(serial_port=Config.SERIAL_PORT, baudrate=Config.BAUDRATE, out_file=Config.OUT_FILE, batch_size=Config.BATCH_SIZE)
    uart.connect()

    uart.send_waveform(filename=Path('data/dac_dc.bin'))
    # uart.send_waveform(filename=Path('data/dac_sine.bin'))
    # uart.send_waveform(filename=Path('data/dac_small_sine.bin'))
    # uart.send_waveform(filename=Path('data/dac_signal_odd_harmonics.bin'))
    # time.sleep(1)
    uart.capture(record_seconds=5, waveform=Waveform.LAST_SENT)
    # uart.capture(record_seconds=5, waveform=Waveform.SQUARE_WAVE)
    # uart.capture(record_seconds=5, waveform=Waveform.SINE)
    uart.close()

    adc = ADC(vcc=3.3, resolution_bits=16)
    data_reader = DataReader(filename=Path(Config.OUT_FILE), adc=adc)
    data_reader.read()
    data_reader.plot_scatter(periods=5)
    data_reader.plot_histogram()
    data_reader.plot(periods=2)
    data_reader.fft()
    data_reader.analyse_signal(scale_to_v=False)

    data_reader.plot_scatter(periods=5, scale_to_v=True)
    data_reader.plot_histogram(scale_to_v=True)
    data_reader.plot(periods=2, scale_to_v=True)
    data_reader.fft(scale_to_v=True)
    data_reader.analyse_signal(scale_to_v=True)
