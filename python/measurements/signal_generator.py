from measurements.fft import FFT
from measurements.signal_analyzer import SignalAnalyzer

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from enum import Enum


class Config:
    FREQ = 50
    MAX_FREQ = 2500


class Signal(Enum):
    SINUS = 0
    SQUARE_WAVE = 1
    TRIANGULAR_WAVE = 2
    DC = 3


class SignalGenerator:
    def __init__(self, n_samples, harmonics_dict: dict, filename: Path):
        self.n_samples = n_samples
        self.harmonics_dict = harmonics_dict
        if not self.harmonics_dict:
            self.harmonics_dict = {1: 1.0}
        self.filename = filename
        self.name = self.filename.parts[-1].split(".")[-2]
        self.t = np.linspace(0, 1, self.n_samples, endpoint=False)
        self.signal = np.zeros_like(self.t)
        self.fft: FFT
        self.parameters: SignalAnalyzer

    def generate_harmonics(self):
        for harmonic, amplitude in self.harmonics_dict.items():
            self.signal += amplitude * np.sin(2 * np.pi * harmonic * self.t)

    def generate_square_wave(self, freq=50):
        period = 1.0 / freq
        self.signal = np.where(self.t * period < (period / 2), 1.0, 0.0)

    def generate_triangular_wave(self, freq=50):
        phase = (self.t * 2) % 2
        self.signal = np.where(phase < 1, phase, 2 - phase)

    def generate_dc(self):
        self.signal = np.ones(self.n_samples, dtype=np.float64)

    def normalize(self):
        if np.min(self.signal) < 0:
            self.signal -= np.min(self.signal)
        self.signal /= np.max(self.signal)
        # self.signal /= self.harmonics_dict[1]

    def save(self):
        self.signal.astype(np.float32).tofile(self.filename)
        print(f"--- Zapisano {len(self.signal)} próbek do pliku: {self.filename} ---")

    def plot(self, amp=1, freq=Config.FREQ, y_label="Amplituda", save=False):
        plt.figure(figsize=(10, 5))
        plt.plot(self.t * 1/freq, self.signal*amp)
        plt.title(self.filename)
        plt.xlabel("Czas [s]")
        plt.ylabel(y_label)
        plt.grid(True)
        if save:
            plt.savefig(f'graphs/{self.name}.png', dpi=500)
        else:
            plt.show()

    def generate(self, signal_type: Signal = Signal.SINUS):
        if signal_type == Signal.SINUS:
            self.generate_harmonics()
        elif signal_type == Signal.SQUARE_WAVE:
            self.generate_square_wave()
        elif signal_type == Signal.TRIANGULAR_WAVE:
            self.generate_triangular_wave()
        elif signal_type == Signal.DC:
            self.generate_dc()
        else:
            raise NotImplementedError()

        self.fft = FFT(self.signal, sampling_rate=self.n_samples)
        self.fft.calculate()
        self.fft.plot_fft(x_scale=Config.FREQ, x_lim=Config.MAX_FREQ)
        if signal_type not in (Signal.SQUARE_WAVE, Signal.TRIANGULAR_WAVE):
            self.fft.get_harmonic_amplitudes(f0=1, num_harmonics=max(self.harmonics_dict.keys()), search_window_hz=2/50)
        else:
            self.fft.get_harmonic_amplitudes(f0=1, num_harmonics=50, search_window_hz=2/50)
        self.fft.print_harmonic_amplitudes()

        self.normalize()
        self.parameters = SignalAnalyzer(signal=self.signal)
        self.parameters.print_parameters(filename=f'data/{self.name}.csv')

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
    harmonic_3 = {
        1:  1.0,
        5:  0.2,
        7:  0.143,
        11: 0.091,
        13: 0.077,
        17: 0.059,
        19: 0.053,
        23: 0.043,
        25: 0.04,
        29: 0.034,
        31: 0.032,
        33: 5.0
    }
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_1, filename=Path("data/signal_odd_harmonics.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonics_2, filename=Path("data/signal_even_harmonics.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={}, filename=Path("data/square_wave.bin")).generate(signal_type=Signal.SQUARE_WAVE)
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={}, filename=Path("data/triangular_wave.bin")).generate(signal_type=Signal.TRIANGULAR_WAVE)
    SignalGenerator(n_samples=SAMPLES, harmonics_dict=harmonic_3, filename=Path("data/harmonics_3.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={1: 1.0}, filename=Path("data/sine.bin")).generate()
    SignalGenerator(n_samples=SAMPLES, harmonics_dict={1: 1.0}, filename=Path("data/dc.bin")).generate(signal_type=Signal.DC)
