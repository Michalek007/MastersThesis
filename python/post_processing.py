from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from signal_processing import SignalProcessing
from measurements.uart import DataReader, UART, Waveform, UartConfig
from calculations.converter import ADC
from calculations.helmholtz_coil import DAC, CurrentSource, HelmholtzCoil, HelmholtzCoilReal
from calculations.sensors import Sensor, AD8429, ALT021, DRV425, DRV5055, HMC1001
from calculate_sensor_parameters import CalculateSensorParams
from calculate_bandwidth import SensorBodeAnalyzer
from signal_validator import SignalValidator
from calculate_noise import NoiseAnalyzer


from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


class Config:
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2
    # SUT = "ALT021"
    # SUT = "HMC1001"
    SUT = "DRV425"
    # PARENT_DIR = Path(f"final/{SUT}/TP3/")
    PARENT_DIR = Path(f"final/{SUT}/")
    RESULTS_DIR = Path(f"{PARENT_DIR}/RESULTS")
    OUT_DIR = Path(f"{PARENT_DIR}/OUT")
    # OUT_K_DIR = Path(f"{OUT_DIR}/K")
    OUT_K_DIR = Path(f"{OUT_DIR}")
    IN_DIR = Path(f"/in/")

    CALIBRATION = 1
    CALIBRATION_N = 4
    if CALIBRATION_N == 2:
        OUT_DIR = Path(f"{PARENT_DIR}/OUT/2")
    elif CALIBRATION_N == 3:
        OUT_DIR = Path(f"{PARENT_DIR}/OUT/3")
    elif CALIBRATION_N == 3:
        OUT_DIR = Path(f"{PARENT_DIR}/OUT/4")
    TEST_PROCEDURE = "TP1"
    # TEST_PROCEDURE = "TP1"
    # TEST_PROCEDURE = "TP2"
    # TEST_PROCEDURE = "TP3"

    GENERATE_DATA = 1
    PROCESS_DATA = 1
    # BS = ""
    # BS = "_BS354"
    # BS = "_BS473"
    BS = "_BS467"

    RD = "RD1"

    R = 8.55/100

    kB = None
    S = None


def get_sut_name(b_value):
    return f"{Config.SUT}_sine_{int(b_value)}_uT_RD1{Config.BS}"
def get_units_str(units="magnetic"):
    if units == "magnetic":
        units_str = "B_uT"
    elif units == "current":
        units_str = "I_mA"
    elif units == "voltage_adc":
        units_str = "Vadc_V"
    else:
        units_str = "Vsensor_mV"
    return units_str
def get_out_file(b_value):
    return f"{Config.OUT_DIR}/out_{get_sut_name(b_value)}.bin"
def get_out_ref_file(b_value):
    return f"{Config.OUT_DIR}/out_{get_sut_name(b_value)}_ref.bin"

def get_data_file(b_value, ref=False, units="magnetic", harmonics=False):
    harmonic_str = "_harmonics" if harmonics else ""
    if ref:
        return f"{Config.RESULTS_DIR}/{get_sut_name(b_value)}_ref{harmonic_str}_{get_units_str(units)}.csv"
    else:
        return f"{Config.RESULTS_DIR}/{get_sut_name(b_value)}{harmonic_str}_{get_units_str(units)}.csv"


if __name__ == '__main__':
    dac = DAC(vcc=3.3, resolution_bits=12, buffer_enabled=True)
    current_source = CurrentSource(R=7.5, dac=dac)
    if Config.RD == "RD2":
        current_source.R_divider = 2
    helmholtz_coil_ideal = HelmholtzCoil(n=45, R=Config.R, current_source=current_source)
    if Config.BS == "_BS354":
        helmholtz_coil = HelmholtzCoilReal(n=45, R=Config.R, current_source=current_source,
                                           B_S=helmholtz_coil_ideal.B_S * 0.75)
    else:
        helmholtz_coil = helmholtz_coil_ideal
    # helmholtz_coil = HelmholtzCoilReal(n=45, R=Config.R, current_source=current_source, B_S=0.5176*1e-6/1e-3)

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2, Rg=6.04e3)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30, Rg=212.26)
    ad8429 = ad8429_g2

    sensor = Sensor(sensivity_v=None, vcc=Config.SENSOR_VCC, offset_max=0, offset_min=0, S=Config.S)
    if Config.SUT == "ALTO21":
        sensor = ALT021(vcc=Config.SENSOR_VCC)
        ad8429 = ad8429_g2
    elif Config.SUT == "HMC1001":
        sensor = HMC1001(vcc=Config.SENSOR_VCC)
        ad8429 = ad8429_g30
    elif Config.SUT == "DRV425":
        sensor = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)
        ad8429 = ad8429_g2
    elif Config.SUT == "DRV5055":
        sensor = DRV5055(vcc=Config.SENSOR_VCC)
        ad8429 = ad8429_g30
    sensor._S = Config.S

    if Config.TEST_PROCEDURE == "TP0":
        dc_values = [0, 5, 20]
        for b in dc_values:
            if Config.PROCESS_DATA:
                name = f"{Config.OUT_DIR}/out_{Config.SUT}_DC_{b}_uT_{Config.RD}_BS{int(helmholtz_coil.B_S * 1e6)}.bin"
                data_reader = DataReader(filename=Path(name), adc=adc)
                data_reader.read()
                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429,
                                             out_name=f"DC_{b}_uT_{Config.RD}_BS{int(helmholtz_coil.B_S * 1e6)}", out_dir=Config.RESULTS_DIR)
                analyzer = NoiseAnalyzer(sp.dac_values * sp.sensor_B_uT_factor, 10e3, int(10e3), unit="uT")
                analyzer.analyze()
                analyzer.print_report()
                analyzer.plot(save_path='widmo_szumu_czujnik_A.png', show=True)
            break
    if Config.TEST_PROCEDURE == "TP1":
        b_values = [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        # b_values = [0, 1, 3, 5, 7, 10, 15, 20, 25]
        # b_values = [0, 1, 3, 5, 7, 10]
        # b_values = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        ref_files = []
        meas_files = []
        meas_files_v = []
        ref_harmonic_files = []
        meas_harmonic_files = []
        meas_harmonic_files_v = []
        ref_files_v = []
        ref_harmonic_files_v = []
        for b in b_values:
            if Config.GENERATE_DATA:
                data_reader = DataReader(filename=Path(get_out_file(b_value=b)), adc=adc)
                data_reader.read()
                # data_reader.plot(periods=2, scale_to_v=True)
                # data_reader.fft(scale_to_v=True)
                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429,
                                             out_name=get_sut_name(b_value=b), out_dir=Config.RESULTS_DIR)
                sp.plot_magnetic_field()
                sp.plot_v_sensor()

                data_reader = DataReader(filename=Path(get_out_ref_file(b_value=b)), adc=adc)
                data_reader.read()
                # data_reader.plot(periods=2, scale_to_v=True)
                # data_reader.fft(scale_to_v=True)
                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429, helmholtz_coil=helmholtz_coil, kB=Config.kB,
                                             out_name=get_sut_name(b_value=b)+"_ref", out_dir=Config.RESULTS_DIR)
                # sp.plot_current()
                sp.plot_magnetic_field()
                if Config.CALIBRATION:
                    sp.plot_v_adc()

            # ref_files.append(get_data_file(b_value=b, ref=True, units="current"))
            # ref_harmonic_files.append(get_data_file(b_value=b, ref=True, units="current", harmonics=True))
            #
            meas_files.append(get_data_file(b_value=b, ref=False, units="magnetic"))
            meas_harmonic_files.append(get_data_file(b_value=b, ref=False, units="magnetic", harmonics=True))

            ref_files.append(get_data_file(b_value=b, ref=True, units="magnetic"))
            ref_harmonic_files.append(get_data_file(b_value=b, ref=True, units="magnetic", harmonics=True))

            ref_files_v.append(get_data_file(b_value=b, ref=True, units="voltage_adc"))
            ref_harmonic_files_v.append(get_data_file(b_value=b, ref=True, units="voltage_adc", harmonics=True))

            meas_files_v.append(get_data_file(b_value=b, ref=False, units="voltage"))
            meas_harmonic_files_v.append(get_data_file(b_value=b, ref=False, units="voltage", harmonics=True))


        if Config.PROCESS_DATA:
            sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files,
                                           harmonics_files=meas_harmonic_files,
                                           ref_harmonics_files=ref_harmonic_files)
            params = sensor.calculate_params()
            print(params)
            sensor.plot_graphs(filename=f"{Config.RESULTS_DIR}/graphs/{Config.SUT}_linearity_Bmeas_uT_Bref_uT_{min(b_values)}_{max(b_values)}")

            sensor = CalculateSensorParams(measured_files=meas_files_v, reference_files=ref_files,
                                           harmonics_files=meas_harmonic_files_v,
                                           ref_harmonics_files=ref_harmonic_files)
            params = sensor.calculate_params()
            print(params)
            sensor.plot_graphs(y_label="Napięcie na wyjściu czujnika RMS [mV]", filename=f"{Config.RESULTS_DIR}/graphs/{Config.SUT}_linearity_Vsensor_mV_Bref_uT_{min(b_values)}_{max(b_values)}")
            if Config.CALIBRATION:
                sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files_v, harmonics_files=meas_harmonic_files, ref_harmonics_files=ref_harmonic_files_v)
                params = sensor.calculate_params()
                print(params)
                sensor.plot_graphs(x_label="Napięcie na rezystorze pomiarowym [V]", filename=f"{Config.RESULTS_DIR}/graphs/{Config.SUT}_linearity_Bmeas_uT_Vref_V_{min(b_values)}_{max(b_values)}")

    elif Config.TEST_PROCEDURE == "TP2":
        b_values = [1, 5, 10, 15, 20, 50]
        k_values = [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]
        if Config.GENERATE_DATA:
            for b in b_values:
                for k in k_values:
                    out_file = Path(f"{Config.OUT_K_DIR}/out_{Config.SUT}_sine_{b}_uT_{Config.RD}_k{k}{Config.BS}.bin")
                    data_reader = DataReader(filename=out_file, adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)
                    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429,
                                          out_name=get_sut_name(b_value=b)+f"_k{k}", out_dir=Config.RESULTS_DIR)
                    # sp.plot_magnetic_field()
                    # sp.plot_v_sensor()
                    sp.calculate_magnetic_filed_harmonics()

                    out_file_ref = Path(f"{Config.OUT_K_DIR}/out_{Config.SUT}_sine_{b}_uT_{Config.RD}_k{k}{Config.BS}_ref.bin")
                    data_reader = DataReader(filename=out_file_ref, adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)
                    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429, helmholtz_coil=helmholtz_coil, kB=Config.kB,
                                          out_name=get_sut_name(b_value=b)+f"_k{k}_ref", out_dir=Config.RESULTS_DIR)
                    # sp.plot_magnetic_field()
                    sp.calculate_magnetic_filed_harmonics()


        if Config.PROCESS_DATA:
            input_files = []
            for b in b_values:
                files_amp = []
                for k in k_values:
                    files_amp.append((
                                      f"{Config.RESULTS_DIR}/{Config.SUT}_sine_{b}_uT_{Config.RD}_k{k}_harmonics_B_uT.csv",
                                      f"{Config.RESULTS_DIR}/{Config.SUT}_sine_{b}_uT_{Config.RD}_k{k}_ref_harmonics_B_uT.csv"))
                input_files.append([f"{b} μT RMS", files_amp])
            analyzer = SensorBodeAnalyzer(input_files)
            analyzer.analyze()
            analyzer.plot(filename=f"{Config.RESULTS_DIR}/graphs/{Config.SUT}_freq_characteristic.png")

    elif Config.TEST_PROCEDURE == "TP3":
        if Config.PROCESS_DATA:
            tp3_b1_values_rms_names = ["7_5uT", "1_8uT", "22uT"]
            # tp3_b1_values_rms_names = ["7_5uT", "1_9uT",  "1_8uT", "22uT", "19uT", "13uT"]
            # tp3_b1_values_rms_names = ["22uT"]
            harmonics_data_names = ["500kV", "220kV", "THD29"]  # "220kV"
            # harmonics_data_names = ["500kV", "400kV", "THD29"]  # "220kV"
            # harmonics_data_names = ["500kV", "220kV", "400kV", "THD29"]
            for value_name in tp3_b1_values_rms_names:
                for harmonic_name in harmonics_data_names:
                    name = f"{Config.SUT}_harmonic_{value_name}_{harmonic_name}_{Config.RD}{Config.BS}"
                    out_file = f"{Config.OUT_DIR}/out_{name}.bin"
                    out_file_ref = f"{Config.OUT_DIR}/out_{name}_ref.bin"
                    data_reader = DataReader(filename=Path(out_file), adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)

                    data_float = np.array(data_reader.values).astype(np.float32)

                    dc_offset = np.mean(data_float)
                    reversed_data_mean = (2 * dc_offset) - data_float

                    # Convert back to 16-bit integer
                    reversed_data_mean = np.clip(reversed_data_mean, 0, 65535).astype(np.uint16)

                    sp = SignalProcessing(dac_values=reversed_data_mean, adc=adc, sensor=sensor, ad8429=ad8429,
                                          out_name=name, out_dir=Config.RESULTS_DIR)
                    sp.plot_magnetic_field()

                    data_reader = DataReader(filename=Path(out_file_ref), adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)
                    # helmholtz_coil_real = HelmholtzCoilReal(n=Config.R, current_source=current_source,
                    #                                    B_S=0.5176 * 1e-6 / 1e-3)
                    # helmholtz_coil_real = HelmholtzCoilReal(n=45, R=Config.R, current_source=current_source,
                    #                                    B_S=0.4 * 1e-6 / 1e-3)
                    sp_ref = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=sensor, ad8429=ad8429,
                                          helmholtz_coil=helmholtz_coil, kB=Config.kB,
                                          out_name=name + "_ref", out_dir=Config.RESULTS_DIR)
                    # sp_ref.plot_current()
                    sp_ref.plot_magnetic_field()

                    validator = SignalValidator(meas_signal=sp, ref_signal=sp_ref)
                    validator.print_report()
                    validator.plot_validation(periods_to_show=3, save_path=f"{Config.RESULTS_DIR}/graphs/{name}.png")
                    # validator.analyze_and_plot_relative_harmonics(save_path=f"{Config.RESULTS_DIR}/graphs/{name}_thd.png")
