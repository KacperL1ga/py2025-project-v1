import time
from datetime import datetime
from Logger import Logger
from Czujniki import TemperatureSensor, HumiditySensor, PressureSensor, AirQualitySensor

def main():
    logger = Logger("config.json")    # Inicjalizacja loggera
    logger.start()
    
    temp_sensor = TemperatureSensor(sensor_id = "temp_1")
    hum_sensor = HumiditySensor(sensor_id = "hum_2", temperature_sensor = temp_sensor)
    ps_sensor = PressureSensor(sensor_id = "press_3")
    aq_sensor = AirQualitySensor(sensor_id = "air_4", humidity_sensor = hum_sensor)

    # Rejestracja loggera jako obserwatora
    for sensors in [
        temp_sensor,
        hum_sensor,
        ps_sensor,
        aq_sensor
    ]:
        sensors.register_callback(logger.log_reading)

    try:
        for i in range(4):# Wykonujemy 4 pomiary
            print(f"\n=== Cykl odczytu {i + 1} ===")
            for sensor in [temp_sensor,hum_sensor,ps_sensor,aq_sensor]:    # Iterujemyn po każdym sensorze
                value = sensor.read_value()    # Pomieranie wartości z sensora 
                if isinstance(sensor, AirQualitySensor):    # Gdy nazwa sensora to AirQuality, sprawdzany jest dodatkowy parametr  
                    print(f"{sensor.name}: {value:.2f} {sensor.unit} | {sensor.get_air_quality_level()}")
                else:    # Jeśli sensor ma parametr wpływający indywidualnie na wartość sensora, podawana jest przyczyna
                    print(f"{sensor.name}: {value:.2f} {sensor.unit}")
                if hasattr(sensor, 'przyczyna'):
                    print(f"    | {sensor.przyczyna}")
            print()
            time.sleep(1)    # Krótka przerwa pomiędzy następnymi pomiarami
    finally:
        logger.stop()
        
if __name__ == "__main__":
    main()
