import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from signal_processing import SignalProcessing


class SignalValidator:
    def __init__(self, meas_signal: SignalProcessing, ref_signal: SignalProcessing, f0=50, max_freq=2500, sampling_rate=10e3):
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
        self.B_ref = (self.ref_signal.dac_values - self.ref_signal.offset) * self.ref_signal.helmholtz_coil_B_uT_factor

        # Oś czasu (przy założeniu identycznego próbkowania dla obu sygnałów)
        self.t = np.array(self.meas_signal.t)
        self.N = len(self.t)
        self.dt = self.t[1] - self.t[0]



        # Słowniki na wyniki
        self.time_metrics = {}
        self.freq_metrics = {}

        self.meas_harmonics = self.meas_signal.calculate_IEEE_harmonics()
        self.ref_harmonics = self.ref_signal.calculate_IEEE_harmonics()

        self.fundamental_rms_meas = 1.0
        self.fundamental_rms_ref = 1.0
        for harmonic_dict in self.meas_harmonics:
            if harmonic_dict['harmonic'] == 1:
                self.fundamental_rms_meas = harmonic_dict['harmonic'] * self.meas_signal.sensor_B_uT_factor
                break
        for harmonic_dict in self.ref_harmonics:
            if harmonic_dict['harmonic'] == 1:
                self.fundamental_rms_ref = harmonic_dict['harmonic'] * self.ref_signal.helmholtz_coil_B_uT_factor
                break
        self.fundamental_ratio = self.fundamental_rms_meas / self.fundamental_rms_ref

        # Wektor błędu resztkowego
        self.e = self.B_meas - self.B_ref
        # self.e /= self.fundamental_ratio

        self._calculate_time_domain_metrics()
        self._calculate_frequency_domain_metrics()

    def _calculate_time_domain_metrics(self):
        """Oblicza błędy w dziedzinie czasu (NRMSE, MAXE)."""
        B_ref_rms = np.sqrt(np.mean(self.B_ref ** 2))

        # Znormalizowany błąd średniokwadratowy [%]
        nrmse = (np.sqrt(np.mean(self.e ** 2)) / B_ref_rms) / self.fundamental_ratio * 100.0

        # Maksymalny błąd względem Bmeas_50/Bref_50 [uT]
        maxe = np.max(np.abs(self.e))

        self.time_metrics = {
            'NRMSE': nrmse,
            'MAXE': maxe,
            'B_ref_RMS': B_ref_rms
        }

    def _calculate_frequency_domain_metrics(self):
        """
        Oblicza błędy dla poszczególnych harmonicznych z wykorzystaniem
        listy słowników self.fft.harmonics_amp wyliczonej uprzednio w SignalProcessing.
        """
        # Współczynniki konwersji na pole magnetyczne B w [uT]
        meas_factor = self.meas_signal.sensor_B_uT_factor
        ref_factor = (self.ref_signal.helmholtz_coil_B_uT_factor
                      if self.ref_signal.helmholtz_coil
                      else self.ref_signal.sensor_B_uT_factor)


        # Zamiana na słowniki, gdzie kluczem jest rząd harmonicznej (h) w celu łatwego parowania
        meas_dict = {h['harmonic']: h for h in self.meas_harmonics}
        ref_dict = {h['harmonic']: h for h in self.ref_harmonics}

        harmonics_h = []
        delta_A_h = []
        delta_phi_h = []
        A_meas_list = []
        A_ref_list = []
        f_h_list = []

        # Ograniczamy analizę do maksymalnej częstotliwości badanej
        max_h = int(self.max_freq / self.f0)

        for h in range(1, max_h + 1):
            if h in meas_dict and h in ref_dict:
                m_h = meas_dict[h]
                r_h = ref_dict[h]

                # UWAGA: W słowniku przechowywane są wartości RMS dla danych RAW.
                # W celu przeliczenia na amplitudę w mikrateslach [uT],
                # mnożymy przez współczynnik skali czujnika/cewki oraz przez pierwiastek z 2.
                A_meas = m_h['rms'] * meas_factor * np.sqrt(2)
                A_ref = r_h['rms'] * ref_factor * np.sqrt(2)

                phi_meas = m_h['phase']
                phi_ref = r_h['phase']

                # Względny błąd amplitudy harmonicznej dAh [%]
                if A_ref > 0:
                    dA = ((A_meas - A_ref) / A_ref) * 100.0
                else:
                    # Zabezpieczenie przed dzieleniem przez zero
                    # (gdy składowa nie wybiła się ponad szum w referencji)
                    dA = 0.0

                # Błąd kąta fazowego dPhi [stopnie]
                # Zawinięcie błędu do przedziału (-180, 180]
                dPhi = phi_meas - phi_ref
                dPhi = (dPhi + 180) % 360 - 180

                harmonics_h.append(h)
                f_h_list.append(r_h['frequency'])
                delta_A_h.append(dA)
                delta_phi_h.append(dPhi)
                A_meas_list.append(A_meas)
                A_ref_list.append(A_ref)

        # Zapis wyników do słownika kompatybilnego z istniejącą metodą plot_validation
        self.freq_metrics = {
            'h': np.array(harmonics_h),
            'f_h': np.array(f_h_list),
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
        Generuje 2-panelowy wykres walidacyjny:
        Panel 1: Przebiegi czasowe z wykresem błędu resztkowego.
        Panel 2: Względne harmoniczne (% składowej podstawowej) ze zlogarytmizowaną osią.

        :param periods_to_show: Liczba okresów składowej podstawowej do wyświetlenia na wykresie czasowym.
        :param save_path: Opcjonalna ścieżka do zapisu pliku.
        """
        # === OBLICZENIA DLA PANELU 2 (Wartości względne i THD) ===
        try:
            idx_fund = np.where(self.freq_metrics['h'] == 1)[0][0]
        except IndexError:
            raise ValueError("Brak składowej podstawowej (h=1) w metrykach częstotliwościowych.")

        A_meas_fund = self.freq_metrics['A_meas'][idx_fund]
        A_ref_fund = self.freq_metrics['A_ref'][idx_fund]

        if A_meas_fund == 0 or A_ref_fund == 0:
            raise ValueError("Amplituda składowej podstawowej wynosi 0, nie można wyliczyć wartości względnych.")

        # Obliczenia wartości procentowych [%]
        meas_rel_perc = (self.freq_metrics['A_meas'] / A_meas_fund) * 100.0
        ref_rel_perc = (self.freq_metrics['A_ref'] / A_ref_fund) * 100.0

        # Obliczenia THD (Total Harmonic Distortion) [%]
        mask_harmonics = self.freq_metrics['h'] > 1
        thd_meas = (np.sqrt(np.sum(self.freq_metrics['A_meas'][mask_harmonics] ** 2)) / A_meas_fund) * 100.0
        thd_ref = (np.sqrt(np.sum(self.freq_metrics['A_ref'][mask_harmonics] ** 2)) / A_ref_fund) * 100.0

        # Wypisanie wyników w konsoli
        print("\n=== Względna analiza harmonicznych (odniesienie do h=1) ===")
        print(f"THD Referencyjne: {thd_ref:.4f} %")
        print(f"THD Pomiarowe:    {thd_meas:.4f} %")
        print("-" * 65)
        print(f"{'Rząd (h)':>8} | {'Czest. [Hz]':>11} | {'Ref [% z h=1]':>15} | {'Pomiar [% z h=1]':>16}")

        for i, h in enumerate(self.freq_metrics['h']):
            print(f"{h:8d} | {self.freq_metrics['f_h'][i]:11.1f} | {ref_rel_perc[i]:15.4f} | {meas_rel_perc[i]:16.4f}")

        # === INICJALIZACJA WYKRESU ===
        fig = plt.figure(figsize=(14, 10))
        # GridSpec: 3 wiersze (Przebieg, Błąd, Widmo względne)
        gs = GridSpec(3, 1, height_ratios=[2, 1, 2.5])
        gs.update(hspace=0.4)

        # === PANEL 1: Przebiegi czasowe z wykresem błędu resztkowego ===
        samples_per_period = 1.0 / (self.f0 * self.dt)
        plot_samples = int(periods_to_show * samples_per_period)

        ax_time = fig.add_subplot(gs[0])
        ax_res = fig.add_subplot(gs[1], sharex=ax_time)

        t_plot = self.t[:plot_samples] * 1000  # konwersja na ms

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

        # === PANEL 2: Widmo procentowe harmonicznych względem składowej podstawowej ===
        ax_fft = fig.add_subplot(gs[2])
        f_h = self.freq_metrics['f_h']

        # Przesunięcie słupków obok siebie dla czytelności
        offset_bar = self.f0 * 0.1

        markerline1, stemlines1, baseline1 = ax_fft.stem(f_h - offset_bar, ref_rel_perc, linefmt='k-', markerfmt='ko',
                                                         basefmt='k-')
        markerline2, stemlines2, baseline2 = ax_fft.stem(f_h + offset_bar, meas_rel_perc, linefmt='r--', markerfmt='rx',
                                                         basefmt='r-')

        markerline1.set_label('Referencja [%]')
        markerline2.set_label('Pomiar [%]')

        ax_fft.set_yscale('log')
        ax_fft.set_xlim([0, self.max_freq + self.f0])
        ax_fft.set_title(f'Panel 2: Porównawcze widmo procentowe względem składowej podstawowej ({self.f0} Hz)\n'
                         f'THD referencyjne: {thd_ref:.2f}%, THD zmierzone: {thd_meas:.2f}%')
        ax_fft.set_ylabel('Wartość harmonicznej jako % składowej podstawowej [%]')
        ax_fft.set_xlabel('Częstotliwość [Hz]')

        # Gęstsza siatka dla osi logarytmicznej
        ax_fft.grid(True, which='both', linestyle=':', alpha=0.7)
        ax_fft.legend(loc='upper right')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.tight_layout()
        plt.show()

    def plot_validation_legacy(self, periods_to_show=3, save_path=None):
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

    def analyze_and_plot_relative_harmonics(self, save_path=None):
        """
        Wylicza i wyświetla udziały procentowe wyższych harmonicznych
        względem harmonicznej podstawowej (h=1) oraz oblicza THD.
        Osobny, zlogarytmizowany wykres ułatwia analizę.
        """
        # 1. Znalezienie indeksu składowej podstawowej (h=1)
        try:
            idx_fund = np.where(self.freq_metrics['h'] == 1)[0][0]
        except IndexError:
            raise ValueError("Brak składowej podstawowej (h=1) w metrykach częstotliwościowych.")

        A_meas_fund = self.freq_metrics['A_meas'][idx_fund]
        A_ref_fund = self.freq_metrics['A_ref'][idx_fund]

        if A_meas_fund == 0 or A_ref_fund == 0:
            raise ValueError("Amplituda składowej podstawowej wynosi 0, nie można wyliczyć wartości względnych.")

        # 2. Obliczenia wartości procentowych [%]
        meas_rel_perc = (self.freq_metrics['A_meas'] / A_meas_fund) * 100.0
        ref_rel_perc = (self.freq_metrics['A_ref'] / A_ref_fund) * 100.0

        # 3. Obliczenia THD (Total Harmonic Distortion) [%]
        # THD = sqrt(suma kwadratów harmonicznych > 1) / amplituda(h=1)
        mask_harmonics = self.freq_metrics['h'] > 1
        thd_meas = (np.sqrt(np.sum(self.freq_metrics['A_meas'][mask_harmonics] ** 2)) / A_meas_fund) * 100.0
        thd_ref = (np.sqrt(np.sum(self.freq_metrics['A_ref'][mask_harmonics] ** 2)) / A_ref_fund) * 100.0

        # 4. Wypisanie wyników (Print)
        print("\n=== Względna analiza harmonicznych (odniesienie do h=1) ===")
        print(f"THD Referencyjne: {thd_ref:.4f} %")
        print(f"THD Pomiarowe:    {thd_meas:.4f} %")
        print("-" * 65)
        print(f"{'Rząd (h)':>8} | {'Czest. [Hz]':>11} | {'Ref [% z h=1]':>15} | {'Pomiar [% z h=1]':>16}")

        for i, h in enumerate(self.freq_metrics['h']):
            print(f"{h:8d} | {self.freq_metrics['f_h'][i]:11.1f} | {ref_rel_perc[i]:15.4f} | {meas_rel_perc[i]:16.4f}")

        # 5. Generowanie wykresu (Logarithmic Stem Plot)
        fig, ax = plt.subplots(figsize=(12, 6))
        f_h = self.freq_metrics['f_h']

        # Przesunięcie słupków na osi X, żeby na siebie nie nachodziły
        offset_bar = self.f0 * 0.1

        # Rysowanie słupków
        markerline1, stemlines1, baseline1 = ax.stem(f_h - offset_bar, ref_rel_perc,
                                                     linefmt='k-', markerfmt='ko', basefmt='k-')
        markerline2, stemlines2, baseline2 = ax.stem(f_h + offset_bar, meas_rel_perc,
                                                     linefmt='r--', markerfmt='rx', basefmt='r-')

        markerline1.set_label('Referencja [%]')
        markerline2.set_label('Pomiar [%]')

        # Konfiguracja osi i wyglądu
        ax.set_yscale('log')
        ax.set_xlim([0, self.max_freq + self.f0])
        ax.set_title(f'Porównawcze widmo procentowe względem składowej podstawowej ({self.f0} Hz)\n'
                     f'THD referencyne: {thd_ref:.2f}%, THD zmierzone: {thd_meas:.2f}%')
        ax.set_ylabel('Wartość harmonicznej jako % składowej podstawowej [%]')
        ax.set_xlabel('Częstotliwość [Hz]')

        # Gęstsza siatka dla osi logarytmicznej
        ax.grid(True, which='both', linestyle=':', alpha=0.7)
        ax.legend(loc='upper right')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    # validator = SignalValidator(meas_signal=meas_signal_obj, ref_signal=ref_signal_obj)
    # validator.print_report()
    # validator.plot_validation(periods_to_show=3, save_path="wyniki/walidacja_zlozona.png")
    pass