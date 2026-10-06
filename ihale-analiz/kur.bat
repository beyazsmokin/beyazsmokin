@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul || (echo Python bulunamadi. https://python.org adresinden kurun. & pause & exit /b 1)
python -m pip install --quiet --disable-pip-version-check openpyxl ezdxf pdfplumber pillow keyring playwright pystray win11toast || (echo Python paketleri kurulamadi. Internet baglantisini kontrol edip tekrar deneyin. & pause & exit /b 1)
python scripts\init_workspace.py %*
pause
