import socket
import json
import logging
from typing import Optional


class NetworkClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0, retries: int = 3):
        """Inicjalizuje klienta sieciowego."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.socket: Optional[socket.socket] = None
        self.logger = logging.getLogger("NetworkClient")

    def connect(self) -> None:
        """Nawiazuje połączenie z serwerem."""
        self.socket = socket.create_connection((self.host, self.port), self.timeout)
        self.logger.info(f"Połączono z serwerem {self.host}:{self.port}")

    def send(self, data: dict) -> bool:
        """Wysyła dane i czeka na potwierdzenie zwrotne."""
        if not self.socket:
            try:
                self.connect()
            except Exception as e:
                self.logger.error(f"Nie udało się połączyć: {e}")
                return False

        serialized_data = self._serialize(data)
        for attempt in range(self.retries):
            try:
                self.socket.sendall(serialized_data)
                self.logger.info(f"Wysłano dane: {data}")
                ack = self.socket.recv(1024).decode('utf-8').strip()
                if ack == "ACK":
                    self.logger.info("Otrzymano potwierdzenie ACK")
                    return True
                else:
                    self.logger.error("Nieprawidłowe potwierdzenie")
            except (socket.timeout, socket.error) as e:
                self.logger.error(f"Błąd podczas wysyłania danych: {e}")

        self.logger.error("Przekroczono maksymalną liczbę prób")
        return False

    def close(self) -> None:
        """Zamyka połączenie."""
        if self.socket:
            self.socket.close()
            self.socket = None
            self.logger.info("Połączenie zostało zamknięte")

    def _serialize(self, data: dict) -> bytes:
        """Serializuje słownik do formatu JSON."""
        return (json.dumps(data) + '\n').encode('utf-8')

    def _deserialize(self, raw: bytes) -> dict:
        """Deserializuje dane z formatu JSON."""
        return json.loads(raw.decode('utf-8'))