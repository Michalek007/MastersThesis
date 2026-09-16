from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from measurements.uart import DataReader, UART, Waveform
from calculations.converter import ADC
from calculations.helmholtz_coil import DAC, CurrentSource, HelmholtzCoil
from calculations.sensors import Sensor, AD8429, ALT021, DRV425, DRV5055, HMC1001

from pathlib import Path
import struct
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class Config:
    SAMPLING_RATE = 10e3
    FREQ = 50
    PERIOD = 1/FREQ
    SAMPLES_PER_PERIOD = SAMPLING_RATE*PERIOD
    TIME_STEP = 1/SAMPLING_RATE
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2
    # DATA_FILE = "data/uart_capture.bin"
    # DATA_FILE = "data/uart_capture_20260911_2136.bin"
    # DATA_FILE = "data/uart_capture_dac_rx_0.bin"
    # DATA_FILE = "data/ad8429_in_0v.bin"
    # DATA_FILE = "data/"
    # DATA_FILE = "data/"
    # DATA_FILE = "data/"
    SERIAL_PORT = "COM3"
    BAUDRATE = 230400
    OUT_FILE = Path(f"data/uart_capture_{datetime.now().strftime('%Y%m%d_%H%M')}.bin")
    DATA_FILE = OUT_FILE
    BATCH_SIZE = 400


class SignalProcessing:
    def __init__(self, dac_values, adc: ADC, sensor: Sensor, ad8429: AD8429):
        self.dac_values = np.array(dac_values, dtype=np.float64)
        self.n_samples = len(dac_values)
        self.t = [i * Config.TIME_STEP for i in range(self.n_samples)]
        self.adc = adc
        self.sensor = sensor
        self.ad8429 = ad8429
        self.fft = FFT(signal=self.dac_values, sampling_rate=Config.SAMPLING_RATE, remove_offset=True)
        self.fft.calculate()
        self.fft.get_harmonic_amplitudes(f0=50, num_harmonics=50)
        self.signal_analyser = SignalAnalyzer(signal=self.dac_values)

    def plot(self, title, y_scale = 1, periods: int = 5, y_label = "Amplitude", offset_calibration=0, save=False, filename='graph'):
        plt.figure()
        plt.plot(self.t[0:int(Config.SAMPLES_PER_PERIOD*periods)], (self.dac_values[0:int(Config.SAMPLES_PER_PERIOD*periods)]-offset_calibration) * y_scale)
        plt.title(title)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.tight_layout()
        if save:
            plt.savefig(f'graphs/{filename}.png', dpi=500)
        else:
            plt.show()

    def plot_v_adc(self):
        self.plot(title="Napięcie od czasu przetwornika A/C", y_scale=adc.Lsb, y_label="Napięcie [V]")
        self.fft.plot_fft(y_scale=adc.Lsb)
        # self.fft.print_harmonic_amplitudes(amp_scale=adc.Lsb)
        self.signal_analyser.print_parameters(scale=adc.Lsb)

    def plot_magnetic_field(self):
        offset = np.average(self.dac_values)
        factor = adc.Lsb / self.ad8429.G / self.sensor.S * 1e6
        self.plot(title="Pole magnetyczne od czasu z usuniętą składową stałą", y_scale=factor, y_label="Pole magnetycze [uT]", offset_calibration=offset)
        fft = FFT(signal=self.dac_values-offset, sampling_rate=Config.SAMPLING_RATE)
        fft.calculate()
        fft.plot_fft(y_scale=factor)
        SignalAnalyzer(signal=self.dac_values-offset).print_parameters(scale=factor)

        ad8429_offset = self.adc.Value(Config.AD8429_V_REF)
        self.plot(title="Pole magnetyczne od czasu", y_scale=factor, y_label="Pole magnetycze [uT]", offset_calibration=ad8429_offset)
        fft = FFT(signal=self.dac_values-ad8429_offset, sampling_rate=Config.SAMPLING_RATE)
        fft.calculate()
        fft.plot_fft(y_scale=factor)
        SignalAnalyzer(self.dac_values-ad8429_offset).print_parameters(scale=factor)


if __name__ == '__main__':
    uart = UART(serial_port=Config.SERIAL_PORT, baudrate=Config.BAUDRATE, out_file=Config.OUT_FILE, batch_size=Config.BATCH_SIZE)
    uart.connect()
    # uart.send_waveform(filename=Path('data/dac_dc_50ut.bin'))
    # uart.send_waveform(filename=Path('data/dac_sine_AC_1uT_DC_50uT.bin'))
    # uart.send_waveform(filename=Path('data/sine_AC_50uT_DC_100uT.bin'))
    # uart.send_waveform(filename=Path('data/dac_500kv_under_line_nT.bin'))

    # uart.send_waveform(filename=Path('data/triangular_AC_50uT_DC_20uT.bin'))
    # uart.capture(record_seconds=5, waveform=Waveform.LAST_SENT)
    # uart.capture(record_seconds=5, waveform=Waveform.SINE)
    uart.capture(record_seconds=5, waveform=Waveform.SINE_ODD_HARMONICS)
    # uart.capture(record_seconds=5, waveform=Waveform.SQUARE_WAVE)
    uart.close()

    data_reader = DataReader(filename=Path(Config.DATA_FILE))
    data_reader.read()
    data_reader.analyse_signal()
    data_reader.plot_scatter(periods=2)
    data_reader.plot_histogram()
    data_reader.plot(periods=2)
    data_reader.fft()

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30)

    alt021 = ALT021(vcc=Config.SENSOR_VCC)
    hmc1001 = HMC1001(vcc=Config.SENSOR_VCC)
    drv5055 = DRV5055(vcc=Config.SENSOR_VCC)
    drv425 = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)

    sp_alt021 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429_g2)
    sp_alt021.plot_v_adc()
    sp_alt021.plot_magnetic_field()

    # sp_hmc1001 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=hmc1001, ad8429=ad8429_g30)
    # sp_hmc1001.plot_v_adc()
    # sp_hmc1001.plot_magnetic_field()

    # sp_drv5055 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=drv5055, ad8429=ad8429_g30)
    # sp_drv5055.plot_v_adc()
    # sp_drv5055.plot_magnetic_field()

    # sp_drv425 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=drv425, ad8429=ad8429_g2)
    # sp_drv425.plot_v_adc()
    # sp_drv425.plot_magnetic_field()
