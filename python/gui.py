from measurements.uart import UART, DataReader, Config, Waveform
from calculations.sensors import AD8429, ALT021, Sensor
from calculations.converter import ADC

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from pathlib import Path
import struct
import time


class ConfigGUI:
    SAMPLING_RATE = 10e3
    FREQ = 50
    PERIOD = 1/FREQ
    SAMPLES_PER_PERIOD = SAMPLING_RATE*PERIOD
    TIME_STEP = 1/SAMPLING_RATE
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2


class GUI:
    def __init__(self, uart: UART, adc: ADC, sensor: Sensor, ad8429: AD8429):
        self.root = tk.Tk()
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.uart = uart
        self.adc = adc
        self.sensor = sensor
        self.ad8429 = ad8429
        self.xdata, self.ydata = [], []
        self.line, = self.ax.plot([], [])
        self.t = 0.0
        self.ticks = 0

        self.xdata = np.linspace(0, 0.2, self.uart.batch_size)
        self.ax.set_xlim(0, 0.2)
        self.line, = self.ax.plot(self.xdata, np.zeros(self.uart.batch_size))

    def reset_graph(self):
        self.xdata, self.ydata = [], []
        self.ax.clear()
        self.line, = self.ax.plot([], [])
        self.canvas.draw()

    def run(self):
        self.root.mainloop()

    def capture(self, record_seconds, waveform):
        print(f"Recording for {record_seconds} seconds...")
        self.record_seconds = record_seconds
        self.waveform = waveform
        self.buffer = bytearray()

        # Set a timeout for when the capture is expected to finish (+1s margin for transmission)
        self.capture_end_time = time.time() + record_seconds + 1.0

        # Send the start packet
        start_packet = bytes([ord("S"), record_seconds, waveform.value])
        self.uart.serial.write(start_packet)

        # Start the non-blocking read/plot loop
        self.root.after(10, self.process_uart_data)

    def process_uart_data(self):
        # 'H' is a 2-byte unsigned short. 400 samples = 800 bytes per batch.
        target_bytes = self.uart.batch_size * 2
        bytes_needed = target_bytes - len(self.buffer)

        # 1. Read available data without blocking the GUI
        if self.uart.serial.in_waiting > 0:
            data = self.uart.serial.read(min(self.uart.serial.in_waiting, bytes_needed))
            if data:
                self.buffer.extend(data)

        # 2. If we have a full batch, unpack and plot it
        if len(self.buffer) == target_bytes:
            # Unpack exact bytes into tuple of 400 integers
            self.ydata = (np.array(struct.unpack(f">{self.uart.batch_size}H", self.buffer)) * self.adc.Lsb - self.ad8429.V_ref) / self.ad8429.G / self.sensor.S * 1e6
            # self.ydata = np.array(struct.unpack(f">{self.uart.batch_size}H", self.buffer)) * self.adc.Lsb

            # self.line.set_data(self.xdata, self.ydata)
            self.line.set_ydata(self.ydata)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()
            # self.canvas.draw()

            self.buffer.clear()

        # 3. Sequence control: Restart or continue polling
        if time.time() > self.capture_end_time and self.uart.serial.in_waiting == 0:
            print("Capture complete. Restarting sequence...")
            # Restart the capture command automatically
            self.root.after(100, lambda: self.capture(self.record_seconds, self.waveform))
        else:
            # Continue checking for data every 10ms
            self.root.after(10, self.process_uart_data)


if __name__ == '__main__':
    uart = UART(serial_port=Config.SERIAL_PORT, baudrate=Config.BAUDRATE, out_file=Config.OUT_FILE,
                # batch_size=Config.BATCH_SIZE
                batch_size = Config.BATCH_SIZE*2
                )
    uart.connect()
    # uart.send_waveform(Path("data/sine_AC_50uT_DC_20uT.bin"))

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=ConfigGUI.AD8429_VP, vs_negative=ConfigGUI.AD8429_VN, v_reference=adc.Vcc/2, gain=2)
    alt021 = ALT021(vcc=ConfigGUI.SENSOR_VCC)

    # uart.capture(record_seconds=5, waveform=Waveform.SINE)
    # adc = ADC(vcc=3.3, resolution_bits=16)
    # data_reader = DataReader(filename=Path(Config.OUT_FILE), adc=adc)
    # data_reader.read()
    # data_reader.plot(periods=2)
    # data_reader.plot(periods=2, scale_to_v=True)
    # data_reader.analyse_signal()
    # data_reader.analyse_signal(scale_to_v=True)

    gui = GUI(uart=uart, adc=adc, sensor=alt021, ad8429=ad8429_g2)
    # gui.capture(record_seconds=5, waveform=Waveform.SINE)
    gui.capture(record_seconds=5, waveform=Waveform.SINE_ODD_HARMONICS)
    gui.run()
