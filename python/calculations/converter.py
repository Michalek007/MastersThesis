
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

    @property
    def Min_value(self):
        return 0

    @property
    def V_max(self):
        return self.Vcc

    @property
    def V_min(self):
        return 0

    def V(self, value):
        value = min(value, self.Max_value)
        return value*self.Lsb

    def Value(self, V):
        V = min(V, self.Vcc)
        return round(V*(1/self.Lsb))


class ADC(Converter):
    pass


class DAC(Converter):
    def __init__(self, resolution_bits, vcc, buffer_enabled=True):
        super().__init__(resolution_bits, vcc)
        self.buffer_enabled = buffer_enabled

    @property
    def V_min(self):
        return 0.2

    @property
    def Min_value(self):
        if self.buffer_enabled:
            return self.Value(self.V_min)
        else:
            return 0
