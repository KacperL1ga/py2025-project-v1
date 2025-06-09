import tkinter as tk
from tkinter import ttk, messagebox
import threading
import socket
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Konfiguracja domyślnego hosta i portu
HOST = '0.0.0.0'
PORT = 65432

# Bufor danych do obliczania średnich wartości (dla każdego czujnika osobno)
sensor_data = defaultdict(lambda: deque(maxlen=1000))  # przechowuje (timestamp, value)

# Klasa serwera TCP działającego w osobnym wątku
class SensorServer(threading.Thread):
    def __init__(self, host, port, on_data_callback, on_status_callback):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.on_data_callback = on_data_callback  # funkcja wywoływana po odebraniu danych
        self.on_status_callback = on_status_callback  # funkcja do aktualizacji statusu GUI
        self.running = False
        self.server_socket = None

    def run(self):
        self.running = True
        try:
            # Tworzenie gniazda TCP
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.on_status_callback(f"Nasłuchiwanie na porcie {self.port}...")

            # Obsługa połączeń klientów
            while self.running:
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, addr = self.server_socket.accept()
                    threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            self.on_status_callback(f"Błąd serwera: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            self.on_status_callback("Serwer zatrzymany.")

    def handle_client(self, client_socket):
        buffer = ""
        with client_socket:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    buffer += data.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        try:
                            payload = json.loads(line)
                            self.on_data_callback(payload)
                            client_socket.sendall(b"ACK\n")
                        except json.JSONDecodeError:
                            client_socket.sendall(b"NACK\n")
                except Exception:
                    break

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

# Klasa GUI aplikacji
class SensorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serwer czujników")
        self.server = None
        self.data = {}  # przechowuje ostatnie dane z czujników
        self.tree_items = {}  # mapowanie sensor_id -> ID w tabeli
        self.build_gui()
        self.update_table_loop()

    # Budowanie interfejsu graficznego
    def build_gui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10)

        tk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(top_frame, width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(top_frame, text="Start", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(top_frame, text="Stop", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(self.root, text="Serwer zatrzymany.", anchor="w")
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # Tabela z danymi czujników
        columns = ("Sensor", "Ostatnia wartość", "Jednostka", "Timestamp", "Średnia 1h", "Średnia 12h")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Uruchomienie serwera
    def start_server(self):
        try:
            port = int(self.port_entry.get())
            self.server = SensorServer(HOST, port, self.on_data_received, self.set_status)
            self.server.start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można uruchomić serwera: {e}")

    # Zatrzymanie serwera
    def stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.set_status("Serwer zatrzymany.")

    # Aktualizacja statusu w GUI
    def set_status(self, text):
        self.status_label.config(text=text)

    # Obsługa odebranych danych z czujnika
    def on_data_received(self, payload):
        sensor_id = payload.get("sensor_id")
        timestamp = datetime.fromisoformat(payload.get("timestamp"))
        value = payload.get("value")
        unit = payload.get("unit")

        # Zapisanie ostatniego odczytu
        self.data[sensor_id] = {
            "value": value,
            "unit": unit,
            "timestamp": timestamp
        }

        # Dodanie do bufora historii
        sensor_data[sensor_id].append((timestamp, value))

    # Aktualizacja tabeli co 3 sekundy
    def update_table_loop(self):
        for sensor_id, info in self.data.items():
            now = datetime.now()
            values_1h = [v for t, v in sensor_data[sensor_id] if now - t <= timedelta(hours=1)]
            values_12h = [v for t, v in sensor_data[sensor_id] if now - t <= timedelta(hours=12)]
            avg_1h = round(sum(values_1h) / len(values_1h), 2) if values_1h else "-"
            avg_12h = round(sum(values_12h) / len(values_12h), 2) if values_12h else "-"

            row = (
                sensor_id,
                round(info["value"], 2),
                info["unit"],
                info["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                avg_1h,
                avg_12h
            )

            if sensor_id in self.tree_items:
                self.tree.item(self.tree_items[sensor_id], values=row)
            else:
                item_id = self.tree.insert("", "end", values=row)
                self.tree_items[sensor_id] = item_id

        self.root.after(3000, self.update_table_loop)  # odświeżenie co 3 sekundy

# Uruchomienie aplikacji
if __name__ == "__main__":
    root = tk.Tk()
    app = SensorGUI(root)
    root.mainloop()
