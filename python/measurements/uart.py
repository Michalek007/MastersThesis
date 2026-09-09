import serial
import struct
import time
import matplotlib.pyplot as plt
from pathlib import Path


SERIAL_PORT = "COM3"
BAUDRATE = 230400
N_BYTES = 400
TIMEOUT = 0.1
RECORD_SECONDS = 5
OUT_FILE = Path("data/uart_capture.bin")

MAX_ADC_VALUE = 2 ** 16 - 1
VCC = 3.3
V_REF = VCC/2


if N_BYTES % 2 != 0:
    raise ValueError("N_BYTES must be even (uint16 conversion)")


def capture_uart():
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        timeout=TIMEOUT,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    )

    print(f"Opened {SERIAL_PORT} @ {BAUDRATE} baud")
    print(f"Recording for {RECORD_SECONDS} seconds...")

    buffer = bytearray()
    # start_time = time.time()

    with open(OUT_FILE, "wb") as f:
        start_packet = bytes([ord("S"), RECORD_SECONDS])
        ser.write(start_packet)
        data = 1
        while data:
            data = ser.read(N_BYTES - len(buffer))
            if data:
                buffer.extend(data)

            if len(buffer) == N_BYTES:
                f.write(buffer)
                buffer.clear()
        # while time.time() - start_time < RECORD_SECONDS:
        #     data = ser.read(N_BYTES - len(buffer))
        #     if not data:
        #         continue
        #
        #     buffer.extend(data)
        #
        #     if len(buffer) == N_BYTES:
        #         f.write(buffer)
        #         buffer.clear()

    ser.close()
    print("Capture complete.")


def read_and_plot():
    with open(OUT_FILE, "rb") as f:
        raw = f.read()

    count = len(raw) // 2
    values = struct.unpack(f">{count}H", raw)
    # values = struct.unpack(f">{count}h", raw)
    x = [i for i in range(count)]

    print(f"Loaded {count} samples")

    plt.figure()
    plt.scatter(x[0:count//20], values[0:count//20], s=0.5)
    plt.title("UART Capture")
    plt.xlabel("Sample index")
    plt.ylabel("Value (uint16)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.figure()
    plt.hist(values, bins=100)
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title("Histogram of Variable Values")
    plt.show()

    vadc_values = []
    for i in range(len(values)):
        vadc_values.append(values[i]*VCC/MAX_ADC_VALUE)

    # plt.figure(figsize=(12, 5), dpi=500)
    plt.scatter(x[0:count//20], vadc_values[0:count//20], s=0.5)
    plt.title("Measured voltage")
    plt.xlabel("Sample index")
    plt.ylabel("Vadc [V]")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.scatter(x[0:count//100], vadc_values[0:count//100], s=0.5)
    plt.title("Measured voltage")
    plt.xlabel("Sample index")
    plt.ylabel("Vadc [V]")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.plot(x[0:count//100], vadc_values[0:count//100])
    plt.title("Measured voltage")
    plt.xlabel("Sample index")
    plt.ylabel("Vadc [V]")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # capture_uart()
    read_and_plot()
