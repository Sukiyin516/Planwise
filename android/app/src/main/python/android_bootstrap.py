"""The same Python server runs inside the Android app, on loopback only."""
from pathlib import Path
from threading import Thread
import main

_server = None


def start(private_directory):
    global _server
    if _server is None:
        _server = main.make_server(Path(private_directory)/'planwise.json',port=0)
        Thread(target=_server.serve_forever,name='planwise-local',daemon=True).start()
    return f'http://127.0.0.1:{_server.server_port}/?tab=map'
