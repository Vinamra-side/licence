import webview
from backend_config import LICENCE_API_URL

def main():
    webview.create_window("Licence Control", LICENCE_API_URL, width=1180, height=760,
                          min_size=(960, 640), background_color="#0b0d11")
    webview.start(private_mode=False)

if __name__ == "__main__":
    main()
