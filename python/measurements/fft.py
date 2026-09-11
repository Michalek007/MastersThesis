import numpy as np
import matplotlib.pyplot as plt
from enum import Enum


class Window(Enum):
    HANNING = 1


class FFT:
    def __init__(self, signal, sampling_rate):
        self.signal = signal
        self.fft = None
        self.freqs = None
        self.sampling_rate = sampling_rate
        self.harmonics_amp = None

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

        # 4. Calculate amplitude and normalize
        # Divide by N and multiply by 2 to recover the true amplitude
        # of the folded negative frequencies
        self.fft = (2.0 / N) * np.abs(self.fft)

        # 5. The DC component (0 Hz) doesn't have a negative twin,
        # so we must divide it back by 2
        self.fft[0] = self.fft[0] / 2.0

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

    def plot_fft(self, y_scale=1, x_scale=1, x_lim=None, y_label="Amplituda", title="Widmo częstotliwościowe", save=False, filename="fft"):
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
        if save:
            plt.savefig(f'graphs/{filename}.png', dpi=500)
        else:
            plt.show()

    def get_harmonic_amplitudes(self, f0, num_harmonics=50, search_window_hz=2.0):
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
                'amplitude': self.fft[peak_idx]
            })

    def print_harmonic_amplitudes(self, amp_scale=1.0, freq_scale=1.0):
        print()
        for h in self.harmonics_amp:
            print(f"H{h['harmonic']}: Freq = {h['frequency']*freq_scale:.1f} Hz | Amplitude = {h['amplitude']*amp_scale:.4f}")
        print()


if __name__ == "__main__":
    # Setup sampling parameters
    fs = 2000.0  # Sample rate in Hz
    t = np.arange(0, 1.0, 1.0 / fs)  # 1 second of data

    # Generate a test signal:
    # 50 Hz fundamental (Amplitude = 3.0) + 150 Hz harmonic (Amplitude = 1.5)
    test_signal = 3.0 * np.sin(2 * np.pi * 50 * t) + 1.5 * np.sin(2 * np.pi * 150 * t)

    # Add a tiny bit of random noise
    test_signal += np.random.normal(0, 0.2, len(t))

    # Calculate and plot
    fft = FFT(signal=test_signal, sampling_rate=fs)
    fft.calculate()
    fft.plot_fft()

    fft.calculate_window(window=Window.HANNING)
    fft.plot_fft()
    fft.get_harmonic_amplitudes(
        f0=50.0,
        num_harmonics=3,
        search_window_hz=3.0
    )
    fft.print_harmonic_amplitudes()
