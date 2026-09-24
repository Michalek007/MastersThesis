import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from signal_processing import SignalProcessing


class SignalValidator:
    def __init__(self, meas_signal, ref_signal, f0=50, max_freq=2500):
        """
        Klasa służąca do walidacji sygnału z czujnika względem sygnału referencyjnego.

        :param meas_signal: Obiekt SignalProcessing zawierający dane z testowanego czujnika.
        :param ref_signal: Obiekt SignalProcessing zawierający dane referencyjne (np. cewki).
        :param f0: Częstotliwość podstawowa [Hz].
        :param max_freq: Maksymalna badana częstotliwość harmoniczna [Hz].
        """
        self.meas_signal = meas_signal
        self.ref_signal = ref_signal
        self.f0 = f0
        self.max_freq = max_freq

        # Konwersja próbek DAC na pole magnetyczne B w mikrateslach [uT]
        self.B_meas = (self.meas_signal.dac_values - self.meas_signal.offset) * self.meas_signal.sensor_B_uT_factor
        self.B_ref = (self.ref_signal.dac_values - self.ref_signal.offset) * (
            self.ref_signal.helmholtz_coil_B_uT_factor if self.ref_signal.helmholtz_coil
            else self.ref_signal.sensor_B_uT_factor
        )

        # Oś czasu (przy założeniu identycznego próbkowania dla obu sygnałów)
        self.t = np.array(self.meas_signal.t)
        self.N = len(self.t)
        self.dt = self.t[1] - self.t[0]

        # Wektor błędu resztkowego
        self.e = self.B_meas - self.B_ref

        # Słowniki na wyniki
        self.time_metrics = {}
        self.freq_metrics = {}

        self._calculate_time_domain_metrics()
        self._calculate_frequency_domain_metrics()

    def _calculate_time_domain_metrics(self):
        """Oblicza błędy w dziedzinie czasu (NRMSE, MAXE)."""
        B_ref_rms = np.sqrt(np.mean(self.B_ref ** 2))

        # Znormalizowany błąd średniokwadratowy [%]
        nrmse = (np.sqrt(np.mean(self.e ** 2)) / B_ref_rms) * 100.0

        # Maksymalny błąd bezwzględny [uT]
        maxe = np.max(np.abs(self.e))

        self.time_metrics = {
            'NRMSE': nrmse,
            'MAXE': maxe,
            'B_ref_RMS': B_ref_rms
        }

    def _calculate_frequency_domain_metrics(self):
        """Oblicza błędy transformaty dla poszczególnych harmonicznych."""
        # Obliczenie transformaty Fouriera dla obu sygnałów
        fft_meas = np.fft.rfft(self.B_meas) / self.N
        fft_ref = np.fft.rfft(self.B_ref) / self.N
        freqs = np.fft.rfftfreq(self.N, d=self.dt)

        harmonics_h = []
        delta_A_h = []
        delta_phi_h = []
        A_meas_list, A_ref_list = [], []

        # Obliczanie błędów dla każdej harmonicznej aż do max_freq
        max_h = int(self.max_freq / self.f0)

        for h in range(1, max_h + 1):
            f_h = h * self.f0
            # Znalezienie indeksu najbliższej częstotliwości w widmie
            idx = np.argmin(np.abs(freqs - f_h))

            # Amplitudy (wymagają pomnożenia przez 2, z wyjątkiem DC, ale tutaj badamy składowe AC)
            A_meas = 2 * np.abs(fft_meas[idx])
            A_ref = 2 * np.abs(fft_ref[idx])

            # Kąty fazowe w stopniach
            phi_meas = np.degrees(np.angle(fft_meas[idx]))
            phi_ref = np.degrees(np.angle(fft_ref[idx]))

            # Względny błąd amplitudy harmonicznej [%]
            if A_ref > 0:
                dA = ((A_meas - A_ref) / A_ref) * 100.0
            else:
                dA = 0.0

            # Błąd kąta fazowego [stopnie] z zawinięciem do (-180, 180]
            dPhi = phi_meas - phi_ref
            dPhi = (dPhi + 180) % 360 - 180

            harmonics_h.append(h)
            delta_A_h.append(dA)
            delta_phi_h.append(dPhi)

            A_meas_list.append(A_meas)
            A_ref_list.append(A_ref)

        self.freq_metrics = {
            'h': np.array(harmonics_h),
            'f_h': np.array(harmonics_h) * self.f0,
            'delta_A': np.array(delta_A_h),
            'delta_phi': np.array(delta_phi_h),
            'A_meas': np.array(A_meas_list),
            'A_ref': np.array(A_ref_list)
        }

    def print_report(self):
        """Wypisuje podsumowanie walidacji w konsoli."""
        print("=== Raport walidacji czujnika ===")
        print(f"NRMSE (Znormalizowany błąd średniokwadratowy): {self.time_metrics['NRMSE']:.4f} %")
        print(f"MAXE (Maksymalny błąd bezwzględny): {self.time_metrics['MAXE']:.4f} uT")
        print("---------------------------------")
        print(" Błędy harmonicznych:")
        print(f"{'Rząd (h)':>8} | {'Czest. [Hz]':>11} | {'Błąd dAh [%]':>12} | {'Błąd dPhi [deg]':>15}")
        for i, h in enumerate(self.freq_metrics['h']):
            print(
                f"{h:8d} | {self.freq_metrics['f_h'][i]:11.1f} | {self.freq_metrics['delta_A'][i]:12.4f} | {self.freq_metrics['delta_phi'][i]:15.4f}")

    def plot_validation(self, periods_to_show=3, save_path=None):
        """
        Generuje 3-panelowy wykres walidacyjny opisany w metodyce.

        :param periods_to_show: Liczba okresów składowej podstawowej do wyświetlenia na wykresie czasowym.
        :param save_path: Opcjonalna ścieżka do zapisu pliku (np. 'walidacja.png').
        """
        fig = plt.figure(figsize=(14, 12))
        # Layout za pomocą GridSpec:
        # Górny panel (dziedzina czasu) ma 2 wiersze: przebiegi oraz błąd resztkowy
        # Środkowy panel: widmo słupkowe (stem plot)
        # Dolny panel: błędy harmonicznych (scatter)
        gs = GridSpec(4, 1, height_ratios=[2, 1, 1.5, 1.5])
        gs.update(hspace=0.4)

        # === PANEL 1: Przebiegi czasowe z wykresem błędu resztkowego ===
        # Wyliczenie liczby próbek do pokazania
        samples_per_period = 1.0 / (self.f0 * self.dt)
        plot_samples = int(periods_to_show * samples_per_period)

        ax_time = fig.add_subplot(gs[0])
        ax_res = fig.add_subplot(gs[1], sharex=ax_time)

        t_plot = self.t[:plot_samples] * 1000  # konwersja na ms dla czytelności

        ax_time.plot(t_plot, self.B_ref[:plot_samples], label=r'$B_{ref}$ (Referencja)', color='black', linewidth=1.5)
        ax_time.plot(t_plot, self.B_meas[:plot_samples], label=r'$B_{meas}$ (Pomiar)', color='red', linestyle='--',
                     linewidth=1.5)
        ax_time.set_ylabel(r'Pole magnetyczne [$\mu$T]')
        ax_time.set_title(
            f'Panel 1: Przebiegi czasowe (NRMSE: {self.time_metrics["NRMSE"]:.2f}%, MAXE: {self.time_metrics["MAXE"]:.2f} $\mu$T)')
        ax_time.grid(True, linestyle=':', alpha=0.7)
        ax_time.legend(loc='upper right')

        ax_res.plot(t_plot, self.e[:plot_samples], color='blue', linewidth=1)
        ax_res.fill_between(t_plot, self.e[:plot_samples], color='blue', alpha=0.1)
        ax_res.set_ylabel(r'Błąd $e[n]$ [$\mu$T]')
        ax_res.set_xlabel('Czas [ms]')
        ax_res.grid(True, linestyle=':', alpha=0.7)

        # === PANEL 2: Porównawcze widmo amplitudowe (Logarithmic Stem Plot) ===
        ax_fft = fig.add_subplot(gs[2])
        f_h = self.freq_metrics['f_h']

        # Przesunięcie słupków obok siebie dla czytelności
        offset_bar = self.f0 * 0.1

        markerline1, stemlines1, baseline1 = ax_fft.stem(f_h - offset_bar, self.freq_metrics['A_ref'], linefmt='k-',
                                                         markerfmt='ko', basefmt='k-')
        markerline2, stemlines2, baseline2 = ax_fft.stem(f_h + offset_bar, self.freq_metrics['A_meas'], linefmt='r--',
                                                         markerfmt='rx', basefmt='r-')

        markerline1.set_label('Amplituda - Referencja')
        markerline2.set_label('Amplituda - Pomiar')

        ax_fft.set_yscale('log')
        ax_fft.set_xlim([0, self.max_freq + self.f0])
        ax_fft.set_title('Panel 2: Porównawcze widmo amplitudowe zlogarytmizowane')
        ax_fft.set_ylabel(r'Amplituda [$\mu$T]')
        ax_fft.set_xlabel('Częstotliwość [Hz]')
        ax_fft.grid(True, which='both', linestyle=':', alpha=0.7)
        ax_fft.legend(loc='upper right')

        # === PANEL 3: Profil błędów harmonicznych ===
        ax_err_amp = fig.add_subplot(gs[3])
        ax_err_phi = ax_err_amp.twinx()  # Podwójna oś Y

        h_array = self.freq_metrics['h']

        ax_err_amp.scatter(h_array, self.freq_metrics['delta_A'], color='blue', marker='s', s=40,
                           label=r'Błąd amplitudy $\delta A_h$')
        ax_err_phi.scatter(h_array, self.freq_metrics['delta_phi'], color='darkorange', marker='^', s=40,
                           label=r'Błąd fazy $\Delta \phi_h$')

        # Normatywne limity błędu +/- 5%
        ax_err_amp.axhline(5, color='blue', linestyle=':', alpha=0.5)
        ax_err_amp.axhline(-5, color='blue', linestyle=':', alpha=0.5)

        ax_err_amp.set_title('Panel 3: Profil błędów harmonicznych')
        ax_err_amp.set_xlabel('Rząd harmonicznej ($h$)')
        ax_err_amp.set_ylabel(r'Względny błąd amplitudy $\delta A_h$ [%]', color='blue')
        ax_err_phi.set_ylabel(r'Błąd kąta fazowego $\Delta \phi_h$ [$^\circ$]', color='darkorange')

        ax_err_amp.tick_params(axis='y', labelcolor='blue')
        ax_err_phi.tick_params(axis='y', labelcolor='darkorange')
        ax_err_amp.set_xticks(h_array)
        ax_err_amp.grid(True, linestyle=':', alpha=0.7)

        # Łączenie legend dla obu osi w panelu 3
        lines_1, labels_1 = ax_err_amp.get_legend_handles_labels()
        lines_2, labels_2 = ax_err_phi.get_legend_handles_labels()
        ax_err_amp.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    # validator = SignalValidator(meas_signal=meas_signal_obj, ref_signal=ref_signal_obj)
    # validator.print_report()
    # validator.plot_validation(periods_to_show=3, save_path="wyniki/walidacja_zlozona.png")
    pass