from calculations.converter import DAC

import math


class Constants:
    u_0 = 4 * math.pi * 1e-7
    c = (4 / 5) ** (3 / 2)


class CurrentSource:
    def __init__(self, R, dac: DAC, R_divider=1):
        self.R_sense = R
        self.R_divider = R_divider
        self.Dac = dac
        # self.I_max = self.Dac.Vcc / self.R_sense / self.R_divider
        # self.I_res = self.Dac.Lsb / self.R_sense / self.R_divider

    @property
    def I_max(self):
        return self.Dac.Vcc / self.R_sense / self.R_divider

    @property
    def I_res(self):
        return self.Dac.Lsb / self.R_sense / self.R_divider


class HelmholtzCoil:
    def __init__(self, n, R, current_source: CurrentSource):
        self.n = n
        self.R = R
        self.current_source = current_source
        # self.B_max = self.B(current_source.I_max)
        # self.B_res = self.B(current_source.I_res)
        # self.B_S = self.B_max / current_source.I_max
        # self.I_S = 1 / self.B_S

    def B(self, I):
        return (Constants.c * Constants.u_0 * self.n * I) / self.R

    def I(self, B):
        return (B * self.R ) / (Constants.c * Constants.u_0 * self.n)

    @property
    def B_max(self):
        return self.B(self.current_source.I_max)

    @property
    def B_res(self):
        return self.B(self.current_source.I_res)

    @property
    def B_S(self):
        return self.B_max / self.current_source.I_max

    @property
    def I_S(self):
        return 1 / self.B_S


class HelmholtzCoilReal(HelmholtzCoil):
    def __init__(self, n, R, current_source: CurrentSource, B_S):
        super().__init__(n, R, current_source)
        self._B_S = B_S

    def B(self, I):
        return I * self.B_S

    def I(self, B):
        return B * self.I_S

    @property
    def B_S(self):
        return self._B_S


if __name__ == '__main__':
    print("Constants: ")
    print("(4/5)^(3/2) ", Constants.c)
    print("Magnetic const ", Constants.u_0)
    print()

    dac = DAC(vcc=3.3, resolution_bits=12)
    current_source = CurrentSource(R=7.5, dac=dac, R_divider=1)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    print("B (200mA)", helmholtz_coil.B(0.2) * 1e6, " uT")
    print("S_B ", helmholtz_coil.B_S * 1e6/1e3, " uT/mA")
    print("S_I ", helmholtz_coil.I_S * 1e3/1e6, " mA/uT")
    print("Bmax ", helmholtz_coil.B_max * 1e6, " uT")
    print("Ires ", current_source.I_res * 1e6, " uA")
    print("Bres ", helmholtz_coil.B_res * 1e6, " uT")
    print()

    helmholtz_coil.current_source.R_divider = 2
    print("Bmax ", helmholtz_coil.B_max * 1e6, " uT")
    print("Ires ", current_source.I_res * 1e6, " uA")
    print("Bres ", helmholtz_coil.B_res * 1e6, " uT")
    print()

    helmholtz_coil.current_source.R_divider = 10
    print("Bmax ", helmholtz_coil.B_max * 1e6, " uT")
    print("Ires ", current_source.I_res * 1e6, " uA")
    print("Bres ", helmholtz_coil.B_res * 1e6, " uT")
    print()

    current_source = CurrentSource(R=7.5, dac=dac, R_divider=1)
    helmholtz_coil = HelmholtzCoilReal(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source, B_S=0.5*1e-6/1e-3)
    print("B (200mA)", helmholtz_coil.B(0.2) * 1e6, " uT")
    print("S_B ", helmholtz_coil.B_S * 1e6/1e3, " uT/mA")
    print("S_I ", helmholtz_coil.I_S * 1e3/1e6, " mA/uT")
    print("Bmax ", helmholtz_coil.B_max * 1e6, " uT")
    print("Ires ", current_source.I_res * 1e6, " uA")
    print("Bres ", helmholtz_coil.B_res * 1e6, " uT")
    print()