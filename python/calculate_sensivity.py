from measurements.fft import FFT

import csv
import numpy as np
import matplotlib.pyplot as plt


class CalculateSensorParams:
    """
    Wyznacza czułość i liniowość czujnika na podstawie prążka 50 Hz.

    harmonics_files     - pliki harmonicznych sygnału czujnika [mV] = (Vout - Vref) / G
    ref_harmonics_files - pliki harmonicznych pola referencyjnego [µT] = K_B * V_Rsense
    fit_range           - zakres Bref RMS [µT], z którego wyznaczana jest czułość
    s_nominal           - czułość z noty [mV/µT] (opcjonalnie, do wyznaczenia błędu czułości)
    """

    def __init__(self, harmonics_files, ref_harmonics_files,
                 fit_range=(0.5, 25.0), s_nominal=None, min_ref_uT=0.1):
        if len(harmonics_files) != len(ref_harmonics_files):
            raise ValueError("All input file lists must have the exact same number of files.")

        self.harmonics_files = list(harmonics_files)
        self.ref_harmonics_files = list(ref_harmonics_files)
        self.fit_range = fit_range
        self.s_nominal = s_nominal
        self.min_ref_uT = min_ref_uT  # punkty poniżej (np. 0 µT) nie wchodzą do analizy

        self._reset_data()
        self._reset_params()

    # ------------------------------------------------------------------ dane
    def _reset_data(self):
        self.ref_fundamental = np.array([])   # µT RMS
        self.meas_fundamental = np.array([])  # mV RMS
        self.meas_thd = np.array([])          # %
        self.ref_thd = np.array([])           # %

    def _reset_params(self):
        self.sensitivity = None       # mV/µT, prosta przez zero, wagi względne
        self.sensitivity_u = None     # niepewność standardowa S
        self.sensitivity_ls = None    # mV/µT, zwykłe LS przez zero (porównawczo)
        self.intercept_check = None   # wyraz wolny prostej z przecięciem (diagnostyka)
        self.r_squared = None
        self.inl_max_pct = None       # % FS w zakresie dopasowania
        self.rel_error_pct = None     # błąd względny każdego punktu [%]
        self.sensitivity_error_pct = None

    @staticmethod
    def _parse_harmonics_file(filepath):
        """
        Zwraca (RMS podstawowej, THD [%] lub NaN).
        THD = NaN, gdy podstawowa została wyzerowana przez bramkę szumu.
        """
        harmonics_rms = {}
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().lower() == 'harmonic':
                    continue
                try:
                    harmonics_rms[int(row[0].strip())] = float(row[2].strip())
                except (ValueError, IndexError):
                    pass

        if 1 not in harmonics_rms:
            raise ValueError(f"Could not extract fundamental RMS (h=1) from {filepath}")

        fundamental = harmonics_rms[1]
        if fundamental > 0.0:
            thd = FFT.calculate_thd_from_dict(harmonics_dict=harmonics_rms, as_percentage=True)
        else:
            thd = np.nan
        return fundamental, thd

    def load_data(self):
        ref_f, meas_f, ref_t, meas_t = [], [], [], []

        for h_file, rh_file in zip(self.harmonics_files, self.ref_harmonics_files):
            r_fund, r_thd = self._parse_harmonics_file(rh_file)
            m_fund, m_thd = self._parse_harmonics_file(h_file)

            if r_fund < self.min_ref_uT:  # np. punkt 0 µT -> tylko szum
                continue

            ref_f.append(r_fund)
            meas_f.append(m_fund)
            ref_t.append(r_thd)
            meas_t.append(m_thd)

        order = np.argsort(ref_f)  # sortowanie dla poprawnych wykresów
        self.ref_fundamental = np.array(ref_f)[order]
        self.meas_fundamental = np.array(meas_f)[order]
        self.ref_thd = np.array(ref_t)[order]
        self.meas_thd = np.array(meas_t)[order]

    # ------------------------------------------------------------ obliczenia
    def calculate_params(self):
        if self.ref_fundamental.size == 0:
            self.load_data()

        b = self.ref_fundamental
        v = self.meas_fundamental
        in_fit = (b >= self.fit_range[0]) & (b <= self.fit_range[1])
        if np.count_nonzero(in_fit) < 3:
            raise ValueError("Za mało punktów w zakresie dopasowania.")

        b_fit, v_fit = b[in_fit], v[in_fit]

        # 1. Czułość: prosta przez zero, wagi 1/B^2 -> średnia czułości punktowych
        s_points = v_fit / b_fit
        self.sensitivity = np.mean(s_points)
        self.sensitivity_u = np.std(s_points, ddof=1) / np.sqrt(len(s_points))

        # 2. Porównawczo: zwykłe LS przez zero (dominują duże pola)
        self.sensitivity_ls = np.sum(b_fit * v_fit) / np.sum(b_fit ** 2)

        # 3. Diagnostyka: prosta z wyrazem wolnym (wyraz wolny powinien być ~0)
        slope_i, intercept_i = np.polyfit(b_fit, v_fit, 1)
        self.intercept_check = intercept_i

        # 4. R^2 dla prostej przez zero (względem średniej, w zakresie dopasowania)
        v_hat = self.sensitivity * b_fit
        ss_res = np.sum((v_fit - v_hat) ** 2)
        ss_tot = np.sum((v_fit - np.mean(v_fit)) ** 2)
        self.r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

        # 5. INL w zakresie dopasowania, odniesione do FS = S * B_max zakresu
        full_scale = self.sensitivity * np.max(b_fit)
        self.inl_max_pct = np.max(np.abs(v_fit - v_hat)) / full_scale * 100.0

        # 6. Błąd względny w KAŻDYM punkcie (także poza zakresem dopasowania)
        self.rel_error_pct = ((v / b) / self.sensitivity - 1.0) * 100.0

        # 7. Błąd czułości względem noty
        if self.s_nominal:
            self.sensitivity_error_pct = (self.sensitivity / self.s_nominal - 1.0) * 100.0

        return {
            "Sensitivity_mV_per_uT": self.sensitivity,
            "Sensitivity_u_mV_per_uT": self.sensitivity_u,
            "Sensitivity_LS_mV_per_uT": self.sensitivity_ls,
            "Intercept_check_mV": self.intercept_check,
            "R_Squared": self.r_squared,
            "Max_INL_Error_%FS": self.inl_max_pct,
            "Max_abs_rel_error_%_full_range": np.max(np.abs(self.rel_error_pct)),
            "Sensitivity_error_vs_nominal_%": self.sensitivity_error_pct,
            "Fit_range_uT": self.fit_range,
        }

    # ---------------------------------------------------------------- wykresy
    def plot_graphs(self, filename=None):
        if self.sensitivity is None:
            self.calculate_params()

        b, v = self.ref_fundamental, self.meas_fundamental
        in_fit = (b >= self.fit_range[0]) & (b <= self.fit_range[1])

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

        # --- Charakterystyka przetwarzania
        ax1.scatter(b[in_fit], v[in_fit], color='red', zorder=5, label='Punkty w zakresie dopasowania')
        ax1.scatter(b[~in_fit], v[~in_fit], facecolors='none', edgecolors='red', zorder=5,
                    label='Punkty poza zakresem dopasowania')
        b_line = np.linspace(0, np.max(b), 200)
        ax1.plot(b_line, self.sensitivity * b_line, 'b--', label='Dopasowanie S·B')
        ax1.axvspan(*self.fit_range, color='blue', alpha=0.05)
        ax1.set_title('Charakterystyka przetwarzania, 50 Hz')
        ax1.set_xlabel('Pole referencyjne 50 Hz RMS [µT]')
        ax1.set_ylabel('Napięcie wyjściowe czujnika 50 Hz RMS [mV]')
        txt = (f"S = {self.sensitivity:.4f} ± {self.sensitivity_u:.4f} mV/µT\n"
               f"R² = {self.r_squared:.6f}\n"
               f"INL = {self.inl_max_pct:.3f} % FS")
        if self.sensitivity_error_pct is not None:
            txt += f"\nε_S = {self.sensitivity_error_pct:+.2f} %"
        ax1.text(0.05, 0.95, txt, transform=ax1.transAxes, va='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        ax1.legend(loc='lower right')
        ax1.grid(True, linestyle=':', alpha=0.7)

        # --- Błąd względny w funkcji pola
        ax2.plot(b, self.rel_error_pct, marker='o', color='purple')
        ax2.axhline(0, color='black', linewidth=1)
        ax2.axvspan(*self.fit_range, color='blue', alpha=0.05)
        ax2.set_title('Błąd względny czułości ε(B)')
        ax2.set_xlabel('Pole referencyjne 50 Hz RMS [µT]')
        ax2.set_ylabel('ε(B) [%]')
        ax2.grid(True, linestyle=':', alpha=0.7)

        # --- THD czujnika i referencji
        ax3.plot(b, self.meas_thd, marker='o', color='green', label='THD czujnika')
        ax3.plot(b, self.ref_thd, marker='s', color='gray', linestyle='--', label='THD referencji')
        ax3.set_title('Liniowość dynamiczna (THD a wartość skuteczna pola)')
        ax3.set_xlabel('Pole referencyjne 50 Hz RMS [µT]')
        ax3.set_ylabel('THD [%]')
        ax3.set_ylim(bottom=0)
        ax3.legend()
        ax3.grid(True, linestyle=':', alpha=0.7)

        plt.tight_layout()
        if filename:
            plt.savefig(filename, dpi=300)
        else:
            plt.show()