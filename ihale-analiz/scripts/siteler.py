#!/usr/bin/env python3
"""İhale sitesi hesapları: giriş paneli, güvenli şifre saklama, oturum ve sayfa çekme.

Kurulum sırasında tarayıcıda yerel bir giriş paneli açılır. Kullanıcı ihaleleri
takip ettiği siteler (EKAP, ihalebul.com ya da başka bir site) için kullanıcı adı
ve şifresini girer ya da bu adımı atlar.

Şifre ASLA düz metin olarak yazılmaz (K-10.1): işletim sisteminin şifre kasasına
(Windows Kimlik Bilgileri Yöneticisi, macOS Anahtar Zinciri, Linux Secret Service)
`keyring` kütüphanesiyle konur. `.sistem/siteler.json` yalnızca site adı, adres,
kullanıcı adı ve durumu tutar.

Kullanım:
  siteler.py panel                      # giriş panelini tarayıcıda açar, kullanıcı bitirene kadar bekler
  siteler.py durum                      # hangi siteler bağlı, rapordaki hangi bölümler eksik kalır
  siteler.py liste
  siteler.py sil --site ekap            # site kaydını ve kasadaki şifresini siler
  siteler.py oturum-ac --site ekap      # görünür tarayıcıda siteyi açar, giriş alanlarını doldurur;
                                        # CAPTCHA / e-Devlet / SMS adımını kullanıcı yapar (K-5.10)
  siteler.py cek --site ekap --url URL --cikti sayfa.html
                                        # açılmış oturumla bir sayfayı kaydeder (ajan sonra okur)

`oturum-ac` ve `cek` için: pip install playwright && python -m playwright install chromium
"""
import argparse
import html
import json
import re
import secrets
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

KASA_SERVIS = "ihale-analiz"
PANEL_SURE_DK = 20

HAZIR_SITELER = {
    "ekap": ("EKAP (Kamu İhale Kurumu)", "https://ekap.kik.gov.tr/EKAP/"),
    "ihalebul": ("ihalebul.com", "https://www.ihalebul.com/"),
}

# Site girişi olmadan raporda sunulamayan bölümler
SITE_GEREKEN = [
    "Hızlı ihale analizi (sitedeki ilan ve doküman bilgileriyle)",
    "Geçmiş ihalelerden kurum birim fiyatı tespiti",
    "Rakip analizi",
    "Katılımcı analizi",
    "Tenzilat analizi",
]
ATLA_METNI = (
    "Site girişi yapılmazsa raporda şu bölümler yer almaz: "
    + "; ".join(SITE_GEREKEN) + ". "
    "Yaklaşık maliyet analizinde kurumların birim fiyatları tespit edilemez, "
    "analiz yalnızca rayiç (piyasa) fiyatları üzerinden yapılır."
)


# --- Kayıt dosyası (şifre içermez) ---------------------------------------

def sistem_dir() -> Path:
    # scripts/ -> skill/ -> .sistem/
    sistem = Path(__file__).resolve().parents[2]
    return sistem if sistem.name == ".sistem" else Path.cwd() / ".sistem"


def kayit_yolu(sistem: Path) -> Path:
    return sistem / "siteler.json"


def oku(sistem: Path) -> dict:
    p = kayit_yolu(sistem)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"durum": "sorulmadi", "siteler": {}}


def yaz(sistem: Path, veri: dict) -> None:
    p = kayit_yolu(sistem)
    p.parent.mkdir(parents=True, exist_ok=True)
    for s in veri["siteler"].values():
        assert "sifre" not in s  # K-10.1: şifre bu dosyaya asla girmez
    p.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")


# --- İşletim sistemi şifre kasası ------------------------------------------

def kasa():
    """Kullanılabilir keyring modülü ya da None (kütüphane yok / kasa yok)."""
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return None
    kr = keyring.get_keyring()
    if isinstance(kr, fail.Keyring) or getattr(kr, "priority", 1) <= 0:
        return None
    return keyring


def kasa_yok_metni() -> str:
    return ("Bu bilgisayarda şifre kasası kullanılamıyor (`pip install keyring`; Linux'ta "
            "GNOME Keyring / KWallet gerekir). Şifre kaydedilmedi; site her açılışta "
            "elle giriş ister.")


def sifre_kaydet(site: str, kullanici: str, sifre: str) -> bool:
    kr = kasa()
    if not kr:
        return False
    kr.set_password(KASA_SERVIS, f"{site}:{kullanici}", sifre)
    return True


def sifre_al(site: str, kullanici: str) -> str | None:
    kr = kasa()
    return kr.get_password(KASA_SERVIS, f"{site}:{kullanici}") if kr else None


def sifre_sil(site: str, kullanici: str) -> None:
    kr = kasa()
    if kr:
        try:
            kr.delete_password(KASA_SERVIS, f"{site}:{kullanici}")
        except Exception:
            pass


def site_anahtari(ad: str) -> str:
    from kisisel_hesap import kucuk
    return re.sub(r"[^a-z0-9]+", "-", kucuk(ad)).strip("-") or "site"


# --- Giriş paneli ----------------------------------------------------------

def panel_html(token: str, veri: dict, mesaj: str = "") -> str:
    kayitli = "".join(
        f"<li><b>{html.escape(s['ad'])}</b> &middot; {html.escape(s['kullanici'])} &middot; "
        f"{'şifre kasada' if s.get('sifre_kasada') else 'şifre kaydedilmedi'}</li>"
        for s in veri["siteler"].values()) or "<li>Henüz site eklenmedi.</li>"
    secenek = "".join(f'<option value="{k}">{html.escape(v[0])}</option>' for k, v in HAZIR_SITELER.items())
    uyari = "" if kasa() else f'<p class="uyari">{html.escape(kasa_yok_metni())}</p>'
    eksik = "".join(f"<li>{html.escape(x)}</li>" for x in SITE_GEREKEN)
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>İhale Analiz · Site Girişi</title>
<style>
:root{{--bg:#f6f7f9;--kart:#fff;--yazi:#1d2433;--ikincil:#5b6476;--vurgu:#1f6feb;--cizgi:#d8dde6;--uyari:#9a3412}}
@media (prefers-color-scheme:dark){{:root{{--bg:#12151b;--kart:#1b2029;--yazi:#e6e9ef;--ikincil:#9aa3b2;--vurgu:#58a6ff;--cizgi:#2d3440;--uyari:#fdba74}}}}
body{{margin:0;background:var(--bg);color:var(--yazi);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:560px;margin:32px auto;padding:0 16px}}
.kart{{background:var(--kart);border:1px solid var(--cizgi);border-radius:10px;padding:20px;margin-bottom:16px}}
h1{{font-size:20px;margin:0 0 8px}} h2{{font-size:16px;margin:0 0 8px}}
p,li{{color:var(--ikincil)}} label{{display:block;margin:12px 0 4px;font-weight:600}}
input,select{{width:100%;box-sizing:border-box;padding:9px;border:1px solid var(--cizgi);border-radius:6px;background:var(--bg);color:var(--yazi);font:inherit}}
.dugmeler{{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}}
button{{padding:9px 14px;border-radius:6px;border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);font:inherit;cursor:pointer}}
button.ana{{background:var(--vurgu);border-color:var(--vurgu);color:#fff}}
.uyari{{color:var(--uyari)}} .mesaj{{color:var(--vurgu);font-weight:600}}
</style></head><body><main>
<div class="kart"><h1>İhale sitesi girişi</h1>
<p>İhaleleri takip ettiğiniz siteye giriş bilgilerinizi ekleyin. Bu bilgiler hızlı ihale
analizi, geçmiş ihalelerden kurum birim fiyatı tespiti, rakip, katılımcı ve tenzilat analizi
için kullanılır.</p>
<p>Şifreniz bilgisayarınızın kendi şifre kasasında saklanır; hiçbir dosyaya, rapora ya da
sohbete yazılmaz ve bu bilgisayardan dışarı gönderilmez.</p>{uyari}
{f'<p class="mesaj">{html.escape(mesaj)}</p>' if mesaj else ''}</div>
<form class="kart" method="post" action="/kaydet?t={token}" autocomplete="off">
<h2>Site ekle</h2>
<label for="site">Site</label>
<select id="site" name="site" onchange="document.getElementById('diger').hidden=this.value!=='diger'">
{secenek}<option value="diger">Başka bir site</option></select>
<div id="diger" hidden><label for="ad">Site adı</label><input id="ad" name="ad">
<label for="url">Giriş adresi</label><input id="url" name="url" placeholder="https://"></div>
<label for="kullanici">Kullanıcı adı</label><input id="kullanici" name="kullanici" required>
<label for="sifre">Şifre</label><input id="sifre" name="sifre" type="password" required>
<div class="dugmeler"><button class="ana" type="submit">Kaydet</button></div></form>
<div class="kart"><h2>Eklenen siteler</h2><ul>{kayitli}</ul>
<form method="post" action="/bitir?t={token}" class="dugmeler">
<button class="ana" type="submit">Bitir</button></form></div>
<form class="kart" method="post" action="/atla?t={token}"><h2>Şimdilik atla</h2>
<p>Giriş yapmazsanız raporda şunlar yer almaz:</p><ul>{eksik}</ul>
<p>Yaklaşık maliyet analizinde kurumların birim fiyatları tespit edilemez; analiz yalnızca
rayiç fiyatlar üzerinden yapılır. Daha sonra istediğiniz zaman "site girişi ekle" diyebilirsiniz.</p>
<div class="dugmeler"><button type="submit">Girişi atla</button></div></form>
</main></body></html>"""


def kapanis_html(baslik: str, metin: str) -> str:
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>{baslik}</title>'
            '<style>body{font:15px/1.5 system-ui,sans-serif;max-width:560px;margin:48px auto;padding:0 16px;'
            'background:#f6f7f9;color:#1d2433}@media (prefers-color-scheme:dark){body{background:#12151b;'
            f'color:#e6e9ef}}}}</style></head><body><h1>{baslik}</h1><p>{html.escape(metin)}</p>'
            '<p>Bu pencereyi kapatabilirsiniz.</p></body></html>')


def panel(sistem: Path, tarayici_ac: bool = True) -> dict:
    """Paneli 127.0.0.1 üzerinde açar; kullanıcı Bitir / Atla deyince ya da süre dolunca döner."""
    veri = oku(sistem)
    token = secrets.token_urlsafe(16)  # aynı bilgisayardaki başka bir sürecin form göndermesine karşı
    bitti = threading.Event()

    class Isleyici(BaseHTTPRequestHandler):
        def log_message(self, *a):  # istekleri (ve form gövdesini) hiçbir yere yazma
            pass

        def _gonder(self, govde: str, kod: int = 200):
            b = govde.encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _yetkili(self) -> bool:
            q = parse_qs(self.path.partition("?")[2])
            return secrets.compare_digest(q.get("t", [""])[0], token)

        def do_GET(self):
            if not self._yetkili():
                return self._gonder("Yetkisiz", 403)
            self._gonder(panel_html(token, veri))

        def do_POST(self):
            if not self._yetkili():
                return self._gonder("Yetkisiz", 403)
            n = int(self.headers.get("Content-Length") or 0)
            form = {k: v[0].strip() for k, v in parse_qs(self.rfile.read(n).decode("utf-8")).items()}
            yol = self.path.partition("?")[0]
            if yol == "/kaydet":
                self._gonder(panel_html(token, veri, kaydet(sistem, veri, form)))
            elif yol == "/bitir":
                veri["durum"] = "bagli" if veri["siteler"] else "atlandi"
                yaz(sistem, veri)
                self._gonder(kapanis_html("Kaydedildi", f"{len(veri['siteler'])} site eklendi."))
                bitti.set()
            elif yol == "/atla":
                if not veri["siteler"]:
                    veri["durum"] = "atlandi"
                    veri["atlama_tarihi"] = date.today().isoformat()
                yaz(sistem, veri)
                self._gonder(kapanis_html("Site girişi atlandı", ATLA_METNI))
                bitti.set()
            else:
                self._gonder("Bulunamadı", 404)

    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    adres = f"http://127.0.0.1:{sunucu.server_address[1]}/?t={token}"
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    print(f"Site giriş paneli açıldı: {adres}")
    print("Panelde siteleri ekleyip Bitir'e ya da Girişi atla'ya basın.", flush=True)
    if tarayici_ac:
        webbrowser.open(adres)
    if not bitti.wait(PANEL_SURE_DK * 60):
        print(f"Panel {PANEL_SURE_DK} dakika içinde kapatılmadı; eklenen siteler kaydedildi.")
        if veri["durum"] == "sorulmadi" and veri["siteler"]:
            veri["durum"] = "bagli"
        yaz(sistem, veri)
    sunucu.shutdown()
    return veri


def kaydet(sistem: Path, veri: dict, form: dict) -> str:
    secim = form.get("site", "")
    if secim in HAZIR_SITELER:
        anahtar, (ad, url) = secim, HAZIR_SITELER[secim]
    else:
        ad, url = form.get("ad", ""), form.get("url", "")
        if not ad or not url.startswith(("https://", "http://")):
            return "Başka bir site için ad ve http(s) ile başlayan giriş adresi gerekli."
        anahtar = site_anahtari(ad)
    kullanici, sifre = form.get("kullanici", ""), form.get("sifre", "")
    if not kullanici or not sifre:
        return "Kullanıcı adı ve şifre gerekli."
    eski = veri["siteler"].get(anahtar)
    if eski and eski["kullanici"] != kullanici:
        sifre_sil(anahtar, eski["kullanici"])
    kasada = sifre_kaydet(anahtar, kullanici, sifre)
    veri["siteler"][anahtar] = {"ad": ad, "url": url, "kullanici": kullanici,
                                "sifre_kasada": kasada, "eklenme": date.today().isoformat()}
    veri["durum"] = "bagli"
    yaz(sistem, veri)
    return f"{ad} eklendi." + ("" if kasada else " " + kasa_yok_metni())


# --- Durum ----------------------------------------------------------------

def durum_metni(veri: dict) -> str:
    if veri["siteler"]:
        satir = ["Bağlı siteler: " + ", ".join(s["ad"] for s in veri["siteler"].values()) + "."]
        satir.append("Raporda kurum birim fiyatı, rakip, katılımcı ve tenzilat analizi yapılabilir.")
        return "\n".join(satir)
    if veri["durum"] == "atlandi":
        return "Site girişi atlandı. " + ATLA_METNI
    return "Site girişi henüz sorulmadı. `siteler.py panel` ile açın. " + ATLA_METNI


def cmd_durum(sistem, a):
    print(durum_metni(oku(sistem)))


def cmd_liste(sistem, a):
    veri = oku(sistem)
    if not veri["siteler"]:
        print("Kayıtlı site yok")
    for k, s in veri["siteler"].items():
        print(f"{k} | {s['ad']} | {s['url']} | {s['kullanici']} | "
              f"{'şifre kasada' if s.get('sifre_kasada') else 'şifre kaydedilmedi'}")


def cmd_sil(sistem, a):
    veri = oku(sistem)
    s = veri["siteler"].pop(a.site, None)
    if not s:
        raise SystemExit(f"Site bulunamadı: {a.site}")
    sifre_sil(a.site, s["kullanici"])
    if not veri["siteler"]:
        veri["durum"] = "atlandi"
    yaz(sistem, veri)
    print(f"Silindi: {s['ad']}")


def cmd_panel(sistem, a):
    veri = panel(sistem, not a.tarayici_acma)
    print(durum_metni(veri))


# --- Oturum (Playwright, isteğe bağlı) ------------------------------------

def profil_dir(sistem: Path, site: str) -> Path:
    return sistem / "oturumlar" / site


def playwright_ac():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Bu komut için: pip install playwright && python -m playwright install chromium")
    return sync_playwright()


def site_al(sistem: Path, site: str) -> dict:
    s = oku(sistem)["siteler"].get(site)
    if not s:
        raise SystemExit(f"Site kayıtlı değil: {site}. Önce `siteler.py panel`.")
    return s


def cmd_oturum_ac(sistem, a):
    """Görünür tarayıcıda siteyi açar, kullanıcı adı ve şifreyi doldurur, gönderme ve
    CAPTCHA / e-Devlet / SMS adımı kullanıcıdadır. Çerezler `.sistem/oturumlar/<site>/`
    altında kalır; `cek` komutu bu oturumu kullanır."""
    s = site_al(sistem, a.site)
    sifre = sifre_al(a.site, s["kullanici"])
    with playwright_ac() as pw:
        ctx = pw.chromium.launch_persistent_context(str(profil_dir(sistem, a.site)), headless=False)
        sayfa = ctx.pages[0] if ctx.pages else ctx.new_page()
        sayfa.goto(s["url"])
        try:
            parola = sayfa.locator("input[type=password]").first
            parola.wait_for(timeout=8000)
            kullanici = sayfa.locator(
                "input[type=email], input[type=text], input:not([type])").first
            kullanici.fill(s["kullanici"])
            if sifre:
                parola.fill(sifre)
            print("Giriş alanları dolduruldu. Girişi siz tamamlayın, sonra tarayıcıyı kapatın.")
        except Exception:
            print("Giriş formu bulunamadı. Tarayıcıda giriş sayfasını açıp girişi siz yapın, "
                  "sonra tarayıcıyı kapatın.")
        sifre = None
        try:
            ctx.wait_for_event("close", timeout=0)
        except Exception:
            pass
    print(f"Oturum kaydedildi: {s['ad']}")


def cmd_cek(sistem, a):
    """Açılmış oturumla bir sayfayı HTML olarak kaydeder; giriş duvarına takılırsa durur."""
    s = site_al(sistem, a.site)
    if not profil_dir(sistem, a.site).exists():
        raise SystemExit(f"Önce oturum açın: siteler.py oturum-ac --site {a.site}")
    with playwright_ac() as pw:
        ctx = pw.chromium.launch_persistent_context(str(profil_dir(sistem, a.site)), headless=True)
        sayfa = ctx.new_page()
        sayfa.goto(a.url, wait_until="networkidle")
        if sayfa.locator("input[type=password]").count():
            ctx.close()
            raise SystemExit(f"{s['ad']} giriş istiyor; oturum süresi dolmuş olabilir. "
                             f"`siteler.py oturum-ac --site {a.site}` ile yeniden giriş yapın.")
        a.cikti.parent.mkdir(parents=True, exist_ok=True)
        a.cikti.write_text(sayfa.content(), encoding="utf-8")
        ctx.close()
    print(f"Kaydedildi: {a.cikti}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sistem", type=Path, default=None, help=".sistem klasörü")
    sub = p.add_subparsers(dest="komut", required=True)
    s = sub.add_parser("panel")
    s.add_argument("--tarayici-acma", action="store_true", help="adresi yalnızca yazdır")
    s.set_defaults(fn=cmd_panel)
    sub.add_parser("durum").set_defaults(fn=cmd_durum)
    sub.add_parser("liste").set_defaults(fn=cmd_liste)
    s = sub.add_parser("sil")
    s.add_argument("--site", required=True)
    s.set_defaults(fn=cmd_sil)
    s = sub.add_parser("oturum-ac")
    s.add_argument("--site", required=True)
    s.set_defaults(fn=cmd_oturum_ac)
    s = sub.add_parser("cek")
    s.add_argument("--site", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--cikti", type=Path, required=True)
    s.set_defaults(fn=cmd_cek)
    a = p.parse_args()
    a.fn(a.sistem or sistem_dir(), a)


if __name__ == "__main__":
    main()
