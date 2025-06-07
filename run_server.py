from NetworkServer import NetworkServer
import yaml

def load_network_config():
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    return config['network']

if __name__ == "__main__":
    config = load_network_config()
    server = NetworkServer(port=config['port'])
    print(f"Uruchamianie serwera na porcie {config['port']}...")
    server.start()