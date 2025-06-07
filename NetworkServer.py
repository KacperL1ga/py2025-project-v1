import socket
import json
import logging
from typing import Optional

class NetworkServer:
    def __init__(self, port: int):
        """Inicjalizuje serwer na wskazanym porcie."""
        self.port = port
        self.logger = logging.getLogger("NetworkServer")
        self.server_socket: Optional[socket.socket] = None

    def start(self) -> None:
        """Uruchamia nasłuchiwanie połączeń i obsługę klientów."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', self.port))
        self.server_socket.listen(5)
        self.logger.info(f"Serwer nasłuchuje na porcie {self.port}")

        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Połączono z klientem {client_address}")
                self._handle_client(client_socket)
        except KeyboardInterrupt:
            self.logger.info("Zatrzymano serwer")
        finally:
            self.server_socket.close()

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Odbiera dane, wysyła ACK i wypisuje je na konsolę."""
        buffer = b""
        try:
            while True:
                chunk = client_socket.recv(1024) # Odbieraj dane w kawałkach
                if not chunk: # Klient zamknął połączenie
                    break
                buffer += chunk

                # Sprawdzamy, czy w buforze znajduje się pełna wiadomość (zakończona nową linią)
                if b'\n' in buffer:
                    message_end_index = buffer.find(b'\n')
                    raw_data = buffer[:message_end_index] # Pobierz wiadomość do znaku nowej linii
                    buffer = buffer[message_end_index + 1:] # Reszta bufora

                    try:
                        data = self._deserialize(raw_data)
                        self.logger.info(f"Otrzymano dane: {data}")
                        print(json.dumps(data, indent=4))
                        client_socket.sendall(b"ACK\n")
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Błąd parsowania JSON: {e} - Surowe dane: {raw_data.decode('utf-8')}")
                        client_socket.sendall(b"NACK\\n") # Opcjonalnie: wyslij NACK przy bledzie JSON
                        break # Przerwij obsluge klienta przy bledzie parsowania JSON
                # Jeśli bufor przekracza sensowny rozmiar i nie ma nowej linii, może to być błąd
                if len(buffer) > 4096: # Przykład: jesli bufor ma wiecej niz 4KB i brak nowej linii
                    self.logger.error("Bufor przekroczył rozmiar bez znaku nowej linii. Zamykanie połączenia.")
                    break # Przerwij, aby uniknąć przepełnienia pamięci

        except socket.error as e:
            self.logger.error(f"Błąd gniazda podczas obsługi klienta: {e}")
        finally:
            client_socket.close()
            self.logger.info("Połączenie z klientem zostało zamknięte")


    def _deserialize(self, raw: bytes) -> dict:
        """Deserializuje dane z formatu JSON."""
        return json.loads(raw.decode('utf-8'))