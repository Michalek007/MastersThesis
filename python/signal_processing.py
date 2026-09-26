from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from measurements.uart import DataReader, UART, Waveform, UartConfig
from calculations.converter import ADC
from calculations.helmholtz_coil import DAC, CurrentSource, HelmholtzCoil
from calculations.sensors import Sensor, AD8429, ALT021, DRV425, DRV5055, HMC1001
from collections import defaultdict

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


class Config:
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2
    # DATA_FILE = "data/uart_capture.bin"
    # DATA_FILE = "data/uart_capture_20260911_2136.bin"
    # DATA_FILE = "data/uart_capture_dac_rx_0.bin"
    # DATA_FILE = "data/ad8429_in_0v.bin"
    # DATA_FILE = UartConfig.OUT_FILE
    DATA_FILE = Path('data/out_ALT021_sine_40_uT.bin')


class SignalProcessing:
    def __init__(self, dac_values, adc: ADC, sensor: Sensor, ad8429: AD8429, out_name=None, out_dir=None, helmholtz_coil: HelmholtzCoil = None, freq=50):
        self.dac_values = np.array(dac_values, dtype=np.float64)
        self.offset = np.mean(self.dac_values)
        self.n_samples = len(dac_values)
        self.t = [i * UartConfig.TIME_STEP for i in range(self.n_samples)]
        self.adc = adc
        self.sensor = sensor
        self.ad8429 = ad8429
        self.fft = FFT(signal=self.dac_values, sampling_rate=UartConfig.SAMPLING_RATE, remove_offset=True)
        self.fft.calculate()
        self.fft.get_harmonic_amplitudes(fundamental_freq=50, max_freq=2500, snr_threshold=3.0)
        self.fft.harmonics_amp = self.calculate_IEEE_harmonics()
        self.signal_analyser = SignalAnalyzer(signal=self.dac_values)
        self.name = out_name
        self.out_dir = out_dir if out_dir else "results"

        self.helmholtz_coil = helmholtz_coil
        self.freq = freq
        self.samples_per_period = UartConfig.SAMPLING_RATE / self.freq

    def calculate_IEEE_harmonics(self):
        iterations = self.n_samples // 2000
        fft_harmonics = []
        for i in range(iterations):
            fft = FFT(signal=self.dac_values[i*2000:(i+1)*2000], sampling_rate=UartConfig.SAMPLING_RATE, remove_offset=True)
            fft.calculate()
            fft.get_harmonic_amplitudes(fundamental_freq=50, max_freq=2500, snr_threshold=3.0)
            fft_harmonics.append(fft.harmonics_amp)

        result_harmonics = []
        for harmonic_group in zip(*fft_harmonics):
            result_harmonics.append({
                'harmonic': harmonic_group[0]['harmonic'],
                'frequency': harmonic_group[0]['frequency'],
                'rms': np.mean([h['rms'] for h in harmonic_group]),
                'phase': np.mean([h['phase'] for h in harmonic_group])
            })
        return result_harmonics

    @property
    def helmholtz_coil_B_uT_factor(self):
        return self.adc.Lsb * self.helmholtz_coil.current_source.I_S * self.helmholtz_coil.B_S * 1e6

    @property
    def helmholtz_coil_I_mA_factor(self):
        return self.adc.Lsb * self.helmholtz_coil.current_source.I_S * 1e3

    @property
    def sensor_B_uT_factor(self):
        return self.adc.Lsb / self.ad8429.G / self.sensor.S * 1e6

    @property
    def sensor_V_mV_factor(self):
        return self.adc.Lsb / self.ad8429.G * 1e3

    def plot(self, title, y_scale=1, periods: int = 5, y_label = "Amplitude", offset_calibration=0, save=False, filename='graph'):
        plt.figure()
        plt.plot(self.t[0:int(self.samples_per_period *periods)], (self.dac_values[0:int(self.samples_per_period *periods)]-offset_calibration) * y_scale)
        plt.title(title)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.tight_layout()
        if save:
            plt.savefig(f'{self.out_dir}/graphs/{filename}.png', dpi=500)
        else:
            plt.show()

    def plot_v_sensor(self):
        factor = self.sensor_V_mV_factor
        self.plot(title="Napięcie od czasu na wyjściu czujnika", y_scale=factor, offset_calibration=self.offset, y_label="Napięcie [mV]")
        self.fft.plot_fft(y_scale=factor, x_lim=2500, y_label="Napięcie [mV]"
                          # , filename=Path(f"results/graphs/{self.name}_fft_Vadc_mV.png")
                         )
        self.fft.print_harmonic_amplitudes(amp_scale=factor, filename=Path(f"{self.out_dir}/{self.name}_harmonics_Vsensor_mV.csv"))
        self.signal_analyser.print_parameters(scale=factor, filename=Path(f"{self.out_dir}/{self.name}_Vsensor_mV.csv"))

    def plot_v_adc(self):
        factor = self.adc.Lsb * 1e3
        self.plot(title="Napięcie od czasu przetwornika A/C", y_scale=factor, y_label="Napięcie [mV]")
        self.fft.plot_fft(y_scale=factor, x_lim=2500, y_label="Napięcie [mV]"
                          # , filename=Path(f"results/graphs/{self.name}_fft_Vadc_mV.png")
                         )
        self.fft.print_harmonic_amplitudes(amp_scale=factor, filename=Path(f"{self.out_dir}/{self.name}_harmonics_Vadc_mV.csv"))
        self.signal_analyser.print_parameters(scale=factor, filename=Path(f"{self.out_dir}/{self.name}_Vadc_mV.csv"))

    def plot_current(self):
        if not self.helmholtz_coil:
            raise ValueError("You need to provide HelmholtzCoil object to calculate current!")
        factor = self.helmholtz_coil_I_mA_factor
        self.plot(title="Nateżenie prądu od czasu cewki Helmholtza", y_scale=factor, y_label="Natężenie prądu [mA]")
        self.fft.plot_fft(y_scale=factor, x_lim=2500, y_label="Natężenie prądu [mA]"
                          # , filename=Path(f"results/graphs/{self.name}_fft_I_mA.png")
                          )
        self.fft.print_harmonic_amplitudes(amp_scale=factor, filename=Path(f"{self.out_dir}/{self.name}_harmonics_I_mA.csv"))
        self.signal_analyser.print_parameters(scale=factor, filename=Path(f"{self.out_dir}/{self.name}_I_mA.csv"))

    def plot_magnetic_field(self):
        # offset = np.average(self.dac_values)
        if self.helmholtz_coil:
            factor = self.helmholtz_coil_B_uT_factor
        else:
            factor = self.sensor_B_uT_factor
        self.plot(title="Pole magnetyczne od czasu", y_scale=factor, y_label="Pole magnetyczne [μT]", offset_calibration=self.offset, save=True, filename=f"{self.name}_B_uT")
        # fft = FFT(signal=self.dac_values-offset, sampling_rate=Config.SAMPLING_RATE)
        # fft.calculate()
        self.fft.plot_fft(y_scale=factor, y_label="Pole magnetyczne [μT]", x_lim=2500, filename=Path(f"{self.out_dir}/graphs/{self.name}_fft_B_uT.png"))
        # self.fft.get_harmonic_amplitudes(f0=50)
        self.fft.print_harmonic_amplitudes(amp_scale=factor, filename=Path(f"{self.out_dir}/{self.name}_harmonics_B_uT.csv"))
        SignalAnalyzer(signal=self.dac_values-self.offset).print_parameters(scale=factor, filename=Path(f"{self.out_dir}/{self.name}_B_uT.csv"))

    def plot_magnetic_field_dc(self):
        pass
        # ad8429_offset = self.adc.Value(Config.AD8429_V_REF)
        # self.plot(title="Pole magnetyczne od czasu z DC", y_scale=factor, y_label="Pole magnetyczne [μT]", offset_calibration=ad8429_offset)
        # fft = FFT(signal=self.dac_values-ad8429_offset, sampling_rate=Config.SAMPLING_RATE)
        # fft.calculate()
        # fft.plot_fft(y_scale=factor)
        # SignalAnalyzer(self.dac_values-ad8429_offset).print_parameters(scale=factor)

    def calculate_magnetic_filed_harmonics(self):
        if self.helmholtz_coil:
            factor = self.helmholtz_coil_B_uT_factor
        else:
            factor = self.sensor_B_uT_factor
        # fft = FFT(signal=self.dac_values, sampling_rate=UartConfig.SAMPLING_RATE, remove_offset=True)
        # fft.calculate()
        # fft.get_harmonic_amplitudes(f0=50)
        self.fft.plot_fft(y_scale=factor, y_label="Pole magnetyczne [μT]", x_lim=2500)
        self.fft.print_harmonic_amplitudes(amp_scale=factor, filename=Path(f"{self.out_dir}/{self.name}_harmonics_B_uT.csv"))


if __name__ == '__main__':
    UART_CAPTURE = 1

    uart = UART(serial_port=UartConfig.SERIAL_PORT, baudrate=UartConfig.BAUDRATE, out_file=UartConfig.OUT_FILE,
                batch_size=UartConfig.BATCH_SIZE)
    if UART_CAPTURE:
        uart.connect()

        # uart.send_waveform(filename=Path('in/dac_sine_0_uT_RD1.bin'))
        # uart.send_waveform(filename=Path('in/dac_sine_3_uT_RD1.bin'))
        uart.send_waveform(filename=Path('in/dac_sine_20_uT_RD1.bin'))
        # uart.send_waveform(filename=Path('in/harmonic_7_5uT_220kV.bin'))
        # uart.send_waveform(filename=Path('in/dac_harmonic_22uT_400kV.bin'))
        # uart.send_waveform(filename=Path('in/dac_harmonic_22uT_220kV.bin'))
        # uart.send_waveform(filename=Path('in/dac_harmonic_22uT_500kV.bin'))
        # uart.send_waveform(filename=Path('in/dac_harmonic_22uT_THD29.bin'))
        # uart.send_waveform(filename=Path('data/dac_sine_50_uT.bin'))
        # uart.send_waveform(filename=Path('data/dac_dc_50ut.bin'))

        uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT, k=1)
        # uart.capture(record_seconds=1, waveform=Waveform.SINE)
        # uart.capture(record_seconds=1, waveform=Waveform.SINE_ODD_HARMONICS)
        # uart.capture(record_seconds=5, waveform=Waveform.SQUARE_WAVE)
        uart.close()

    adc = ADC(vcc=3.3, resolution_bits=16)
    data_reader = DataReader(filename=uart.out_file, adc=adc)
    data_reader.read()
    data_reader.analyse_signal()
    # data_reader.plot_scatter(periods=2)
    # data_reader.plot_histogram()
    # data_reader.plot(periods=2)
    # data_reader.fft()
    data_reader.analyse_signal(scale_to_v=True)
    data_reader.plot_scatter(periods=2, scale_to_v=True)
    data_reader.plot_histogram(scale_to_v=True)
    data_reader.plot(periods=2, scale_to_v=True)
    data_reader.fft(scale_to_v=True)

    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30, Rg=212.26)
    print(ad8429_g30.G)

    alt021 = ALT021(vcc=Config.SENSOR_VCC)
    hmc1001 = HMC1001(vcc=Config.SENSOR_VCC)
    drv5055 = DRV5055(vcc=Config.SENSOR_VCC)
    drv425 = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)

    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=hmc1001, ad8429=ad8429_g30, out_name="TEST_HMC1001")
    sp.plot_magnetic_field()
    # sp_alt021.plot_v_sensor()

    dac = DAC(vcc=3.3, resolution_bits=12, buffer_enabled=True)
    current_source = CurrentSource(R=7.5, dac=dac)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    # current_source.R_divider = 2

    data_reader = DataReader(filename=uart.out_ref_file, adc=adc)
    data_reader.read()
    data_reader.plot(periods=2, scale_to_v=True)
    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=hmc1001, ad8429=ad8429_g30, out_name="TEST_H_COIL", helmholtz_coil=helmholtz_coil)
    sp.plot_current()
    sp.plot_magnetic_field()

    # sp_hmc1001 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=hmc1001, ad8429=ad8429_g30)
    # sp_hmc1001.plot_v_adc()
    # sp_hmc1001.plot_magnetic_field()

    # sp_drv5055 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=drv5055, ad8429=ad8429_g30)
    # sp_drv5055.plot_v_adc()
    # sp_drv5055.plot_magnetic_field()

    # sp_drv425 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=drv425, ad8429=ad8429_g2)
    # sp_drv425.plot_v_adc()
    # sp_drv425.plot_magnetic_field()
