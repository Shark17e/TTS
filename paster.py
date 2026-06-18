import time

import pyautogui
import pyperclip


def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
