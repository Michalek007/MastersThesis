import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


class SignalGenerator:
    def __init__(self, n_samples, harmonics_dict, filename: Path):
        self.n_samples = n_samples
        self.harmonics_dict = harmonics_dict
        self.filename = filename
        self.t = np.linspace(0, 1, self.n_samples, endpoint=False)
        self.signal = np.zeros_like(self.t)

    def generate_harmonics(self):
        # self.signal = np.zeros_like(t)
        for harmonic, amplitude in self.harmonics_dict.items():
            self.signal += amplitude * np.sin(2 * np.pi * harmonic * self.t)

    def normalize(self):
        self.signal -= np.min(self.signal)
        self.signal /= np.max(self.signal)
        # self.signal /= self.signal[0]

    def save(self):
        self.signal.astype(np.float32).tofile(self.filename)
        print(f"--- Zapisano {len(self.signal)} próbek do pliku: {self.filename} ---")

    def plot(self, amp=1, y_label="Amplituda"):
        plt.figure(figsize=(10, 5))
        plt.plot(self.t*1/50, self.signal*amp)
        plt.title(self.filename)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.show()

    def generate(self):
        self.generate_harmonics()
        self.normalize()
        self.plot()
        self.save()


# class SquareWave(SignalGenerator):
#     def generate_square_signal(self, freq):
#         # # 1. Configuration
#         # SAMPLES = 1000  # Number of points in one period (defines resolution)
#         # FREQ = 50  # Frequency in Hz
#         # PERIOD = 1.0 / FREQ
#         #
#         # # Create a time array for exactly one period of a 50 Hz signal
#         # t = np.linspace(0, PERIOD, SAMPLES, endpoint=False)
#
#         # 2. Generate the waveform (Square Wave)
#         # A square wave is high (1.0) for the first half of the period, and low (0.0) for the second half
#         self.signal = np.where(t < (1/freq * self.n_samples/50e3 / 2), 1.0, 0.0)


def generate_harmonics(t, harmonics_dict):
    """
    Generuje sygnał na podstawie słownika harmonicznych.
    :param t: tablica czasu
    :param harmonics_dict: słownik, gdzie klucz to numer harmonicznej, a wartość to amplituda
    """
    signal = np.zeros_like(t)
    for harmonic, amplitude in harmonics_dict.items():
        signal += amplitude * np.sin(2 * np.pi * harmonic * t)
    return signal


def normalize_signal(signal):
    """
    Normalizuje sygnał, przesuwając go nad zero i skalując do zakresu 0.0 - 1.0.
    """
    signal_shifted = signal - np.min(signal)
    signal_normalized = signal_shifted / np.max(signal_shifted)
    return signal_normalized


def save_to_bin(signal, filename):
    """
    Zapisuje sygnał do pliku binarnego (jako 32-bitowe liczby float).
    """
    signal.astype(np.float32).tofile(filename)
    print(f"--- Zapisano {len(signal)} próbek (0.0 - 1.0) do pliku: {filename} ---")


def plot_signal(t, signal, title):
    """
    Wyświetla wykres podanego sygnału.
    """
    plt.figure(figsize=(10, 5))
    plt.plot(t, signal)
    plt.title(title)
    plt.xlabel("Czas [s]")
    plt.ylabel("Amplituda (0.0 - 1.0)")
    plt.grid(True)
    plt.show()


# =========================================================================

if __name__ == '__main__':
    # Konfiguracja globalna
    SAMPLES = 1000
    t = np.linspace(0, 1, SAMPLES, endpoint=False)

    # --- 1. Sygnał: harmoniczne nieparzyste ---
    harmonics_1 = {
        1: 1.0,  # Podstawowa
        3: 0.33,  # 3. harmoniczna
        5: 0.20  # 5. harmoniczna
    }

    signal_1 = generate_harmonics(t, harmonics_1)
    signal_1_norm = normalize_signal(signal_1)

    save_to_bin(signal_1_norm, "data\\signal_odd_harmonics.bin")
    plot_signal(t, signal_1_norm, "Sygnał 1: Harmoniczne nieparzyste (0.0 - 1.0)")

    # --- 2. Sygnał: harmoniczne parzyste ---
    harmonics_2 = {
        1: 1.0,  # Podstawowa
        2: 0.50,  # 2. harmoniczna
        4: 0.25  # 4. harmoniczna
    }

    signal_2 = generate_harmonics(t, harmonics_2)
    signal_2_norm = normalize_signal(signal_2)

    save_to_bin(signal_2_norm, "data\\signal_even_harmonics.bin")
    plot_signal(t, signal_2_norm, "Sygnał 2: Harmoniczne parzyste (0.0 - 1.0)")

    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_1, filename=Path("data/signal_odd_harmonics.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_2, filename=Path("data/signal_even_harmonics.bin")).generate()
