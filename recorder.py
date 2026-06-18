import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, config):
        self._config = config
        self._stop_requested = False
        self._is_recording = False

    @property
    def is_recording(self):
        return self._is_recording

    def stop(self):
        self._stop_requested = True

    def record(self):
        sr = self._config["audio"]["sample_rate"]
        threshold = self._config["audio"]["silence_threshold"]
        silence_dur = self._config["audio"]["silence_duration_sec"]
        min_dur = self._config["audio"]["min_duration_sec"]
        max_dur = self._config["audio"]["max_duration_sec"]

        chunk_ms = 100
        chunk_size = int(sr * chunk_ms / 1000)
        self._stop_requested = False
        self._is_recording = True

        chunks = []
        silent_chunks = 0
        max_silent = int(silence_dur * 1000 / chunk_ms)
        min_chunks = int(min_dur * 1000 / chunk_ms)
        max_chunks = int(max_dur * 1000 / chunk_ms)

        try:
            stream = sd.InputStream(samplerate=sr, channels=1, dtype="float32")
            stream.start()
        except Exception as e:
            self._is_recording = False
            raise RuntimeError(f"Impossibile aprire il microfono: {e}") from e

        try:
            while True:
                if self._stop_requested:
                    break

                chunk, _ = stream.read(chunk_size)
                rms = np.sqrt(np.mean(chunk ** 2))
                chunks.append(chunk)

                if rms < threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                if len(chunks) > min_chunks and silent_chunks >= max_silent:
                    break

                if len(chunks) >= max_chunks:
                    break
        finally:
            stream.stop()
            stream.close()
            self._is_recording = False

        if not chunks:
            return None

        audio = np.concatenate(chunks)
        return audio.flatten()
