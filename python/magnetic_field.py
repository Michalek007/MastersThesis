from measurements.signal_generator import SignalGenerator
from measurements.convert_signal_for_dac import CovertSignalForDAC
from calculations.helmholtz_coil import HelmholtzCoil, DAC, CurrentSource

from pathlib import Path


class MagneticFieldSignalGenerator:
    def __init__(self, B_1, B_offset, n_samples, harmonics_dict, filename: Path, helmholtz_coil: HelmholtzCoil, current_source: CurrentSource, dac: DAC):
        self.B_1 = B_1
        self.B_offset = B_offset
        self.signal_generator = SignalGenerator(n_samples=n_samples, harmonics_dict=harmonics_dict, filename=filename)
        self.helmholtz_coil = helmholtz_coil
        self.current_source = current_source
        self.dac = dac

    def dac_value(self, B):
        return self.dac.Value(B * self.helmholtz_coil.I_S * self.current_source.R_sense)

    def generate(self):

        print("B_1: ", self.B_1)
        current_1 = self.B_1 * self.helmholtz_coil.I_S
        print("current_1: ", current_1)
        v_dac_1 = current_1 * self.current_source.R_sense
        print("v_dac_1: ", v_dac_1)
        dac_value_1 = self.dac.Value(v_dac_1)
        print("dac_value_1: ", dac_value_1)

        self.signal_generator.generate()
        self.signal_generator.plot(amp=self.B_1*1e6, y_label="Pole magnetyczne [uT]")
        self.signal_generator.plot(amp=current_1*1e3, y_label="Natężenie prądu [mA]")
        self.signal_generator.plot(amp=v_dac_1, y_label="Napięcie na wyjściu C/A [V]")
        CovertSignalForDAC(dac=self.dac, filename=self.signal_generator.filename).convert_and_save(amp=dac_value_1, offset=self.dac_value(self.B_offset))


if __name__ == '__main__':
    dac = DAC(vcc=3.3, resolution_bits=12)
    current_source = CurrentSource(R=7.5, DAC=dac)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    mf = MagneticFieldSignalGenerator(B_1=100e-6, B_offset=20e-6, harmonics_dict={1: 1.0, 5: 0.5}, n_samples=1000, filename=Path("data/test.bin"),
                                      helmholtz_coil=helmholtz_coil, current_source=current_source, dac=dac)
    mf.generate()