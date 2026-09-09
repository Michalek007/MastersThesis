

def TPS723():
    R1 = 100e3

    R2_p1 = 100e3
    R2_p2 = 22e3
    R2 = R2_p1 * R2_p2 / (R2_p1+R2_p2)

    V_fb = 1.186
    I_fb = 0.1e-6

    V_out = V_fb * (1 + R1/R2)
    I_fb_divider = V_out/(R1+R2)
    R_eq_max = V_out/(I_fb*100)
    R_eq = R1+R2

    print("TPS723: ")
    print("V_out [V]: ", -V_out)
    print("I_fb [uA]: ", I_fb * 1e6)
    print("I_fb_divider [uA]: ", I_fb_divider * 1e6)
    print("I_fb_divider / I_fb: ", I_fb_divider / I_fb)
    print("R_eq_max [kOhm]: ", R_eq_max / 1e3)
    print("R_eq: [kOhm]", R_eq / 1e3)
    print()


def LT1716():
    R1 = 100e3

    R2_p1 = 100e3
    R2_p2 = 22e3
    R2 = R2_p1 * R2_p2 / (R2_p1+R2_p2)

    V_adj= 1.22
    I_adj = 30e-9

    V_out = V_adj * (1+R1/R2) + I_adj*R1

    print("LT1716: ")
    print("V_out [V]: ", V_out)
    print("I_adj*R1: ", I_adj*R1)
    print()


if __name__ == '__main__':
    TPS723()
    LT1716()
