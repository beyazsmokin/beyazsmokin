#!/usr/bin/env python3
"""ihale-analiz çalışma alanını masaüstüne kurar.

Kullanım: python3 init_workspace.py [hedef-klasor]

- Masaüstünde "İhale Analiz" klasörünü özel simgesiyle oluşturur.
- Sistem dosyalarını (ayarlar, hafıza, skill dosyaları, Excel şablonları)
  gizli `.sistem` klasörüne kurar.
- Mevcut dosyaların üzerine yazmaz; tekrar çalıştırmak güvenlidir.
"""
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "setup" / "workspace-template"
FOLDER_NAME = "İhale Analiz"
SKILL_PARTS = ["SKILL.md", "kurallar.md", "agents", "templates", "scripts", "assets"]


def desktop_dir() -> Path:
    if sys.platform == "win32":
        # OneDrive ya da yerelleştirilmiş masaüstü yolunu Windows'tan al
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf)  # CSIDL_DESKTOPDIRECTORY
        if buf.value:
            return Path(buf.value)
    elif sys.platform.startswith("linux") and shutil.which("xdg-user-dir"):
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True).stdout.strip()
        if out:
            return Path(out)
    return Path.home() / "Desktop"


def copy_tree(src: Path, dst: Path) -> int:
    created = 0
    for f in [src] if src.is_file() else src.rglob("*"):
        if f.is_dir() or "__pycache__" in f.parts:
            continue
        target = dst if src.is_file() else dst / f.relative_to(src)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        created += 1
    return created


def hide(path: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(["attrib", "+h", "+s", str(path)], capture_output=True)
    elif sys.platform == "darwin":
        subprocess.run(["chflags", "hidden", str(path)], capture_output=True)
    # Linux: nokta ile başlayan adlar zaten gizlidir


def set_icon(folder: Path, sistem: Path) -> None:
    if sys.platform == "win32":
        ini = folder / "desktop.ini"
        if ini.exists():
            subprocess.run(["attrib", "-h", "-s", str(ini)], capture_output=True)
        ini.write_text(
            "[.ShellClassInfo]\r\n"
            "IconResource=.sistem\\skill\\assets\\ikon.ico,0\r\n"
            "InfoTip=İhale analiz çalışma alanı\r\n",
            encoding="utf-16",
        )
        subprocess.run(["attrib", "+h", "+s", str(ini)], capture_output=True)
        subprocess.run(["attrib", "+r", str(folder)], capture_output=True)  # Explorer desktop.ini'yi okusun
    elif sys.platform == "darwin":
        png = sistem / "skill" / "assets" / "ikon.png"
        script = (
            'ObjC.import("AppKit");'
            f'$.NSWorkspace.sharedWorkspace.setIconForFileOptions('
            f'$.NSImage.alloc.initWithContentsOfFile("{png}"), "{folder}", 0);'
        )
        subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True)
    elif shutil.which("gio"):
        png = sistem / "skill" / "assets" / "ikon.png"
        subprocess.run(["gio", "set", str(folder), "metadata::custom-icon", png.as_uri()],
                       capture_output=True)


def main() -> None:
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else desktop_dir() / FOLDER_NAME
    sistem = root / ".sistem"

    created = copy_tree(TEMPLATE, root)
    for part in SKILL_PARTS:
        created += copy_tree(SKILL_DIR / part, sistem / "skill" / part)
    created += copy_tree(SKILL_DIR / "templates" / "excel", sistem / "sablonlar")

    config = sistem / "config.yaml"
    text = config.read_text(encoding="utf-8")
    if 'kurulum_tarihi: ""' in text:
        text = text.replace('kurulum_tarihi: ""', f'kurulum_tarihi: "{date.today()}"')
        config.write_text(text, encoding="utf-8")

    hide(sistem)
    set_icon(root, sistem)

    print(f"Çalışma alanı: {root}")
    print(f"Oluşturulan dosya: {created}")
    dwg_kontrol()
    site_girisi(sistem)


def dwg_kontrol() -> None:
    """DWG çeviricisi yoksa nedenini ve diğer yolu anlatır, indirme sayfasını önerir."""
    import dwg_cevirici
    print()
    print(dwg_cevirici.durum_metni())
    if dwg_cevirici.bul() is None and sys.stdin.isatty():
        try:
            cevap = input("ODA File Converter indirme sayfası açılsın mı? (E/H): ").strip().lower()
        except EOFError:
            return
        if cevap in ("e", "evet", "y"):
            import webbrowser
            webbrowser.open(dwg_cevirici.ODA_URL)


def site_girisi(sistem: Path) -> None:
    """İhale sitesi giriş panelini açar (kullanıcı panelde atlayabilir)."""
    import siteler
    print()
    if siteler.oku(sistem)["durum"] != "sorulmadi":
        print(siteler.durum_metni(siteler.oku(sistem)))
        return
    if not sys.stdin.isatty():
        print("İhale sitesi girişi için: python scripts/siteler.py panel")
        return
    print("İhaleleri takip ettiğiniz site için tarayıcıda giriş paneli açılıyor.")
    print("İstemezseniz panelde 'Girişi atla' deyin.")
    print(siteler.durum_metni(siteler.panel(sistem)))


if __name__ == "__main__":
    main()
