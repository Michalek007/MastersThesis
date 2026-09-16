harmonics_500kv_under_line_nT = {
    1: 7531.2,
    2: 7.34,
    3: 57.78,
    4: 17.74,
    5: 124.44,
    6: 2.46,
    7: 51.98,
    8: 4.58,
    9: 16.56,
    10: 3.42,
    11: 44.86,
    12: 1.72,
    13: 8.99,
    14: 1.04,
    15: 4.44,
    16: 3.48,
    17: 13.72,
    18: 2.24,
    19: 8.18,
    20: 1.16
}


# Therefore, the harmonic spectrum of the current represents the maximum allowable har
# monic distortion defined by IEEE Std 519-2014 for HV OPLs with a maximum demand
# current of over 1000 A [16]. The calculated THD of the current is 37.1%
#  IEEE Std 519-2014 (Revision of IEEE Std 519-1992); IEEE Recommended Practice and Requirements for Harmonic Control in
# Electric Power Systems. IEEE: Piscataway, NJ, USA, 2014; pp. 1–29.
harmonics_IEEE_max_current = {
    1: 1.0,
    2: 0.028,
    3: 0.15,
    4: 0.028,
    5: 0.15,
    6: 0.028,
    7: 0.15,
    8: 0.028,
    9: 0.15,
    10: 0.018,
    12: 0.018,
    14: 0.018,
    16: 0.016,
    18: 0.016,
    20: 0.016,
}


# DIAGNOSTYKA, 2022, Vol. 23, No. 2
# e-ISSN 2449-5220
# DOI: 10.29354/diag/150068
# MAGNETIC FIELD EVALUATION AROUND 400 KV UNDERGROUND POWER
# CABLE UNDER HARMONICS EFFECTS
# Houari BOUDJELLA 1, * , Ahmed N. E. I AYAD 1 , Tahar ROUIBAH 1, Benyekhlef LAROUCI 1 ,
# Thamer A. H ALGHAMDI 2 , Ahmed ALTHOBAITI 3 , Sherif S. M. GHONEIM 3 ,
# Abdelkader Si TAYEB 4
# harmonics_current_I_case {
#     1: 1.0,
#     3:
# }

# Calculation of Magnetic Flux Density Harmonics in the Vicinity
# of Overhead Lines
# Adnan Mujezinovi´c * , Emir Turajli´c
# , Ajdin Alihodži´c
# , Maja Mufti´c Dedovi´c andNedisDautbaši´
harmonic_10kV_170A = {
    1: 1.0,
    5: 0.2,
    7: 0.143,
    11: 0.091,
    13: 0.077,
    17: 0.059,
    19: 0.053,
    23: 0.043,
    25: 0.04,
    29: 0.034,
    31: 0.032,
}
