import numpy as np
import matplotlib.pyplot as plt
from enum import Enum
import csv
from pathlib import Path


class Window(Enum):
    HANNING = 1


class FFT:
    def __init__(self, signal, sampling_rate, remove_offset=False):
        self.signal = signal
        self.n_samples = len(self.signal)
        if remove_offset:
            self.signal = self.signal - np.mean(self.signal)
        self.fft = None
        self.freqs = None
        self.phase = None
        self.sampling_rate = sampling_rate
        self.harmonics_amp = None
        self.thd = None

    def calculate(self):
        """
        Calculates the single-sided FFT of a real time-domain signal.
        Returns frequencies and true signal amplitudes.
        """
        N = len(self.signal)

        # 1. Compute the standard FFT
        fft_complex = np.fft.fft(self.signal)

        # 2. Compute the corresponding frequencies for the x-axis
        freqs = np.fft.fftfreq(N, d=1.0 / self.sampling_rate)

        # 3. Discard the negative frequencies (symmetric for real signals)
        half_n = N // 2
        self.freqs = freqs[:half_n]
        self.fft = fft_complex[:half_n]
        self.phase = np.angle(self.fft)

        # 4. Calculate amplitude and normalize
        # Divide by N and multiply by 2 to recover the true amplitude
        # of the folded negative frequencies
        self.fft = (2.0 / N) * np.abs(self.fft)

        # fft_rms = self.fft * np.sqrt(2)
        # fund_idx = np.argmin(np.abs(self.freqs - 50))
        # fund_window = 2
        # fund_energy = np.sum(fft_rms[fund_idx - fund_window: fund_idx + fund_window + 1] ** 2)
        # total_ac_energy = np.sum(fft_rms ** 2)
        # noise_dist_energy = max(total_ac_energy - fund_energy, 0)
        # print(noise_dist_energy)

        # 5. The DC component (0 Hz) doesn't have a negative twin,
        # so we must divide it back by 2
        self.fft[0] = self.fft[0] / 2.0
        self.phase[self.fft < 1e-5] = 0
        self.phase = np.degrees(self.phase)

    def calculate_window(self, window: Window = Window.HANNING):
        N = len(self.signal)
        # 1. Generate the window array
        window_array = np.hanning(N)

        # 2. Apply the window to the time-domain signal
        self.signal = self.signal * window_array

        # 3. Calculate the amplitude correction factor.
        # A Hann window reduces the signal's average amplitude by exactly half,
        # so the correction factor is roughly 2.0.
        # Using 1.0 / mean(window) mathematically guarantees the exact factor.
        correction_factor = 1.0 / np.mean(window_array)

        self.calculate()
        self.fft *= correction_factor

    def plot_fft(self, y_scale=1, x_scale=1, x_lim=None, y_label="Amplituda", title="Widmo częstotliwościowe", filename=None):
        plt.figure(figsize=(10, 5))
        plt.plot(self.freqs*x_scale, self.fft*y_scale, color='b')

        plt.title(title)
        plt.xlabel("Częstotliwość [Hz]")
        plt.ylabel(y_label)

        # Add a grid for easier reading of peaks
        plt.grid(True, which="both", linestyle="--", alpha=0.7)

        # Limit x-axis to slightly past our highest known signal component for clarity
        # (Remove or adjust this line depending on your actual Nyquist limit needs)
        if x_lim:
            plt.xlim(0, x_lim)
        plt.tight_layout()
        if filename:
            plt.savefig(filename, dpi=500)
        else:
            plt.show()

    def get_harmonic_amplitudes_legacy(self, f0, num_harmonics=50, search_window_hz=2.0):
        self.harmonics_amp = []

        for n in range(1, num_harmonics + 1):
            target_freq = n * f0

            # 1. Create a mask to find bins within our search window
            mask = (self.freqs >= target_freq - search_window_hz) & (self.freqs <= target_freq + search_window_hz)
            valid_indices = np.where(mask)[0]

            if len(valid_indices) == 0:
                print(f"Warning: Harmonic {n} at {target_freq}Hz is out of bounds or window is too small.")
                continue

            # 2. Find the index of the maximum amplitude within this specific window
            local_mag = self.fft[valid_indices]
            peak_idx = valid_indices[np.argmax(local_mag)]

            # 3. Store the results
            self.harmonics_amp.append({
                'harmonic': n,
                'frequency': self.freqs[peak_idx],
                'rms': self.fft[peak_idx] / np.sqrt(2),
                'phase': self.phase[peak_idx],
            })

    def print_harmonic_amplitudes(self, amp_scale=1.0, freq_scale=1.0, filename=None, amplitude=False):
        value_name = "RMS"
        # if amplitude:
        #     amp_scale *= np.sqrt(2)
        #     value_name = "Amplitude"
        if filename:
            print(filename)
        for h in self.harmonics_amp:
            if h['rms'] > 0.0:
                print(f"H{h['harmonic']}: Freq = {h['frequency']*freq_scale} Hz | {value_name} = {h['rms']*amp_scale}| Phase = {h['phase']}")
        print()
        if filename:
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["harmonic", "frequency_hz", value_name, "phase"])
                for h in self.harmonics_amp:
                    writer.writerow(
                        [
                            h["harmonic"],
                            h["frequency"] * freq_scale,
                            h["rms"] * amp_scale,
                            h["phase"]
                        ]
                    )

    def get_harmonic_amplitudes(self, fundamental_freq=50.0, max_freq=2500.0, snr_threshold=3.0):
        """
        Zwraca słownik z wartościami RMS harmonicznych. Odrzuca te, które giną w lokalnym szumie.
        """
        self.harmonics_amp = []
        max_harmonic = int(max_freq / fundamental_freq)

        amplitudes_rms = self.fft / np.sqrt(2)

        # Krok częstotliwości pomiędzy prążkami FFT (dla okna 200 ms będzie to 5 Hz)
        freq_step = self.sampling_rate / self.n_samples

        for h in range(1, max_harmonic + 1):
            valid_harmonics = {}
            target_freq = h * fundamental_freq

            # 1. Znajdź indeks centralny dla tej harmonicznej
            k = int(target_freq / freq_step)

            # 2. Oblicz energię podgrupy harmonicznej (zgodnie z IEC: prążek centralny +/- 1 prążek)
            if k + 1 < len(amplitudes_rms):
                harmonic_energy = amplitudes_rms[k - 1] ** 2 + amplitudes_rms[k] ** 2 + amplitudes_rms[k + 1] ** 2
                harmonic_rms = np.sqrt(harmonic_energy)
            else:
                continue

            # 3. Wyznacz LOKALNY szum w pobliżu tej harmonicznej
            # Badamy okno obok harmonicznej (np. od k+2 do k+6 oraz od k-6 do k-2)
            # Omijamy samo centrum, które wycięliśmy do podgrupy harmonicznej
            noise_bins = []
            for offset in [-6, -5, -4, -3, -2, 2, 3, 4, 5, 6]:
                if 0 <= k + offset < len(amplitudes_rms):
                    noise_bins.append(amplitudes_rms[k + offset])

            # Obliczenie RMS lokalnego szumu (tylko z tych bocznych prążków)
            local_noise_rms = np.sqrt(np.sum(np.array(noise_bins) ** 2) / len(noise_bins))

            # 4. Decyzja: Czy harmoniczna "wystaje" ponad szum?
            # Stosujemy próg np. 3-krotności RMS lokalnego szumu (możesz dostroić parametr snr_threshold)
            if harmonic_rms > (snr_threshold * local_noise_rms):
                valid_harmonics['harmonic'] = h
                valid_harmonics['frequency'] = fundamental_freq*h
                valid_harmonics['rms'] = harmonic_rms
                valid_harmonics['phase'] = self.phase[k]
            else:
                valid_harmonics['harmonic'] = h
                valid_harmonics['frequency'] = fundamental_freq * h
                valid_harmonics['rms'] = 0.0
                valid_harmonics['phase'] = 0.0
            self.harmonics_amp.append(valid_harmonics)
        return self.harmonics_amp

    def calculate_thd(self, as_percentage=True):
        fundamental_amp = 0.0
        sum_squares_harmonics = 0.0

        for item in self.harmonics_amp:
            n = item.get('harmonic')
            amp = item.get('rms', 0.0)

            if n == 1:
                fundamental_amp = amp
            elif n is not None and n > 1:
                sum_squares_harmonics += amp ** 2

        if fundamental_amp == 0.0:
            raise ValueError("Fundamental amplitude (harmonic 1) is missing or zero.")

        thd = np.sqrt(sum_squares_harmonics) / fundamental_amp
        self.thd = thd * 100 if as_percentage else thd

    @staticmethod
    def calculate_thd_from_dict(harmonics_dict, as_percentage=True):
        fundamental_amp = 0.0
        sum_squares_harmonics = 0.0

        for n, amp in harmonics_dict.items():
            if n == 1:
                fundamental_amp = amp
            elif n > 1:
                sum_squares_harmonics += amp ** 2

        if fundamental_amp == 0.0:
            raise ValueError("Fundamental amplitude (harmonic 1) is missing or zero.")

        thd = np.sqrt(sum_squares_harmonics) / fundamental_amp
        return thd * 100 if as_percentage else thd


if __name__ == "__main__":
    # Setup sampling parameters
    fs = 2000.0  # Sample rate in Hz
    t = np.arange(0, 1.0, 1.0 / fs)  # 1 second of data

    # Generate a test signal:
    # 50 Hz fundamental (Amplitude = 3.0) + 150 Hz harmonic (Amplitude = 1.5)
    test_signal = 3.0 * np.sin(2 * np.pi * 50 * t) + 1.5 * np.sin(2 * np.pi * 150 * t) + 0.5 * np.sin(2 * np.pi * 250 * t)

    # Add a tiny bit of random noise
    test_signal += np.random.normal(0, 5, len(t))

    # Calculate and plot
    fft = FFT(signal=test_signal, sampling_rate=fs)
    fft.calculate()
    fft.plot_fft()
    fft.get_harmonic_amplitudes_legacy(
        f0=50.0,
        num_harmonics=3,
        search_window_hz=3.0
    )
    fft.print_harmonic_amplitudes(filename=Path('data/harmonics.csv'))

    fft.get_harmonic_amplitudes(
        fundamental_freq=50.0,
        snr_threshold=3.0
    )
    fft.print_harmonic_amplitudes(filename=Path('data/harmonics.csv'))

    fft.calculate_window(window=Window.HANNING)
    fft.plot_fft()
    fft.get_harmonic_amplitudes(
        fundamental_freq=50.0,
        snr_threshold=3.0
    )
    fft.print_harmonic_amplitudes()
