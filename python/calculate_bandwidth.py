import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def extract_fundamental(csv_path):
    """
    Wczytuje plik CSV i zwraca parametry dla częstotliwości podstawowej
    (tej o największej amplitudzie RMS).
    """
    df = pd.read_csv(csv_path)

    # Znalezienie indeksu dla maksymalnej wartości RMS (prążek wymuszający fx)
    idx_max = df['RMS'].idxmax()
    row = df.loc[idx_max]

    return row['frequency_hz'], row['RMS'], row['phase']


def process_amplitude_group(file_pairs):
    """
    Przetwarza listę par plików (V_out_csv, B_ref_csv) dla danej amplitudy.
    Zwraca posortowaną po częstotliwości listę słowników z wynikami.
    """
    results = []

    for vout_csv, bref_csv in file_pairs:
        # Ekstrakcja parametrów z obu plików
        f_v, v_rms, v_phase = extract_fundamental(vout_csv)
        f_b, b_rms, b_phase = extract_fundamental(bref_csv)
        print(f_v, v_rms, v_phase)

        # Zabezpieczenie: sprawdzenie czy częstotliwości się zgadzają
        if abs(f_v - f_b) > 1.0:
            print(f"Ostrzeżenie: Rozbieżność częstotliwości między {vout_csv} ({f_v}Hz) a {bref_csv} ({f_b}Hz)")

        f_x = f_v

        # 1. Czułość bezwzględna S(f) [V/T]
        # Zakładamy, że plik referencyjny B_uT ma wartości w mikroteslach.
        # Konwersja na Tesle (1 uT = 1e-6 T), aby uzyskać S w [V/T].
        b_rms_T = b_rms * 1e-6
        S = v_rms / b_rms_T

        # 3. Przesunięcie fazowe delta_phi [stopnie]
        # Przykładowe dane w CSV ("171.033") są już w stopniach.
        # Jeśli FFT wyrzucałoby radiany, należałoby użyć: np.degrees(v_phase) - np.degrees(b_phase)
        delta_phi = v_phase - b_phase

        # Zawinięcie fazy do przedziału [-180, 180] stopni (zabezpieczenie przed skokami 360 st.)
        delta_phi = (delta_phi + 180) % 360 - 180

        results.append({
            'frequency': f_x,
            'S_VT': S,
            'RMS': v_rms,
            'delta_phi': delta_phi
        })

    # Sortowanie wyników rosnąco po częstotliwości
    results = sorted(results, key=lambda x: x['frequency'])

    # Szukanie punktu odniesienia bliskiego 50 Hz do normalizacji
    ref_50hz = min(results, key=lambda x: abs(x['frequency'] - 50.0))
    print(ref_50hz)
    # S_50 = ref_50hz['S_VT']
    RMS_50 = ref_50hz['RMS']

    # 2. Znormalizowany spadek wzmocnienia G(f) [dB]
    for r in results:
        r['G_dB'] = 20 * np.log10(r['RMS'] / RMS_50)

    return results


def plot_bode_family(data_10, data_50, data_90):
    """
    Generuje i wyświetla wykresy charakterystyk dla trzech amplitud.
    """
    datasets = [
        ("10% Amplitudy", data_10, 'blue', 'o-'),
        ("50% Amplitudy", data_50, 'green', 's-'),
        ("90% Amplitudy", data_90, 'red', '^-')
    ]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    fig.suptitle('Charakterystyki częstotliwościowe czujnika dla różnych amplitud', fontsize=14)

    for label, data, color, fmt in datasets:
        freqs = [d['frequency'] for d in data]
        S_vals = [d['S_VT'] for d in data]
        G_vals = [d['G_dB'] for d in data]
        phi_vals = [d['delta_phi'] for d in data]

        # Wykres 1: Czułość bezwzględna
        ax1.plot(freqs, S_vals, fmt, color=color, label=label, markersize=5)

        # Wykres 2: Znormalizowany spadek [dB]
        ax2.plot(freqs, G_vals, fmt, color=color, label=label, markersize=5)

        # Wykres 3: Przesunięcie fazowe
        ax3.plot(freqs, phi_vals, fmt, color=color, label=label, markersize=5)

    # Formatowanie osi i siatek
    for ax in (ax1, ax2, ax3):
        ax.set_xscale('log')
        ax.grid(True, which="both", ls="--", alpha=0.6)
        ax.legend()

    ax1.set_ylabel('Czułość bezwzględna S [V/T]')
    ax1.set_title('Bezwzględna czułość napięciowa S(f)')

    ax2.set_ylabel('Znormalizowane wzmocnienie G [dB]')
    ax2.set_title('Tłumienie G(f) względem 50 Hz')
    # Opcjonalnie: stałe granice dla osi Y, np. do oceny błędu płaskości (-3dB do +0.5dB)
    # ax2.set_ylim(-3.5, 0.5)
    ax2.axhline(0, color='black', linewidth=1)

    ax3.set_ylabel('Przesunięcie fazowe Δφ [°]')
    ax3.set_title('Charakterystyka fazowa Δφ(f)')
    ax3.set_xlabel('Częstotliwość [Hz]')

    plt.tight_layout()
    plt.show()


# ==========================================
# PRZYKŁAD UŻYCIA:
# ==========================================
if __name__ == "__main__":
    # Należy zdefiniować listy par plików CSV: (plik_wyjscia_czujnika, plik_odniesienia)
    # Przykład struktury dla amplitudy 10%
    # "ALT021_sine_15_uT_k1_harmonics_B_uT.csv"
    files = []
    b_values = [15, 20, 50]
    for b in b_values:
        files_amp = []
        for k in [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]:
            files_amp.append((f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv", f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv"))
        files.append(files_amp)

    for file in files:
        x = []
        y = []
        for vout_csv, bref_csv in file:
            # Ekstrakcja parametrów z obu plików
            f_v, v_rms, v_phase = extract_fundamental(vout_csv)
            x.append(f_v)
            y.append(v_rms)
        plt.plot(x, y)
    plt.grid(True)
    plt.xlabel("Częstotliwość [Hz]")
    plt.ylabel("Pole magnetyczne RMS [uT]")
    plt.show()

    # files_amp_10 = [
    #     ("sens_V_10_50Hz.csv", "ref_B_10_50Hz.csv"),
    #     ("sens_V_10_100Hz.csv", "ref_B_10_100Hz.csv"),
    #     # ... kolejne częstotliwości aż do 2.5 kHz ...
    # ]
    #
    # files_amp_50 = [
    #     # ... odpowiednie pary plików dla 50% amplitudy ...
    # ]
    #
    # files_amp_90 = [
    #     # ... odpowiednie pary plików dla 90% amplitudy ...
    # ]

    # ODKOMENTUJ PONIŻSZE LINIE PO UZUPEŁNIENIU LIST PLIKÓW:

    data_10 = process_amplitude_group(files[0])
    data_50 = process_amplitude_group(files[1])
    data_90 = process_amplitude_group(files[2])

    plot_bode_family(data_10, data_50, data_90)