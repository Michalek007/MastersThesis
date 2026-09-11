from measurements.fft import FFT

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from enum import Enum


class Signal(Enum):
    SINUS = 0
    SQUARE_WAVE = 1
    TRIANGULAR_WAVE = 2


class SignalGenerator:
    def __init__(self, n_samples, harmonics_dict, filename: Path):
        self.n_samples = n_samples
        self.harmonics_dict = harmonics_dict
        self.filename = filename
        self.t = np.linspace(0, 1, self.n_samples, endpoint=False)
        self.signal = np.zeros_like(self.t)

    def generate_harmonics(self):
        for harmonic, amplitude in self.harmonics_dict.items():
            self.signal += amplitude * np.sin(2 * np.pi * harmonic * self.t)

    def generate_square_wave(self, freq=50):
        period = 1.0 / freq
        self.signal = np.where(self.t * period < (period / 2), 1.0, 0.0)

    def generate_triangular_wave(self, freq=50):
        phase = (self.t * 2) % 2
        self.signal = np.where(phase < 1, phase, 2 - phase)

    def normalize(self):
        self.signal -= np.min(self.signal)
        self.signal /= np.max(self.signal)
        # self.signal /= self.harmonics_dict[1]

    def save(self):
        self.signal.astype(np.float32).tofile(self.filename)
        print(f"--- Zapisano {len(self.signal)} próbek do pliku: {self.filename} ---")

    def plot(self, amp=1, freq=50, y_label="Amplituda"):
        plt.figure(figsize=(10, 5))
        plt.plot(self.t * 1/freq, self.signal*amp)
        plt.title(self.filename)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        plt.show()

    def generate(self, signal_type: Signal = Signal.SINUS):
        if signal_type == Signal.SINUS:
            self.generate_harmonics()
        elif signal_type == Signal.SQUARE_WAVE:
            self.generate_square_wave()
        elif signal_type == Signal.TRIANGULAR_WAVE:
            self.generate_triangular_wave()
        else:
            raise NotImplementedError()

        fft = FFT(self.signal, sampling_rate=self.n_samples)
        fft.calculate()
        fft.plot_fft(x_scale=50, x_lim=2500)

        self.normalize()
        self.plot()
        self.save()


if __name__ == '__main__':
    SAMPLES = 1000
    harmonics_1 = {
        1: 1.0,
        3: 0.33,
        5: 0.20
    }
    harmonics_2 = {
        1: 1.0,
        2: 0.50,
        4: 0.25
    }
    harmonics_3 = {i: 0.75 if i % 2 else 0.0 for i in range(1, 50)}
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_1, filename=Path("data/signal_odd_harmonics.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_2, filename=Path("data/signal_even_harmonics.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={}, filename=Path("data/square_wave.bin")).generate(signal_type=Signal.SQUARE_WAVE)
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={}, filename=Path("data/triangular_wave.bin")).generate(signal_type=Signal.TRIANGULAR_WAVE)
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_3, filename=Path("data/harmonics_3.bin")).generate()
