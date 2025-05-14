import os.path
import time
from datetime import datetime
from Logger import Logger
from Sensor import Sensor
from typing import List
from Czujniki import TemperatureSensor, HumiditySensor, PressureSensor, AirQualitySensor

def main():
    logger = Logger("config.json")    # Inicjalizacja loggera
    print(f"Sciezka do logow: {os.path.abspath(logger.log_dir)}")
    logger.start()
    
    temp_sensor = TemperatureSensor(sensor_id = "temp_1")
    hum_sensor = HumiditySensor(sensor_id = "hum_2", temperature_sensor = temp_sensor)
    ps_sensor = PressureSensor(sensor_id = "press_3")
    aq_sensor = AirQualitySensor(sensor_id = "air_4", humidity_sensor = hum_sensor)

    def process_sensors(sensors: List[Sensor]):    # Funkcja do generowania callback'ow z przystkich sensorow
        for sensor in sensors:
            sensor.register_callback(logger.log_reading)    # Przekazywanie callback'u do funkcji log_reading
    sensors = [temp_sensor, hum_sensor, ps_sensor, aq_sensor]
    process_sensors(sensors)    # Inizjalizowanie procesu

    try:
        current_time = datetime.now()    # Pobranie aktualnej godziny generowanie pomiarów 
        print(f"=== Odczyty: godzina pomiaru: {current_time.strftime("%Y-%m-%d %H:%M")} ===")

        for i in range(3):    # Wykonujemy 3 pomiary
        print(f"\n=== Cykl odczytu {i + 1} ===")
            for sensor in sensors:    # Iterujemyn po każdym sensorze
                value = sensor.read_value()    # Pomieranie wartości z sensora 
                if isinstance(sensor, AirQualitySensor):    # Gdy nazwa sensora to AirQuality, sprawdzany jest dodatkowy parametr  
                    print(f"{sensor.name}: {value:.2f} {sensor.unit} | {sensor.get_air_quality_level()}")
                else:    # Jeśli sensor ma parametr wpływający indywidualnie na wartość sensora, podawana jest przyczyna
                    print(f"{sensor.name}: {value:.2f} {sensor.unit}")
                if hasattr(sensor, 'przyczyna'):
                    print(f"    | {sensor.przyczyna}")
            time.sleep(1)    # Krótka przerwa pomiędzy następnymi pomiarami

    latest_log = os.path.join(logger.log_dir, datetime.now().strftime("sensors_%Y%m%d.csv"))
    if os.path.exists(latest_log):    # Warunek dodatkowy wyświetlający zawartość pliku zapisanych logow
        with open(latest_log, 'r') as f:
            print("Zawartosc pliku logow:")
            print(f.read())
    else:
        print("\nPlik logow nie istnieje")
        
if __name__ == "__main__":
    main()
