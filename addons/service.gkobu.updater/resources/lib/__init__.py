import xbmc

class MainMonitor(xbmc.Monitor):
    def __init__(self):
        super(MainMonitor, self).__init__()

monitor = MainMonitor()

