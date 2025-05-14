from datetime import datetime

from Sensor import Sensor
import numpy as np

# == Czujnik Temperatury ==
class TemperatureSensor(Sensor):
    def __init__(self, sensor_id, frequency=1):
        super().__init__(sensor_id,"Czujnik temperatury","°C",-20,50,frequency)

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony!")

        if self.last_value is None:     # Pierwsze przypisanie wartośći temperatury
            value = np.random.uniform(self.min_value + 5, self.max_value - 5)
        else:
            zmiennosc = np.random.uniform(-5,5)     # Wylosowanie zmienności imitującej naturalne wahania temperatury
            value = self.last_value + zmiennosc     # Obliczanie końcowej temperatury
            value = max(self.min_value, min(self.max_value, value)) # # Sprawdzenie czy nowa wartość mieści się w zalooznych granicach

        self.last_value = round(value,2)    # Zaokrąglenie do 2 miejsc po przecinku
        
        timestamp = datetime.now()    # Pobranie aktualnej godziny pomiaru
        for callback in self.callbacks:    # Generowanie callback'ów dla tego sensora 
            try:
                callback(self.sensor_id, timestamp, self.last_value, self.unit)    # Callback pobiera dane z czujnika i przekazuje go do funkcji register_callback 
            except Exception as e:
                print(f"Blad w callbacku {callback.__name__} dla {self.sensor_id}: {str(e)}")    # W przypadku błędu zwraca tresc bledu

        return self.last_value

# == Czujnik Wilgotności ==
class HumiditySensor(Sensor):
    def __init__(self, sensor_id, temperature_sensor = None, frequency=2):
        super().__init__(sensor_id,"Czujnik wilgoci","%",0,100,frequency)
        self.temperature_sensor = temperature_sensor    # Pobieranie danych o temperaturze z jej czujnika
        self.base_humidity = None   # Przechowywanie pierwszej wylosowanej wartości wilgotności
        self.current_enviroment = None     # Zmienna przechowująca wystąpienie zmian środowiskowych

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony!")

        if self.base_humidity is None:      # Pierwsze losowanie bazowej wartości wilgotności
            self.base_humidity = np.random.uniform(self.min_value + 10, self.max_value - 10)
            value = self.base_humidity
        else:
            value = self.base_humidity      # Przepisanie  bazowej wartości pod modyfikacje
            if self.temperature_sensor and self.temperature_sensor.last_value is not None:
                temp = self.temperature_sensor.last_value   # Przepisanie wartości temperatury do obliczenia zmienności wilgotności
                if (temp > 15):     # Spadek wilgotności, gdy temperatura jest większa niż 15 stopni
                    zmiennosc = (temp - 15) * -1    # Za każdy spodniej różnicy temperatury, wilgotność spada o punkt procentowy
                else:
                    zmiennosc = (15- temp) * 1      # Za każdy spodniej różnicy temperatury, wilgotność wzrasta o punkt procentowy

                value = self.base_humidity * (1 + zmiennosc/100)    # Obliczanie nowej wartości po uiszczeniu procentowym

                self.current_enviroment = np.random.uniform(0,1)     # Generowanie losowości dla zmiennch środowiskowych
                if self.current_enviroment <= 0.2:   # 20% szansy na wystąpienie opadów deszczu
                    zmiennosc = np.random.uniform(1,3)
                    value += zmiennosc  # Dodanie wyżej wylosowanych punktów procentowych
                    self.przyczyna = f"Wzrost o dodatkowe {zmiennosc:.2f}% - wpływ opadów deszczu"
                elif 0.2 < self.current_enviroment <= 0.4: # 20% szansy na wystąpienie suchego powietrza
                    zmiennosc = np.random.uniform(-3,-1)
                    value += zmiennosc  # Odjęcie wyżej wylosowanych punktów procentowych
                    self.przyczyna = f"Spadek o dodatkowe {zmiennosc:.2f}% - wpływ suchego powietrza"
                else:
                    value += np.random.uniform(-1, 1)

        value = max(self.min_value, min(self.max_value, value)) # Sprawdzenie czy nowa wartość mieści się w zalooznych granicach
        self.last_value = round(value,2)    # Zaokrąglenie wyniku do dwóch miejsc po przecinku
        
        timestamp = datetime.now()    # Pobranie aktualnej godziny pomiaru
        for callback in self.callbacks:    # Generowanie callback'ów dla tego sensora 
            try:
                callback(self.sensor_id, timestamp, self.last_value, self.unit)    # Callback pobiera dane z czujnika i przekazuje go do funkcji register_callback 
            except Exception as e:
                print(f"Blad w callbacku {callback.__name__} dla {self.sensor_id}: {str(e)}")    # W przypadku błędu zwraca tresc bledu

        return self.last_value

# == Czujnik Ciśnienia ==
class PressureSensor(Sensor):
    def __init__(self, sensor_id, frequency=2):
        super().__init__(sensor_id,"Czujnik cisnienia","hPa",950,1050,frequency)
        self.base_value = np.random.uniform(self.min_value+5,self.max_value-5)   # Pierotne solowanie wartości ciśnienia

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony!")

        zmiennosc = np.random.uniform(-5,5)     # Naturalna fluktuacja

        if np.random.uniform(0,1) <= 0.2:    # 20% szans na zwiększoną zmianę ciśnienia
            zmiennosc += np.random.uniform(-5,5)

        value = self.base_value + zmiennosc     # Obliczanie końcowej wartości ciśnienia
        value = max(self.min_value, min(self.max_value, value))
        self.last_value = round(value,2)    # Zaokrąglenie do 2 miejsc po przecinku
        
        timestamp = datetime.now()    # Pobranie aktualnej godziny pomiaru
        for callback in self.callbacks:    # Generowanie callback'ów dla tego sensora 
            try:
                callback(self.sensor_id, timestamp, self.last_value, self.unit)    # Callback pobiera dane z czujnika i przekazuje go do funkcji register_callback 
            except Exception as e:
                print(f"Blad w callbacku {callback.__name__} dla {self.sensor_id}: {str(e)}")    # W przypadku błędu zwraca tresc bledu

        return self.last_value

# == Czujnik zanieczyszczenia ==
class AirQualitySensor(Sensor):
    def __init__(self, sensor_id, humidity_sensor = None, frequency=1):
        super().__init__(sensor_id, "Czujnik jakości powietrza", "AQI",0,500)
        self.base_value = np.random.uniform(20,100)
        self.humidity_sensor = humidity_sensor  # Odwołanie do czujnika wilgotności

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony!")

        now = datetime.now().hour   # Pobranie godziny do ustalenia poziomu zanieczyszczenia
        if 7 <= now <= 9 or 14 <= now <= 17:    # W godzinach szczytu zanieczyszczenie szybko wzrasta
            zmiennosc = np.random.uniform(20,30)
            value = self.base_value + zmiennosc # Obliczanie bieżącego zanieczyszczenia
        else:   #   Poza godzinami szczytu poziom AQI stopniowo spada
            zmiennosc = np.random.uniform(-5,-10)
            value = self.base_value + zmiennosc

        if self.humidity_sensor and self.humidity_sensor.current_enviroment is not None:
            if self.humidity_sensor.current_enviroment <= 0.2:  # Sprawdzamy czy jest deszcz (enviroment <= 0.2)
                improvement = np.random.uniform(10, 20)     # Poprawa jakości powietrza gdy jest deszcz
                value -= improvement
                self.przyczyna = f"Poprawa o {improvement:.2f} AQI - opady deszczu"
            elif 0.2 < self.humidity_sensor.current_enviroment <= 0.4:  # 20% szansy na wystąpienie suchego powietrza
                zmiennosc = np.random.uniform(-3, -1)
                value += zmiennosc  # Odjęcie wyżej wylosowanych punktów procentowych
                self.przyczyna = f"Pogorszenie o dodatkowe {zmiennosc:.2f}% - wpływ suchego powietrza"
            else:
                value += np.random.uniform(-5, 5)   # Drobne fluktuacje dzienne

        if np.random.random() <= 0.1:   # 20% na nagłą poprawę jakości
            zmiennosc = np.random.uniform(20,45)
            value -= zmiennosc
        elif 0.1 < np.random.random() <= 0.2:    # 20% na nagłe pogorszenie jakości
            zmiennosc = np.random.uniform(20,45)
            value += zmiennosc

        value = max(self.min_value, min(self.max_value, value))
        self.last_value = round(value,2)    # Zaokrąglanie do 2 miejsc po przecinku
        
        timestamp = datetime.now()    # Pobranie aktualnej godziny pomiaru
        for callback in self.callbacks:    # Generowanie callback'ów dla tego sensora 
            try:
                callback(self.sensor_id, timestamp, self.last_value, self.unit)    # Callback pobiera dane z czujnika i przekazuje go do funkcji register_callback 
            except Exception as e:
                print(f"Blad w callbacku {callback.__name__} dla {self.sensor_id}: {str(e)}")    # W przypadku błędu zwraca tresc bledu

        return self.last_value

    def get_air_quality_level(self):    # Funkcja zajmująca się oceną jakości powietrza
        if self.last_value is None:
            return "Brak danych"

        if self.last_value <= 50:
            return "Dobra"
        elif self.last_value <= 100:
            return "Umiarkowana"
        elif self.last_value <= 200:
            return "Niezdrowa"
        elif self.last_value <= 300:
            return "Bardzo niezdrowa"
        else:
            return "Niebezpieczna"
