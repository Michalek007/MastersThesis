import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq


# --- DEFINICJE FUNKCJI ---

def calculate_thd_n(signal, fs, fundamental_freq=50.0):
    N = len(signal)
    fft_vals = rfft(signal)
    fft_freqs = rfftfreq(N, 1 / fs)

    amplitudes_rms = (np.abs(fft_vals) / N) * np.sqrt(2)
    amplitudes_rms[0] = 0  # Usunięcie DC

    fund_idx = np.argmin(np.abs(fft_freqs - fundamental_freq))
    fund_window = 2

    fund_energy = np.sum(amplitudes_rms[fund_idx - fund_window: fund_idx + fund_window + 1] ** 2)
    fund_rms = np.sqrt(fund_energy)

    total_ac_energy = np.sum(amplitudes_rms ** 2)
    noise_dist_energy = max(total_ac_energy - fund_energy, 0)

    return (np.sqrt(noise_dist_energy) / fund_rms) * 100.0


def calculate_thd_iec(signal, fs, fundamental_freq=50.0, max_freq=2500.0):
    N = len(signal)
    fft_vals = rfft(signal)
    C = (np.abs(fft_vals) / N) * np.sqrt(2)

    def get_subgroup_rms(h):
        k = int((h * fundamental_freq) / (fs / N))
        if k + 1 >= len(C): return 0.0
        return np.sqrt(C[k - 1] ** 2 + C[k] ** 2 + C[k + 1] ** 2)

    C_sg_1 = get_subgroup_rms(1)
    if C_sg_1 == 0: return 0.0

    max_harmonic = int(max_freq / fundamental_freq)
    sum_harmonics_energy = sum(get_subgroup_rms(h) ** 2 for h in range(2, max_harmonic + 1))

    return (np.sqrt(sum_harmonics_energy) / C_sg_1) * 100.0


# # --- GENEROWANIE SYGNAŁU TESTOWEGO ---
#
# # Parametry (Scenariusz: 10 000 próbek w 200 ms)
# N_samples = 10000
# duration = 0.2  # sekundy (okno wymagane przez normę)
# fs = N_samples / duration  # Wynik: 50 000 Hz
#
# # Oś czasu
# t = np.linspace(0, duration, N_samples, endpoint=False)
#
# # Sygnał czysty: 50 Hz (1.0 V) + 150 Hz (0.05 V) + 250 Hz (0.0005 V)
# f1, f3, f5 = 50.0, 150.0, 250.0
# a1, a3, a5 = 1.0, 0.05, 0.0005
#
# clean_signal = (a1 * np.sin(2 * np.pi * f1 * t) +
#                 a3 * np.sin(2 * np.pi * f3 * t) +
#                 a5 * np.sin(2 * np.pi * f5 * t))
#
# # Dodajemy szum Gaussa
# # Poziom szumu dobrany tak, aby zamaskował 5. harmoniczną (amplituda 0.0005)
# noise_rms = 0.02
# noisy_signal = clean_signal + np.random.normal(0, noise_rms, N_samples)
noisy_signal = np.fromfile("data\\out_ALT021_sine_15_uT.bin", dtype=np.float32)
N_samples = len(noisy_signal)
fs = 10e3

# --- OBLICZENIA WSKAŹNIKÓW ---

thd_n_val = calculate_thd_n(noisy_signal, fs)
thd_iec_val = calculate_thd_iec(noisy_signal, fs)

print("-" * 50)
print(f"Częstotliwość próbkowania: {fs} Hz")
print(f"Liczba próbek: {N_samples}")
print("-" * 50)
print(f"Wynik THD+N:     {thd_n_val:.3f} %")
print(f"Wynik THD (IEC): {thd_iec_val:.3f} %")
print("-" * 50)

# --- WYKRES WIDMA (FFT) ---

fft_vals = rfft(noisy_signal)
fft_freqs = rfftfreq(N_samples, 1 / fs)
# Przeliczenie na wartość szczytową amplitudy dla wykresu
amplitudes = np.abs(fft_vals) / (N_samples / 2)
amplitudes[0] /= 2  # Poprawka dla DC

plt.figure(figsize=(12, 6))
# Pokazujemy pasmo tylko do 400 Hz, żeby dobrze widzieć co się dzieje z harmonicznymi
plt.plot(fft_freqs[fft_freqs <= 400], amplitudes[fft_freqs <= 400], color='blue')

plt.title('Widmo Amplitudowe FFT (Sygnał z ukrytą harmoniczną)')
plt.xlabel('Częstotliwość [Hz]')
plt.ylabel('Amplituda [V]')
plt.grid(True, linestyle='--', alpha=0.7)

# Skala logarytmiczna dla Y pięknie pokazuje poziom szumu
plt.yscale('log')

# Dodanie adnotacji
plt.axvline(x=50, color='r', linestyle='--', alpha=0.5)
plt.axvline(x=150, color='g', linestyle='--', alpha=0.5)
plt.axvline(x=250, color='orange', linestyle='--', alpha=0.5, label='Ukryta 5. harm (250 Hz)')
plt.legend()

plt.show()