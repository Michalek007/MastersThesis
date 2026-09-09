def r_parallel(*r_list):
    one_divide_r_z = 0
    for r in r_list:
        one_divide_r_z += 1/r

    return 1/one_divide_r_z


if __name__ == '__main__':
    R1 = 6.04e3
    R2 = 220
    RZ = r_parallel(R1, R2)
    print("RZ: ", RZ)
