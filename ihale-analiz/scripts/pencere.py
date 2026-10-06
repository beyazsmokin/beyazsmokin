"""Paneli tarayıcı sekmesi yerine kendi uygulama penceresinde açar.

Edge ya da Chrome `--app` kipinde açılır: adres çubuğu ve sekmeler olmaz, görev
çubuğunda panelin kendi simgesi görünür. İkisi de yoksa varsayılan tarayıcıya düşer.
"""
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def tarayici_yolu() -> str | None:
    if sys.platform == "win32":
        adaylar = []
        for kok in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"),
                    os.environ.get("LOCALAPPDATA")):
            if kok:
                adaylar += [Path(kok) / "Microsoft/Edge/Application/msedge.exe",
                            Path(kok) / "Google/Chrome/Application/chrome.exe"]
        return next((str(p) for p in adaylar if p.is_file()), None)
    if sys.platform == "darwin":
        for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
            if Path(p).is_file():
                return p
        return None
    for ad in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
        if shutil.which(ad):
            return shutil.which(ad)
    return None


def one_getir(baslik: str) -> bool:
    """Başlığında `baslik` geçen açık pencere varsa öne getirir (Windows). İkinci pencere açılmaz."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    bulunan = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def tara(hwnd, _):
        if u.IsWindowVisible(hwnd):
            n = u.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, b, n + 1)
            if baslik in b.value:
                bulunan.append(hwnd)
                return False
        return True
    u.EnumWindows(tara, 0)
    if not bulunan:
        return False
    u.ShowWindow(bulunan[0], 9)  # SW_RESTORE
    u.SetForegroundWindow(bulunan[0])
    return True


def ac(adres: str, genislik: int = 1280, yukseklik: int = 860, baslik: str | None = "İhale Analiz") -> None:
    if baslik and one_getir(baslik):
        return
    exe = tarayici_yolu()
    if not exe:
        webbrowser.open(adres)
        return
    ek = {"creationflags": 0x00000008 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
    try:
        subprocess.Popen([exe, f"--app={adres}", f"--window-size={genislik},{yukseklik}"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **ek)
    except OSError:
        webbrowser.open(adres)
