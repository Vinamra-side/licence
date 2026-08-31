from pathlib import Path

from PIL import Image


assets = Path(__file__).parent / "assets"
image = Image.open(assets / "app-icon-512.png").convert("RGBA")
image.save(assets / "app-icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
