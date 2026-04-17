"""Launch the local Flask dashboard and open it in the browser."""
import os
import sys
import threading
import time
import webbrowser

HOST = "127.0.0.1"
PORT = 5050
URL = f"http://{HOST}:{PORT}"


def open_browser():
    time.sleep(1.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dashboard"))
    from db import init_db
    init_db()

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"🦞 MimiClaw Dashboard starting at {URL}")

    from dashboard.app import create_app
    flask_app = create_app()
    flask_app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
