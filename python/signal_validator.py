import csv
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from signal_processing import SignalProcessing


class SignalValidator:
    def __init__(self, meas_signal: SignalProcessing, ref_signal: SignalProcessing,
                 f0=50, max_freq=2500, sampling_rate=10e3,
                 phase_in_radians=False, phase_min_rel_perc=0.1):
        """
        Klasa służąca do walidacji sygnału z czujnika względem sygnału referencyjnego.

        :param meas_signal: Obiekt SignalProcessing zawierający dane z testowanego czujnika.
        :param ref_signal: Obiekt SignalProcessing zawierający dane referencyjne (np. cewki).
        :param f0: Częstotliwość podstawowa [Hz].
        :param max_freq: Maksymalna badana częstotliwość harmoniczna [Hz].
        :param phase_in_radians: True, jeśli calculate_IEEE_harmonics zwraca fazę w radianach.
        :param phase_min_rel_perc: Próg istotności harmonicznej [% składowej podstawowej].
                                   Błędy amplitudy są wyznaczane, gdy udział w referencji
                                   przekracza próg; błąd fazy - gdy przekracza go w obu
                                   sygnałach (faza prążka na poziomie szumu jest losowa).
        """
        self.meas_signal = meas_signal
        self.ref_signal = ref_signal
        self.f0 = f0
        self.max_freq = max_freq
        self.phase_in_radians = phase_in_radians
        self.phase_min_rel_perc = phase_min_rel_perc

        # Współczynniki konwersji na pole magnetyczne B w [uT]
        self._meas_factor = self.meas_signal.sensor_B_uT_factor
        self._ref_factor = (self.ref_signal.helmholtz_coil_B_uT_factor
                            if self.ref_signal.helmholtz_coil
                            else self.ref_signal.sensor_B_uT_factor)

        # Oś czasu (przy założeniu identycznego, synchronicznego próbkowania obu sygnałów)
        self.t = np.array(self.meas_signal.t)
        self.N = len(self.t)
        self.dt = self.t[1] - self.t[0]

        # Konwersja próbek na pole magnetyczne B [uT]
        B_meas = (np.asarray(self.meas_signal.dac_values) - self.meas_signal.offset) * self._meas_factor
        B_ref = (np.asarray(self.ref_signal.dac_values) - self.ref_signal.offset) * self._ref_factor

        # Usunięcie składowej stałej (średnia z całkowitej liczby okresów f0).
        # Wzór (3.16) zakłada sygnały o zerowej wartości średniej.
        n_int = self._samples_in_integer_periods()
        self.B_meas = B_meas - np.mean(B_meas[:n_int])
        self.B_ref = B_ref - np.mean(B_ref[:n_int])

        # Wektor błędu bez korekcji (wzór 3.20)
        self.e = self.B_meas - self.B_ref
        # Współczynnik skali (wzór 3.16) i wektor błędu kształtu
        self.alpha = np.sum(self.B_meas * self.B_ref) / np.sum(self.B_ref ** 2)
        self.e_alpha = self.B_meas - self.alpha * self.B_ref

        # Harmoniczne z SignalProcessing
        self.meas_harmonics = self.meas_signal.calculate_IEEE_harmonics()
        self.ref_harmonics = self.ref_signal.calculate_IEEE_harmonics()

        self.time_metrics = {}
        self.freq_metrics = {}
        self._calculate_time_domain_metrics()
        self._calculate_frequency_domain_metrics()

    # ------------------------------------------------------------------
    # Obliczenia
    # ------------------------------------------------------------------
    def _samples_in_integer_periods(self):
        """Liczba próbek odpowiadająca największej całkowitej liczbie okresów f0."""
        samples_per_period = 1.0 / (self.f0 * self.dt)
        n_periods = int(np.floor(self.N / samples_per_period))
        if n_periods < 1:
            return self.N
        return int(round(n_periods * samples_per_period))

    def _calculate_time_domain_metrics(self):
        """Oblicza błędy w dziedzinie czasu (NRMSE, MAXE, e_RMS) po korekcji skali."""
        B_ref_rms = np.sqrt(np.mean(self.B_ref ** 2))

        e_rms_raw = np.sqrt(np.mean(self.e ** 2))
        e_rms = np.sqrt(np.mean(self.e_alpha ** 2))

        nrmse_raw = e_rms_raw / B_ref_rms * 100.0
        nrmse_alpha = e_rms / (self.alpha * B_ref_rms) * 100.0

        self.time_metrics = {
            'NRMSE': nrmse_alpha,                        # [%], po korekcji alfa
            'NRMSE_raw': nrmse_raw,                      # [%], bez korekcji
            'alpha': self.alpha,                         # [-]
            'MAXE': np.max(np.abs(self.e_alpha)),        # [uT], po korekcji alfa
            'e_RMS': e_rms,                              # [uT], po korekcji alfa
            'B_ref_RMS': B_ref_rms,                      # [uT]
        }

    def _phase_deg(self, phase):
        return np.degrees(phase) if self.phase_in_radians else phase

    def _calculate_frequency_domain_metrics(self):
        """
        Oblicza błędy amplitudy i fazy dla harmonicznych h = 1 ... max_freq/f0.
        Harmoniczne nieobecne w którymkolwiek sygnale otrzymują wartości NaN.
        """
        meas_dict = {h['harmonic']: h for h in self.meas_harmonics}
        ref_dict = {h['harmonic']: h for h in self.ref_harmonics}

        max_h = int(self.max_freq / self.f0)

        h_arr = np.arange(1, max_h + 1)
        f_h = h_arr * float(self.f0)
        A_meas = np.full(max_h, np.nan)
        A_ref = np.full(max_h, np.nan)
        phi_meas = np.full(max_h, np.nan)
        phi_ref = np.full(max_h, np.nan)

        for i, h in enumerate(h_arr):
            if h in meas_dict:
                A_meas[i] = meas_dict[h]['rms'] * self._meas_factor * np.sqrt(2)
                phi_meas[i] = self._phase_deg(meas_dict[h]['phase'])
            if h in ref_dict:
                A_ref[i] = ref_dict[h]['rms'] * self._ref_factor * np.sqrt(2)
                phi_ref[i] = self._phase_deg(ref_dict[h]['phase'])
                f_h[i] = ref_dict[h]['frequency']

        if np.isnan(A_meas[0]) or np.isnan(A_ref[0]) or A_meas[0] == 0 or A_ref[0] == 0:
            raise ValueError("Brak składowej podstawowej (h=1) w jednym z sygnałów.")

        # Udziały względem składowej podstawowej [%]
        meas_rel = A_meas / A_meas[0] * 100.0
        ref_rel = A_ref / A_ref[0] * 100.0

        with np.errstate(divide='ignore', invalid='ignore'):
            # Względny błąd amplitudy (wzór 3.23) - zawiera błąd skali
            delta_A = np.where(A_ref > 0, (A_meas - A_ref) / A_ref * 100.0, np.nan)
            # Względny błąd udziału harmonicznej h_n = A_n/A_1 - niewrażliwy na błąd skali
            delta_A_rel = np.where(ref_rel > 0, (meas_rel - ref_rel) / ref_rel * 100.0, np.nan)

        # Błąd fazy (wzór 3.24), zawinięty do przedziału [-180, 180)
        delta_phi = phi_meas - phi_ref
        delta_phi = (delta_phi + 180.0) % 360.0 - 180.0

        # Błędy amplitudy wyznaczane tylko dla harmonicznych obecnych w sygnale referencyjnym
        # (dla składowych na poziomie szumu referencji błąd względny nie ma sensu fizycznego)
        in_ref = ref_rel >= self.phase_min_rel_perc
        in_ref[0] = True
        delta_A = np.where(in_ref, delta_A, np.nan)
        delta_A_rel = np.where(in_ref, delta_A_rel, np.nan)

        # Faza wyznaczana tylko dla harmonicznych wyraźnie obecnych w obu sygnałach
        significant = in_ref & (meas_rel >= self.phase_min_rel_perc)
        significant[0] = True
        delta_phi = np.where(significant, delta_phi, np.nan)

        # THD na podstawie harmonicznych obecnych w obu sygnałach
        mask = (h_arr > 1) & ~np.isnan(A_meas) & ~np.isnan(A_ref)
        thd_meas = np.sqrt(np.sum(A_meas[mask] ** 2)) / A_meas[0] * 100.0
        thd_ref = np.sqrt(np.sum(A_ref[mask] ** 2)) / A_ref[0] * 100.0

        self.freq_metrics = {
            'h': h_arr,
            'f_h': f_h,
            'A_meas': A_meas,
            'A_ref': A_ref,
            'meas_rel_perc': meas_rel,
            'ref_rel_perc': ref_rel,
            'delta_A': delta_A,
            'delta_A_rel': delta_A_rel,
            'delta_phi': delta_phi,
            'THD_meas': thd_meas,
            'THD_ref': thd_ref,
        }

    # ------------------------------------------------------------------
    # Zapis do CSV
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt(value, decimal):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return ''
        if isinstance(value, (int, np.integer)):
            return str(value)
        if isinstance(value, (float, np.floating)):
            s = f"{float(value):.6g}"
            return s.replace('.', decimal) if decimal != '.' else s
        return str(value)

    def save_time_metrics_csv(self, filename, label=None, append=False, delimiter=';', decimal=','):
        """
        Zapisuje metryki w dziedzinie czasu oraz THD do pliku CSV.

        :param filename: Ścieżka do pliku CSV.
        :param label: Opcjonalny opis przypadku (np. 'ALT021_22uT_110kV'), zapisywany w pierwszej kolumnie.
        :param append: True - dopisuje wiersz do istniejącego pliku (nagłówek tylko przy tworzeniu pliku).
        :param delimiter: Separator kolumn (';' dla polskiej wersji Excela).
        :param decimal: Separator dziesiętny (',' dla polskiej wersji Excela).
        """
        columns = ['label', 'NRMSE_perc', 'NRMSE_raw_perc', 'alpha', 'MAXE_uT',
                   'e_RMS_uT', 'B_ref_RMS_uT', 'THD_ref_perc', 'THD_meas_perc', 'delta_THD_pp']
        tm, fm = self.time_metrics, self.freq_metrics
        row = [label if label is not None else '',
               tm['NRMSE'], tm['NRMSE_raw'], tm['alpha'], tm['MAXE'],
               tm['e_RMS'], tm['B_ref_RMS'],
               fm['THD_ref'], fm['THD_meas'], fm['THD_meas'] - fm['THD_ref']]

        write_header = not (append and os.path.exists(filename))
        mode = 'a' if append else 'w'
        with open(filename, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=delimiter)
            if write_header:
                writer.writerow(columns)
            writer.writerow([self._fmt(v, decimal) for v in row])

    def save_harmonics_csv(self, filename, delimiter=';', decimal=','):
        """
        Zapisuje do pliku CSV amplitudy, udziały oraz błędy amplitudy i fazy
        dla harmonicznych h = 1 ... max_freq/f0 (domyślnie 1 ... 50).
        Puste pola oznaczają harmoniczne nieobecne w sygnale lub fazę poniżej progu istotności.
        """
        columns = ['h', 'f_h_Hz', 'A_ref_uT', 'A_meas_uT', 'ref_rel_perc', 'meas_rel_perc',
                   'delta_A_perc', 'delta_A_rel_perc', 'delta_phi_deg']
        fm = self.freq_metrics
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow(columns)
            for i in range(len(fm['h'])):
                row = [int(fm['h'][i]), fm['f_h'][i], fm['A_ref'][i], fm['A_meas'][i],
                       fm['ref_rel_perc'][i], fm['meas_rel_perc'][i],
                       fm['delta_A'][i], fm['delta_A_rel'][i], fm['delta_phi'][i]]
                writer.writerow([self._fmt(v, decimal) for v in row])

    # ------------------------------------------------------------------
    # Raporty i wykresy
    # ------------------------------------------------------------------
    def print_report(self):
        """Wypisuje podsumowanie walidacji w konsoli."""
        tm, fm = self.time_metrics, self.freq_metrics
        print("=== Raport walidacji czujnika ===")
        print(f"alpha:      {tm['alpha']:.5f}")
        print(f"NRMSE:      {tm['NRMSE']:.4f} %  (bez korekcji: {tm['NRMSE_raw']:.4f} %)")
        print(f"MAXE:       {tm['MAXE']:.4f} uT")
        print(f"e_RMS:      {tm['e_RMS'] * 1000:.2f} nT")
        print(f"THD ref / meas: {fm['THD_ref']:.4f} % / {fm['THD_meas']:.4f} %")
        print("---------------------------------")
        print(f"{'h':>3} | {'f [Hz]':>7} | {'ref [%]':>9} | {'meas [%]':>9} | "
              f"{'dA [%]':>9} | {'dA_rel [%]':>10} | {'dPhi [deg]':>10}")
        for i, h in enumerate(fm['h']):
            if np.isnan(fm['A_ref'][i]) and np.isnan(fm['A_meas'][i]):
                continue
            print(f"{h:3d} | {fm['f_h'][i]:7.1f} | {fm['ref_rel_perc'][i]:9.4f} | "
                  f"{fm['meas_rel_perc'][i]:9.4f} | {fm['delta_A'][i]:9.3f} | "
                  f"{fm['delta_A_rel'][i]:10.3f} | {fm['delta_phi'][i]:10.3f}")

    def _plot_time_panels(self, fig, gs_time, gs_err, periods_to_show):
        samples_per_period = 1.0 / (self.f0 * self.dt)
        begin_plot = 2000
        plot_samples = int(periods_to_show * samples_per_period)
        plot_samples += begin_plot
        t_plot = self.t[begin_plot:plot_samples] * 1000  # [ms]

        ax_time = fig.add_subplot(gs_time)
        ax_res = fig.add_subplot(gs_err, sharex=ax_time)

        ax_time.plot(t_plot, self.B_ref[begin_plot:plot_samples], label=r'$B_{ref}$ (Referencja)',
                     color='black', linewidth=1.5)
        ax_time.plot(t_plot, self.B_meas[begin_plot:plot_samples], label=r'$B_{meas}$ (Pomiar)',
                     color='red', linestyle='--', linewidth=1.5)
        ax_time.plot(t_plot, self.alpha * self.B_ref[begin_plot:plot_samples], label=r'$\alpha B_{ref}$',
                     color='gray', linestyle=':', linewidth=1.0)
        ax_time.set_ylabel(r'Pole magnetyczne [$\mu$T]')
        ax_time.set_title(
            f'Panel 1: Przebiegi czasowe ($\\alpha$ = {self.time_metrics["alpha"]:.4f}, '
            f'NRMSE: {self.time_metrics["NRMSE"]:.2f}%, '
            f'MAXE: {self.time_metrics["MAXE"]:.2f} $\\mu$T)')
        ax_time.grid(True, linestyle=':', alpha=0.7)
        ax_time.legend(loc='upper right')

        ax_res.plot(t_plot, self.e_alpha[begin_plot:plot_samples], color='blue', linewidth=1)
        ax_res.fill_between(t_plot, self.e_alpha[begin_plot:plot_samples], color='blue', alpha=0.1)
        ax_res.set_ylabel(r'Błąd kształtu $e_[n]$ [$\mu$T]')
        ax_res.set_xlabel('Czas [ms]')
        ax_res.grid(True, linestyle=':', alpha=0.7)

    def _plot_relative_spectrum(self, ax, title_prefix=''):
        fm = self.freq_metrics
        valid_ref = ~np.isnan(fm['ref_rel_perc'])
        valid_meas = ~np.isnan(fm['meas_rel_perc'])
        offset_bar = self.f0 * 0.1

        ml1, _, _ = ax.stem(fm['f_h'][valid_ref] - offset_bar, fm['ref_rel_perc'][valid_ref],
                            linefmt='k-', markerfmt='ko', basefmt='k-')
        ml2, _, _ = ax.stem(fm['f_h'][valid_meas] + offset_bar, fm['meas_rel_perc'][valid_meas],
                            linefmt='r--', markerfmt='rx', basefmt='r-')
        ml1.set_label('Referencja [%]')
        ml2.set_label('Pomiar [%]')

        ax.set_yscale('log')
        ax.set_xlim([0, self.max_freq + self.f0])
        ax.set_title(f'{title_prefix}Porównawcze widmo procentowe względem składowej podstawowej ({self.f0} Hz)\n'
                     f'THD referencyjne: {fm["THD_ref"]:.2f}%, THD zmierzone: {fm["THD_meas"]:.2f}%')
        ax.set_ylabel('Wartość harmonicznej jako % $B_1$ [%]')
        ax.set_xlabel('Częstotliwość [Hz]')
        ax.grid(True, which='both', linestyle=':', alpha=0.7)
        ax.legend(loc='upper right')

    def plot_validation(self, periods_to_show=3, save_path=None):
        """
        Panel 1: przebiegi czasowe B_ref, B_meas, alpha*B_ref oraz błąd kształtu e_alpha.
        Panel 2: udziały harmonicznych względem składowej podstawowej (skala logarytmiczna).
        """
        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(3, 1, height_ratios=[2, 1, 2.5])
        gs.update(hspace=0.4)

        self._plot_time_panels(fig, gs[0], gs[1], periods_to_show)
        self._plot_relative_spectrum(fig.add_subplot(gs[2]), title_prefix='Panel 2: ')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.tight_layout()
        plt.show()

    def plot_validation_legacy(self, periods_to_show=3, save_path=None):
        """Wykres 3-panelowy: przebiegi, widmo amplitudowe, profil błędów harmonicznych."""
        fm = self.freq_metrics
        fig = plt.figure(figsize=(14, 12))
        gs = GridSpec(4, 1, height_ratios=[2, 1, 1.5, 1.5])
        gs.update(hspace=0.4)

        self._plot_time_panels(fig, gs[0], gs[1], periods_to_show)

        # Panel 2: widmo amplitudowe
        ax_fft = fig.add_subplot(gs[2])
        offset_bar = self.f0 * 0.1
        vr, vm = ~np.isnan(fm['A_ref']), ~np.isnan(fm['A_meas'])
        ml1, _, _ = ax_fft.stem(fm['f_h'][vr] - offset_bar, fm['A_ref'][vr],
                                linefmt='k-', markerfmt='ko', basefmt='k-')
        ml2, _, _ = ax_fft.stem(fm['f_h'][vm] + offset_bar, fm['A_meas'][vm],
                                linefmt='r--', markerfmt='rx', basefmt='r-')
        ml1.set_label('Amplituda - Referencja')
        ml2.set_label('Amplituda - Pomiar')
        ax_fft.set_yscale('log')
        ax_fft.set_xlim([0, self.max_freq + self.f0])
        ax_fft.set_title('Panel 2: Porównawcze widmo amplitudowe zlogarytmizowane')
        ax_fft.set_ylabel(r'Amplituda [$\mu$T]')
        ax_fft.set_xlabel('Częstotliwość [Hz]')
        ax_fft.grid(True, which='both', linestyle=':', alpha=0.7)
        ax_fft.legend(loc='upper right')

        # Panel 3: profil błędów harmonicznych
        ax_amp = fig.add_subplot(gs[3])
        ax_phi = ax_amp.twinx()
        ax_amp.scatter(fm['h'], fm['delta_A_rel'], color='blue', marker='s', s=40,
                       label=r'Błąd udziału harmonicznej $\delta h_n$')
        ax_phi.scatter(fm['h'], fm['delta_phi'], color='darkorange', marker='^', s=40,
                       label=r'Błąd fazy $\Delta \phi_h$')
        ax_amp.axhline(5, color='blue', linestyle=':', alpha=0.5)
        ax_amp.axhline(-5, color='blue', linestyle=':', alpha=0.5)
        ax_amp.set_title('Panel 3: Profil błędów harmonicznych')
        ax_amp.set_xlabel('Rząd harmonicznej ($h$)')
        ax_amp.set_ylabel(r'Względny błąd udziału $\delta h_n$ [%]', color='blue')
        ax_phi.set_ylabel(r'Błąd kąta fazowego $\Delta \phi_h$ [$^\circ$]', color='darkorange')
        ax_amp.tick_params(axis='y', labelcolor='blue')
        ax_phi.tick_params(axis='y', labelcolor='darkorange')
        ax_amp.grid(True, linestyle=':', alpha=0.7)
        l1, lb1 = ax_amp.get_legend_handles_labels()
        l2, lb2 = ax_phi.get_legend_handles_labels()
        ax_amp.legend(l1 + l2, lb1 + lb2, loc='upper left')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.tight_layout()
        plt.show()

    def analyze_and_plot_relative_harmonics(self, save_path=None):
        """Osobny wykres udziałów harmonicznych względem składowej podstawowej."""
        self.print_report()
        fig, ax = plt.subplots(figsize=(12, 6))
        self._plot_relative_spectrum(ax)
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    # validator = SignalValidator(meas_signal=meas_signal_obj, ref_signal=ref_signal_obj)
    # validator.print_report()
    # validator.save_time_metrics_csv("wyniki/metryki_czasowe.csv", label="ALT021_22uT_110kV", append=True)
    # validator.save_harmonics_csv("wyniki/ALT021_22uT_110kV_harmoniczne.csv")
    # validator.plot_validation(periods_to_show=3, save_path="wyniki/walidacja_zlozona.png")
    pass