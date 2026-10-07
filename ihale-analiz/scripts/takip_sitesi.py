#!/usr/bin/env python3
"""Kullanıcının ihaleleri takip ettiği site: ihale listesi, İKN bilgisi, takip listesi, ihale dosyası.

Mimari: bütün ihale verisi kullanıcının kendi hesabıyla girdiği takip sitesinden gelir
(şimdilik ihalesitesi.com). EKAP'a doğrudan sorgu atılmaz; ihale dosyası, sitenin ilan
penceresindeki "EKAP Dökümanı" bağlantısıyla EKAP'ın doküman sayfasından indirilir.

- Giriş: kullanıcı adı `.sistem/siteler.json`'da, şifre bilgisayarın şifre kasasında durur
  (K-10.1); şifre hiçbir dosyaya, loga ya da çıktıya yazılmaz. Oturum
  `.sistem/oturumlar/<site>/` altındaki tarayıcı profilinde kalır.
- Takip listesi iki yönlüdür: panelden takibe alınan ihale sitede de takibe alınır, panelden
  takipten çıkarılan sitede de bırakılır; sitede takip edilenler panele gelir.
- İhale dosyası: EKAP'ın doküman sayfasındaki güvenlik kodu resmi kullanıcıya gösterilir,
  kodu KULLANICI yazar (K-5.10). Sonra "İndir"e basılır, dosya ihalenin klasörüne iner.

Kullanım:
  takip_sitesi.py liste [--gun 7] [--tur YAPIM] [--kelime okul]
  takip_sitesi.py bilgi 2026/1771435
  takip_sitesi.py takip-listesi
  takip_sitesi.py sonuclar [--gun 7] [--tur YAPIM]   # kesinleşen sonuçlar: kazanan, bedel, tenzilat
  takip_sitesi.py takip-et 2026/1771435      |  takip-birak 2026/1771435
  takip_sitesi.py indir 2026/1771435 --hedef "İhaleler/2026-1771435/kaynak"

Gerekli: pip install playwright keyring (bilgisayardaki Edge ya da Chrome kullanılır).
"""
import argparse
import html
import json
import re
import sys
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import siteler

SITE = "ihalesitesi"
TABAN = "https://www.ihalesitesi.com"
XHR = {"X-Requested-With": "XMLHttpRequest"}
TAKIP_KOLONLARI = ["checkbox", "snotify", "ih_kayit_no", "ih_tarihi", "ih_idare_adi", "ih_ihale_adi",
                   "ih_mkazanan", "ih_suresi", "kalansure", "ih_itirazbedel"]

_kilit = threading.Lock()  # aynı tarayıcı profilini iki iş birden açmasın


class SiteHatasi(RuntimeError):
    pass


# --- Yardımcılar -----------------------------------------------------------------------

def sistem_dir() -> Path:
    sistem = Path(__file__).resolve().parents[2]
    return sistem if sistem.name == ".sistem" else Path.cwd() / ".sistem"


def ikn_norm(ikn: str) -> str:
    s = re.sub(r"\s", "", ikn or "")
    if re.fullmatch(r"\d{2}DT\d+", s, re.I):  # doğrudan temin numarası (ör. 26DT1939622)
        return s.upper()
    m = re.fullmatch(r"(\d{4})[/-](\d+)", s)
    if not m:
        raise SiteHatasi(f"İKN anlaşılamadı: {ikn!r} (ör. 2026/123456 ya da 26DT123456)")
    return f"{m.group(1)}/{m.group(2)}"


def tarih_iso(v) -> str | None:
    """'18.11.2026 10:00' biçimini panelin biçimine (2026-11-18T10:00) çevirir."""
    v = str(v or "").strip()
    for f in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            d = datetime.strptime(v, f)
            return d.strftime("%Y-%m-%dT%H:%M" if "%H" in f else "%Y-%m-%d")
        except ValueError:
            pass
    return None


def _temiz(v) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(v or ""))).split())


def tr_baslik(metin: str) -> str:
    """'ESKİŞEHİR' -> 'Eskişehir' (str.title() Türkçe İ/ı harflerini bozar)."""
    def kucuk(x):
        return x.replace("I", "ı").replace("İ", "i").lower()

    def buyuk(x):
        return x.replace("i", "İ").replace("ı", "I").upper()
    return " ".join(buyuk(k[:1]) + kucuk(k[1:]) for k in (metin or "").split())


def site_kayitli(sistem: Path, site: str = SITE) -> bool:
    return site in siteler.oku(sistem)["siteler"]


def sadelestir(r: dict) -> dict:
    """Site satırını panelin ihale alanlarına çevirir. Uydurma alan eklenmez."""
    benzer = _temiz(r.get("ih_benzeris"))
    tur = _temiz(r.get("ih_turu"))
    return {
        "ikn": _temiz(r.get("ih_kayit_no")) or None,
        "ad": _temiz(r.get("ih_ihale_adi")) or None,
        "idare": _temiz(r.get("ih_idare_adi")) or None,
        "il": tr_baslik(_temiz(r.get("ih_sehir"))) or None,
        "ihale_tarihi": tarih_iso(_temiz(r.get("ih_tarihi"))),
        "ilan_tarihi": _temiz(r.get("ih_ilan_tarihi_1")) or None,
        "ihale_tipi": tur or None,
        "benzer_is": benzer or None,
        "site_id": str(r.get("ih_id") or "") or None,
        "teminat": _temiz(r.get("ih_teminat")) or None,
        "sure": _temiz(r.get("ih_suresi")) or None,
        "itiraz_bedeli": _temiz(r.get("ih_itirazbedel")) or None,
        "kazanan": _temiz(r.get("ih_mkazanan")) or None,
        "kaynak_url": f"{TABAN}/ihale-ilanlari/goster/{r.get('ih_id')}",
        "notlar": " · ".join(x for x in (tur, benzer and "Benzer iş: " + benzer) if x) or None,
    }


# --- Tarayıcı oturumu --------------------------------------------------------------------

def _tarayici_ac(pw, profil: Path, gorunur: bool):
    profil.mkdir(parents=True, exist_ok=True)
    indirme = profil.parent / "_indirilen"  # ilerleme yüzdesi için inen dosya burada izlenir
    indirme.mkdir(exist_ok=True)
    for f in indirme.iterdir():
        f.unlink(missing_ok=True) if f.is_file() else None
    son = None
    for kanal in ("msedge", "chrome", None):  # bilgisayardaki tarayıcı; yoksa Playwright'ınki
        try:
            ctx = pw.chromium.launch_persistent_context(
                str(profil), channel=kanal, headless=not gorunur, locale="tr-TR",
                downloads_path=str(indirme),
                viewport=None if gorunur else {"width": 1280, "height": 900},
                args=["--window-size=1150,850"] if gorunur else [])
            ctx.indirme_klasoru = indirme
            return ctx
        except Exception as e:
            son = e
    raise SiteHatasi(f"Edge ya da Chrome açılamadı: {son}")


def _oturum_var(ctx) -> bool:
    try:
        y = ctx.request.get(TABAN + "/ihale-ilanlari", headers=XHR,
                            params={"draw": "1", "start": "0", "length": "1", "search[value]": ""})
        ih_id = (y.json().get("data") or [{}])[0].get("ih_id")
        return bool(ih_id) and not re.search(
            r'name="password"', ctx.request.get(f"{TABAN}/ihale-ilanlari/goster/{ih_id}").text())
    except Exception:
        return False


def _token(ctx) -> str:
    m = re.search(r'name="_token"\s+value="([^"]+)"|_token=([A-Za-z0-9]+)',
                  ctx.request.get(TABAN + "/takip-ettiklerim").text())
    return (m.group(1) or m.group(2)) if m else ""


def _giris(ctx, sistem: Path, site: str) -> None:
    kayit = siteler.oku(sistem)["siteler"].get(site)
    if not kayit:
        raise SiteHatasi("İhale takip siteniz kayıtlı değil. Panelde Ayarlar > İhale takip sitesi "
                         "ekle ile kullanıcı adınızı ve şifrenizi kaydedin.")
    sifre = siteler.sifre_al(site, kayit["kullanici"])
    if not sifre:
        raise SiteHatasi("Şifre bilgisayarın şifre kasasında bulunamadı. Ayarlar'dan siteyi "
                         "yeniden kaydedin.")
    m = re.search(r'name="_token"\s+value="([^"]+)"', ctx.request.get(TABAN + "/").text())
    y = ctx.request.post(TABAN + "/login2", form={"_token": m.group(1) if m else "",
                                                  "username": kayit["kullanici"], "password": sifre})
    sifre = None
    try:
        tamam = y.json().get("status") is True
    except Exception:
        tamam = False
    if not tamam:
        raise SiteHatasi(f"{kayit['ad']} girişi başarısız. Kullanıcı adı ve şifreyi Ayarlar'dan "
                         "kontrol edin.")


def _oturumlu(sistem: Path, site: str, is_, gorunur: bool = False):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SiteHatasi("Takip sitesine bağlanmak için Playwright gerekli: python -m pip install playwright")
    with _kilit, sync_playwright() as pw:
        ctx = _tarayici_ac(pw, siteler.profil_dir(sistem, site), gorunur)
        try:
            if not _oturum_var(ctx):
                _giris(ctx, sistem, site)
            return is_(ctx)
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def _satir_bul(ctx, ikn: str) -> dict:
    y = ctx.request.get(TABAN + "/ihale-ilanlari", headers=XHR, params={
        "draw": "1", "start": "0", "length": "10", "search[value]": "", "ih_kayit_no": ikn})
    try:
        satirlar = y.json().get("data") or []
    except Exception:
        satirlar = []
    for r in satirlar:
        if ikn == _temiz(r.get("ih_kayit_no")):
            return r
    raise SiteHatasi(f"İhale sitesinde {ikn} İKN'li ihale bulunamadı.")


# --- Liste ve bilgi ----------------------------------------------------------------------

# Sitenin arama formundaki alanlar (ilan ve sonuç listesi); panel bunları aynen gönderir
FILTRELER = {"qstr", "ih_ihale_adi", "ih_idare_adi", "ih_kayit_no", "ih_benzeris", "ih_sehir", "ih_turu",
             "ih_kazanan", "ih_ilan_tarihi_s", "ih_ilan_tarihi_e", "ih_tarihi_s", "ih_tarihi_e"}


def _filtre(filtre: dict | None, gun: int) -> dict:
    """Panel filtresini sitenin parametrelerine çevirir; tarih verilmezse son `gun` günün ilanları."""
    q = {}
    for k, v in (filtre or {}).items():
        if k not in FILTRELER or v in (None, ""):
            continue
        v = str(v).strip()
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
        q["ih_sehir[]" if k == "ih_sehir" else k] = f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else v
    if not any(k in q for k in ("ih_ilan_tarihi_s", "ih_ilan_tarihi_e", "ih_tarihi_s", "ih_tarihi_e", "ih_kayit_no")):
        q["ih_ilan_tarihi_s"] = f"{date.today() - timedelta(days=gun):%d.%m.%Y}"
        q["ih_ilan_tarihi_e"] = f"{date.today():%d.%m.%Y}"
    return q


def liste(sistem: Path | None = None, site: str = SITE, gun: int = 7, filtre: dict | None = None,
          adet: int = 300) -> list[dict]:
    """İhale ilanları; `filtre` sitenin arama formundaki alanlardır (FILTRELER)."""
    q0 = _filtre(filtre, gun)

    def cek(ctx):
        sonuc, start = [], 0
        while start < adet:
            d = ctx.request.get(TABAN + "/ihale-ilanlari", headers=XHR, params={
                "draw": str(start // 30 + 1), "start": str(start), "length": "30", "search[value]": "", **q0}).json()
            veri = d.get("data") or []
            sonuc += veri
            start += 30
            if not veri or start >= (d.get("recordsFiltered") or 0):
                break
        return sonuc
    return [sadelestir(r) for r in _oturumlu(sistem or sistem_dir(), site, cek)[:adet]]


SONUC_KOLONLARI = ["first", "ih_ilan_tarihi_4", "ih_kayit_no", "ih_tarihi", "ih_idare_adi", "ih_ihale_adi",
                   "ih_sehir", "ih_kazanan", "ih_sozlesme_bedeli", "tenzilat"]


def sonuclar(sistem: Path | None = None, site: str = SITE, gun: int = 7, filtre: dict | None = None,
             adet: int = 300) -> list[dict]:
    """Kesinleşen ihale sonuçları (kazanan, sözleşme bedeli, tenzilat); `filtre` için bkz. FILTRELER."""
    q0 = _filtre(filtre, gun)

    def cek(ctx):
        sonuc, start = [], 0
        while start < adet:
            q = {"draw": str(start // 30 + 1), "start": str(start), "length": "30", "search[value]": "", **q0}
            for i, k in enumerate(SONUC_KOLONLARI):
                q.update({f"columns[{i}][data]": k, f"columns[{i}][name]": k})
            d = ctx.request.get(TABAN + "/kesinlesen-sonuclar", params=q, headers=XHR).json()
            veri = d.get("data") or []
            sonuc += veri
            start += 30
            if not veri or start >= (d.get("recordsFiltered") or 0):
                break
        return sonuc

    def sade(r):
        x = sadelestir(r)
        x.update({"kazanan": _temiz(r.get("ih_kazanan")) or None,
                  "sozlesme_bedeli": _temiz(r.get("ih_sozlesme_bedeli")) or None,
                  "yaklasik": float(r["ih_yaklasik"]) if str(r.get("ih_yaklasik") or "").replace(".", "", 1).isdigit() else None,
                  "tenzilat": _temiz(r.get("tenzilat")) or None,
                  "sonuc_tarihi": _temiz(r.get("ih_ilan_tarihi_4")) or None})
        return x
    return [sade(r) for r in _oturumlu(sistem or sistem_dir(), site, cek)[:adet]]


def bilgi(ikn: str, sistem: Path | None = None, site: str = SITE) -> dict:
    ikn = ikn_norm(ikn)
    return {**sadelestir(_oturumlu(sistem or sistem_dir(), site, lambda c: _satir_bul(c, ikn))), "ikn": ikn}


# --- Takip listesi -----------------------------------------------------------------------

def takip_listesi(sistem: Path | None = None, site: str = SITE) -> list[dict]:
    """Sitedeki "Takip Ettiklerim" listesi."""
    def cek(ctx):
        sonuc, start = [], 0
        while True:
            q = {"draw": "1", "start": str(start), "length": "100", "search[value]": "",
                 "search[regex]": "false", "order[0][column]": "3", "order[0][dir]": "asc"}
            for i, k in enumerate(TAKIP_KOLONLARI):
                q.update({f"columns[{i}][data]": k, f"columns[{i}][name]": k,
                          f"columns[{i}][searchable]": "true", f"columns[{i}][orderable]": "true",
                          f"columns[{i}][search][value]": "", f"columns[{i}][search][regex]": "false"})
            y = ctx.request.get(TABAN + "/takip-ettiklerim", params=q, headers=XHR)
            try:
                d = y.json()
            except Exception:
                raise SiteHatasi("Sitedeki takip listesi okunamadı.")
            veri = d.get("data") or []
            sonuc += veri
            start += 100
            if not veri or start >= (d.get("recordsFiltered") or d.get("recordsTotal") or 0):
                return sonuc
    return [sadelestir(r) for r in _oturumlu(sistem or sistem_dir(), site, cek)]


def _takip_istegi(uc: str, ikn: str, sistem: Path | None, site: str) -> dict:
    ikn = ikn_norm(ikn)

    def is_(ctx):
        r = _satir_bul(ctx, ikn)
        y = ctx.request.post(TABAN + uc, headers=XHR, form={
            "_token": _token(ctx), "ih_id": str(r["ih_id"]), "ih_kayit_no": " " + ikn})
        if not y.ok:
            raise SiteHatasi(f"Sitede takip listesi güncellenemedi (HTTP {y.status}).")
        return {"ikn": ikn, "site_id": str(r["ih_id"])}
    return _oturumlu(sistem or sistem_dir(), site, is_)


def takip_et(ikn: str, sistem: Path | None = None, site: str = SITE) -> dict:
    return _takip_istegi("/takip-et", ikn, sistem, site)


def takip_birak(ikn: str, sistem: Path | None = None, site: str = SITE) -> dict:
    return _takip_istegi("/takip-birak", ikn, sistem, site)


# --- İhale dosyası (EKAP Dökümanı) -----------------------------------------------------------

def _ekap_baglantisi(ctx, ih_id) -> str:
    metin = ctx.request.get(f"{TABAN}/ihale-ilanlari/goster/{ih_id}").text()
    for href, ic in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', metin, re.S | re.I):
        if re.search(r"ekap\s*d[öo]k[üu]man", _temiz(ic), re.I):
            return urljoin(TABAN, html.unescape(href))
    raise SiteHatasi("İlan penceresinde 'EKAP Dökümanı' bağlantısı yok; doküman henüz "
                     "yayımlanmamış olabilir.")


DUGME = "button,[role=button],a,input[type=submit],input[type=button]"


def _tikla(sayfa, metin: str, sure: float = 8) -> bool:
    son = time.time() + sure
    while time.time() < son:
        try:
            k = sayfa.evaluate("""([secici, metin]) => {
                const b = [...document.querySelectorAll(secici)].find(e => {
                    const t = (e.innerText || e.value || e.title || '').trim();
                    const r = e.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && t.includes(metin);
                });
                if (!b) return null;
                b.scrollIntoView({block: 'center'});
                const r = b.getBoundingClientRect();
                return {x: r.x + r.width / 2, y: r.y + r.height / 2};
            }""", [DUGME, metin])
        except Exception:
            k = None
        if k:
            sayfa.mouse.click(k["x"], k["y"])
            return True
        sayfa.wait_for_timeout(400)
    return False


def _kod_resmi(sayfa) -> bytes | None:
    sayfa.wait_for_timeout(800)
    try:
        img = sayfa.locator("img[src^='data:image'], img[src*='aptcha' i], img[id*='aptcha' i], "
                            "img[src*='ResimOlustur' i], img[src*='guvenlik' i]").first
        if img.count() and img.is_visible():
            return img.screenshot()
    except Exception:
        pass
    return None


def _kod_ve_indir(ctx, sayfa, hedef: Path, kod_iste, bildir) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        resim = _kod_resmi(sayfa)
        if resim is None:
            break
        bildir("Güvenlik kodu bekleniyor")
        kod = (kod_iste(resim) or "").strip()
        if not kod:
            raise SiteHatasi("Güvenlik kodu girilmedi.")
        kutu = sayfa.locator("input[type=text]:visible, input:not([type]):visible").first
        kutu.fill(kod)
        if not (_tikla(sayfa, "Doğrula", 2) or _tikla(sayfa, "Onayla", 1) or _tikla(sayfa, "Gönder", 1)):
            kutu.press("Enter")
        sayfa.wait_for_timeout(2500)
        if sayfa.is_closed():  # EKAP onaydan sonra sekmeyi yenileyebilir
            sayfa = ctx.pages[-1]
    else:
        raise SiteHatasi("Güvenlik kodu üç kez kabul edilmedi.")
    bildir("İhale ilanı açılıyor")
    inenler = []
    def yakala(d):  # Playwright yerleşik işlevi dinleyici olarak kabul etmiyor
        inenler.append(d)
    boyutlar = []  # indirilen dosyanın toplam boyutu (sunucu bildiriyorsa), ilerleme yüzdesi için

    def yanit(y):
        try:
            b = y.headers
            if "attachment" in (b.get("content-disposition") or "").lower() and b.get("content-length"):
                boyutlar.append(int(b["content-length"]))
        except Exception:
            pass
    ctx.on("response", yanit)
    sayfa.on("download", yakala)
    ctx.on("page", lambda p: p.on("download", yakala))
    sayfa.wait_for_timeout(1000)
    # EKAP: İlan Bilgileri > "İhale İlanı" (varsa "Düzeltme İlanı") altındaki en son tarihli ilan > en altta
    # "İhale Dokümanını İndir"
    try:
        sayfa.locator("a[href='#tabIlanBilgi']").first.click()
    except Exception:
        pass
    sayfa.wait_for_timeout(800)
    ilanlar = sayfa.locator("#pnlIhaleIlan a[id*='lnkbutton'], #pnlDuzeltmeIlan a[id*='lnkbutton']")
    if ilanlar.count():
        tarihler = [ilanlar.nth(i).inner_text().strip() for i in range(ilanlar.count())]
        sira = max(range(len(tarihler)), key=lambda i: tarih_iso(tarihler[i]) or "")
        ilanlar.nth(sira).click()
    bildir("İndiriliyor")
    son = time.time() + 40
    tiklandi = False
    while time.time() < son and not tiklandi:
        sayfa.wait_for_timeout(1000)
        for cerceve in sayfa.frames:  # ilan önizlemesi pencere içinde (iframe) açılabilir
            for metin in ("İhale Dokümanını İndir", "Dokümanı İndir", "Doküman İndir"):
                try:
                    dugme = cerceve.get_by_text(metin, exact=False).last
                    if dugme.count() and dugme.is_visible():
                        dugme.scroll_into_view_if_needed()
                        dugme.click()
                        tiklandi = True
                        break
                except Exception:
                    pass
            if tiklandi:
                break
    if tiklandi:
        son = time.time() + 180
        while time.time() < son and not inenler:
            # bazı ihalelerde indirmeden önce ikinci bir güvenlik kodu istenir
            for sf in ctx.pages:
                resim = _kod_resmi(sf)
                if resim:
                    kod = (kod_iste(resim) or "").strip()
                    if not kod:
                        raise SiteHatasi("Güvenlik kodu girilmedi.")
                    k = sf.locator("input[type=text]:visible, input:not([type]):visible").first
                    k.fill(kod)
                    if not _tikla(sf, "Doğrula", 2):
                        k.press("Enter")
            sayfa.wait_for_timeout(1500)
        if inenler:
            _ilerleme_bekle(sayfa, ctx, boyutlar, bildir)
            d = inenler[0]
            yol = hedef / (d.suggested_filename or "ihale-dokumani.zip")
            d.save_as(yol)
            bildir(f"İndi: {yol.name}")
            return [yol]
    # Sayfa yapısı değişmiş: incelemek için sayfanın kaydı bırakılır (şifre/kod içermez)
    try:
        (hedef / "_indirme-tanilama.html").write_text(
            "\n<!-- çerçeve -->\n".join(c.content() for c in sayfa.frames), encoding="utf-8")
        kayit = sayfa.evaluate("""() => [...document.querySelectorAll('a,button,input,[onclick]')]
            .filter(e => e.offsetParent !== null)
            .map(e => [e.tagName, e.id, (e.innerText || e.value || e.title || e.alt || '').trim().slice(0, 60),
                       (e.getAttribute('href') || e.getAttribute('onclick') || '').slice(0, 120)])""")
        (hedef / "_indirme-tanilama.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        sayfa.screenshot(path=str(hedef / "_indirme-tanilama.png"), full_page=True)
    except Exception:
        pass
    raise SiteHatasi("EKAP sayfasında indirme düğmesi bulunamadı. Sayfanın kaydını aldım; "
                     "asistana 'indirme tanılama' diyerek inceletebilirsiniz.")


def _ilerleme_bekle(sayfa, ctx, boyutlar: list, bildir, sure: float = 1800) -> None:
    """İnen dosyanın büyüklüğünü izleyip 'İndiriliyor %45' bildirir; bitince döner."""
    klasor = getattr(ctx, "indirme_klasoru", None)
    son, onceki, durgun = time.time() + sure, -1, 0
    while time.time() < son:
        boyut = 0
        try:
            if klasor and klasor.is_dir():
                boyut = max((f.stat().st_size for f in klasor.iterdir() if f.is_file()), default=0)
        except OSError:
            pass
        toplam = boyutlar[-1] if boyutlar else 0
        if toplam:
            bildir(f"İndiriliyor %{min(99, int(100 * boyut / toplam))}")
            if boyut >= toplam:
                return
        else:
            bildir(f"İndiriliyor {boyut / 1048576:.1f} MB")
        durgun = durgun + 1 if boyut == onceki and boyut > 0 else 0
        if durgun >= 4:  # boyut bildirilmiyorsa: dosya bir süredir büyümüyor, bitmiştir
            return
        onceki = boyut
        sayfa.wait_for_timeout(1000)


def _ih_id_bul(ctx, ikn: str, kaynak_url: str | None = None):
    """İhalenin sitedeki numarası: ilan bağlantısından; yoksa ilanlarda, takip listesinde ve
    sonuçlarda aranır (tarihi geçmiş ihaleler ilan aramasında çıkmaz)."""
    m = re.search(r"/goster/(\d+)", kaynak_url or "")
    if m:
        return m.group(1)
    try:
        return _satir_bul(ctx, ikn)["ih_id"]
    except SiteHatasi:
        pass
    q = {"draw": "1", "start": "0", "length": "10", "search[value]": "", "ih_kayit_no": ikn}
    for i, k in enumerate(SONUC_KOLONLARI):
        q.update({f"columns[{i}][data]": k, f"columns[{i}][name]": k})
    for uc in ("/kesinlesen-sonuclar", "/ihale-sonuclari"):
        try:
            for r in ctx.request.get(TABAN + uc, params=q, headers=XHR).json().get("data") or []:
                if _temiz(r.get("ih_kayit_no")) == ikn:
                    return r["ih_id"]
        except Exception:
            pass
    raise SiteHatasi(f"İhale sitesinde {ikn} İKN'li ihale bulunamadı.")


def indir(ikn: str, hedef: Path, kod_iste, sistem: Path | None = None, site: str = SITE,
          bildir=print, kaynak_url: str | None = None) -> list[Path]:
    """İhale dosyasını indirir. Tarayıcı penceresi açılmaz; EKAP'ın güvenlik kodu resmi
    `kod_iste(png_bayt)` ile kullanıcıya (panelde) sorulur, kodu kullanıcı yazar."""
    ikn = ikn_norm(ikn)

    def is_(ctx):
        bildir("İhale sitesine bağlanılıyor")
        if "DT" in ikn:
            raise SiteHatasi("Bu bir doğrudan temin ilanı; sitede EKAP ihale dokümanı bağlantısı yok. "
                             "Şartname varsa ilan metnindedir.")
        url = _ekap_baglantisi(ctx, _ih_id_bul(ctx, ikn, kaynak_url))
        bildir("EKAP doküman sayfası açılıyor")
        sayfa = ctx.new_page()
        sayfa.goto(url, wait_until="domcontentloaded", timeout=60_000)
        return _kod_ve_indir(ctx, sayfa, hedef, kod_iste, bildir)
    return _oturumlu(sistem or sistem_dir(), site, is_, gorunur=False)


def _kod_terminalden(resim: bytes) -> str:
    yol = sistem_dir() / "ekap-guvenlik-kodu.png"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(resim)
    print(f"Güvenlik kodu resmi: {yol}", flush=True)
    try:
        import os
        os.startfile(yol)
    except Exception:
        pass
    return input("Resimdeki güvenlik kodunu yazıp Enter'a basın: ")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", default=SITE)
    sub = p.add_subparsers(dest="komut", required=True)
    s = sub.add_parser("liste")
    s.add_argument("--gun", type=int, default=7)
    s.add_argument("--tur", default="")
    s.add_argument("--kelime", default="")
    sub.add_parser("takip-listesi")
    s = sub.add_parser("sonuclar")
    s.add_argument("--gun", type=int, default=7)
    s.add_argument("--tur", default="")
    s.add_argument("--kelime", default="")
    for ad in ("bilgi", "takip-et", "takip-birak"):
        sub.add_parser(ad).add_argument("ikn")
    s = sub.add_parser("indir")
    s.add_argument("ikn")
    s.add_argument("--hedef", type=Path, required=True)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        sonuc = {
            "liste": lambda: liste(site=a.site, gun=a.gun, filtre={"ih_turu": a.tur, "qstr": a.kelime}),
            "takip-listesi": lambda: takip_listesi(site=a.site),
            "sonuclar": lambda: sonuclar(site=a.site, gun=a.gun, filtre={"ih_turu": a.tur, "qstr": a.kelime}),
            "bilgi": lambda: bilgi(a.ikn, site=a.site),
            "takip-et": lambda: takip_et(a.ikn, site=a.site),
            "takip-birak": lambda: takip_birak(a.ikn, site=a.site),
            "indir": lambda: [str(f) for f in indir(a.ikn, a.hedef, _kod_terminalden, site=a.site)],
        }[a.komut]()
    except SiteHatasi as e:
        sys.exit(str(e))
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
