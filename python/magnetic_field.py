from measurements.signal_generator import SignalGenerator, Signal
from measurements.signal_analyzer import SignalAnalyzer
from measurements.convert_signal_for_dac import CovertSignalForDAC
from calculations.helmholtz_coil import HelmholtzCoil, DAC, CurrentSource
from harmonic_data import *

from pathlib import Path
import math


class MagneticFieldSignalGenerator:
    def __init__(self, B_1, DAC_V_offset, n_samples, harmonics_dict, signal_type: Signal, filename: Path, helmholtz_coil: HelmholtzCoil, current_source: CurrentSource, dac: DAC, n_periods=1):
        if signal_type == Signal.DC:
            self._B_1 = B_1
        else:
            self._B_1 = B_1 * math.sqrt(2)
        self.DAC_V_offset = DAC_V_offset
        self.n_samples = n_samples
        self.harmonics_dict = harmonics_dict
        self.signal_type = signal_type
        self.filename = filename

        self.helmholtz_coil = helmholtz_coil
        self.current_source = current_source
        self.dac = dac

        self.n_periods = n_periods

    @property
    def B_1(self):
        return self._B_1

    @B_1.setter
    def B_1(self, B_1_RMS):
        self._B_1 = B_1_RMS * math.sqrt(2)

    def dac_value(self, B):
        return self.dac.Value(B * self.helmholtz_coil.I_S * self.current_source.V_S)

    def generate(self):
        signal_generator = SignalGenerator(n_samples=self.n_samples, harmonics_dict=self.harmonics_dict, filename=self.filename, n_periods=self.n_periods)

        scale_to_B_uT = self.B_1 * 1e6
        scale_to_I_mA = self.B_1 * self.helmholtz_coil.I_S*1e3

        signal_generator.generate(signal_type=self.signal_type)
        signal_generator.plot(amp=scale_to_B_uT, y_label="Pole magnetyczne [uT]", save=True, name=signal_generator.name + "_B_uT")
        signal_generator.plot(amp=scale_to_I_mA, y_label="Natężenie prądu [mA]", save=True, name=signal_generator.name + "_I_mA")

        signal_generator.fft.print_harmonic_amplitudes(amp_scale=scale_to_B_uT, freq_scale=50*self.n_periods, filename=Path(f"data/{signal_generator.name}_harmonics_B_uT.csv"))
        signal_generator.fft.print_harmonic_amplitudes(amp_scale=scale_to_I_mA, freq_scale=50*self.n_periods, filename=Path(f"data/{signal_generator.name}_harmonics_I_mA.csv"))

        signal_generator.analyzer.print_parameters(scale=scale_to_B_uT, filename=Path(f"data/{signal_generator.name}_B_uT.csv"))
        signal_generator.analyzer.print_parameters(scale=scale_to_I_mA, filename=Path(f"data/{signal_generator.name}_I_mA.csv"))
        CovertSignalForDAC(dac=self.dac, filename=self.filename).convert_and_save(amp=self.dac_value(self.B_1), offset=self.dac.Value(self.DAC_V_offset), dc=(self.signal_type == Signal.DC))


if __name__ == '__main__':
    dac = DAC(vcc=3.3, resolution_bits=12)
    current_source = CurrentSource(R=7.5, dac=dac)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)

    # MagneticFieldSignalGenerator(B_1=100e-6, B_offset=20e-6, harmonics_dict={1: 1.0, 5: 0.5}, n_samples=1000, filename=Path("data/test.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac, signal_type=Signal.SINE).generate()
    #
    # MagneticFieldSignalGenerator(B_1=50e-6, B_offset=0, harmonics_dict={1: 1.0}, n_samples=1000, signal_type=Signal.DC, filename=Path("data/dc_50ut.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac).generate()
    #
    # MagneticFieldSignalGenerator(B_1=7.5312e-6, B_offset=20e-6, harmonics_dict=harmonic_500kv_under_line_nT, n_samples=1000, signal_type=Signal.SINE, filename=Path("data/500kv_under_line_nT.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac).generate()
    #
    # MagneticFieldSignalGenerator(B_1=1e-6, B_offset=50e-6, harmonics_dict={1: 1.0}, n_samples=1000, signal_type=Signal.SINE, filename=Path("data/sine_AC_1uT_DC_50uT.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac).generate()
    #
    # MagneticFieldSignalGenerator(B_1=50e-6, B_offset=20e-6, harmonics_dict={1: 1.0}, n_samples=1000, signal_type=Signal.SINE, filename=Path("data/sine_AC_50uT_DC_20uT.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac).generate()
    #
    # MagneticFieldSignalGenerator(B_1=10e-6, B_offset=10e-6, harmonics_dict={1: 1.0}, n_samples=1000, signal_type=Signal.TRIANGULAR_WAVE, filename=Path("data/triangular_AC_50uT_DC_20uT.bin"),
    #                              helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac).generate()

    # mf_signal_generator = MagneticFieldSignalGenerator(
    #     B_1=harmonic_500kv_under_line_nT[1]*1e-9, DAC_V_offset=0.1, harmonics_dict=harmonic_220kv_nT,
    #     n_samples=1000, signal_type=Signal.SINE, filename=Path("data/harmonic_500kv_under_line_nT_test.bin"),
    #     helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    # )
    # mf_signal_generator = MagneticFieldSignalGenerator(
    #     B_1=50*1e-6, DAC_V_offset=0.05, harmonics_dict={1: 1.0},
    #     n_samples=2000, signal_type=Signal.SINE, filename=Path("data/calibration_test_sine_50_uT.bin"),
    #     helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    # )
    # mf_signal_generator.generate()
    # mf_signal_generator = MagneticFieldSignalGenerator(
    #     B_1=20*1e-6, DAC_V_offset=0.05, harmonics_dict={1: 1.0},
    #     n_samples=2000, signal_type=Signal.SINE, filename=Path("data/calibration_test_sine_20_uT.bin"),
    #     helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    # )
    # mf_signal_generator.generate()
    # mf_signal_generator = MagneticFieldSignalGenerator(
    #     B_1=10*1e-6, DAC_V_offset=0.05, harmonics_dict={1: 1.0},
    #     n_samples=2000, signal_type=Signal.SINE, filename=Path("data/calibration_test_sine_10_uT.bin"),
    #     helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac
    # )
    # mf_signal_generator.generate()
    # mf_signal_generator = MagneticFieldSignalGenerator(
    #     B_1=10*1e-6, DAC_V_offset=0.05, harmonics_dict={1: 1.0},
    #     n_samples=2000, signal_type=Signal.SINE, filename=Path("data/calibration_test_sine_10_uT_k2.bin"),
    #     helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac, n_periods=2
    # )
    # mf_signal_generator.generate()

    mf_signal_generator = MagneticFieldSignalGenerator(
        B_1=50*1e-6, DAC_V_offset=0.00, harmonics_dict={1: 1.0},
        n_samples=2000, signal_type=Signal.DC, filename=Path("data/calibration_test_dc_10_uT.bin"),
        helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac, n_periods=1
    )
    # mf_signal_generator.generate()

    # helmholtz_coil.current_source.R_divider = 10
    # mf_signal_generator.harmonics_dict = harmonic_220kv_nT
    # mf_signal_generator.B_1 = harmonic_220kv_nT[1] * 1e-9
    # mf_signal_generator.filename = Path("data/harmonic_220kv_nT_test.bin")
    # mf_signal_generator.generate()

    # helmholtz_coil.current_source.R_divider = 10
    # mf_signal_generator.harmonics_dict = harmonic_400kV_1_8kA_I
    # mf_signal_generator.B_1 = harmonic_400kV_1kA_10m_uT[1] * 1e-6
    # mf_signal_generator.filename = Path("data/harmonic_400kV_1kA_10m_uT.bin")
    # mf_signal_generator.generate()
