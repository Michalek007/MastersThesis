import math


class Constants:
    u_0 = 4 * math.pi * 1e-7
    c = (4 / 5) ** (3 / 2)


class DAC:
    def __init__(self, resolution_bits, vcc):
        self.Res_bits = resolution_bits
        self.Vcc = vcc
        self.Lsb = self.Vcc/(2**self.Res_bits)


class CurrentSource:
    def __init__(self, R, DAC):
        self.R_sense = R
        self.I_max = DAC.Vcc / self.R_sense
        self.I_res = DAC.Lsb / self.R_sense


class HelmholtzCoil:
    def __init__(self, n, R, current_source):
        self.n = n
        self.R = R
        self.B_max = self.B(current_source.I_max)
        self.B_res = self.B(current_source.I_res)
        self.B_S = self.B_max / current_source.I_max
        self.I_S = 1 / self.B_S

    def B(self, I):
        return (Constants.c * Constants.u_0 * self.n * I) / self.R


if __name__ == '__main__':
    print("Constants: ")
    print("(4/5)^(3/2) ", Constants.c)
    print("Magnetic const ", Constants.u_0)
    print()

    dac = DAC(vcc=3.3, resolution_bits=12)
    current_source = CurrentSource(R=7.5, DAC=dac)
    helmholtz_coil = HelmholtzCoil(n=45, R=(8 + 0.4 + 0.15) / 100, current_source=current_source)
    print("B (200mA)", helmholtz_coil.B(0.2) * 1e6, " uT")
    print("S_B ", helmholtz_coil.B_S * 1e6/1e3, " uT/mA")
    print("S_I ", helmholtz_coil.I_S * 1e3/1e6, " mA/uT")
    print("Bmax ", helmholtz_coil.B_max * 1e6, " uT")
    print("Ires ", current_source.I_res * 1e6, " uA")
    print("Bres ", helmholtz_coil.B_res * 1e6, " uT")
