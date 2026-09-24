from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer
from signal_processing import SignalProcessing
from measurements.uart import DataReader, UART, Waveform, UartConfig
from calculations.converter import ADC
from calculations.helmholtz_coil import DAC, CurrentSource, HelmholtzCoil
from calculations.sensors import Sensor, AD8429, ALT021, DRV425, DRV5055, HMC1001
from calculate_sensor_parameters import CalculateSensorParams
from calculate_bandwidth import SensorBodeAnalyzer

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


class Config:
    SENSOR_VCC = 5
    AD8429_VP = 7.8
    AD8429_VN = -7.6
    AD8429_V_REF = 3.3 / 2
    SUT = "ALT021"
    PARENT_DIR = Path(f"final/{SUT}/TP3/")
    RESULTS_DIR = Path(f"{PARENT_DIR}/RESULTS")
    OUT_DIR = Path(f"{PARENT_DIR}/OUT")
    OUT_K_DIR = Path(f"{OUT_DIR}/K")
    IN_DIR = Path(f"/in/")

    # TEST_PROCEDURE = "TP1"
    TEST_PROCEDURE = "TP2"

    GENERATE_DATA = 0
    PROCESS_DATA = 1


def get_sut_name(b_value):
    return f"{Config.SUT}_sine_{int(b_value)}_uT"
def get_units_str(units="magnetic"):
    if units == "magnetic":
        units_str = "B_uT"
    elif units == "current":
        units_str = "I_mA"
    else:
        units_str = "V_mV"
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
    # current_source.R_divider = 2
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    # helmholtz_coil = HelmholtzCoilReal(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source, B_S=0.5176*1e-6/1e-3)

    adc = ADC(vcc=3.3, resolution_bits=16)
    ad8429_g2 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=2, Rg=6.04e3)
    ad8429_g30 = AD8429(vs_positive=Config.AD8429_VP, vs_negative=Config.AD8429_VN, v_reference=adc.Vcc/2, gain=30, Rg=212.26)
    ad8429 = ad8429_g2

    alt021 = ALT021(vcc=Config.SENSOR_VCC)
    hmc1001 = HMC1001(vcc=Config.SENSOR_VCC)
    drv5055 = DRV5055(vcc=Config.SENSOR_VCC)
    drv425 = DRV425(vcc=Config.SENSOR_VCC, R_shunt=100)


    if Config.TEST_PROCEDURE == "TP1":
        b_values = [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        ref_files = []
        meas_files = []
        ref_harmonic_files = []
        meas_harmonic_files = []
        for b in b_values:
            if Config.GENERATE_DATA:
                data_reader = DataReader(filename=Path(get_out_file(b_value=b)), adc=adc)
                data_reader.read()
                # data_reader.plot(periods=2, scale_to_v=True)
                # data_reader.fft(scale_to_v=True)
                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429,
                                             out_name=get_sut_name(b_value=b), out_dir=Config.RESULTS_DIR)
                sp.plot_magnetic_field()

                data_reader = DataReader(filename=Path(get_out_ref_file(b_value=b)), adc=adc)
                data_reader.read()
                # data_reader.plot(periods=2, scale_to_v=True)
                # data_reader.fft(scale_to_v=True)
                sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429, helmholtz_coil=helmholtz_coil,
                                             out_name=get_sut_name(b_value=b)+"_ref", out_dir=Config.RESULTS_DIR)
                sp.plot_current()


            # ref_files.append(Path(f"{Config.RESULTS_DIR}/ALT021_sine_{b}_uT_ref_I_mA.csv"))
            # ref_harmonic_files.append(Path(f"final/results/ALT021_sine_{b}_uT_ref_harmonics_I_mA.csv"))
            #
            # meas_files.append(Path(f"{Config.RESULTS_DIR}/ALT021_sine_{b}_uT_B_uT.csv"))
            # meas_harmonic_files.append(Path(f"{Config.RESULTS_DIR}/ALT021_sine_{b}_uT_harmonics_B_uT.csv"))
            ref_files.append(get_data_file(b_value=b, ref=True, units="current"))
            ref_harmonic_files.append(get_data_file(b_value=b, ref=True, units="current", harmonics=True))

            meas_files.append(get_data_file(b_value=b, ref=False, units="magnetic"))
            meas_harmonic_files.append(get_data_file(b_value=b, ref=False, units="magnetic", harmonics=True))

            if Config.PROCESS_DATA:
                sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files,
                                               harmonics_files=meas_harmonic_files,
                                               ref_harmonics_files=ref_harmonic_files)
                params = sensor.calculate_params()
                sensor.plot_graphs()

    elif Config.TEST_PROCEDURE == "TP2":
        b_values = [1, 5, 10, 15, 20, 50]
        k_values = [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]
        if Config.GENERATE_DATA:
            for b in b_values:
                for k in k_values:
                    out_file = Path(f"{Config.OUT_K_DIR}/out_{Config.SUT}_sine_{b}_uT_k{k}.bin")
                    data_reader = DataReader(filename=out_file, adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)
                    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429,
                                          out_name=get_sut_name(b_value=b)+f"_k{k}", out_dir=Config.RESULTS_DIR)
                    sp.plot_magnetic_field()

                    out_file_ref = Path(f"{Config.OUT_K_DIR}/out_ALT021_sine_{b}_uT_k{k}_ref.bin")
                    data_reader = DataReader(filename=out_file_ref, adc=adc)
                    data_reader.read()
                    # data_reader.plot(periods=2, scale_to_v=True)
                    # data_reader.fft(scale_to_v=True)
                    sp = SignalProcessing(dac_values=data_reader.values, adc=adc, sensor=alt021, ad8429=ad8429, helmholtz_coil=helmholtz_coil,
                                          out_name=get_sut_name(b_value=b)+f"_k{k}_ref", out_dir=Config.RESULTS_DIR)
                    sp.plot_magnetic_field()

        if Config.PROCESS_DATA:
            input_files = []
            for b in b_values:
                files_amp = []
                for k in k_values:
                    files_amp.append((f"{Config.RESULTS_DIR}/{Config.SUT}_sine_{b}_uT_k{k}_harmonics_B_uT.csv",
                                      f"{Config.RESULTS_DIR}/{Config.SUT}_sine_{b}_uT_k{k}_ref_harmonics_B_uT.csv"))
                input_files.append([f"{b}", files_amp])

            analyzer = SensorBodeAnalyzer(input_files)
            analyzer.analyze()
            analyzer.plot()
