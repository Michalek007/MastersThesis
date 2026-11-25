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
        """
        self.amplitude_groups = amplitude_groups
        self.processed_datasets = []

    def _extract_fundamental(self, csv_path):
        df = pd.read_csv(csv_path)
        idx_max = df['RMS'].idxmax()
        row = df.loc[idx_max]
        return row['frequency_hz'], row['RMS'], row['phase']

    def _process_amplitude_group(self, label, file_pairs, normalize_phase=True):
        results = []

        ref_50hz = None
        meas_50hz = None

        for meas_csv, ref_csv in file_pairs:
            f_meas, meas_rms, meas_phase = self._extract_fundamental(meas_csv)
            f_ref, ref_rms, ref_phase = self._extract_fundamental(ref_csv)

            if abs(f_meas - f_ref) > 1.0:
                print(
                    f"Ostrzeżenie ({label}): Rozbieżność częstotliwości między {meas_csv} ({f_meas}Hz) a {ref_csv} ({f_ref}Hz)"
                )

            # Surowa różnica faz zawinięta do [-180, 180]
            delta_phi = (meas_phase - ref_phase + 180) % 360 - 180

            if ref_rms == 0.0:
                ref_rms = 1e-12

            results.append({
                'frequency': f_ref,
                'ref_rms': ref_rms,
                'meas_rms': meas_rms,
                'delta_phi': delta_phi
            })

            if abs(f_ref - 50) < 1:
                ref_50hz = ref_rms
                meas_50hz = meas_rms

        if ref_50hz is not None and meas_50hz is not None:
            ratio_50hz = meas_50hz / ref_50hz
        else:
            print(f"Ostrzeżenie ({label}): Nie znaleziono punktu dla 50 Hz. Przyjęto ratio_50hz = 1.0.")
            ratio_50hz = 1.0

        # 1. Sortowanie po częstotliwości MUSI być przed odwijaniem fazy (unwrap)
        results = sorted(results, key=lambda x: x['frequency'])

        # 2. Odwijanie fazy (eliminacja skoków między -180 a +180 stopni)
        phases_rad = np.deg2rad([r['delta_phi'] for r in results])
        unwrapped_phases_deg = np.rad2deg(np.unwrap(phases_rad))

        # 3. Znalezienie fazy dla 50 Hz (jeśli chcemy wyzerować przesunięcie od polaryzacji)
        phi_50hz = 0.0
        if normalize_phase:
            for r, phi in zip(results, unwrapped_phases_deg):
                if abs(r['frequency'] - 50) < 1:
                    phi_50hz = phi
                    break

        # 4. Przypisanie końcowych wartości G_dB oraz ciągłej fazy
        for r, phi in zip(results, unwrapped_phases_deg):
            r['G_dB'] = 20 * np.log10((r['meas_rms'] / r['ref_rms']) / ratio_50hz)
            r['delta_phi'] = phi - phi_50hz

        return results, ratio_50hz

    def analyze(self):
        """
        Przetwarza wszystkie grupy amplitud podane podczas inicjalizacji.
        """
        self.processed_datasets = []
        for label, file_pairs in self.amplitude_groups:
            print(f"Przetwarzanie grupy: {label}")
            data, ratio_50hz = self._process_amplitude_group(label, file_pairs, normalize_phase=True)
            self.processed_datasets.append({
                'label': label,
                'ratio_50hz': ratio_50hz,
                'data': data
            })

    def save_to_csv(self, filename="bode_results.csv"):
        """
        Zapisuje całą wyznaczoną charakterystykę (wszystkie punkty dla każdej amplitudy)
        oraz odpowiadającą wartość ratio_50Hz do pliku CSV.
        """
        if not self.processed_datasets:
            print("Brak danych do zapisania. Uruchom najpierw metodę analyze().")
            return

        rows = []
        for dataset in self.processed_datasets:
            label = dataset['label']
            ratio_50hz = dataset['ratio_50hz']

            for point in dataset['data']:
                rows.append({
                    'amplitude_label': label,
                    'frequency_hz': point['frequency'],
                    'ref_rms': point['ref_rms'],
                    'meas_rms': point['meas_rms'],
                    'ratio_50Hz': ratio_50hz,
                    'G_dB': point['G_dB'],
                    'delta_phi_deg': point['delta_phi']
                })

        df_out = pd.DataFrame(rows)
        df_out.to_csv(filename, index=False)
        print(f"Zapisano wyniki charakterystyki do pliku: {filename}")

    def plot(self, filename=None):
        """
        Generuje i wyświetla wykresy charakterystyk dla wszystkich przetworzonych amplitud.
        """
        if not self.processed_datasets:
            print("Brak danych do wyświetlenia. Uruchom najpierw metodę analyze().")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), sharex=True)
        fig.suptitle('Charakterystyki częstotliwościowe czujnika dla różnych wartości RMS', fontsize=14)

        colors = itertools.cycle(plt.cm.tab10.colors)
        markers = itertools.cycle(['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h'])

        for dataset in self.processed_datasets:
            label = dataset['label']
            data = dataset['data']

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
        ax1.set_title('Wzmocnienie G(f) względem 50 Hz')
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
    pass
    # files = []
    # b_values = [15, 20, 50]
    # for b in b_values:
    #     files_amp = []
    #     for k in [1, 2, 4, 5, 8, 10, 16, 20, 32, 40]:
    #         files_amp.append((
    #             f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv",
    #             f"results\\ALT021_sine_{b}_uT_k{k}_harmonics_B_uT.csv"
    #         ))
    #     files.append([f"{b}", files_amp])
    #
    # analyzer = SensorBodeAnalyzer(files)
    # analyzer.analyze()
    # analyzer.save_to_csv("results\\charakterystyka_bode.csv")
    # analyzer.plot()