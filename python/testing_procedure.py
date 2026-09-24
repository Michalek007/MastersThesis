from magnetic_field import MagneticFieldSignalGenerator
from signal_processing import SignalAnalyzer
from measurements.uart import UartConfig, UART, DataReader, Waveform
from calculations.helmholtz_coil import HelmholtzCoil, CurrentSource, DAC, HelmholtzCoilReal
from calculations.sensors import Sensor, ADC, AD8429, DRV425, DRV5055, ALT021, HMC1001
from measurements.signal_generator import Signal
from signal_processing import SignalProcessing
import time
from harmonic_data import *

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

    # ALL_SIGNALS = 1
    LOW_SIGNALS = 1

    GAIN = "2"
    # GAIN = "30"

    R_DIVIDER = "1"
    # R_DIVIDER = "2"

    # TEST_PROCEDURE = "TP0"
    TEST_PROCEDURE = "TP1"
    # TEST_PROCEDURE = "TP2"
    # TEST_PROCEDURE = "TP3"


if __name__ == '__main__':
    dac = DAC(vcc=3.3, resolution_bits=12, buffer_enabled=True)
    current_source = CurrentSource(R=7.5, dac=dac)
    if Config.R_DIVIDER == "2":
        current_source.R_divider = 2
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    # helmholtz_coil = HelmholtzCoilReal(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source, B_S=0.5176*1e-6/1e-3)

    mf_signal_generator = MagneticFieldSignalGenerator(
        B_1=10e-6, DAC_V_offset=0.1, harmonics_dict={1: 1.0},
        n_samples=1000, signal_type=Signal.SINE, filename=Path(f"data/sine_10_uT_{Config.R_DIVIDER}.bin"),
        helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    )
    if Config.LOW_SIGNALS:
        # b1_values_rms = [0.5e-6, 1e-6, 3e-6, 5e-6, 7e-6, 10e-6]
        b1_values_rms = [0.5e-6, 1e-6, 3e-6, 5e-6, 7e-6, 10e-6, 15e-6, 20e-6, 25e-6, 30e-6, 35e-6, 40e-6, 45e-6]
    else:
        b1_values_rms = [15e-6, 20e-6, 25e-6, 30e-6, 35e-6, 40e-6, 45e-6, 50e-6, 55e-6, 60e-6]

    names_tp1 = []
    for b1_rms in b1_values_rms:
        name = f"sine_{int(b1_rms*1e6)}_uT_RD{Config.R_DIVIDER}"
        names_tp1.append(name)
        if Config.GENERATE_DATA and Config.TEST_PROCEDURE == "TP1":
            mf_signal_generator.B_1 = b1_rms
            mf_signal_generator.filename = Path(f"in/{name}.bin")
            mf_signal_generator.generate()

    if Config.LOW_SIGNALS:
        names_tp2 = [f"sine_1_uT_RD{Config.R_DIVIDER}", f"sine_5_uT_RD{Config.R_DIVIDER}", f"sine_10_uT_RD{Config.R_DIVIDER}"]
    else:
        names_tp2 = [f"sine_15_uT_RD{Config.R_DIVIDER}", f"sine_20_uT_RD{Config.R_DIVIDER}", f"sine_50_uT_RD{Config.R_DIVIDER}"]
    k_values = [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]

    if Config.LOW_SIGNALS:
        tp3_b1_values_rms = {"7_5uT": harmonic_500kv_under_line_nT[1] * 1e-9, "1_9uT": harmonic_35kV_300A[1] * 1e-6,
                             "1_8uT": harmonic_220kv_nT[1] * 1e-9}
    else:
        tp3_b1_values_rms = {"22uT": harmonics_110kV_700A_uT[1] * 1e-6, "19uT": harmonic_400kV_1kA_10m_uT[1] * 1e-6,
                             "13uT": harmonic_400kV_2t_1kA_10m_uT[1] * 1e-6}
    harmonics_data_dicts = {"500kV": harmonic_500kv_under_line_nT, "220kV": harmonic_220kv_nT, "400kV": harmonic_400kV_1_8kA_IV, "THD29": harmonic_typical_values}
    names_tp3 = []
    for value_name, value in tp3_b1_values_rms.items():
        for harmonic_name, harmonics_data in harmonics_data_dicts.items():
            name = f"harmonic_{value_name}_{harmonic_name}_RD{Config.R_DIVIDER}"
            names_tp3.append(name)
            mf_signal_generator.filename = Path(f"in/{name}.bin")

            if Config.GENERATE_DATA and Config.TEST_PROCEDURE == "TP3":
                mf_signal_generator.B_1 = value
                mf_signal_generator.harmonics_dict = harmonics_data
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
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2, Rg=6.04e3)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30, Rg=212.26)

    alt021 = ALT021(vcc=Config.SENSOR_VCC)
    hmc1001 = HMC1001(vcc=Config.SENSOR_VCC)
    drv5055 = DRV5055(vcc=Config.SENSOR_VCC)
    drv425 = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)

    sensor = alt021
    ad8429 = ad8429_g2
    if Config.SUT == "ALT021":
        sensor = alt021
        ad8429 = ad8429_g2
        if Config.GAIN == "30":
            ad8429 = ad8429_g30
    elif Config.SUT == "DRV425":
        sensor = drv425
        ad8429 = ad8429_g2
        # if Config.LOW_SIGNALS:
        #     ad8429 = ad8429_g30
    elif Config.SUT == "HMC1001":
        sensor = hmc1001
        ad8429 = ad8429_g30
    else:
        sensor = drv5055
        ad8429 = ad8429_g30

    uart = UART(serial_port=UartConfig.SERIAL_PORT, baudrate=UartConfig.BAUDRATE, out_file=UartConfig.OUT_FILE,
                batch_size=UartConfig.BATCH_SIZE)

    if Config.CAPTURE_DATA:
        uart.connect()
        if Config.TEST_PROCEDURE == "TP1":
            for name in names_tp1:
                dac_file = Path(f"in/dac_{name}.bin")
                out_file = Path(f"out/out_{Config.SUT}_{name}.bin")
                out_ref_file = Path(f"out/out_{Config.SUT}_{name}_ref.bin")
                uart.out_file = out_file
                uart.out_ref_file = out_ref_file
                uart.send_waveform(dac_file)
                uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT)
                time.sleep(2)
        elif Config.TEST_PROCEDURE == "TP2":
            for name in names_tp2:
                for k in k_values:
                    dac_file = Path(f"in/dac_{name}.bin")
                    out_file = Path(f"out/out_{Config.SUT}_{name}_k{k}.bin")
                    out_ref_file = Path(f"out/out_{Config.SUT}_{name}_k{k}_ref.bin")
                    uart.out_file = out_file
                    uart.out_ref_file = out_ref_file
                    uart.send_waveform(dac_file)
                    uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT, k=k)
                    time.sleep(2)
        if Config.TEST_PROCEDURE == "TP3":
            for name in names_tp3:
                dac_file = Path(f"in/dac_{name}.bin")
                out_file = Path(f"out/out_{Config.SUT}_{name}.bin")
                out_ref_file = Path(f"out/out_{Config.SUT}_{name}_ref.bin")
                uart.out_file = out_file
                uart.out_ref_file = out_ref_file
                uart.send_waveform(dac_file)
                uart.capture(record_seconds=1, waveform=Waveform.LAST_SENT)
                time.sleep(2)
        uart.close()

    if Config.PROCESS_DATA:
        if Config.TEST_PROCEDURE == "TP1":
            meas_files = []
            meas_harmonic_files = []
            ref_harmonic_files = []
            ref_files = []
            for name in names_tp1:
                ref_files.append(Path(f"results/{Config.SUT}_{name}_ref_I_mA.csv"))
                ref_harmonic_files.append(Path(f"results/{Config.SUT}_{name}_ref_harmonics_I_mA.csv"))

                meas_files.append(Path(f"results/{Config.SUT}_{name}_B_uT.csv"))
                meas_harmonic_files.append(Path(f"results/{Config.SUT}_{name}_harmonics_B_uT.csv"))

                out_file = Path(f"out/out_{Config.SUT}_{name}.bin")
                data_reader = DataReader(filename=out_file, adc=adc)
                data_reader.read()

                out_ref_file = Path(f"out/out_{Config.SUT}_{name}_ref.bin")
                data_reader_ref = DataReader(filename=out_ref_file, adc=adc)
                data_reader_ref.read()

                # data_reader.analyse_signal(scale_to_v=True)
                # data_reader.plot_scatter(periods=2, scale_to_v=True)
                # data_reader.plot_histogram(scale_to_v=True)
                # data_reader.plot(periods=2, scale_to_v=True)
                # data_reader.fft(scale_to_v=True)

                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429, out_name=f"{Config.SUT}_{name}")
                sp.plot_magnetic_field()
                sp.plot_v_sensor()

                sp_ref = SignalProcessing(dac_values=data_reader_ref.values, adc=adc, sensor=sensor, ad8429=ad8429, out_name=f"{Config.SUT}_{name}_ref", helmholtz_coil=helmholtz_coil)
                sp_ref.plot_magnetic_field()
                sp_ref.plot_current()

            from calculate_sensor_parameters import CalculateSensorParams
            sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files,
                                           harmonics_files=meas_harmonic_files, ref_harmonics_files=ref_harmonic_files)
            params = sensor.calculate_params()
            sensor.plot_graphs(y_label="Pole magnetyczne zmierzone przez czujnik RMS [uT]", x_label="Prąd płynący przez cewkę [mA]")

        elif Config.TEST_PROCEDURE == "TP2":
            for name in names_tp2:
                for k in k_values:
                    out_file = Path(f"out/out_{Config.SUT}_{name}_k{k}.bin")
                    out_file_ref = Path(f"out/out_{Config.SUT}_{name}_k{k}_ref.bin")
                    data_reader = DataReader(filename=out_file, adc=adc, freq=k*50)
                    data_reader.read()
                    data_reader.analyse_signal(scale_to_v=True)
                    data_reader.fft(scale_to_v=True)
                    # data_reader.plot_scatter(periods=2, scale_to_v=True)
                    # data_reader.plot_histogram(scale_to_v=True)
                    # data_reader.plot(periods=2, scale_to_v=True)
                    data_reader_ref = DataReader(filename=out_file_ref, adc=adc)
                    data_reader_ref.read()

                    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429_g2,
                                                 out_name=f"{Config.SUT}_{name}_k{k}")
                    sp.calculate_magnetic_filed_harmonics()
                    # # sp.plot_v_adc()
                    # sp.plot_magnetic_field()
                    sp_ref = SignalProcessing(dac_values=data_reader_ref.values, adc=adc, sensor=alt021, ad8429=ad8429_g2,
                                                 out_name=f"{Config.SUT}_{name}_k{k}_ref", helmholtz_coil=helmholtz_coil)
                    sp_ref.calculate_magnetic_filed_harmonics()
        elif Config.TEST_PROCEDURE == "TP3":
            for name in names_tp3:
                out_file = Path(f"out/out_{Config.SUT}_{name}.bin")
                data_reader = DataReader(filename=out_file, adc=adc)
                data_reader.read()

                out_ref_file = Path(f"out/out_{Config.SUT}_{name}_ref.bin")
                data_reader_ref = DataReader(filename=out_ref_file, adc=adc)
                data_reader_ref.read()

                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429,
                                      out_name=f"{Config.SUT}_{name}")
                sp.plot_magnetic_field()
                sp.plot_v_sensor()

                sp_ref = SignalProcessing(dac_values=data_reader_ref.values, adc=adc, sensor=sensor,
                                          ad8429=ad8429, out_name=f"{Config.SUT}_{name}_ref",
                                          helmholtz_coil=helmholtz_coil)
                sp_ref.plot_magnetic_field()
                sp_ref.plot_current()
