import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools


class SensorBodeAnalyzer:
    def __init__(self, amplitude_groups):
        """
        Inicjalizuje analizator.

        :param amplitude_groups: Lista krotek/list w formacie:
            [
                (k_1, [(v_out_1, b_ref_1), (v_out_2, b_ref_2), ...]),
                (k_2, [(v_out_1, b_ref_1), (v_out_2, b_ref_2), ...]),
                ...
            ]
            Gdzie 'k' to etykieta (np. "10% Amplitudy"), a wewnątrz znajduje się
            lista par ścieżek do plików CSV dla danej amplitudy.
        """
        self.amplitude_groups = amplitude_groups
        self.processed_datasets = []

    def _extract_fundamental(self, csv_path):
        df = pd.read_csv(csv_path)
        idx_max = df['RMS'].idxmax()
        row = df.loc[idx_max]
        return row['frequency_hz'], row['RMS'], row['phase']

    def _process_amplitude_group(self, label, file_pairs):
        results = []

        ref_50hz = 1
        meas_50hz = 1

        for meas_csv, ref_csv in file_pairs:
            f_meas, meas_rms, meas_phase = self._extract_fundamental(meas_csv)
            f_ref, ref_rms, ref_phase = self._extract_fundamental(ref_csv)

            if abs(f_meas - f_ref) > 1.0:
                print(
                    f"Ostrzeżenie ({label}): Rozbieżność częstotliwości między {meas_csv} ({f_meas}Hz) a {ref_csv} ({f_ref}Hz)")
            # S = v_rms / b_rms_T if b_rms_T != 0 else 0
            delta_phi = meas_phase - ref_phase
            delta_phi = (delta_phi + 180) % 360 - 180

            if ref_rms == 0.0:
                ref_rms = 1e-12

            results.append({
                'frequency': f_ref,
                'ref_rms': ref_rms,
                'meas_rms': meas_rms,
                'delta_phi': delta_phi
            })
            if f_ref == 50:
                ref_50hz = ref_rms
                meas_50hz = meas_rms

        ratio_50hz = meas_50hz/ref_50hz
        for r in results:
            r['G_dB'] = 20 * np.log10(r['meas_rms']/r['ref_rms']/ratio_50hz)

        # results = sorted(results, key=lambda x: x['frequency'])

        # if results:
        #     ref_50hz = min(results, key=lambda x: abs(x['frequency'] - 50.0))
        #     RMS_50 = ref_50hz['ref_rms']


        # if results:
        #     ref_50hz = min(results, key=lambda x: abs(x['frequency'] - 50.0))
        #     RMS_50 = ref_50hz['ref_rms']
        #
        #     for r in results:
        #         ratio = r['RMS'] / RMS_50 if RMS_50 != 0 else 1e-12
        #         r['G_dB'] = 20 * np.log10(ratio)

        return results

    def analyze(self):
        """
        Przetwarza wszystkie grupy amplitud podane podczas inicjalizacji.
        """
        self.processed_datasets = []
        for label, file_pairs in self.amplitude_groups:
            print(f"Przetwarzanie grupy: {label}")
            data = self._process_amplitude_group(label, file_pairs)
            self.processed_datasets.append((label, data))

    def plot(self, filename=None):
        """
        Generuje i wyświetla wykresy charakterystyk dla wszystkich przetworzonych amplitud.
        """
        if not self.processed_datasets:
            print("Brak danych do wyświetlenia. Uruchom najpierw metodę analyze().")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), sharex=True)
        fig.suptitle('Charakterystyki częstotliwościowe czujnika dla różnych wartości RMS', fontsize=14)

        # Dynamiczne generowanie kolorów i znaczników dla dowolnej liczby amplitud
        colors = itertools.cycle(plt.cm.tab10.colors)
        markers = itertools.cycle(['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h'])

        for label, data in self.processed_datasets:
            color = next(colors)
            marker = next(markers)
            fmt = f'{marker}-'

            freqs = [d['frequency'] for d in data]
            G_vals = [d['G_dB'] for d in data]
            phi_vals = [d['delta_phi'] for d in data]

            ax1.plot(freqs, G_vals, fmt, color=color, label=str(label), markersize=5)
            ax2.plot(freqs, phi_vals, fmt, color=color, label=str(label), markersize=5)

        for ax in (ax1, ax2):
            ax.set_xscale('log')
            ax.grid(True, which="both", ls="--", alpha=0.6)
            ax.legend()

        ax1.set_ylabel('Znormalizowane wzmocnienie G [dB]')
        ax1.set_title('Tłumienie G(f) względem 50 Hz')
        ax1.axhline(0, color='black', linewidth=1)

        ax2.set_ylabel('Przesunięcie fazowe Δφ [°]')
        ax2.set_title('Charakterystyka fazowa Δφ(f)')
        ax2.set_xlabel('Częstotliwość [Hz]')

        plt.tight_layout()
        if filename:
            plt.savefig(filename, dpi=300)
        else:
            plt.show()


if __name__ == "__main__":
    files = []
    b_values = [15, 20, 50]
    for b in b_values:
        files_amp = []
        for k in [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]:
            files_amp.append((f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv", f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv"))
        files.append([f"{b}", files_amp])

    analyzer = SensorBodeAnalyzer(files)
    analyzer.analyze()
    analyzer.plot()
