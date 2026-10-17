import os
import sys
import time
import socket
import webbrowser
import threading
try:
    import uvicorn
    HAS_UVICORN = True
except ImportError:
    HAS_UVICORN = False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_browser():
    time.sleep(1.2)
    url = "http://localhost:7860"
    print(f"Opening browser at {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    local_ip = get_local_ip()
    print("=" * 65)
    print("   [*] Starting LoveVoice AI Studio (Global Multilingual Edition)")
    print("   [*] 322+ Neural Voices in 76+ Languages (Urdu, Hindi, Spanish, etc.)")
    print("   [*] PC Address:     http://localhost:7860")
    print(f"   [*] Mobile Address: http://{local_ip}:7860")
    print("=" * 65)
    
    port = int(os.environ.get("PORT", 7860))
    if not os.environ.get("RENDER") and not os.environ.get("TERMUX_VERSION"):
        try:
            threading.Thread(target=open_browser, daemon=True).start()
        except Exception:
            pass

    if HAS_UVICORN:
        uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
    else:
        print("   [!] FastAPI/Uvicorn not found, launching ultra-light mobile engine...")
        import mobile_server
        app = mobile_server.create_app()
        mobile_server.web.run_app(app, host="0.0.0.0", port=port)

