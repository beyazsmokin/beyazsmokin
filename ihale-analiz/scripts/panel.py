#!/usr/bin/env python3
"""İhale Analiz paneli: bilgisayarda çalışan, PWA olarak kurulabilen web paneli.

Kullanım:
  panel.py                         # paneli başlatır ve tarayıcıda açar (zaten açıksa yalnızca açar)
  panel.py --arka-plan             # tarayıcı açmadan çalışır (otomatik başlatma bunu kullanır)
  panel.py baslangic --ac|--kapat  # bilgisayar açılınca panel kendiliğinden başlasın / başlamasın
  panel.py durdur

Panel yalnızca bu bilgisayarda (127.0.0.1) çalışır, internete açılmaz, dış sunucu kullanmaz.
Adres sabittir (varsayılan http://127.0.0.1:8765, `config.yaml` > panel.port) ki tarayıcı
paneli uygulama olarak kurabilsin (Chrome/Edge adres çubuğunda "Uygulamayı yükle").

Panelden:
  - ihale eklenir, dosyası yüklenir, "Analizi başlat" ile kuyruğa alınır (`takip.py kuyruk`);
    `config.yaml` > panel.analiz_komutu tanımlıysa analiz o komutla hemen başlatılır,
  - ihale günleri, yer görme, açıklama talebi gibi tarihler ajandada izlenir (.ics dışa aktarım),
  - analiz süreci adım adım canlı izlenir (`calisma/durum.json`),
  - HTML rapor panelde açılır, PDF ve Excel indirilir,
  - ihale sonucu girilir; sonuç öğrenen veritabanına yazılır.
"""
import argparse
import json
import mimetypes
import re
import shlex
import subprocess
import sys
import threading
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import urlopen

import takip
import vt

SCRIPTS = Path(__file__).resolve().parent
STATIK = SCRIPTS.parent / "panel"
VARSAYILAN_PORT = 8765
AZAMI_YUKLEME = 1024 ** 3  # 1 GB
UYGULAMA = "ihale-analiz-panel"
STATIK_DOSYALAR = {"index.html", "app.js", "stil.css", "sw.js", "manifest.webmanifest",
                   "ikon-192.png", "ikon-512.png", "ikon-maskable.png", "apple-touch-icon.png"}


def ayar(alan: Path, anahtar: str, varsayilan=None):
    """config.yaml > panel: altındaki basit `anahtar: değer` satırını okur (PyYAML gerekmez)."""
    cfg = alan / ".sistem" / "config.yaml"
    if not cfg.exists():
        return varsayilan
    m = re.search(r"^panel:[^\n]*\n((?:[ \t]+.*\n?)*)", cfg.read_text(encoding="utf-8"), re.M)
    if not m:
        return varsayilan
    d = re.search(rf"^[ \t]+{anahtar}:[ \t]*(.*?)[ \t]*(#.*)?$", m.group(1), re.M)
    if not d or d.group(1) in ("", '""', "''", "null"):
        return varsayilan
    v = d.group(1).strip()
    if v[:1] in "\"'" and v[-1:] == v[:1]:
        v = v[1:-1]
    return v


def port_al(alan: Path, arg: int | None) -> int:
    return arg or int(ayar(alan, "port", VARSAYILAN_PORT))


# --- API --------------------------------------------------------------------------

class Hata(Exception):
    def __init__(self, kod: int, mesaj: str):
        super().__init__(mesaj)
        self.kod = kod


def ozet(con, alan: Path) -> dict:
    ihaleler = takip.liste(con)
    sayac = {k: 0 for k in takip.DURUMLAR}
    for t in ihaleler:
        sayac[t["durum"]] = sayac.get(t["durum"], 0) + 1
    bugun = date.today()
    # otomatik hatırlatmaların yalnızca bugün ve yarına düşenleri gösterilir, liste kalabalıklaşmasın
    yaklasan = [o for o in takip.ajanda(con, alan, bugun, bugun + timedelta(days=14)) if not o["tamam"]
                and (o["tur"] != "hatirlatma" or o["kaynak"] != "otomatik"
                     or date.fromisoformat(o["tarih"]) <= bugun + timedelta(days=1))]
    acik = [t for t in ihaleler if t["durum"] not in takip.KAPALI]
    analizde = []
    for t in ihaleler:
        if t["durum"] in ("hesaplanacak", "analizde"):
            s = takip.surec(takip.ihale_klasoru(alan, t["kod"]))
            analizde.append({"kod": t["kod"], "ad": t["ad"], "durum": t["durum"], "yuzde": s["yuzde"],
                             "aktif": next((a["ad"] for a in s["adimlar"] if a["durum"] == "calisiyor"), None)})
    raporlar = []
    for t in ihaleler:
        k = takip.ihale_klasoru(alan, t["kod"])
        h = next(iter(sorted(k.glob("* Rapor.html"))), None) if k.is_dir() else None
        if h:
            raporlar.append({"kod": t["kod"], "ad": t["ad"], "dosya": h.name, "zaman": h.stat().st_mtime})
    raporlar.sort(key=lambda r: -r["zaman"])
    return {
        "sayac": sayac,
        "acik_sayi": len(acik),
        "acik_butce": sum(t["yaklasik"] or 0 for t in acik),
        "yaklasan": yaklasan[:12],
        "analizde": analizde,
        "raporlar": raporlar[:6],
        "basari": basari(con),
        "kuyruk_komutu": ayar(alan, "analiz_komutu"),
        "alan": str(alan),
    }


def basari(con) -> dict:
    r = con.execute("""SELECT SUM(sonuc='kazanildi') k, SUM(sonuc='kaybedildi') y, COUNT(*) n
                       FROM ihaleler""").fetchone()
    k, y = r["k"] or 0, r["y"] or 0
    return {"kazanilan": k, "kaybedilen": y, "analiz": r["n"] or 0,
            "oran": round(100 * k / (k + y)) if k + y else None}


def ogrenme(con) -> dict:
    tz = vt.tenzilat_satirlari(con)
    kaz = [vt.yuzde(r["kazanan"], r["ym"]) for r in tz if r["kazanan"] is not None]
    rakipler = [dict(r) for r in con.execute(
        """SELECT firma, COUNT(DISTINCT ihale_kod) n, SUM(durum='kazanan') k,
                  AVG(CASE WHEN yaklasik_maliyet > 0 THEN (1 - teklif / yaklasik_maliyet) * 100 END) tz
           FROM katilimcilar WHERE teklif IS NOT NULL GROUP BY firma ORDER BY n DESC, k DESC LIMIT 10""")]
    idareler = [dict(r) for r in con.execute(
        """SELECT idare, COUNT(*) n, SUM(sonuc='kazanildi') k FROM ihaleler WHERE idare IS NOT NULL
           GROUP BY idare ORDER BY n DESC LIMIT 8""")]
    aylik = [dict(r) for r in con.execute(
        """SELECT substr(tarih,1,7) ay, COUNT(*) n, SUM(sonuc='kazanildi') k FROM ihaleler
           WHERE tarih IS NOT NULL GROUP BY ay ORDER BY ay DESC LIMIT 12""")][::-1]
    dersler = [dict(r) for r in con.execute(
        "SELECT tarih, metin, ajan, idare, kullanim FROM dersler ORDER BY id DESC LIMIT 15")]
    kurallar = [dict(r) for r in con.execute(
        "SELECT id, ad, kapsam, islem, deger, kaynak_cumle FROM hesap_kurallari WHERE aktif=1 ORDER BY id")]
    agirlik = vt.tercih_agirliklari(con)
    etiket = dict(vt.TERCIH_ALANLARI)
    tercihler = [{"alan": etiket[a], "deger": d, "begen": b, "ret": r, "agirlik": round(w, 2)}
                 for (a, d), (b, r, w) in sorted(agirlik.items(), key=lambda x: -abs(x[1][2]))[:10]]
    sayi = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("ihaleler", "metraj", "dersler", "katilimcilar", "kurum_fiyatlari", "tercihler")}
    return {"basari": basari(con), "tenzilat": {"ihale": len(tz), "ort_kazanan": round(sum(kaz) / len(kaz), 2)
                                                if kaz else None},
            "rakipler": rakipler, "idareler": idareler, "aylik": aylik, "dersler": dersler,
            "kurallar": kurallar, "tercihler": tercihler, "sayi": sayi}


def taramalar(alan: Path) -> list[dict]:
    d = alan / "Taramalar"
    return [{"ad": f.stem, "zaman": f.stat().st_mtime}
            for f in sorted(d.glob("*.md"), key=lambda f: -f.stat().st_mtime)] if d.is_dir() else []


def tarama(alan: Path, ad: str) -> dict:
    f = guvenli_yol(alan / "Taramalar", ad + ".md")
    if not f.is_file():
        raise Hata(404, "Tarama bulunamadı")
    metin = f.read_text(encoding="utf-8")
    satirlar = [l.strip() for l in metin.splitlines() if l.strip().startswith("|")]
    tablo = [[c.strip() for c in l.strip("|").split("|")] for l in satirlar
             if not re.fullmatch(r"[|\s:-]+", l)]
    if not tablo:
        return {"ad": ad, "metin": metin, "satirlar": []}
    bas = [h.replace("İ", "i").replace("I", "ı").lower() for h in tablo[0]]
    eslesme = {"ikn": "ikn", "idare": "idare", "il": "il", "konu": "konu", "tür": "tur",
               "skor": "skor", "yaklaşık maliyet": "yaklasik", "son tarih": "son_tarih", "neden": "neden"}
    anahtarlar = [eslesme.get(h, h) for h in bas]
    return {"ad": ad, "satirlar": [dict(zip(anahtarlar, r)) for r in tablo[1:]]}


def guvenli_yol(kok: Path, goreli: str) -> Path:
    yol = (kok / goreli).resolve()
    if kok.resolve() not in (yol, *yol.parents):
        raise Hata(403, "Geçersiz yol")
    return yol


def analiz_baslat(con, alan: Path, kod: str) -> dict:
    t = con.execute("SELECT * FROM takip WHERE kod=?", (kod,)).fetchone()
    if not t:
        raise Hata(404, "İhale bulunamadı")
    con.execute("UPDATE takip SET durum='hesaplanacak', guncelleme=? WHERE kod=?", (takip.simdi(), kod))
    komut = ayar(alan, "analiz_komutu")
    if not komut:
        return {"komut": False, "mesaj": "İhale kuyruğa alındı. Yapay zeka asistanınıza "
                                         "\"kuyruktaki ihaleleri analiz et\" yazın; süreç burada canlı görünür."}
    klasor = takip.ihale_klasoru(alan, kod)
    argv = [p.replace("{kod}", kod).replace("{klasor}", str(klasor)).replace("{alan}", str(alan))
            for p in shlex.split(komut)]
    log = klasor / "calisma" / "analiz-komutu.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log, "ab") as f:
            subprocess.Popen(argv, cwd=alan, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
    except OSError as e:
        return {"komut": False, "mesaj": f"Analiz komutu çalıştırılamadı ({e}). İhale kuyrukta bekliyor."}
    return {"komut": True, "mesaj": "Analiz başlatıldı; adımlar aşağıda canlı görünecek."}


def rapor_uret(alan: Path, kod: str) -> dict:
    import html_rapor
    try:
        s = html_rapor.olustur(takip.ihale_klasoru(alan, kod))
    except FileNotFoundError:
        raise Hata(404, "Bu ihalenin Markdown raporu henüz yok. Önce analiz tamamlanmalı.")
    return {"html": s["html"].name, "pdf": s["pdf"].name if s["pdf"] else None,
            "mesaj": "HTML ve PDF rapor oluşturuldu." if s["pdf"] else
            "HTML rapor oluşturuldu. PDF için raporu açıp Yazdır > PDF olarak kaydet'i kullanın."}


def siteler_durum(alan: Path) -> dict:
    import siteler
    veri = siteler.oku(alan / ".sistem")
    return {"durum": veri["durum"], "siteler": [{"anahtar": k, "ad": s["ad"], "kullanici": s["kullanici"],
                                                 "sifre_kasada": s.get("sifre_kasada")}
                                                for k, s in veri["siteler"].items()],
            "eksik": siteler.SITE_GEREKEN}


class Uygulama:
    def __init__(self, alan: Path, port: int):
        self.alan = alan
        self.port = port
        self.kilit = threading.Lock()

    def api(self, yontem: str, yol: list[str], sorgu: dict, govde) -> object:
        alan = self.alan
        with self.kilit:
            con = takip.baglan(alan)
            try:
                with con:
                    return self._yonlendir(con, alan, yontem, yol, sorgu, govde)
            finally:
                con.close()

    def _yonlendir(self, con, alan, yontem, yol, sorgu, govde):
        y = (yontem, *yol)
        if y == ("GET", "saglik"):
            return {"uygulama": UYGULAMA}
        if y == ("GET", "ozet"):
            takip.esitle(con, alan)
            return ozet(con, alan)
        if y == ("GET", "sabitler"):
            return {"durumlar": takip.DURUMLAR, "kapali": sorted(takip.KAPALI),
                    "etkinlik_turleri": takip.ETKINLIK_TURLERI,
                    "adimlar": [{"adim": a, "ad": b, "ajan": c} for a, b, c, _ in takip.ADIMLAR]}
        if y == ("GET", "ihaleler"):
            takip.esitle(con, alan)
            return takip.liste(con)
        if y == ("POST", "ihaleler"):
            try:
                kod = takip.ekle(con, alan, govde or {})
            except ValueError as e:
                raise Hata(400, str(e))
            if (govde or {}).get("analiz"):
                analiz_baslat(con, alan, kod)
            return {"kod": kod}
        if len(yol) >= 2 and yol[0] == "ihaleler":
            return self._ihale(con, alan, yontem, unquote(yol[1]), yol[2:], sorgu, govde)
        if y == ("GET", "ajanda"):
            try:
                bas = date.fromisoformat(sorgu.get("bas", [""])[0])
                son = date.fromisoformat(sorgu.get("son", [""])[0])
            except ValueError:
                bas = date.today().replace(day=1)
                son = bas + timedelta(days=62)
            return takip.ajanda(con, alan, bas, son)
        if y == ("POST", "etkinlikler"):
            try:
                return {"id": takip.etkinlik_ekle(con, govde or {})}
            except ValueError as e:
                raise Hata(400, str(e))
        if len(yol) == 2 and yol[0] == "etkinlikler":
            if yontem == "PUT":
                con.execute("UPDATE etkinlikler SET tamam=? WHERE id=?", (int(bool(govde.get("tamam"))), yol[1]))
                return {"tamam": True}
            if yontem == "DELETE":
                con.execute("DELETE FROM etkinlikler WHERE id=?", (yol[1],))
                return {"silindi": True}
        if y == ("GET", "ogrenme"):
            return ogrenme(con)
        if y == ("GET", "taramalar"):
            return taramalar(alan)
        if len(yol) == 2 and y[:2] == ("GET", "taramalar"):
            return tarama(alan, unquote(yol[1]))
        if y == ("GET", "siteler"):
            return siteler_durum(alan)
        if y == ("POST", "siteler"):
            subprocess.Popen([sys.executable, str(SCRIPTS / "siteler.py"), "--sistem", str(alan / ".sistem"),
                              "panel"], cwd=alan, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"mesaj": "Site giriş paneli yeni bir sekmede açılıyor."}
        if y == ("POST", "klasor"):
            klasor_ac(guvenli_yol(alan, (govde or {}).get("yol", "")))
            return {"acildi": True}
        raise Hata(404, "Bulunamadı")

    def _ihale(self, con, alan, yontem, kod, alt, sorgu, govde):
        t = con.execute("SELECT * FROM takip WHERE kod=?", (kod,)).fetchone()
        if not t:
            raise Hata(404, "İhale bulunamadı")
        klasor = takip.ihale_klasoru(alan, kod)
        if yontem == "GET" and not alt:
            etk = [dict(e) for e in con.execute("SELECT * FROM etkinlikler WHERE kod=? ORDER BY tarih, saat",
                                                (kod,))]
            gecmis = con.execute("SELECT * FROM ihaleler WHERE kod=?", (kod,)).fetchone()
            return {"ihale": dict(t), "etkinlikler": etk, "surec": takip.surec(klasor),
                    "dosyalar": takip.dosyalar(klasor), "analiz": dict(gecmis) if gecmis else None}
        if yontem == "PUT" and not alt:
            try:
                takip.guncelle(con, kod, govde or {})
            except ValueError as e:
                raise Hata(400, str(e))
            return {"guncellendi": True}
        if yontem == "DELETE" and not alt:
            con.execute("DELETE FROM takip WHERE kod=?", (kod,))
            con.execute("DELETE FROM etkinlikler WHERE kod=?", (kod,))
            # klasör silinmez; esitle tekrar eklemesin diye işaret bırakılır
            if klasor.is_dir():
                (klasor / "calisma").mkdir(exist_ok=True)
                (klasor / "calisma" / ".takip-disi").write_text("panelden kaldırıldı\n", encoding="utf-8")
            return {"silindi": True}
        if (yontem, *alt) == ("GET", "surec"):
            return {"surec": takip.surec(klasor), "durum": t["durum"]}
        if (yontem, *alt) == ("POST", "analiz"):
            return analiz_baslat(con, alan, kod)
        if (yontem, *alt) == ("POST", "rapor"):
            return rapor_uret(alan, kod)
        raise Hata(404, "Bulunamadı")

    def yukle(self, kod: str, ad: str, akis, uzunluk: int) -> dict:
        if uzunluk > AZAMI_YUKLEME:
            raise Hata(413, "Dosya 1 GB'tan büyük")
        ad = Path(ad.replace("\\", "/")).name
        if not ad or ad.startswith("."):
            raise Hata(400, "Geçersiz dosya adı")
        klasor = takip.ihale_klasoru(self.alan, kod)
        if not klasor.is_dir():
            raise Hata(404, "İhale klasörü yok")
        hedef = guvenli_yol(klasor / "kaynak", ad)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        if hedef.exists():
            hedef = hedef.with_name(f"{hedef.stem} ({date.today():%Y%m%d}){hedef.suffix}")
        kalan = uzunluk
        with open(hedef, "wb") as f:
            while kalan > 0:
                parca = akis.read(min(1 << 20, kalan))
                if not parca:
                    break
                f.write(parca)
                kalan -= len(parca)
        if kalan:
            hedef.unlink(missing_ok=True)
            raise Hata(400, "Yükleme yarıda kaldı")
        if hedef.suffix.lower() == ".zip":
            import zipfile
            try:
                with zipfile.ZipFile(hedef) as z:
                    cikis = klasor / "kaynak" / hedef.stem
                    try:
                        for uye in z.infolist():
                            guvenli_yol(cikis, uye.filename)  # zip içinden klasör dışına yazmayı engelle
                    except Hata:
                        return {"ad": hedef.name, "uyari": "Zip klasör dışına dosya yazmaya çalışıyor; açılmadı."}
                    z.extractall(cikis)
            except zipfile.BadZipFile:
                return {"ad": hedef.name, "uyari": "Zip dosyası bozuk; açılmadı."}
        return {"ad": hedef.name}


def klasor_ac(yol: Path) -> None:
    if sys.platform == "win32":
        import os
        os.startfile(str(yol))  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(yol)])
    else:
        subprocess.Popen(["xdg-open", str(yol)])


def isleyici(app: Uygulama):
    izinli_host = {f"127.0.0.1:{app.port}", f"localhost:{app.port}"}

    class Isleyici(BaseHTTPRequestHandler):
        server_version = "IhalePanel"

        def log_message(self, *a):
            pass

        def _yaz(self, kod: int, govde: bytes, tur: str, ek: dict | None = None):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(govde)

        def _json(self, veri, kod=200):
            self._yaz(kod, json.dumps(veri, ensure_ascii=False, default=str).encode("utf-8"),
                      "application/json; charset=utf-8", {"Cache-Control": "no-store"})

        def _guvenli(self) -> bool:
            # DNS yeniden bağlama saldırısına karşı: yalnızca bu bilgisayarın adresi
            if self.headers.get("Host") not in izinli_host:
                self._yaz(403, b"Yetkisiz", "text/plain")
                return False
            # Başka bir sitenin sayfası arka planda istek gönderemesin: değiştiren her istek bu
            # başlığı taşır; tarayıcı başka kökenden gelen özel başlıklı isteğe izin vermez.
            if self.command not in ("GET", "HEAD") and self.headers.get("X-Ihale-Panel") != "1":
                self._yaz(403, b"Yetkisiz", "text/plain")
                return False
            return True

        def do_OPTIONS(self):
            self._yaz(403, b"", "text/plain")

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._guvenli():
                return
            u = urlparse(self.path)
            yol = u.path
            if yol.startswith("/api/"):
                return self._api("GET", u)
            if yol == "/takvim.ics":
                return self._takvim()
            if yol.startswith("/dosya/"):
                return self._dosya(unquote(yol[len("/dosya/"):]))
            ad = "index.html" if yol in ("/", "/index.html") else yol.lstrip("/")
            if ad not in STATIK_DOSYALAR or not (STATIK / ad).is_file():
                return self._yaz(404, b"Bulunamadi", "text/plain")
            tur = {"webmanifest": "application/manifest+json", "js": "text/javascript; charset=utf-8",
                   "css": "text/css; charset=utf-8", "html": "text/html; charset=utf-8",
                   "png": "image/png"}[ad.rsplit(".", 1)[1]]
            ek = {"Cache-Control": "no-cache"}
            if ad == "index.html":
                ek["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; "
                                                 "style-src 'self' 'unsafe-inline'; frame-src 'self'; "
                                                 "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if ad == "sw.js":
                ek["Service-Worker-Allowed"] = "/"
            self._yaz(200, (STATIK / ad).read_bytes(), tur, ek)

        def do_POST(self):
            self._degistir("POST")

        def do_PUT(self):
            self._degistir("PUT")

        def do_DELETE(self):
            self._degistir("DELETE")

        def _degistir(self, yontem):
            if not self._guvenli():
                return
            u = urlparse(self.path)
            m = re.fullmatch(r"/api/ihaleler/([^/]+)/dosya", u.path)
            if yontem == "POST" and m:
                try:
                    ad = unquote(self.headers.get("X-Dosya-Adi", ""))
                    uzunluk = int(self.headers.get("Content-Length") or 0)
                    return self._json(app.yukle(unquote(m.group(1)), ad, self.rfile, uzunluk))
                except Hata as e:
                    self.close_connection = True
                    return self._json({"hata": str(e)}, e.kod)
            self._api(yontem, u)

        def _api(self, yontem, u):
            govde = None
            if yontem in ("POST", "PUT"):
                n = int(self.headers.get("Content-Length") or 0)
                if n > 1_000_000:
                    return self._json({"hata": "İstek çok büyük"}, 413)
                try:
                    govde = json.loads(self.rfile.read(n) or b"{}")
                except json.JSONDecodeError:
                    return self._json({"hata": "Geçersiz JSON"}, 400)
            parcalar = [p for p in u.path[len("/api/"):].split("/") if p]
            try:
                self._json(app.api(yontem, parcalar, parse_qs(u.query), govde))
            except Hata as e:
                self._json({"hata": str(e)}, e.kod)
            except Exception as e:  # panel çökmesin, hata kullanıcıya görünsün
                self._json({"hata": f"Beklenmeyen hata: {e}"}, 500)

        def _takvim(self):
            con = takip.baglan(app.alan)
            try:
                bugun = date.today()
                olaylar = takip.ajanda(con, app.alan, bugun - timedelta(days=30), bugun + timedelta(days=365))
            finally:
                con.close()
            self._yaz(200, takip.ics(olaylar).encode("utf-8"), "text/calendar; charset=utf-8",
                      {"Content-Disposition": "attachment; filename=ihale-ajandasi.ics",
                       "Cache-Control": "no-store"})

        def _dosya(self, goreli: str):
            kok = app.alan / "İhaleler"
            try:
                yol = guvenli_yol(kok, goreli)
            except Hata:
                return self._yaz(403, b"Yetkisiz", "text/plain")
            if not yol.is_file() or ".sistem" in yol.parts:
                return self._yaz(404, b"Bulunamadi", "text/plain")
            tur = mimetypes.guess_type(yol.name)[0] or "application/octet-stream"
            ek = {"Cache-Control": "no-cache"}
            if yol.suffix.lower() in (".html", ".htm"):
                tur = "text/html; charset=utf-8"
                # rapor sayfası betik çalıştıramaz, dışarıya istek atamaz
                ek["Content-Security-Policy"] = ("default-src 'none'; style-src 'unsafe-inline'; "
                                                 "img-src data:; frame-ancestors 'self'")
            elif yol.suffix.lower() in (".md", ".txt", ".csv", ".json"):
                tur = "text/plain; charset=utf-8"
            elif tur not in ("application/pdf",) and not tur.startswith("image/"):
                from urllib.parse import quote
                ek["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(yol.name)}"
            self._yaz(200, yol.read_bytes(), tur, ek)

    return Isleyici


# --- Başlatma ------------------------------------------------------------------------

def calisiyor_mu(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/saglik", timeout=1.5) as r:
            return json.load(r).get("uygulama") == UYGULAMA
    except Exception:
        return False


def baslat(alan: Path, port: int, tarayici: bool) -> None:
    adres = f"http://127.0.0.1:{port}/"
    if calisiyor_mu(port):
        print(f"Panel zaten açık: {adres}")
        if tarayici:
            webbrowser.open(adres)
        return
    if not (alan / ".sistem").is_dir():
        sys.exit(f"Çalışma alanı bulunamadı: {alan}. Önce init_workspace.py çalıştırın.")
    try:
        sunucu = ThreadingHTTPServer(("127.0.0.1", port), isleyici(Uygulama(alan, port)))
    except OSError:
        sys.exit(f"{port} numaralı kapı başka bir program tarafından kullanılıyor. "
                 f"config.yaml > panel.port değerini değiştirin.")
    sunucu.daemon_threads = True
    print(f"İhale Analiz paneli: {adres}")
    print("Tarayıcının adres çubuğundaki 'Uygulamayı yükle' ile paneli uygulama olarak kurabilirsiniz.")
    print("Kapatmak için Ctrl+C.", flush=True)
    if tarayici:
        threading.Timer(0.6, webbrowser.open, (adres,)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sunucu.server_close()


def durdur(port: int) -> None:
    """Paneli kapatır: sunucu kendi kendini kapatma ucu sunmaz; süreci işletim sistemiyle bulur."""
    if not calisiyor_mu(port):
        print("Panel çalışmıyor")
        return
    if sys.platform == "win32":
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
        pid = next((l.split()[-1] for l in out.splitlines() if f"127.0.0.1:{port} " in l and "LISTEN" in l), None)
        if pid:
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    else:
        subprocess.run(["sh", "-c", f"kill $(lsof -t -iTCP:{port} -sTCP:LISTEN) 2>/dev/null || "
                                    f"fuser -k {port}/tcp 2>/dev/null"], capture_output=True)
    print("Panel kapatıldı" if not calisiyor_mu(port) else "Panel kapatılamadı; süreci elle sonlandırın.")


def pythonw() -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        w = exe.with_name("pythonw.exe")
        if w.exists():
            return str(w)
    return str(exe)


def baslangic(alan: Path, ac: bool) -> None:
    """Oturum açılınca paneli arka planda başlatan kaydı ekler ya da kaldırır."""
    betik = Path(__file__).resolve()
    if sys.platform == "win32":
        import os
        hedef = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/İhale Paneli.vbs"
        icerik = (f'CreateObject("WScript.Shell").Run """{pythonw()}"" ""{betik}"" --alan ""{alan}"" '
                  f'--arka-plan", 0, False\r\n')
        kodlama = "utf-16"
    elif sys.platform == "darwin":
        hedef = Path.home() / "Library/LaunchAgents/com.ihale-analiz.panel.plist"
        icerik = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.ihale-analiz.panel</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{betik}</string>
<string>--alan</string><string>{alan}</string><string>--arka-plan</string></array>
<key>RunAtLoad</key><true/></dict></plist>
"""
        kodlama = "utf-8"
    else:
        hedef = Path.home() / ".config/autostart/ihale-paneli.desktop"
        icerik = (f"[Desktop Entry]\nType=Application\nName=İhale Analiz Paneli\n"
                  f"Exec={shlex.quote(sys.executable)} {shlex.quote(str(betik))} --alan {shlex.quote(str(alan))} "
                  f"--arka-plan\nX-GNOME-Autostart-enabled=true\n")
        kodlama = "utf-8"
    if ac:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(icerik, encoding=kodlama)
        print(f"Panel bilgisayar açılınca kendiliğinden başlayacak ({hedef})")
    else:
        hedef.unlink(missing_ok=True)
        print("Otomatik başlatma kapatıldı")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alan", type=Path, help="çalışma alanı (varsayılan: Masaüstü/İhale Analiz)")
    p.add_argument("--port", type=int)
    p.add_argument("--arka-plan", action="store_true", help="tarayıcı açma")
    sub = p.add_subparsers(dest="komut")
    s = sub.add_parser("baslangic")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--ac", action="store_true")
    g.add_argument("--kapat", action="store_true")
    sub.add_parser("durdur")
    a = p.parse_args()
    alan = (a.alan or takip.alan_dir()).expanduser().resolve()
    port = port_al(alan, a.port)
    if a.komut == "baslangic":
        baslangic(alan, a.ac)
    elif a.komut == "durdur":
        durdur(port)
    else:
        baslat(alan, port, not a.arka_plan)


if __name__ == "__main__":
    main()
