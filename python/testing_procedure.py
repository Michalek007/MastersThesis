from magnetic_field import MagneticFieldSignalGenerator
from signal_processing import SignalAnalyzer
from measurements.uart import UartConfig, UART, DataReader, Waveform
from calculations.helmholtz_coil import HelmholtzCoil, CurrentSource, DAC
from calculations.sensors import Sensor, ADC, AD8429, DRV425, DRV5055, ALT021, HMC1001
from measurements.signal_generator import Signal
from signal_processing import SignalProcessing
import time

from pathlib import Path


class Config:
    GENERATE_DATA = 0
    CAPTURE_DATA = 0
    PROCESS_DATA = 1

    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2

    SUT = "ALT021"
    # SUT = "DRV425"
    # SUT = "DRV5055"
    # SUT = "HMC1001"


if __name__ == '__main__':
    dac = DAC(vcc=3.3, resolution_bits=12, buffer_enabled=True)
    current_source = CurrentSource(R=7.5, dac=dac)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)

    mf_signal_generator = MagneticFieldSignalGenerator(
        B_1=10e-6, DAC_V_offset=0.1, harmonics_dict={1: 1.0},
        n_samples=1000, signal_type=Signal.SINE, filename=Path("data/sine_10_uT.bin"),
        helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    )

    b1_values_rms = [15e-6, 20e-6, 25e-6, 30e-6, 40e-6, 50e-6]
    names_tp1 = []
    for b1_rms in b1_values_rms:
        name = f"sine_{int(b1_rms*1e6)}_uT"
        names_tp1.append(name)
        if Config.GENERATE_DATA:
            mf_signal_generator.B_1 = b1_rms
            mf_signal_generator.filename = Path(f"data/{name}.bin")
            mf_signal_generator.generate()

    # helmholtz_coil.current_source.R_divider = 2
    # b1_values_rms_small = [1e-6, 3e-6, 5e-6, 7e-6, 10e-6]
    # for b1_rms in b1_values_rms_small:
    #     mf_signal_generator.B_1 = b1_rms
    #     mf_signal_generator.filename = Path(f"data/sine_{int(b1_rms*1e6)}_uT.bin")
    #     mf_signal_generator.generate()

    # test_signals_bandwidth = {
    #     1250: 1024,
    #     2500: 1024
    # }
    # mf_signal_generator.B_1 = 20e-6
    # mf_signal_generator.filename = Path(f"data/sine_d1_1_uT.bin")
    # mf_signal_generator.generate()
    #
    # current_source.R_divider = 2
    # mf_signal_generator.B_1 = 20e-6
    # mf_signal_generator.filename = Path(f"data/sine_d2_1_uT.bin")
    # mf_signal_generator.generate()

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30)

    alt021 = ALT021(vcc=Config.SENSOR_VCC)
    hmc1001 = HMC1001(vcc=Config.SENSOR_VCC)
    drv5055 = DRV5055(vcc=Config.SENSOR_VCC)
    drv425 = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)

    uart = UART(serial_port=UartConfig.SERIAL_PORT, baudrate=UartConfig.BAUDRATE, out_file=UartConfig.OUT_FILE,
                batch_size=UartConfig.BATCH_SIZE)

    if Config.CAPTURE_DATA:
        uart.connect()
        for name in names_tp1:
            dac_file = Path(f"data/dac_{name}.bin")
            out_file = Path(f"data/out_{Config.SUT}_{name}.bin")
            uart.out_file = out_file
            uart.send_waveform(dac_file)
            uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT)
            time.sleep(0.1)
        uart.close()

    if Config.PROCESS_DATA:
        for name in names_tp1:
            out_file = Path(f"data/out_{Config.SUT}_{name}.bin")
            data_reader = DataReader(filename=out_file, adc=adc)
            data_reader.read()
            data_reader.analyse_signal(scale_to_v=True)
            data_reader.plot_scatter(periods=2, scale_to_v=True)
            data_reader.plot_histogram(scale_to_v=True)
            data_reader.plot(periods=2, scale_to_v=True)
            data_reader.fft(scale_to_v=True)

            sp_alt021 = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429_g2)
            # sp_alt021.plot_v_adc()
            sp_alt021.plot_magnetic_field()
