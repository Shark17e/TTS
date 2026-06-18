import sys
import threading

from config import load_config
from hotkey import HotkeyListener
from paster import paste_text
from recorder import Recorder
from transcriber import Transcriber
from tray import TrayIcon


def main():
    try:
        config = load_config()
    except Exception as e:
        print(f"Errore caricamento config.json: {e}", file=sys.stderr)
        sys.exit(1)

    tray = TrayIcon(on_exit=lambda: tray.stop())
    tray.set_error("Avvio...")

    try:
        recorder = Recorder(config)
    except Exception as e:
        print(f"Errore inizializzazione microfono: {e}", file=sys.stderr)
        recorder = None

    try:
        transcriber = Transcriber(config)
    except Exception as e:
        print(f"Errore caricamento modello: {e}", file=sys.stderr)
        transcriber = None

    _lock = threading.Lock()

    def _work():
        try:
            tray.set_recording()
            audio = recorder.record()
            if audio is not None:
                tray.set_processing()
                text = transcriber.transcribe(audio)
                if text:
                    paste_text(text)
            tray.set_idle()
        except Exception as e:
            print(f"Errore: {e}", file=sys.stderr)
            tray.set_error(str(e)[:60])

    def on_hotkey():
        if recorder is None:
            tray.set_error("Microfono non disponibile")
            return
        if transcriber is None:
            tray.set_error("Modello non caricato")
            return
        if recorder.is_recording:
            recorder.stop()
            return
        if not _lock.acquire(blocking=False):
            return
        threading.Thread(target=_work_wrapper, daemon=True).start()

    def _work_wrapper():
        try:
            _work()
        finally:
            _lock.release()

    hotkey = HotkeyListener(config, on_hotkey)

    try:
        hotkey.start()
    except Exception as e:
        print(f"Errore registrazione hotkey: {e}", file=sys.stderr)
        tray.set_error("Hotkey")
        hotkey = None

    print(f"Dictate-Win avviato. Hotkey: {hotkey.hotkey_str if hotkey else 'N/A'}")
    tray.set_idle()
    tray.run()

    if hotkey is not None:
        hotkey.stop()


if __name__ == "__main__":
    main()
