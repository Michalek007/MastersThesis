
class Converter:
    def __init__(self, resolution_bits, vcc):
        self.Res_bits = resolution_bits
        self.Vcc = vcc

    @property
    def Lsb(self):
        return self.Vcc/(2**self.Res_bits)

    @property
    def Max_value(self):
        return 2 ** self.Res_bits - 1

    def V(self, value):
        value = min(value, self.Max_value)
        return value*self.Lsb

    def Value(self, V):
        V = min(V, self.Vcc)
        return round(V*(1/self.Lsb))


class ADC(Converter):
    pass


class DAC(Converter):
    pass
