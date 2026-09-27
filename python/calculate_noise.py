import numpy as np
from scipy.signal import welch
import matplotlib.pyplot as plt
from typing import Optional, Dict, Tuple


class NoiseAnalyzer:
    """
    Klasa do analizy parametrów szumowych toru pomiarowego i czujnika pola magnetycznego.
    """

    def __init__(self, signal: np.ndarray, fs: float, nperseg: int, unit: str):
        self.signal = signal
        self.fs = fs
        self.nperseg = nperseg
        self.unit = unit

        # Parametry pasma
        self.f_min = 45
        self.f_max = 2550
        self.harmonics = np.arange(100, 2550, 50)

        # Zmienne na wyniki
        self.f: Optional[np.ndarray] = None
        self.NSD: Optional[np.ndarray] = None
        self.rms_band: Optional[float] = None
        self.bin_noise: Dict[int, float] = {}

    def analyze(self) -> None:
        """
        Przeprowadza obliczenia gęstości widmowej, RMS w paśmie i progów wykrywalności.
        """
        # 1. Gęstość widmowa mocy (PSD) metodą Welcha (okno Hanna)
        self.f, S_bb = welch(self.signal, self.fs, window='hann',
                             nperseg=self.nperseg, scaling='density')

        # Amplitudowa gęstość widmowa szumu (NSD)
        self.NSD = np.sqrt(S_bb)

        # 2. Wartość skuteczna szumu (RMS) w zadanym paśmie
        idx_band = np.where((self.f >= self.f_min) & (self.f <= self.f_max))[0]
        self.rms_band = np.sqrt(np.trapz(S_bb[idx_band], self.f[idx_band]))

        # 3. Poziom szumu w binach (próg wykrywalności harmonicznych)
        df = self.f[1] - self.f[0]
        N_ENBW = 1.5  # dla okna Hanna
        ENBW = N_ENBW * df

        self.bin_noise.clear()
        for h in self.harmonics:
            idx_h = np.argmin(np.abs(self.f - h))
            self.bin_noise[h] = self.NSD[idx_h] * np.sqrt(ENBW)

    def plot(self, save_path: Optional[str] = None, show: bool = True) -> None:
        """
        Generuje wykres gęstości widmowej szumu.

        Parametry:
        save_path - opcjonalna ścieżka do zapisu pliku (np. 'szum_czujnik_1.png')
        show      - czy wyświetlić wykres na ekranie
        """
        if self.f is None or self.NSD is None:
            raise RuntimeError("Brak danych. Najpierw wywołaj metodę analyze().")

        plt.figure(figsize=(10, 5))
        plt.plot(self.f, self.NSD, label='Gęstość widmowa szumu (NSD)', color='#1f77b4', linewidth=1.2)

        # Zaznaczenie pasma całkowania
        plt.axvspan(self.f_min, self.f_max, color='red', alpha=0.08,
                    label=f'Pasmo RMS ({self.f_min} Hz - {self.f_max / 1000:.2f} kHz)')

        # Zaznaczenie przykładowych progów dla kilku wybranych harmonicznych
        plot_harmonics = [100, 150, 500, 1000, 2500]
        for h in plot_harmonics:
            if h in self.bin_noise:
                idx = np.argmin(np.abs(self.f - h))
                plt.plot(self.f[idx], self.NSD[idx], marker='o', color='darkred', markersize=5)

        # Dodanie "pustego" punktu do legendy, żeby opisać kropki
        plt.plot([], [], marker='o', color='darkred', linestyle='',
                 markersize=5, label='Próg detekcji harmonicznych')

        plt.title('Widmo szumu czujnika i toru pomiarowego')
        plt.xlabel('Częstotliwość [Hz]')
        plt.ylabel(f'NSD [{self.unit}/' + r'$\sqrt{Hz}$]')
        plt.xlim(0, 3000)
        plt.yscale('log')
        plt.grid(True, which="both", linestyle="--", alpha=0.6)
        plt.legend()
        plt.tight_layout()

        if save_path:
            # bbox_inches='tight' zapobiega ucinaniu etykiet przy zapisie
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Zapisano wykres do pliku: {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

    def print_report(self) -> None:
        """
        Wypisuje sformatowany raport z wynikami w konsoli.
        """
        if self.f is None:
            raise RuntimeError("Brak danych. Najpierw wywołaj metodę analyze().")

        df = self.f[1] - self.f[0]
        print("--- RAPORT SZUMOWY TORU ---")
        print(f"Rozdzielczość widma (df): {df:.2f} Hz")
        print(f"Szum RMS w paśmie {self.f_min}-{self.f_max} Hz: {self.rms_band:.4f} nT\n")
        print("Próg wykrywalności dla przykładowych harmonicznych (szum w binie):")

        for h in [100, 150, 500, 1000, 2500]:
            if h in self.bin_noise:
                print(f"  - {h:>4} Hz: {self.bin_noise[h]:.4f} nT")


# ==========================================
# Przykładowe użycie klasy
# ==========================================
if __name__ == "__main__":
    fs = 10000
    T_record = 1.0
    T_total = 10.0

    t = np.arange(0, T_total, 1 / fs)

    # Symulowany sygnał tła w nT
    noise_signal = np.random.normal(0, 0.2, len(t))
    nperseg = int(fs * T_record)

    # Tworzymy instancję klasy z zarejestrowanym sygnałem
    analyzer = NoiseAnalyzer(noise_signal, fs, nperseg)

    # Przetwarzamy
    analyzer.analyze()

    # Raport w konsoli
    analyzer.print_report()

    # Wyświetlamy wykres i zapisujemy go do pliku o nazwie 'widmo_szumu.png'
    analyzer.plot(save_path='widmo_szumu_czujnik_A.png', show=True)