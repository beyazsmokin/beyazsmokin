#!/usr/bin/env python3
"""ihale-analiz çalışma alanını kurar. Mevcut dosyaların üzerine yazmaz."""
import shutil
import sys
from datetime import date
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "setup" / "workspace-template"
DEFAULT_TARGET = Path.home() / "ihale-analiz-calisma"


def main() -> None:
    target = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_TARGET
    created = []
    for src in TEMPLATE.rglob("*"):
        if src.is_dir():
            continue
        dst = target / src.relative_to(TEMPLATE)
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        created.append(dst)

    config = target / "config.yaml"
    text = config.read_text(encoding="utf-8")
    if 'kurulum_tarihi: ""' in text:
        config.write_text(
            text.replace('kurulum_tarihi: ""', f'kurulum_tarihi: "{date.today()}"'),
            encoding="utf-8",
        )

    print(f"Çalışma alanı: {target}")
    print(f"Oluşturulan dosya: {len(created)}")


if __name__ == "__main__":
    main()
