"""
GPTify Meet - Launcher Script
Starts the backend server and opens the app in the browser.
"""
import sys
import webbrowser
import threading
import time
import uvicorn
from server import app

def open_browser():
    time.sleep(1.2)
    print("\n[GPTify Meet] Ilova brauzerda ochilmoqda: http://127.0.0.1:8000\n")
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
