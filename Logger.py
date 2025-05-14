import csv
import json
import os
import zipfile
from datetime import datetime, timedelta
from typing import Dict, Iterator, Optional
import glob


class Logger:
    def __init__(self, config_path: str):
        """
        Inicjalizuje logger na podstawie pliku konfiguracyjnego JSON.

        Args:
            config_path (str): Ścieżka do pliku konfiguracyjnego JSON zawierającego:
                - log_dir: Katalog do przechowywania logów
                - filename_pattern: Wzór nazwy pliku (np. 'sensors_%Y%m%d.csv')
                - buffer_size: Liczba wpisów w buforze przed zapisem do pliku
                - rotate_every_hours: Częstotliwość rotacji plików (w godzinach)
                - max_size_mb: Maksymalny rozmiar pliku przed rotacją (w MB)
                - rotate_after_lines: Maksymalna liczba linii przed rotacją
                - retention_days: Liczba dni przechowywania archiwów
        """
        # Wczytanie konfiguracji z pliku JSON
        with open(config_path) as f:
            config = json.load(f)

        # Podstawowe ustawienia logowania
        self.log_dir = config["log_dir"]  # Główny katalog logów
        self.filename_pattern = config["filename_pattern"]  # Wzór nazwy pliku (strftime)
        self.buffer_size = config["buffer_size"]  # Rozmiar bufora przed zapisem

        # Ustawienia rotacji plików
        self.rotate_every_hours = config["rotate_every_hours"]  # Rotacja czasowa
        self.max_size_mb = config["max_size_mb"]  # Rotacja po rozmiarze
        self.rotate_after_lines = config.get("rotate_after_lines", float('inf'))  # Rotacja po liczbie linii
        self.retention_days = config["retention_days"]  # Czas przechowywania archiwów

        # Stan wewnętrzny loggera
        self.current_file = None  # Obiekt aktualnie otwartego pliku
        self.current_file_path = None  # Ścieżka do aktualnego pliku
        self.buffer = []  # Bufor przechowujący wpisy przed zapisem
        self.line_count = 0  # Licznik linii w aktualnym pliku
        self.last_rotation = datetime.now()  # Czas ostatniej rotacji

        # Utworzenie niezbędnych katalogów jeśli nie istnieją
        os.makedirs(os.path.join(self.log_dir, "archive"), exist_ok=True)

    def start(self) -> None:
        """
        Otwiera nowy plik CSV do logowania i zapisuje nagłówek jeśli plik jest nowy.
        Inicjalizuje wszystkie niezbędne zmienne stanu.
        """
        # Generowanie ścieżki do pliku na podstawie wzorca i aktualnej daty
        self.current_file_path = os.path.join(
            self.log_dir,
            datetime.now().strftime(self.filename_pattern)
        )

        # Sprawdzenie czy plik już istnieje
        is_new_file = not os.path.exists(self.current_file_path)

        # Otwarcie pliku w trybie dopisywania (append)
        self.current_file = open(self.current_file_path, 'a', newline='')
        self.writer = csv.writer(self.current_file, delimiter=';')

        # Jeśli plik jest nowy, zapisz nagłówek CSV
        if is_new_file:
            self.writer.writerow(["timestamp", "sensor_id", "value", "unit"])
            self.current_file.flush()  # Wymuszenie natychmiastowego zapisu

        # Inicjalizacja liczników
        self.line_count = self._count_lines()  # Policz istniejące linie
        self.last_rotation = datetime.now()  # Zresetuj czas ostatniej rotacji

    def stop(self) -> None:
        """
        Bezpiecznie zamyka logger - wymusza zapis bufora i zamyka plik.
        Powinien być wywoływany przed zakończeniem programu.
        """
        self._flush_buffer()  # Zapisz wszystko co jest w buforze
        if self.current_file:
            self.current_file.close()  # Zamknij plik
            self.current_file = None  # Wyczyść referencję

    def log_reading(
            self,
            sensor_id: str,
            timestamp: datetime,
            value: float,
            unit: str
    ) -> None:
        """
        Loguje pojedynczy odczyt z czujnika do systemu plików.

        Args:
            sensor_id (str): ID czujnika
            timestamp (datetime): Czas odczytu
            value (float): Wartość odczytu
            unit (str): Jednostka miary
        """
        # Dodanie wpisu do bufora
        self.buffer.append((timestamp.isoformat(), str(sensor_id), str(value), str(unit)))

        # Jeśli bufor osiągnął maksymalny rozmiar, zapisz do pliku
        if len(self.buffer) >= self.buffer_size:
            print("DEBUG: Bufer pełny - zapis do pliku")
            self._flush_buffer()

        # Sprawdź czy potrzebna jest rotacja plików
        self._check_rotation()

    def read_logs(
            self,
            start: datetime,
            end: datetime,
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Generator odczytujący historyczne dane z logów.

        Args:
            start (datetime): Data początkowa zakresu
            end (datetime): Data końcowa zakresu
            sensor_id (Optional[str]): ID konkretnego czujnika (None dla wszystkich)

        Yields:
            Dict: Słownik z danymi odczytu w formacie:
                {
                    "timestamp": datetime,
                    "sensor_id": str,
                    "value": float,
                    "unit": str
                }
        """
        # Przeszukaj bieżące pliki CSV
        for filepath in glob.glob(os.path.join(self.log_dir, "*.csv")):
            yield from self._read_log_file(filepath, start, end, sensor_id)

        # Przeszukaj archiwa ZIP
        for filepath in glob.glob(os.path.join(self.log_dir, "archive", "*.zip")):
            with zipfile.ZipFile(filepath, 'r') as zipf:
                for name in zipf.namelist():
                    if name.endswith('.csv'):
                        with zipf.open(name) as f:
                            yield from self._read_log_file(f, start, end, sensor_id)

        # Przeszukaj niezakompresowane archiwa CSV
        for filepath in glob.glob(os.path.join(self.log_dir, "archive", "*.csv")):
            yield from self._read_log_file(filepath, start, end, sensor_id)

    # ==============================================
    # Metody prywatne - używane tylko wewnętrznie
    # ==============================================

    def _flush_buffer(self) -> None:
        """Wymusza zapis zawartości bufora do pliku."""
        if self.buffer and self.current_file:
            self.writer.writerows(self.buffer)  # Zapisz wszystkie wpisy naraz
            self.current_file.flush()  # Wymuś fizyczny zapis na dysk
            self.line_count += len(self.buffer)  # Zaktualizuj licznik linii
            self.buffer.clear()  # Wyczyść bufor

    def _check_rotation(self) -> None:
        """
        Sprawdza czy należy dokonać rotacji plików na podstawie:
        - upływu czasu
        - rozmiaru pliku
        - liczby linii
        """
        needs_rotation = False

        # Rotacja czasowa (co określoną liczbę godzin)
        if (datetime.now() - self.last_rotation) >= timedelta(hours=self.rotate_every_hours):
            needs_rotation = True

        # Rotacja po rozmiarze pliku (jeśli przekroczony maksymalny rozmiar)
        if self.current_file_path and os.path.exists(self.current_file_path):
            file_size = os.path.getsize(self.current_file_path) / (1024 * 1024)  # Rozmiar w MB
            if file_size >= self.max_size_mb:
                needs_rotation = True

        # Rotacja po liczbie linii
        if self.line_count >= self.rotate_after_lines:
            needs_rotation = True

        if needs_rotation:
            self._rotate_file()

    def _rotate_file(self) -> None:
        """Wykonuje pełny proces rotacji pliku logów."""
        # 1. Zapisz bufor i zamknij plik
        self._flush_buffer()
        self.stop()

        # 2. Jeśli plik istnieje, zarchiwizuj go
        if self.current_file_path and os.path.exists(self.current_file_path):
            # Generuj unikalną nazwę archiwum z timestampem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = os.path.basename(self.current_file_path).replace('.csv', f'_{timestamp}.zip')
            archive_path = os.path.join(self.log_dir, "archive", archive_name)

            # Kompresja do ZIP
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.current_file_path, os.path.basename(self.current_file_path))

            # Usuń oryginalny plik po skompresowaniu
            os.remove(self.current_file_path)

        # 3. Wyczyść stare archiwa
        self._clean_old_archives()

        # 4. Otwórz nowy plik logów
        self.start()

    def _clean_old_archives(self) -> None:
        """Usuwa archiwa starsze niż retention_days dni."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for filepath in glob.glob(os.path.join(self.log_dir, "archive", "*")):
            # Sprawdź datę modyfikacji pliku
            if os.path.getmtime(filepath) < cutoff.timestamp():
                try:
                    os.remove(filepath)  # Usuń plik
                except OSError as e:
                    print(f"Błąd podczas usuwania archiwum {filepath}: {e}")

    def _count_lines(self) -> int:
        """Liczy liczbę linii w aktualnym pliku logów (bez nagłówka)."""
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            return 0

        with open(self.current_file_path, 'r') as f:
            return sum(1 for _ in f) - 1  # -1 pomija nagłówek

    def _read_log_file(
            self,
            filepath,
            start: datetime,
            end: datetime,
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Pomocnicza metoda do czytania pojedynczego pliku logów.
        Obsługuje zarówno zwykłe pliki jak i obiekty plików (np. z ZIP).
        """
        is_file_object = hasattr(filepath, 'read')

        with (filepath if is_file_object else open(filepath, 'r')) as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # Pomijamy nagłówek

            for row in reader:
                # Sprawdź poprawność wiersza
                if len(row) != 4:
                    continue

                # Parsuj timestamp
                try:
                    timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    continue

                # Filtruj po dacie
                if not (start <= timestamp <= end):
                    continue

                # Filtruj po ID czujnika (jeśli podano)
                if sensor_id and row[1] != sensor_id:
                    continue

                # Zwróć sformatowane dane
                yield {
                    "timestamp": timestamp,
                    "sensor_id": row[1],
                    "value": float(row[2]),
                    "unit": row[3]
                }