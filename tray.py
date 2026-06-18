import pystray
from PIL import Image, ImageDraw


def _make_image(hex_color):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
    draw.ellipse([6, 6, size - 6, size - 6], fill=(*rgb, 255))
    return img


class TrayIcon:
    def __init__(self, on_exit):
        menu = pystray.Menu(pystray.MenuItem("Esci", lambda icon: on_exit()))
        self._icon = pystray.Icon(
            "dictate-win",
            _make_image("#22c55e"),
            "Dictate-Win - In ascolto",
            menu,
        )

    def set_idle(self):
        self._icon.icon = _make_image("#22c55e")
        self._icon.title = "Dictate-Win - In ascolto"

    def set_recording(self):
        self._icon.icon = _make_image("#ef4444")
        self._icon.title = "Dictate-Win - Registrazione..."

    def set_processing(self):
        self._icon.icon = _make_image("#f59e0b")
        self._icon.title = "Dictate-Win - Trascrizione in corso..."

    def set_error(self, msg=""):
        self._icon.icon = _make_image("#ef4444")
        self._icon.title = f"Dictate-Win - Errore{': ' + msg if msg else ''}"

    def run(self):
        self._icon.run()

    def stop(self):
        self._icon.stop()
