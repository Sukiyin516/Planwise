"""Portable launcher; requires only Python 3.9+ standard library."""
import sys

if sys.version_info < (3, 9):
    raise SystemExit('Please install Python 3.9 or newer from https://www.python.org/downloads/')

from pathlib import Path
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'app'))
from main import make_server
from storage import empty_state, save_state


def run():
    demo = '--demo' in sys.argv
    data = ROOT / ('sample-data.json' if demo else 'my-data.json')
    if not demo and not data.exists():
        save_state(data, empty_state())
    server = make_server(data, port=0, demo=demo)
    url = 'http://127.0.0.1:%s/' % server.server_port
    print('Planwise: ' + url, flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    run()
