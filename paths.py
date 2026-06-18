import os
import sys


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def models_dir(custom_dir=None):
    base = custom_dir if custom_dir else get_base_dir()
    return os.path.join(base, "whisper-models")
