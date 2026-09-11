from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from calculations.converter import ADC

import serial
import struct
from pathlib import Path
import matplotlib.pyplot as plt


class Config:
    SERIAL_PORT = "COM3"
    BAUDRATE = 230400
    SAMPLING_RATE = 10e3
    FREQ = 50
    SAMPLES_PER_PERIOD = 10e3/FREQ
    N_BYTES = 400  # data sent in one burst
    RECORD_SECONDS = 5
    OUT_FILE = Path("data/uart_capture.bin")
    VCC = 3.3
    V_REF = VCC/2


class UART:
    def __init__(self, serial_port, baudrate, out_file, n_bytes=400, timeout=0.1):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.out_file = out_file
        self.n_bytes = n_bytes
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

    def capture(self, record_seconds):
        print(f"Recording for {record_seconds} seconds...")

        buffer = bytearray()
        with open(self.out_file, "wb") as f:
            start_packet = bytes([ord("S"), record_seconds])
            self.serial.write(start_packet)
            data = 1
            while data:
                data = self.serial.read(self.n_bytes - len(buffer))
                if data:
                    buffer.extend(data)

                if len(buffer) == self.n_bytes:
                    f.write(buffer)
                    buffer.clear()
        print("Capture complete.")


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


if __name__ == "__main__":
    uart = UART(serial_port=Config.SERIAL_PORT, baudrate=Config.BAUDRATE, out_file=Config.OUT_FILE, n_bytes=Config.N_BYTES)
    uart.connect()
    uart.capture(record_seconds=5)
    uart.close()

    data_reader = DataReader(filename=Path(Config.OUT_FILE))
    data_reader.read()
    data_reader.plot_scatter(periods=2)
    data_reader.plot_histogram()
    data_reader.plot(periods=1)
    data_reader.fft()
