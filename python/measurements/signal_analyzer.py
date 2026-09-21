import numpy as np
from pathlib import Path
import csv


class SignalAnalyzer:
    def __init__(self, signal):
        self.signal = np.asarray(signal, dtype=np.float64)
        self.N = len(signal)

        # --- Time Domain Parameters ---
        # 1. DC Offset (Mean)
        self.mean = np.mean(self.signal)

        # 2. Root Mean Square (RMS)
        self.rms = np.sqrt(np.mean(self.signal ** 2))

        # 3. Peak-to-Peak Amplitude
        self.peak_to_peak = np.max(self.signal) - np.min(self.signal)

        # 4. Standard Deviation (AC RMS)
        self.ac_rms = np.std(self.signal)
        # self.ac_rms = SignalAnalyzer.rms(self.signal-self.mean)

        # # 5. Crest Factor (Peak to RMS ratio)
        # peak_abs = np.max(np.abs(self.signal))
        # self.crest_factor = peak_abs / self.rms if self.rms != 0 else 0

    @staticmethod
    def rms(signal):
        return np.sqrt(np.mean(signal ** 2))

    def print_parameters(self, scale=1.0, filename="data/parameters.csv"):
        # print(
        #     "\nMean (DC): ", self.mean*scale,
        #     "\nRMS: ", self.rms*scale,
        #     "\nAC_RMS: ", self.ac_rms*scale,
        #     "\nSTD: ", self.std*scale,
        #     "\nPeak-to-Peak: ", self.peak_to_peak*scale,
        # )
        params = {
            "MEAN": self.mean * scale,
            "RMS": self.rms * scale,
            "AC_RMS": self.ac_rms * scale,
            # "STD": self.std * scale,
            "Peak-to-Peak": self.peak_to_peak * scale,
        }

        print(filename)
        for name, val in params.items():
            print(f"{name}: {val}\n", end="")
        print()

        # Save to CSV
        path = Path(filename)
        # path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Parameter", "Value"])
            for name, val in params.items():
                writer.writerow([name, val])


if __name__ == '__main__':
    fs = 2000.0
    t = np.arange(0, 1.0, 1.0 / fs)
    test_signal = 3.0 * np.sin(2 * np.pi * 50 * t) + 1.5 * np.sin(2 * np.pi * 150 * t)
    test_signal += 2
    signal_analyzer = SignalAnalyzer(signal=test_signal)
    signal_analyzer.print_parameters()

    test_signal = 3.0 * np.sin(2 * np.pi * 50 * t) + 3
    signal_analyzer = SignalAnalyzer(signal=test_signal)
    signal_analyzer.print_parameters()
