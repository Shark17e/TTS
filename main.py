import sys
import threading

# Nascondi console appena possibile (prima di qualsiasi output)
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0
    )

from config import load_config, save_config, get_config_path
from hotkey import HotkeyListener
from paster import paste_text
from recorder import Recorder
from transcriber import Transcriber
from tray import TrayIcon


def main():
    config_path = get_config_path()

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Errore caricamento config.json: {e}", file=sys.stderr)
        sys.exit(1)

    _lock = threading.Lock()

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

    # --- callbacks ---

    def _on_hotkey():
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

    def _on_model_change(new_model):
        nonlocal config
        config["whisper"]["model_size"] = new_model
        save_config(config, config_path)
        tray.update_config(config)
        if transcriber is not None:
            transcriber.reload(new_model)

    def _on_hotkey_change():
        nonlocal config, hotkey
        save_config(config, config_path)
        new = HotkeyListener(config, _on_hotkey)
        try:
            new.start()
        except Exception as e:
            print(f"Errore nuovo hotkey: {e}", file=sys.stderr)
            new.stop()
        else:
            old = hotkey
            hotkey = new
            old.stop()
            tray.update_config(config)

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

    def _work_wrapper():
        try:
            _work()
        finally:
            _lock.release()

    # --- init ---

    hotkey = HotkeyListener(config, _on_hotkey)
    try:
        hotkey.start()
    except Exception as e:
        print(f"Errore registrazione hotkey: {e}", file=sys.stderr)
        hotkey = None

    tray = TrayIcon(
        config=config,
        on_exit=lambda: tray.stop(),
        on_model_change=_on_model_change,
        on_hotkey_change=_on_hotkey_change,
    )
    tray.set_idle()
    tray.run()

    if hotkey is not None:
        hotkey.stop()


if __name__ == "__main__":
    main()
