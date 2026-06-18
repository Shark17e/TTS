import os
import sys
import threading
import tkinter as tk
from tkinter import ttk

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


def _model_is_available(config):
    model_size = config["whisper"]["model_size"]
    model_dir = config["whisper"]["model_dir"]
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_dir)
    local = os.path.join(base, model_size)
    return os.path.isfile(os.path.join(local, "model.bin"))


def _ensure_model(config):
    if _model_is_available(config):
        return True

    import ctypes
    from download_models import download_model, SIZES, MODELS

    model_size = config["whisper"]["model_size"]
    size_str = SIZES.get(model_size, "?")
    model_names = ", ".join(f"{k} ({v})" for k, v in SIZES.items())

    msg = (
        f"Modello Whisper '{model_size}' non trovato.\n\n"
        f"Il modello occupa circa {size_str}.\n"
        f"Scaricarlo ora? (richiede connessione internet)\n\n"
        f"Modelli disponibili: {model_names}"
    )

    ret = ctypes.windll.user32.MessageBoxW(
        0, msg, "TTS - Modello mancante", 4 | 32
    )

    if ret != 6:
        return False

    root = tk.Tk()
    root.title("TTS - Download modello")
    root.geometry("420x130")
    root.resizable(False, False)
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")

    tk.Label(root, text=f"Download {model_size} ({size_str}) in corso...").pack(pady=(20, 5))
    bar = ttk.Progressbar(root, mode="indeterminate")
    bar.pack(fill=tk.X, padx=20, pady=5)
    bar.start()
    status = tk.Label(root, text="", fg="gray")
    status.pack()

    def _ok():
        root.destroy()

    def _done():
        bar.stop()
        status.config(text="Download completato!")
        tk.Button(root, text="OK", command=_ok).pack(pady=10)

    def _err(e):
        bar.stop()
        status.config(text=f"Errore: {e}", fg="red")
        tk.Button(root, text="Esci", command=_ok).pack(pady=10)

    def _do():
        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            config["whisper"]["model_dir"],
        )
        try:
            download_model(model_size, base_dir)
            root.after(0, _done)
        except Exception as e:
            root.after(0, lambda: _err(e))

    threading.Thread(target=_do, daemon=True).start()
    root.mainloop()

    return _model_is_available(config)


def main():
    config_path = get_config_path()

    try:
        config = load_config(config_path)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(
            0, f"Errore caricamento config.json:\n{e}", "TTS - Errore", 16
        )
        sys.exit(1)

    if not _ensure_model(config):
        sys.exit(0)

    _lock = threading.Lock()

    try:
        recorder = Recorder(config)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(
            0, f"Microfono non disponibile:\n{e}", "TTS - Errore", 16
        )
        recorder = None

    try:
        transcriber = Transcriber(config)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(
            0, f"Errore caricamento modello:\n{e}", "TTS - Errore", 16
        )
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
