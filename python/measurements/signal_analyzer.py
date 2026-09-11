import numpy as np


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
        self.std = np.std(self.signal)
        self.ac_rms = SignalAnalyzer.rms(self.signal-self.mean)

        # # 5. Crest Factor (Peak to RMS ratio)
        # peak_abs = np.max(np.abs(self.signal))
        # self.crest_factor = peak_abs / self.rms if self.rms != 0 else 0

    @staticmethod
    def rms(signal):
        return np.sqrt(np.mean(signal ** 2))

    def print_parameters(self, scale=1.0):
        print(
            "\nMean (DC): ", self.mean*scale,
            "\nRMS: ", self.rms*scale,
            "\nAC_RMS: ", self.ac_rms*scale,
            "\nSTD: ", self.std*scale,
            "\nPeak-to-Peak: ", self.peak_to_peak*scale,
        )


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
