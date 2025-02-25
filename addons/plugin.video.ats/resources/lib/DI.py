import requests
import routing


class DI:
    session = requests.Session()
    plugin = routing.Plugin()

DI = DI()
