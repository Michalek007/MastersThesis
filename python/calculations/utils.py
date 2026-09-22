def r_parallel(*r_list):
    one_divide_r_z = 0
    for r in r_list:
        one_divide_r_z += 1/r

    return 1/one_divide_r_z


class VoltageDivider:
    def __init__(self, r1, r2, vcc):
        self.R1 = r1
        self.R2 = r2
        self.Vcc = vcc

    @property
    def Divider(self):
        return self.R1 / (self.R1+self.R2)

    @property
    def Vout(self, Vin=None):
        if Vin:
            return self.Divider * Vin
        else:
            return self.Divider * self.Vcc


if __name__ == '__main__':
    R1 = 6.04e3
    R2 = 220
    RZ = r_parallel(R1, R2)
    print("RZ: ", RZ)

    R1 = 1e3
    R2 = 9.09e3
    RZ = r_parallel(R1, R2)
    print("RZ: ", RZ)
    v_divider = VoltageDivider(r1=R1, r2=R2, vcc=3.3)

    print("Divider: ", v_divider.Divider)
    print("Vout: ", v_divider.Vout)

    R1 = 1e3
    R2 = 1e3
    RZ = r_parallel(R1, R2)
    print("RZ: ", RZ)
    v_divider = VoltageDivider(r1=R1, r2=R2, vcc=3.3)

    print("Divider: ", v_divider.Divider)
    print("Vout: ", v_divider.Vout)
