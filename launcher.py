"""
HireMate Desktop Launcher
Opens HireMate in a native desktop window (no browser needed).
"""
import sys
import os
import threading
import logging

logging.disable(logging.WARNING)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

sys.stdout = open(os.devnull, "w")
sys.stderr = open(os.devnull, "w")

from app import app

def start_server():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    import webview

    server = threading.Thread(target=start_server, daemon=True)
    server.start()

    import time
    import urllib.request

    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1)
            break
        except Exception:
            time.sleep(0.3)

    window = webview.create_window(
        "HireMate",
        "http://127.0.0.1:5000/dashboard",
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color="#08080a",
        text_select=True,
    )
    webview.start()
