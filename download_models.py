import os
import shutil
import sys

from huggingface_hub import snapshot_download, list_repo_files

MODELS = {
    "tiny": "guillaumekln/faster-whisper-tiny",
    "base": "guillaumekln/faster-whisper-base",
    "small": "guillaumekln/faster-whisper-small",
    "medium": "guillaumekln/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

SIZES_BYTES = {
    "tiny": 150 * 1024 * 1024,
    "base": 300 * 1024 * 1024,
    "small": 500 * 1024 * 1024,
    "medium": 1500 * 1024 * 1024,
    "large-v3": 3000 * 1024 * 1024,
}

SIZES = {k: f"~{v // (1024*1024)} MB" for k, v in SIZES_BYTES.items()}
SIZES["medium"] = "~1.5 GB"
SIZES["large-v3"] = "~3 GB"


class DownloadCancelled(Exception):
    pass


class _TqdmWrapper:
    cancel = None
    on_progress = None

    def __init__(self, iterable=None, desc=None, total=None, unit=None, disable=False, **kwargs):
        self.total = total or 0
        self.n = 0
        self.desc = desc or ""

    def _check(self):
        if self.cancel and self.cancel.is_set():
            raise DownloadCancelled()

    def update(self, n=1):
        self._check()
        self.n += n
        if self.on_progress:
            self.on_progress(self.n, self.total)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def set_description(self, desc):
        self._check()
        self.desc = desc


def download_model(model_size, base_dir, on_progress=None, cancel=None):
    if model_size not in MODELS:
        raise ValueError(f"Modello sconosciuto: {model_size}")

    repo_id = MODELS[model_size]
    local_dir = os.path.join(base_dir, model_size)
    os.makedirs(local_dir, exist_ok=True)

    _TqdmWrapper.cancel = cancel
    _TqdmWrapper.on_progress = on_progress

    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            tqdm_class=_TqdmWrapper,
            max_workers=1,
        )
    except DownloadCancelled:
        shutil.rmtree(local_dir, ignore_errors=True)
        raise
    finally:
        _TqdmWrapper.cancel = None
        _TqdmWrapper.on_progress = None

    return local_dir


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper-models")
    selected = sys.argv[1:] if len(sys.argv) > 1 else list(MODELS.keys())

    total_mb = sum(SIZES_BYTES[k] for k in selected if k in SIZES_BYTES) // (1024 * 1024)
    print(f"Modelli da scaricare: {', '.join(selected)}")
    print(f"Spazio stimato: ~{total_mb} MB (~{total_mb/1024:.1f} GB)")
    print()

    for name in selected:
        try:
            download_model(name, base_dir)
        except DownloadCancelled:
            print("Download annullato.")
            break

    print("Tutti i download completati.")
    print(f"I modelli si trovano in: {base_dir}")


if __name__ == "__main__":
    main()
