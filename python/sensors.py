class Constants:
    Vcc = 5
    B_max = 200e-6
    B_min = -B_max


class ADC:
    def __init__(self, resolution_bits, vcc):
        self.Res_bits = resolution_bits
        self.Vcc = vcc

    @property
    def Lsb(self):
        return self.Vcc/(2**self.Res_bits)


class Sensor:
    def __init__(self, sensivity_v, vcc, offset_max, offset_min, S=None):
        self.Sv = sensivity_v
        self.Vcc = vcc
        # self.S = self.Sv*self.Vcc
        # self.Offset = (self.Vcc/2)
        self.Offset_max = offset_max
        self.Offset_min = offset_min
        self._S = S

    @property
    def S(self):
        if self._S:
            return self._S
        return self.Sv*self.Vcc

    @property
    def Offset(self):
        return self.Vcc/2

    def Vout(self, B):
        return self.S * B + self.Offset

    def Vout_max(self, B_max):
        return self.Vout(B_max) + self.Offset_max

    def Vout_min(self, B_min):
        return self.Vout(B_min) + self.Offset_min


class AD8429:
    def __init__(self, vs_positive, vs_negative, v_reference, gain):
        self.Vs_p = vs_positive
        self.Vs_n = vs_negative
        self.V_ref = v_reference
        self.G = gain

    @property
    def Vin_max(self):
        return self.Vs_p - 2.5

    @property
    def Vin_min(self):
        return self.Vs_n + 2.8

    def Vout(self, Vin_p, Vin_n):
        return (Vin_p - Vin_n) * self.G + self.V_ref


class HMC1001(Sensor):
    def __init__(self, vcc):
        super().__init__(32, vcc, 0.030, -0.060)


class ALT021(Sensor):
    def __init__(self, vcc):
        super().__init__(500, vcc, 0.020*vcc, -0.020*vcc)


class DRV5055(Sensor):
    def __init__(self, vcc):
        super().__init__(None, vcc, 0.070, -0.070, S=100)


class DRV425(Sensor):
    def __init__(self, vcc, R_shunt):
        super().__init__(None, vcc, None, None)
        # S_I 12.2 mT/mA, G= 4V/V
        # max offset +- 8uT
        # typical +- 2uT
        self.R_shunt = R_shunt

    @property
    def S(self):
        return 12.2 * 4 * self.R_shunt

    @property
    def Offset_max(self):
        return self.S * 8e-6

    @property
    def Offset_min(self):
        return -self.S * 8e-6

    @Offset_max.setter
    def Offset_max(self, offset_max):
        pass

    @Offset_min.setter
    def Offset_min(self, offset_min):
        pass


if __name__ == "__main__":
    adc = ADC(resolution_bits=16, vcc=3.3)

    print("Constants: ")
    print("B_max [uT]: ", Constants.B_max * 1e6)
    print("B_min [uT]: ", Constants.B_min * 1e6)
    print("Vcc_sensors [V]: ", Constants.Vcc)
    print()

    print("ADC: ")
    print("Resolution bits: ", adc.Res_bits)
    print("Vcc [V]: ", adc.Vcc)
    print("Vref [V]: ", adc.Vcc/2)
    print()

    hmc1001 = HMC1001(vcc=Constants.Vcc)
    alt021 = ALT021(vcc=Constants.Vcc)
    drv5055 = DRV5055(vcc=Constants.Vcc)
    drv425 = DRV425(vcc=Constants.Vcc, R_shunt=100)

    ad8429_g30 = AD8429(vs_positive=8, vs_negative=-8, v_reference=adc.Vcc/2, gain=30)
    print("HMC1001: ")
    print("S [mV/mT]: ", hmc1001.S, "; after AD8429: ", hmc1001.S * ad8429_g30.G)
    print("Vout_max [V]: ", hmc1001.Vout_max(Constants.B_max))
    print("Vout_min [V]: ", hmc1001.Vout_min(Constants.B_min))
    print("HMC1001->AD8429: Vref [V]: ", ad8429_g30.V_ref, "; Gain: ", ad8429_g30.G)
    print("Vout_max [V]: ", ad8429_g30.Vout(hmc1001.Vout_max(Constants.B_max), hmc1001.Offset))
    print("Vout_min [V]: ", ad8429_g30.Vout(hmc1001.Vout_min(Constants.B_min), hmc1001.Offset))
    print()

    ad8429_g50 = AD8429(vs_positive=8, vs_negative=-8, v_reference=adc.Vcc/2, gain=50)
    print("DRV5055: ")
    print("S [mV/mT]: ", drv5055.S, "; after AD8429: ", drv5055.S * ad8429_g50.G)
    print("Vout_max [V]: ", drv5055.Vout_max(Constants.B_max))
    print("Vout_min [V]: ", drv5055.Vout_min(Constants.B_min))
    print("DRV5055->AD8429: Vref [V]: ", ad8429_g50.V_ref, "; Gain: ", ad8429_g50.G)
    print("Vout_max [V]: ", ad8429_g50.Vout(drv5055.Vout_max(Constants.B_max), drv5055.Offset))
    print("Vout_min [V]: ", ad8429_g50.Vout(drv5055.Vout_min(Constants.B_min), drv5055.Offset))
    print()

    ad8429_g2 = AD8429(vs_positive=8, vs_negative=-8, v_reference=adc.Vcc/2, gain=2)
    print("DRV425: ")
    print("Rshunt [Ohm]: ", drv425.R_shunt)
    print("S [mV/mT]: ", drv425.S, "; after AD8429: ", drv425.S * ad8429_g2.G)
    print("Vout_max [V]: ", drv425.Vout_max(Constants.B_max))
    print("Vout_min [V]: ", drv425.Vout_min(Constants.B_min))
    print("DRV425->AD8429: Vref [V]: ", ad8429_g2.V_ref, "; Gain: ", ad8429_g2.G)
    print("Vout_max [V]: ", ad8429_g2.Vout(drv425.Vout_max(Constants.B_max), drv425.Offset))
    print("Vout_min [V]: ", ad8429_g2.Vout(drv425.Vout_min(Constants.B_min), drv425.Offset))
    print()

    print("ALT021: ")
    print("S [mV/mT]: ", alt021.S, "; after AD8429: ", alt021.S * ad8429_g2.G)
    print("Vout_max [V]: ", alt021.Vout_max(Constants.B_max))
    print("Vout_min [V]: ", alt021.Vout_min(Constants.B_min))
    print("ALT021->AD8429: Vref [V]: ", ad8429_g2.V_ref, "; Gain: ", ad8429_g2.G)
    print("Vout_max [V]: ", ad8429_g2.Vout(alt021.Vout_max(Constants.B_max), alt021.Offset))
    print("Vout_min [V]: ", ad8429_g2.Vout(alt021.Vout_min(Constants.B_min), alt021.Offset))
    print()
