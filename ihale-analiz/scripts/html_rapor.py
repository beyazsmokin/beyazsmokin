#!/usr/bin/env python3
"""Analiz raporunu (Markdown) panelde görünen HTML'e ve PDF'e çevirir.

Kullanım: python3 html_rapor.py <İhaleler/ihale-kodu> [--pdf | --pdf-yok]

Okur:  <ihale-kodu> Rapor.md (rapor-yazari çıktısı)
Yazar: <ihale-kodu> Rapor.html (tek dosya, dış bağlantısız, yazdırmaya hazır A4)
       <ihale-kodu> Rapor.pdf  (varsayılan; bulunan ilk yolla)

PDF için sırayla denenir, hiçbiri ek kurulum zorunlu kılmaz:
  1. Playwright Chromium (pip install playwright)
  2. Bilgisayardaki Microsoft Edge ya da Google Chrome (Windows'ta Edge hep vardır)
  3. WeasyPrint (pip install weasyprint)
Hiçbiri yoksa HTML yine yazılır; panelde "Yazdır > PDF olarak kaydet" aynı çıktıyı verir.

Rapor içeriği değiştirilmez: Markdown aynen HTML'e çevrilir, yalnızca karar satırı
renkli bir rozete, güven etiketleri (BELGE, RESMİ, ARŞİV, TAHMİN) renkli işaretlere döner.
"""
import argparse
import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ETIKETLER = ("BELGE", "RESMİ", "ARŞİV", "TAHMİN")


# --- Markdown -> HTML (yalnızca raporlarda kullanılan alt küme) --------------------

def satir_ici(s: str) -> str:
    kodlar = []

    def kod_sakla(m):
        kodlar.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(kodlar) - 1}\x00"

    s = re.sub(r"`([^`]+)`", kod_sakla, s)
    s = html.escape(s, quote=False)

    def baglanti(m):
        metin, url = m.group(1), html.unescape(m.group(2))
        if not re.match(r"^(https?://|mailto:|#|[\w.\- ]+(/[\w.\- ]+)*$)", url):
            return metin
        return f'<a href="{html.escape(url)}">{metin}</a>'

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", baglanti, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    cip = lambda m: f'<span class="etiket e-{etiket_sinif(m.group(1))}">{m.group(1)}</span>'
    s = re.sub(r"\((" + "|".join(ETIKETLER) + r")\)", cip, s)
    s = re.sub(r"(?<![\w>])(" + "|".join(ETIKETLER) + r")(?![\w<])", cip, s)
    return re.sub(r"\x00(\d+)\x00", lambda m: kodlar[int(m.group(1))], s)


def etiket_sinif(e: str) -> str:
    return {"BELGE": "belge", "RESMİ": "resmi", "ARŞİV": "arsiv", "TAHMİN": "tahmin"}[e]


def tablo_hucreleri(satir: str) -> list[str]:
    return [h.strip() for h in satir.strip().strip("|").split("|")]


def md_html(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Markdown'ı HTML gövdesine çevirir; (html, [(başlık-id, başlık)]) döner."""
    satirlar = md.replace("\r\n", "\n").split("\n")
    cikti, icindekiler, i = [], [], 0
    paragraf: list[str] = []

    def paragraf_bitir():
        if paragraf:
            cikti.append(f"<p>{satir_ici(' '.join(paragraf))}</p>")
            paragraf.clear()

    while i < len(satirlar):
        s = satirlar[i]
        st = s.strip()
        if st.startswith("```"):
            paragraf_bitir()
            j = i + 1
            while j < len(satirlar) and not satirlar[j].strip().startswith("```"):
                j += 1
            cikti.append(f"<pre><code>{html.escape(chr(10).join(satirlar[i + 1:j]))}</code></pre>")
            i = j + 1
            continue
        if not st:
            paragraf_bitir()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            paragraf_bitir()
            seviye, metin = len(m.group(1)), m.group(2).strip()
            kimlik = f"b{len(icindekiler) + 1}"
            if seviye == 2:
                icindekiler.append((kimlik, re.sub(r"[*_`]", "", metin)))
            cikti.append(f'<h{seviye} id="{kimlik}">{satir_ici(metin)}</h{seviye}>')
            i += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", st):
            paragraf_bitir()
            cikti.append("<hr>")
            i += 1
            continue
        if st.startswith("|") and i + 1 < len(satirlar) and re.fullmatch(
                r"\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?", satirlar[i + 1].strip()):
            paragraf_bitir()
            bas = tablo_hucreleri(st)
            hiza = ["right" if h.endswith(":") and not h.startswith(":") else "center"
                    if h.startswith(":") and h.endswith(":") else "" for h in tablo_hucreleri(satirlar[i + 1])]
            j = i + 2
            govde = []
            while j < len(satirlar) and satirlar[j].strip().startswith("|"):
                govde.append(tablo_hucreleri(satirlar[j]))
                j += 1

            def hucre(etiket, metin, k):
                h = hiza[k] if k < len(hiza) else ""
                sayi = re.fullmatch(r"[-+%₺\s]*[\d.,]+\s*(₺|TL|%|m²|m³|m|kg|ton|adet)?", metin or "")
                stil = f' style="text-align:{h}"' if h else ' class="sayi"' if sayi else ""
                return f"<{etiket}{stil}>{satir_ici(metin)}</{etiket}>"

            cikti.append('<div class="tablo"><table><thead><tr>'
                         + "".join(hucre("th", h, k) for k, h in enumerate(bas)) + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(hucre("td", h, k) for k, h in enumerate(r)) + "</tr>"
                                   for r in govde) + "</tbody></table></div>")
            i = j
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", st):
            paragraf_bitir()
            sirali = bool(re.match(r"^\d", st))
            ogeler = []
            while i < len(satirlar) and re.match(r"^\s*([-*+]|\d+[.)])\s+", satirlar[i]):
                ogeler.append(re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", satirlar[i]))
                i += 1
                while i < len(satirlar) and satirlar[i].startswith(("   ", "\t")) and satirlar[i].strip() \
                        and not re.match(r"^\s*([-*+]|\d+[.)])\s+", satirlar[i]):
                    ogeler[-1] += " " + satirlar[i].strip()
                    i += 1
            lis = []
            for o in ogeler:
                g = re.match(r"^\[( |x|X)\]\s+(.*)$", o)
                if g:
                    isaret = "☑" if g.group(1).lower() == "x" else "☐"
                    lis.append(f'<li class="gorev"><span class="kutu">{isaret}</span>{satir_ici(g.group(2))}</li>')
                else:
                    lis.append(f"<li>{satir_ici(o)}</li>")
            t = "ol" if sirali else "ul"
            cikti.append(f"<{t}>{''.join(lis)}</{t}>")
            continue
        if st.startswith(">"):
            paragraf_bitir()
            alinti = []
            while i < len(satirlar) and satirlar[i].strip().startswith(">"):
                alinti.append(satirlar[i].strip()[1:].strip())
                i += 1
            cikti.append(f"<blockquote>{satir_ici(' '.join(alinti))}</blockquote>")
            continue
        paragraf.append(st)
        i += 1
    paragraf_bitir()
    return "\n".join(cikti), icindekiler


# --- Sayfa --------------------------------------------------------------------------

KARAR_SINIF = (("şartlı", "sartli"), ("katılma", "katilma"), ("katil", "katil"), ("katıl", "katil"))


def karar_bul(md: str) -> tuple[str | None, str | None]:
    m = re.search(r"^\*\*Karar:\*\*\s*(.+)$", md, re.M)
    if not m:
        return None, None
    metin = m.group(1).strip()
    k = metin.lower()
    for anahtar, sinif in KARAR_SINIF:
        if k.startswith(anahtar):
            return metin, sinif
    return metin, "belirsiz"


def logo() -> str:
    for p in (SKILL_DIR / "panel" / "ikon-192.png", SKILL_DIR / "assets" / "ikon.png"):
        if p.exists() and p.stat().st_size < 200_000:
            return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return ""


CSS = """
:root{--zemin:#f4f6f9;--kagit:#fff;--yazi:#1a2230;--ikincil:#5a6475;--cizgi:#dfe3ea;--vurgu:#1f5fbf;
--yesil:#13795b;--yesil-z:#e3f4ec;--sari:#9a6400;--sari-z:#fdf1d8;--kirmizi:#b42318;--kirmizi-z:#fde8e6;
--mavi-z:#e7effb;--mor:#6941c6;--mor-z:#f0eafc;--gri-z:#eef0f3}
@media (prefers-color-scheme:dark){:root{--zemin:#0f131a;--kagit:#171c25;--yazi:#e5e9f0;--ikincil:#9aa4b5;
--cizgi:#2a3140;--vurgu:#6ea8ff;--yesil:#5fd3a5;--yesil-z:#11352a;--sari:#f2c063;--sari-z:#3a2e12;
--kirmizi:#ff8a80;--kirmizi-z:#3b1714;--mavi-z:#16263f;--mor:#b8a1ff;--mor-z:#271f42;--gri-z:#222937}}
*{box-sizing:border-box}
body{margin:0;background:var(--zemin);color:var(--yazi);font:15px/1.6 "Segoe UI",system-ui,-apple-system,sans-serif}
.sayfa{max-width:900px;margin:24px auto;background:var(--kagit);border:1px solid var(--cizgi);border-radius:12px;
padding:40px 48px}
header.ust{display:flex;gap:16px;align-items:center;border-bottom:2px solid var(--vurgu);padding-bottom:16px;margin-bottom:20px}
header.ust img{width:52px;height:52px;border-radius:10px}
header.ust .baslik{flex:1}
header.ust .baslik small{color:var(--ikincil);display:block;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
header.ust h1{margin:0;font-size:22px;line-height:1.3}
header.ust .tarih{color:var(--ikincil);font-size:13px;text-align:right}
.karar{display:flex;gap:14px;align-items:center;border-radius:10px;padding:14px 18px;margin:0 0 20px;
background:var(--gri-z);border:1px solid var(--cizgi)}
.karar b{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--ikincil)}
.karar span{font-size:16px;font-weight:600}
.karar.katil{background:var(--yesil-z);border-color:var(--yesil)} .karar.katil span{color:var(--yesil)}
.karar.sartli{background:var(--sari-z);border-color:var(--sari)} .karar.sartli span{color:var(--sari)}
.karar.katilma{background:var(--kirmizi-z);border-color:var(--kirmizi)} .karar.katilma span{color:var(--kirmizi)}
nav.icindekiler{border:1px solid var(--cizgi);border-radius:10px;padding:12px 18px;margin-bottom:24px;font-size:14px}
nav.icindekiler b{display:block;margin-bottom:4px}
nav.icindekiler ol{margin:0;padding-left:20px;columns:2;column-gap:24px}
nav.icindekiler a{color:var(--vurgu);text-decoration:none}
h1{font-size:22px} h2{font-size:18px;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--cizgi)}
h3{font-size:16px;margin:20px 0 8px}
a{color:var(--vurgu)}
.tablo{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{border:1px solid var(--cizgi);padding:6px 9px;vertical-align:top;text-align:left}
th{background:var(--mavi-z);font-weight:600}
tbody tr:nth-child(even) td{background:color-mix(in srgb,var(--gri-z) 55%,transparent)}
td.sayi,th.sayi{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
blockquote{margin:12px 0;padding:10px 16px;border-left:4px solid var(--vurgu);background:var(--mavi-z);border-radius:0 8px 8px 0}
code{background:var(--gri-z);padding:1px 5px;border-radius:4px;font-size:.92em}
pre{background:var(--gri-z);padding:12px;border-radius:8px;overflow:auto}
li.gorev{list-style:none;margin-left:-20px} .kutu{display:inline-block;width:22px;color:var(--vurgu)}
.etiket{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.04em;padding:0 6px;border-radius:9px;
vertical-align:1px;border:1px solid}
.e-belge{color:var(--yesil);border-color:var(--yesil);background:var(--yesil-z)}
.e-resmi{color:var(--vurgu);border-color:var(--vurgu);background:var(--mavi-z)}
.e-arsiv{color:var(--mor);border-color:var(--mor);background:var(--mor-z)}
.e-tahmin{color:var(--sari);border-color:var(--sari);background:var(--sari-z)}
hr{border:0;border-top:1px solid var(--cizgi);margin:24px 0}
footer.alt{margin-top:28px;padding-top:12px;border-top:1px solid var(--cizgi);color:var(--ikincil);font-size:12px;
display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:640px){.sayfa{margin:0;border-radius:0;border:0;padding:20px 16px}nav.icindekiler ol{columns:1}
header.ust .tarih{display:none}}
@page{size:A4;margin:16mm 14mm 18mm}
@media print{:root{--zemin:#fff;--kagit:#fff;--yazi:#000;--ikincil:#444;--cizgi:#c9ced6;--vurgu:#1f5fbf;
--yesil:#13795b;--yesil-z:#e3f4ec;--sari:#8a5a00;--sari-z:#fdf1d8;--kirmizi:#b42318;--kirmizi-z:#fde8e6;
--mavi-z:#e7effb;--mor:#6941c6;--mor-z:#f0eafc;--gri-z:#f1f3f6}
body{background:#fff;font-size:11pt}.sayfa{margin:0;border:0;padding:0;max-width:none}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
h2{break-after:avoid}tr,blockquote,.karar{break-inside:avoid}nav.icindekiler a{color:inherit}}
"""


def sayfa(md: str, kod: str) -> str:
    govde, icindekiler = md_html(md)
    karar, sinif = karar_bul(md)
    if karar:
        govde = re.sub(r"<p><strong>Karar:</strong>.*?</p>", "", govde, count=1, flags=re.S)
    govde = re.sub(r"^<h1[^>]*>.*?</h1>", "", govde, count=1, flags=re.S)
    baslik_m = re.search(r"^#\s+(.+)$", md, re.M)
    baslik = re.sub(r"[*_`]", "", baslik_m.group(1)) if baslik_m else f"İhale Analiz Raporu: {kod}"
    zaman = datetime.now().strftime("%d.%m.%Y %H:%M")
    ic = "".join(f'<li><a href="#{k}">{html.escape(t)}</a></li>' for k, t in icindekiler)
    lg = logo()
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{html.escape(baslik)}</title>
<style>{CSS}</style></head>
<body><article class="sayfa">
<header class="ust">{f'<img src="{lg}" alt="">' if lg else ''}
<div class="baslik"><small>İhale Analiz Raporu</small><h1>{html.escape(baslik)}</h1></div>
<div class="tarih">Oluşturma<br>{zaman}</div></header>
{f'<div class="karar {sinif}"><b>Karar</b><span>{satir_ici(karar)}</span></div>' if karar else ''}
{f'<nav class="icindekiler"><b>İçindekiler</b><ol>{ic}</ol></nav>' if len(icindekiler) > 2 else ''}
{govde}
<footer class="alt"><span>{html.escape(kod)}</span><span>ihale-analiz · {zaman}</span></footer>
</article></body></html>
"""


# --- PDF ---------------------------------------------------------------------------

def tarayici_bul() -> str | None:
    adaylar = []
    if sys.platform == "win32":
        for kok in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"),
                    os.environ.get("LOCALAPPDATA")):
            if kok:
                adaylar += [Path(kok) / "Microsoft/Edge/Application/msedge.exe",
                            Path(kok) / "Google/Chrome/Application/chrome.exe"]
    elif sys.platform == "darwin":
        adaylar += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                    Path("/Applications/Chromium.app/Contents/MacOS/Chromium")]
    for p in adaylar:
        if p.exists():
            return str(p)
    for ad in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge"):
        if shutil.which(ad):
            return shutil.which(ad)
    return None


def pdf_yaz(html_yolu: Path, pdf_yolu: Path) -> str | None:
    """PDF'i yazar; kullanılan yolu ya da None döner."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            s = b.new_page()
            s.goto(html_yolu.resolve().as_uri())
            s.emulate_media(media="print")
            s.pdf(path=str(pdf_yolu), format="A4", print_background=True, display_header_footer=True,
                  header_template="<span></span>",
                  footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#666">'
                                  '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                  margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
            b.close()
        return "Playwright"
    except Exception:
        pass
    exe = tarayici_bul()
    if exe:
        ek = ["--no-sandbox"] if hasattr(os, "geteuid") and os.geteuid() == 0 else []  # root'ta Chrome şart koşar
        with tempfile.TemporaryDirectory() as profil:
            try:
                subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", *ek,
                                f"--user-data-dir={profil}", f"--print-to-pdf={pdf_yolu}",
                                html_yolu.resolve().as_uri()], capture_output=True, timeout=90)
            except (subprocess.TimeoutExpired, OSError):
                pass
        if pdf_yolu.exists() and pdf_yolu.stat().st_size > 0:
            return Path(exe).stem
    try:
        from weasyprint import HTML
        HTML(filename=str(html_yolu)).write_pdf(str(pdf_yolu))
        return "WeasyPrint"
    except Exception:
        return None


def olustur(klasor: Path, pdf: bool = True) -> dict:
    md_yolu = next(iter(sorted(klasor.glob("* Rapor.md"))), None)
    if not md_yolu:
        raise FileNotFoundError(f"Rapor bulunamadı: {klasor}/<kod> Rapor.md")
    kod = md_yolu.name[: -len(" Rapor.md")]
    html_yolu = md_yolu.with_suffix(".html")
    html_yolu.write_text(sayfa(md_yolu.read_text(encoding="utf-8"), kod), encoding="utf-8")
    sonuc = {"html": html_yolu, "pdf": None, "pdf_yolu": None}
    if pdf:
        pdf_yolu = md_yolu.with_suffix(".pdf")
        if pdf_yolu.exists():
            pdf_yolu.unlink()
        yol = pdf_yaz(html_yolu, pdf_yolu)
        if yol:
            sonuc.update(pdf=pdf_yolu, pdf_yolu=yol)
    return sonuc


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("klasor", type=Path)
    p.add_argument("--pdf-yok", action="store_true", help="yalnızca HTML yaz")
    a = p.parse_args()
    try:
        s = olustur(a.klasor, not a.pdf_yok)
    except FileNotFoundError as e:
        sys.exit(str(e))
    print(f"HTML: {s['html']}")
    if s["pdf"]:
        print(f"PDF: {s['pdf']} ({s['pdf_yolu']})")
    elif not a.pdf_yok:
        print("PDF yazılamadı: Edge/Chrome, Playwright ya da WeasyPrint bulunamadı. "
              "HTML raporu panelde açıp Yazdır > PDF olarak kaydet ile alabilirsiniz.")


if __name__ == "__main__":
    main()
