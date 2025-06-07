import time

from Logger import Logger
from Czujniki import TemperatureSensor, HumiditySensor, PressureSensor, AirQualitySensor
from NetworkClient import NetworkClient
import yaml


def load_network_config():
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    return config['network']

def main():
    #Wczytanie konfiguracji sieci
    network_config = load_network_config()
    network_client = NetworkClient(
        host=network_config['host'],
        port=network_config['port'],
        timeout=network_config['timeout'],
        retries=network_config['retries']
    )

    logger = Logger("config.json")  # Inicjalizacja loggera
    logger.start()

    temp_sensor = TemperatureSensor(sensor_id="temp_1")
    hum_sensor = HumiditySensor(sensor_id="hum_2", temperature_sensor=temp_sensor)
    ps_sensor = PressureSensor(sensor_id="press_3")
    aq_sensor = AirQualitySensor(sensor_id="air_4", humidity_sensor=hum_sensor)

    def send_to_network(sensor_id, timestamp, value, unit):
        data = {
            "sensor_id" : sensor_id,
            "timestamp" : timestamp.isoformat(),
            "value" : value,
            "unit" : unit
        }
        try:
            if not hasattr(network_client, 'socket') or not network_client.socket:
                network_client.connect()
            network_client.send(data)
        except Exception as e:
            logger.logger.error(f"Błąd wysyłania danych sieciowych", exc_info=True)

    # Rejestracja loggera jako obserwatora
    for sensors in [temp_sensor, hum_sensor, ps_sensor, aq_sensor]:
        sensors.register_callback(logger.log_reading)
        sensors.register_callback(send_to_network)

    try:
        for i in range(4):  # Wykonujemy 4 pomiary
            print(f"\n=== Cykl odczytu {i + 1} ===")
            for sensor in [temp_sensor, hum_sensor, ps_sensor, aq_sensor]:  # Iterujemyn po każdym sensorze
                value = sensor.read_value()  # Pomieranie wartości z sensora
                if isinstance(sensor,
                              AirQualitySensor):  # Gdy nazwa sensora to AirQuality, sprawdzany jest dodatkowy parametr
                    print(f"{sensor.name}: {value:.2f} {sensor.unit} | {sensor.get_air_quality_level()}")
                else:  # Jeśli sensor ma parametr wpływający indywidualnie na wartość sensora, podawana jest przyczyna
                    print(f"{sensor.name}: {value:.2f} {sensor.unit}")
                if hasattr(sensor, 'przyczyna'):
                    print(f"    | {sensor.przyczyna}")
            print()
            time.sleep(1)  # Krótka przerwa pomiędzy następnymi pomiarami
    finally:
        logger.stop()
        network_client.close()


if __name__ == "__main__":
    main()