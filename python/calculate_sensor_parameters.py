from measurements.fft import FFT


import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path


class CalculateSensorParams:
    def __init__(self, measured_files, reference_files, harmonics_files, ref_harmonics_files):
        """
        Initializes the calculator with separate standard and harmonic files.

        :param measured_files: List of standard CSV files (MEAN, RMS, Peak-to-Peak) for sensor.
        :param reference_files: List of standard CSV files for the reference input.
        :param harmonics_files: List of FFT harmonics CSV files for the sensor.
        :param ref_harmonics_files: List of FFT harmonics CSV files for the reference input.
        """
        print(len(measured_files))
        print(len(reference_files))
        print(len(harmonics_files))
        print(len(ref_harmonics_files))
        if not (len(measured_files) == len(reference_files) == len(harmonics_files) == len(ref_harmonics_files)):
            raise ValueError("All input file lists must have the exact same number of files.")

        self.measured_files = measured_files
        self.reference_files = reference_files
        self.harmonics_files = harmonics_files
        self.ref_harmonics_files = ref_harmonics_files

        # Standard values
        self.ref_standard = []
        self.meas_standard = []

        # Harmonic values (Fundamental 50Hz and THD)
        self.ref_fundamental = []
        self.meas_fundamental = []
        self.meas_thd = []

        # Computed parameters
        self.sensitivity = None
        self.intercept = None
        self.r_squared = None
        self.inl_max_pct = None

    def _parse_standard_file(self, filepath):
        """Parses Parameter,Value formatted files."""
        data = {}
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0].strip().upper() != 'PARAMETER':
                    try:
                        data[row[0].strip()] = float(row[1].strip())
                    except ValueError:
                        continue
        return data

    def _parse_harmonics_file(self, filepath):
        """
        Parses harmonic,frequency_hz,RMS,phase formatted files.
        Returns the fundamental (h=1) RMS and calculates THD (%).
        """
        fundamental_rms = None
        harmonics_rms = {}

        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().lower() == 'harmonic':
                    continue
                try:
                    h = int(row[0].strip())
                    rms = float(row[2].strip())
                    if h == 1:
                        fundamental_rms = rms
                    harmonics_rms[h] = rms
                except (ValueError, IndexError):
                    pass

        if fundamental_rms is None:
            raise ValueError(f"Could not extract fundamental RMS (h=1) from {filepath}")

        # Calculate THD (Total Harmonic Distortion) in percent
        # thd_pct = 0.0
        # if harmonics_rms:
        #     sum_of_squares = sum(v ** 2 for v in harmonics_rms)
        #     thd_pct = (np.sqrt(sum_of_squares) / fundamental_rms) * 100.0
        return fundamental_rms, FFT.calculate_thd_from_dict(harmonics_dict=harmonics_rms, as_percentage=True)

    def load_data(self):
        """Loads and parses all specified files."""
        self.ref_standard.clear()
        self.meas_standard.clear()
        self.ref_fundamental.clear()
        self.meas_fundamental.clear()
        self.meas_thd.clear()

        for m_file, r_file, h_file, rh_file in zip(
                self.measured_files, self.reference_files,
                self.harmonics_files, self.ref_harmonics_files
        ):
            # Load standard parameters (e.g., overall RMS, Peak-to-Peak)
            self.meas_standard.append(self._parse_standard_file(m_file))
            self.ref_standard.append(self._parse_standard_file(r_file))

            # Load harmonic values
            r_fund, _ = self._parse_harmonics_file(rh_file)
            m_fund, m_thd = self._parse_harmonics_file(h_file)

            self.ref_fundamental.append(r_fund)
            self.meas_fundamental.append(m_fund)
            self.meas_thd.append(m_thd)

        self.ref_fundamental = np.array(self.ref_fundamental)
        self.meas_fundamental = np.array(self.meas_fundamental)
        self.meas_thd = np.array(self.meas_thd)

    def calculate_params(self):
        """Calculates amplitude linearity based strictly on the 50 Hz fundamental."""
        if not len(self.ref_fundamental):
            self.load_data()

        # Linear Regression (Transfer Curve) using only the 50 Hz fundamental
        slope, intercept, r_value, p_value, std_err = linregress(self.ref_fundamental, self.meas_fundamental)
        self.sensitivity = slope
        self.intercept = intercept
        self.r_squared = r_value ** 2

        # Calculate Maximum INL (Integral Non-Linearity) Error % relative to Full Scale
        ideal_fit = slope * self.ref_fundamental + intercept
        deviations = np.abs(self.meas_fundamental - ideal_fit)
        full_scale = np.max(ideal_fit) - np.min(ideal_fit)

        if full_scale > 0:
            self.inl_max_pct = (np.max(deviations) / full_scale) * 100
        else:
            self.inl_max_pct = 0.0

        return {
            "Sensitivity": self.sensitivity,
            "R_Squared": self.r_squared,
            "Max_INL_Error_%": self.inl_max_pct
        }

    def plot_graphs(self, x_label=None, y_label=None, filename=None):
        """Plots the AC Transfer Curve and Dynamic Linearity (THD)."""
        if self.sensitivity is None:
            self.calculate_params()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # --- Plot 1: Amplitude Linearity (Krzywa transferu AC) ---
        ideal_fit = self.sensitivity * self.ref_fundamental + self.intercept

        ax1.scatter(self.ref_fundamental, self.meas_fundamental, color='red', label='Pole magnetyczne zmierzone 50 Hz RMS [μT]', zorder=5)
        ax1.plot(self.ref_fundamental, ideal_fit, 'b--', label='Dopasowanie liniowe')

        ax1.set_title('Liniowość dla częstotliwości 50 Hz')
        ax1.set_xlabel('Pole magnetyczne referencyjne 50 Hz RMS [μT]')
        ax1.set_ylabel('Pole magnetyczne zmierzone RMS [μT]')

        metrics_text = (f"R² (Determinacja): {self.r_squared:.6f}\n"
                        f"INL: {self.inl_max_pct:.3f}% FS\n"
                        f"Czułość: {self.sensitivity:.4f}")
        ax1.text(0.05, 0.95, metrics_text, transform=ax1.transAxes,
                 va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

        ax1.legend(loc='lower right')
        ax1.grid(True, linestyle=':', alpha=0.7)

        # --- Plot 2: Dynamic Linearity (Analiza THD vs Amplituda) ---
        ax2.plot(self.ref_fundamental, self.meas_thd, marker='o', color='green', linestyle='-', linewidth=2)

        ax2.set_title('Liniowiość dynamiczna (THD a wartość skuteczna sygnału)')
        ax2.set_xlabel('Pole magnetyczne referencyjne 50 Hz RMS [μT]')
        ax2.set_ylabel('THD zmierzonego pola magnetycznego [%]')

        ax2.set_ylim(bottom=0)
        ax2.grid(True, linestyle=':', alpha=0.7)

        if x_label:
            ax1.set_xlabel(x_label)
            ax2.set_xlabel(x_label)
        if y_label:
            ax1.set_ylabel(y_label)

        plt.tight_layout()
        if filename:
            plt.savefig(filename, dpi=500)
        else:
            plt.show()


if __name__ == '__main__':
    b_values = [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    # b_values = [0, 1, 3, 5, 7, 10]
    # b_values = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    # b_values = [30, 35, 40, 45, 50, 55, 60]
    # b_values = [15, 20, 25, 30, 35]
    # name = 'ALT021_sine_15_uT_B_uT.csv'
    # harmonics_name = 'ALT021_sine_15_uT_B_uT.csv'
    ref_files = []
    meas_files = []
    ref_harmonic_files = []
    meas_harmonic_files = []
    for b in b_values:
        ref_files.append(Path(f"results/ALT021_sine_{b}_uT_ref_I_mA.csv"))
        ref_harmonic_files.append(Path(f"results/ALT021_sine_{b}_uT_ref_harmonics_I_mA.csv"))

        meas_files.append(Path(f"results/ALT021_sine_{b}_uT_B_uT.csv"))
        meas_harmonic_files.append(Path(f"results/ALT021_sine_{b}_uT_harmonics_B_uT.csv"))
    #
    # sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files, harmonics_files=meas_harmonic_files, ref_harmonics_files=ref_harmonic_files)
    # params = sensor.calculate_params()
    # sensor.plot_graphs()

    # for b in b_values:
    #     ref_files.append(Path(f"results/ALT021_sine_{b}_uT_ref_B_uT.csv"))
    #     ref_harmonic_files.append(Path(f"results/ALT021_sine_{b}_uT_ref_harmonics_B_uT.csv"))
    #
    #     # meas_files.append(Path(f"results/ALT021_sine_{b}_uT_B_uT.csv"))
    #     # meas_harmonic_files.append(Path(f"results/ALT021_sine_{b}_uT_harmonics_B_uT.csv"))
    #     meas_files.append(Path(f"results/ALT021_sine_{b}_uT_Vsensor_mV.csv"))
    #     meas_harmonic_files.append(Path(f"results/ALT021_sine_{b}_uT_harmonics_Vsensor_mV.csv"))

    sensor = CalculateSensorParams(measured_files=meas_files, reference_files=ref_files, harmonics_files=meas_harmonic_files, ref_harmonics_files=ref_harmonic_files)
    params = sensor.calculate_params()
    sensor.plot_graphs()