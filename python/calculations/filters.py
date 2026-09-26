from utils import r_parallel

import math


class FilterRC:
    def __init__(self, R, C):
        self.R = R
        self.C = C

    @property
    def freq_3dB(self):
        return 1/(2*math.pi*self.R*self.C)


if __name__ == '__main__':
    print("Filter RC 1k 22n: ")
    f = FilterRC(R=1e3, C=22e-9)
    print(f.freq_3dB)

    f = FilterRC(R=1e3, C=33e-9)
    print(f.freq_3dB)

    f = FilterRC(R=900.9, C=22e-9)
    print(f.freq_3dB)

    f = FilterRC(R=5e3, C=4.3e-9)
    print(f.freq_3dB)

    f = FilterRC(R=1e3, C=100e-12)
    print(f.freq_3dB)

    f = FilterRC(R=1e3, C=2.2e-9)
    print(f.freq_3dB)

    f = FilterRC(R=1e3, C=3.3e-9)
    print(f.freq_3dB)
    print()

    f = FilterRC(R=r_parallel(1e3, 9.09e3), C=22e-9)
    print(f.freq_3dB)
    print()

    print("R1=10k, R2=10k")
    f = FilterRC(R=r_parallel(10e3, 10e3), C=3.3e-9)
    print(f.freq_3dB)
    print()
