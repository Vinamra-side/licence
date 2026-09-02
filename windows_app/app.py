import sys
from pathlib import Path
import webview
from backend_config import LICENCE_API_URL

def main():
    icon = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "app-icon.ico"
    webview.create_window("Licence Control", LICENCE_API_URL, width=1180, height=760,
                          min_size=(960, 640), background_color="#0b0d11")
    webview.start(icon=str(icon) if icon.exists() else None, private_mode=False)

if __name__ == "__main__":
    main()
