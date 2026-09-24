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


class UartConfig:
    SERIAL_PORT = "COM3"
    BAUDRATE = 230400
    SAMPLING_RATE = 10e3
    FREQ = 50
    SAMPLES_PER_PERIOD = 10e3/FREQ
    TIME_STEP = 1/SAMPLING_RATE
    BATCH_SIZE = 400  # data sent in one burst [bytes]
    RECORD_SECONDS = 5
    OUT_FILE = Path(f"data/uart_capture_{datetime.now().strftime('%Y%m%d_%H%M')}.bin")
    # OUT_FILE = Path(f"data/uart_capture_test.bin")
    VCC = 3.3
    V_REF = VCC/2


class UART:
    def __init__(self, serial_port, baudrate, out_file: Path, batch_size=400, timeout=2):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.out_file = out_file
        self.out_ref_file = self.out_file.with_name(f"{self.out_file.stem}_ref{self.out_file.suffix}")
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

    # def create_start_packet(self, command_byte="S", record_seconds=1, waveform_value=0, k=1):
    #     return bytes([ord(command_byte), record_seconds, waveform_value, k])

    def capture(self, record_seconds, waveform: Waveform, k=1):
        print(f"Recording for {record_seconds} seconds...")

        buffer = bytearray()
        collected_bytes = 0
        target_bytes = UartConfig.SAMPLING_RATE * record_seconds * 2
        with open(self.out_file, "wb") as f:
            start_packet = bytes([ord("S"), record_seconds, waveform.value, k])
            self.serial.write(start_packet)
            data = 1
            while data:
                if collected_bytes == target_bytes:
                    break

                data = self.serial.read(self.batch_size - len(buffer))
                if data:
                    buffer.extend(data)

                if len(buffer) == self.batch_size:
                    collected_bytes += self.batch_size
                    f.write(buffer)
                    buffer.clear()

        with open(self.out_ref_file, "wb") as f:
            n_bytes = int(UartConfig.SAMPLING_RATE * record_seconds * 2)
            data = self.serial.read(n_bytes)
            f.write(data)

        # with open(self.out_ref_file, "wb") as f:
        #     n_bytes = int(UartConfig.SAMPLING_RATE * record_seconds * 2)
        #     collected_ref_bytes = 0
        #
        #     while collected_ref_bytes < n_bytes:
        #         # Pytaj o resztę brakujących danych, ale nie więcej niż np. wielkość batch_size
        #         bytes_to_read = min(self.batch_size, n_bytes - collected_ref_bytes)
        #         data = self.serial.read(bytes_to_read)
        #
        #         if not data:
        #             # Wyjście z pętli w razie braku danych (np. wyczerpanie timeoutu bez żadnych nowych bajtów)
        #             print(f"Warning: Serial timeout! Otrzymano {collected_ref_bytes}/{n_bytes} bajtów.")
        #             break
        #
        #         f.write(data)
        #         collected_ref_bytes += len(data)

        print("Capture complete.")

    def send_waveform(self, filename):
        start_packet = bytes([ord("R"), 0, 0, 1])
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
    def __init__(self, filename: Path, adc: ADC = None, freq=50):
        self.filename = filename
        self.count = None
        self.values = None
        self.x = None

        self.adc = adc
        self.v_adc = None
        self.t = None

        self.freq = freq
        self.samples_per_period = UartConfig.SAMPLING_RATE / self.freq

    def read(self):
        with open(self.filename, "rb") as f:
            raw = f.read()

        self.count = len(raw) // 2
        self.values = struct.unpack(f">{self.count}H", raw)
        # self.values = rc_filter_numpy(self.values)
        self.x = [i for i in range(self.count)]

        if self.adc:
            self.v_adc = [i * self.adc.Lsb for i in self.values]
            self.t = [i * UartConfig.TIME_STEP for i in range(self.count)]

        if self.count == 0:
            raise ValueError("Error: loaded 0 samples!")
        print(f"Loaded {self.count} samples")

    def plot(self, periods=10, scale_to_v=False):
        y = self.values if not scale_to_v else self.v_adc
        x = self.x if not scale_to_v else self.t
        plt.figure()
        plt.plot(x[0:int(self.samples_per_period*periods)], y[0:int(self.samples_per_period*periods)])
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
        plt.scatter(x[0:int(self.samples_per_period*periods)], y[0:int(self.samples_per_period*periods)], s=0.5)
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
        fft = FFT(signal=self.values if not scale_to_v else self.v_adc, sampling_rate=UartConfig.SAMPLING_RATE, remove_offset=True)
        fft.calculate()
        fft.plot_fft(x_lim=2500)
        fft.get_harmonic_amplitudes(fundamental_freq=50, max_freq=2500)
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
    k = 1
    uart = UART(serial_port=UartConfig.SERIAL_PORT, baudrate=UartConfig.BAUDRATE, out_file=UartConfig.OUT_FILE, batch_size=UartConfig.BATCH_SIZE)
    uart.connect()
    # uart.send_waveform(filename=Path('data/dac_500kv_under_line_nT.bin'))
    # uart.send_waveform(filename=Path('data/dac_sine_7_uT.bin'))
    # uart.send_waveform(filename=Path('data/dac_sine_100.bin'))
    # uart.send_waveform(filename=Path('data/dac_dc.bin'))
    # uart.send_waveform(filename=Path('data/dac_sine.bin'))
    uart.send_waveform(filename=Path('data/dac_small_sine.bin'))
    # uart.send_waveform(filename=Path('data/dac_signal_odd_harmonics.bin'))
    # time.sleep(0.1)
    uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT, k=k)
    # uart.capture(record_seconds=1, waveform=Waveform.SQUARE_WAVE)
    # uart.capture(record_seconds=1, waveform=Waveform.SINE, k=k)
    # uart.capture(record_seconds=1, waveform=Waveform.SINE_ODD_HARMONICS)
    uart.close()

    adc = ADC(vcc=3.3, resolution_bits=16)
    data_reader = DataReader(filename=Path(UartConfig.OUT_FILE), adc=adc, freq=k*50)
    data_reader.read()
    # data_reader.plot_scatter(periods=2)
    # data_reader.plot_histogram()
    # data_reader.plot(periods=2)
    # data_reader.fft()
    data_reader.analyse_signal()

    data_reader.plot_scatter(periods=2, scale_to_v=True)
    data_reader.plot_histogram(scale_to_v=True)
    data_reader.plot(periods=2, scale_to_v=True)
    data_reader.fft(scale_to_v=True)
    data_reader.analyse_signal(scale_to_v=True)

    data_reader = DataReader(filename=uart.out_ref_file, adc=adc, freq=k*50)
    data_reader.read()
    data_reader.analyse_signal()

    data_reader.plot_scatter(periods=2, scale_to_v=True)
    data_reader.plot_histogram(scale_to_v=True)
    data_reader.plot(periods=2, scale_to_v=True)
    data_reader.fft(scale_to_v=True)
    data_reader.analyse_signal(scale_to_v=True)
