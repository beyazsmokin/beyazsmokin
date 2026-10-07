#!/usr/bin/env python3
"""Analiz motoru: panelden başlatılan ön incelemeyi ve detaylı analizi uçtan uca çalıştırır.

Panel "Analizi başlat" ya da "takibe al" dediğinde bu betik ayrı bir süreçte çalışır, her adımı
`calisma/durum.json`'a yazar (panel canlı gösterir), raporu ve Excel'i ihale klasörüne bırakır.

İki tür:
  on     Ön inceleme (ihale dosyası gerekmez): takip sitesinin ilan bilgisi, bu idarenin geçmiş
         ihaleleri, rakip ve tenzilat (öğrenen veritabanı), firma ve tercihlere göre uygunluk
         puanı (tara.py), kısa değerlendirme. Çıktı: "<kod> Ön İnceleme Rapor.md/.html".
  detay  Detaylı analiz (kaynak/ klasöründe ihale dosyası olmalı): SKILL.md §2 akışı.
           0  dokümanların metni (belge_metni.py), çizimler (proje_oku.py), geçmiş (vt.py baglam)
           1  doküman okuyucu ajan  -> 01-ozet.md, tarihler ajandaya, ihale bilgileri panele
           2a-2d idari, teknik, mali, metraj ajanları (paralel) -> 02..06; metraj CSV'lerinden
              BFTC kıyası (metraj_kiyas.py) ve kişisel hesap (kisisel_hesap.py) betikle
           3  risk denetçisi       -> 05-riskler.md
           4  rapor yazarı         -> <kod> Rapor.md, Excel (excel_rapor.py), HTML/PDF (html_rapor.py)
           5  öğrenme kaydı        -> vt.py ihale-kaydet, metraj-yukle, pursantaj-yukle, ders-ekle

Ajanları yapay zekâ çalıştırır (`yz.py`: Claude Code, Claude API, ChatGPT ya da Hermes/yerel model).
Bağlantı yoksa ön inceleme kural tabanlı çalışır; detaylı analizde dokümanlar hazırlanır ve ajan
adımları sohbetteki asistana bırakılır ("Kuyruktaki ihaleleri analiz et"). Sayıları betikler
hesaplar, ajanlar alan doldurur (K-4.2.1).

Kullanım:
  motor.py calistir --kod 2026-1234567 [--tur on|detay]   # tür verilmezse kaynak/ doluysa detay
  motor.py kuyruk                                         # "hesaplanacak" ihalelerin hepsi sırayla
  motor.py durum                                          # hangi yapay zekâ bağlantısı kullanılacak
  motor.py anahtar --saglayici anthropic|openai           # API anahtarını şifre kasasına yazar
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import belge_metni
import takip
import vt
import yz

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
KILIT = ".motor.kilit"
ADIM_ADI = {a[0]: a[1] for a in takip.ADIMLAR + takip.ON_ADIMLAR}

PLATFORM_NOTU = """
## Bu adım nasıl çalışıyor

Bu adımı ihale panelinin analiz motoru çalıştırıyor. Komut çalıştıramaz, dosya yazamazsın;
talimatta geçen betik komutlarını (takip.py, vt.py, metraj_kiyas.py, kisisel_hesap.py,
excel_rapor.py, html_rapor.py) motor senin yerine çalıştırır ve sonuçları sana girdi olarak verir.

Cevabın doğrudan istenen Markdown dosyasının içeriği olsun: giriş, açıklama ya da kapanış cümlesi
yazma, cevabı kod bloğuna sarma. Ek çıktıları cevabın sonunda yalnızca şu kod bloklarıyla ver:

- Ek dosya (CSV ya da MD), adı talimattaki gibi:
  ```dosya:metraj-idare.csv
  poz_no,tanim,birim,miktar
  ```
- Dokümanda açıkça yazan tarihler (ajandaya girer), JSON listesi; tur: yer_gorme, aciklama_talebi,
  dokuman, teminat, sozlesme, diger:
  ```ajanda
  [{"tarih": "2026-10-15", "saat": "14:00", "tur": "yer_gorme", "baslik": "Yer görme", "aciklama": "İdari şartname md. 7"}]
  ```
- İhale bilgileri (panelde ihaleye yazılır), yalnızca dokümanda olanlar; tur: birim_fiyat ya da anahtar_teslim:
  ```ihale
  {"idare": "...", "il": "...", "ihale_tarihi": "2026-10-20 10:30", "tur": "birim_fiyat", "yaklasik": 2500000}
  ```
- Sonraki ihalelerde işe yarayacak ders (öğrenen veritabanına girer):
  ```ders
  [{"metin": "...", "ajan": "mali-analist"}]
  ```
"""

BLOK = re.compile(r"```(dosya:[^\n`]+|ajanda|ihale|ders)[ \t]*\n(.*?)```", re.S)
DOSYA_ADI = re.compile(r"[\w.-]+\.(csv|md|txt)")


class Durdur(Exception):
    """Akışı kullanıcıya açıklanacak bir nedenle durdurur."""


# --- Ayarlar ---------------------------------------------------------------------------

def _deger(v: str):
    v = v.strip()
    if v[:1] in "\"'" and v[-1:] == v[:1]:
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [_deger(x) for x in v[1:-1].split(",") if x.strip()]
    if v in ("", "null", "~"):
        return None
    if v in ("true", "false"):
        return v == "true"
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def ayarlar(alan: Path, bolum: str) -> dict:
    """config.yaml içindeki bir bölümün düz `anahtar: değer` satırları (PyYAML gerekmez)."""
    cfg = alan / ".sistem" / "config.yaml"
    if not cfg.exists():
        return {}
    m = re.search(rf"^{bolum}:[^\n]*\n((?:[ \t]+.*\n?|\s*\n)*)", cfg.read_text(encoding="utf-8"), re.M)
    out = {}
    for satir in (m.group(1).splitlines() if m else []):
        d = re.match(r"^[ \t]+([\w-]+):[ \t]*(.*?)[ \t]*(?:#.*)?$", satir)
        if d:
            out[d.group(1)] = _deger(d.group(2))
    return out


def yz_sec(alan: Path):
    return yz.sec(ayarlar(alan, "analiz"))


def py(betik: str, *args, cwd: Path | None = None, zaman: int = 600) -> str:
    """Skill betiğini çalıştırır, çıktısını döner; hata verirse Durdur değil RuntimeError."""
    r = subprocess.run([sys.executable, str(SCRIPTS / betik), *map(str, args)], capture_output=True,
                       text=True, encoding="utf-8", cwd=cwd, timeout=zaman,
                       **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
    if r.returncode:
        hata = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError(f"{betik}: {hata[-1] if hata else r.returncode}")
    return r.stdout


def oku(p: Path, sinir: int | None = None) -> str:
    try:
        s = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return s if not sinir or len(s) <= sinir else s[:sinir] + f"\n\n> (dosya {len(s)} karakter; ilk {sinir} karakter verildi)\n"


# --- Kilit -----------------------------------------------------------------------------

def calisiyor(klasor: Path) -> bool:
    """Bu ihale için motor çalışıyor mu (kilit 3 saatten eskiyse bayat sayılır)."""
    k = klasor / "calisma" / KILIT
    try:
        return (datetime.now().timestamp() - k.stat().st_mtime) < 3 * 3600
    except OSError:
        return False


# --- Motor -----------------------------------------------------------------------------

class Motor:
    def __init__(self, alan: Path, kod: str, tur: str | None = None):
        self.alan, self.kod = alan, takip.klasor_adi(kod)
        self.klasor = takip.ihale_klasoru(alan, self.kod)
        self.calisma, self.kaynak = self.klasor / "calisma", self.klasor / "kaynak"
        self.sistem = alan / ".sistem"
        self.db = self.sistem / "veritabani" / "ihale.db"
        self.analiz = ayarlar(alan, "analiz")
        self.surucu, self.yz_ad = yz.sec(self.analiz)
        self._kilit = threading.Lock()
        self.dersler: list[dict] = []
        self.ajanda_sayi = 0
        self.karar = "Belirsiz"
        with self.vt() as con:
            t = con.execute("SELECT * FROM takip WHERE kod=?", (self.kod,)).fetchone()
        if not t:
            raise Durdur(f"Takipte böyle bir ihale yok: {self.kod}")
        self.ihale = dict(t)
        self.tur = tur or ("detay" if self.kaynak_dosyalari() else "on")

    # yardımcılar
    @contextmanager
    def vt(self):
        con = takip.baglan(self.alan)
        try:
            with con:
                yield con
        finally:
            con.close()

    def kaynak_dosyalari(self) -> list[Path]:
        return [f for f in self.kaynak.rglob("*") if f.is_file() and not f.name.startswith(".")] \
            if self.kaynak.is_dir() else []

    def adim(self, kimlik: str, durum: str, mesaj: str | None = None) -> None:
        with self._kilit:  # paralel ajanlar durum.json'a sırayla yazsın
            takip.adim_yaz(self.klasor, kimlik, durum, mesaj)

    def calistir_adim(self, kimlik: str, is_) -> str | None:
        self.adim(kimlik, "basladi")
        try:
            mesaj = is_()
        except Exception as e:
            self.adim(kimlik, "hata", str(e) or e.__class__.__name__)
            raise
        self.adim(kimlik, "bitti", mesaj)
        return mesaj

    def durum_yaz(self, durum: str) -> None:
        with self.vt() as con:
            con.execute("UPDATE takip SET durum=?, guncelleme=? WHERE kod=?", (durum, takip.simdi(), self.kod))

    def vt_metin(self, *args) -> str:
        try:
            return py("vt.py", "--vt", self.db, *args).strip()
        except RuntimeError as e:
            return f"(alınamadı: {e})"

    def hafiza(self, ad: str) -> str:
        return oku(self.sistem / "hafiza" / ad)

    def site_durumu(self) -> str:
        try:
            import siteler
            return siteler.durum_metni(siteler.oku(self.sistem))
        except Exception as e:
            return f"(site durumu okunamadı: {e})"

    # çalıştırma
    def calistir(self) -> None:
        self.calisma.mkdir(parents=True, exist_ok=True)
        kilit = self.calisma / KILIT
        kilit.write_text(f"{takip.simdi()}\n", encoding="utf-8")
        onceki = self.ihale["durum"]
        takip.surec_baslat(self.klasor, self.tur)
        self.durum_yaz("analizde")
        log = self.calisma / "motor.log"
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n=== {takip.simdi()} {self.tur} · yapay zekâ: {self.yz_ad}\n")
            son = self.on_inceleme() if self.tur == "on" else self.detay()
            self.durum_yaz(son)
        except Exception as e:
            with open(log, "a", encoding="utf-8") as f:
                f.write(traceback.format_exc())
            # ihale yeniden başlatılabilsin: "analizde"de takılı kalmaz
            self.durum_yaz(onceki if onceki not in ("analizde", "hesaplanacak") else "takipte")
            if not isinstance(e, Durdur):
                print(f"Hata: {e}", file=sys.stderr)
            raise
        finally:
            takip.surec_bitir(self.klasor)
            kilit.unlink(missing_ok=True)

    # --- yapay zekâ ----------------------------------------------------------------------

    def ajan(self, ad: str, gorev: str, girdiler: list[tuple[str, str]]) -> str:
        """Ajanı çalıştırır, ek blokları işler, ana Markdown'ı döner."""
        sistem = (f"Sen ihale-analiz sisteminin **{ad}** ajanısın. Türkçe yaz.\n\n"
                  f"{oku(SKILL / 'kurallar.md')}\n\n{oku(SKILL / 'agents' / f'{ad}.md')}\n{PLATFORM_NOTU}")
        parca = [f"İhale kodu: {self.kod}\nBugün: {date.today():%Y-%m-%d}\n\n## Görevin\n{gorev}"]
        if self.surucu.dosya_okur:
            parca.append("Kaynak dosyalar `kaynak/` klasöründe. Aşağıdaki metinde eksik kalan, taranmış ya "
                         "da çizim/görsel dosyaları Read aracıyla açabilirsin.")
        parca += [f"## Girdi: {b}\n\n{m.strip() or '(boş)'}" for b, m in girdiler]
        cevap = self.surucu.sor(sistem, "\n\n".join(parca), str(self.klasor))
        return self.bloklari_isle(cevap, ad)

    def bloklari_isle(self, cevap: str, ajan: str) -> str:
        notlar = []
        for tur, govde in BLOK.findall(cevap):
            try:
                if tur.startswith("dosya:"):
                    ad = tur[6:].strip()
                    if DOSYA_ADI.fullmatch(ad):
                        (self.calisma / ad).write_text(govde.strip() + "\n", encoding="utf-8")
                        notlar.append(ad)
                elif tur == "ajanda":
                    self.ajanda_ekle(json.loads(govde))
                elif tur == "ihale":
                    self.ihale_guncelle(json.loads(govde))
                elif tur == "ders":
                    self.dersler += [{**d, "ajan": d.get("ajan") or ajan} for d in json.loads(govde)
                                     if isinstance(d, dict) and d.get("metin")]
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass  # bozuk ek blok ana çıktıyı bozmasın
        md = BLOK.sub("", cevap).strip()
        m = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*?)\n```", md, re.S)
        return (m.group(1) if m else md).strip() + "\n"

    def ajanda_ekle(self, olaylar: list) -> None:
        with self.vt() as con:
            for o in olaylar if isinstance(olaylar, list) else []:
                if not isinstance(o, dict):
                    continue
                tur = o.get("tur") if o.get("tur") in takip.ETKINLIK_TURLERI and o.get("tur") != "ihale" else "diger"
                try:
                    takip.etkinlik_ekle(con, {"kod": self.kod, "tarih": o.get("tarih"), "saat": o.get("saat"),
                                              "tur": tur, "baslik": o.get("baslik"), "aciklama": o.get("aciklama"),
                                              "kaynak": "ajan"})
                    self.ajanda_sayi += 1
                except ValueError:
                    pass

    def ihale_guncelle(self, veri: dict) -> None:
        tur = str(veri.get("tur") or "").lower()
        veri["tur"] = "anahtar_teslim" if ("anahtar" in tur or "götürü" in tur or "goturu" in tur) \
            else "birim_fiyat" if "birim" in tur else None
        with self.vt() as con:
            for k in ("idare", "il", "ihale_tarihi", "tur", "yaklasik"):
                if veri.get(k) in (None, ""):
                    continue
                try:
                    takip.guncelle(con, self.kod, {k: veri[k]})
                except (ValueError, KeyError):
                    pass
            self.ihale.update(dict(con.execute("SELECT * FROM takip WHERE kod=?", (self.kod,)).fetchone()))

    # --- ön inceleme ---------------------------------------------------------------------

    def on_inceleme(self) -> str:
        t = self.ihale
        ilan: dict = {}
        on: dict = {}

        def ilan_bilgisi():
            for ad in ("site-ilanlar.json", "site-sonuclar.json"):
                try:
                    liste = json.loads(oku(self.sistem / ad) or "{}").get("liste", [])
                except json.JSONDecodeError:
                    liste = []
                for r in liste:
                    if t["ikn"] and r.get("ikn") == t["ikn"]:
                        ilan.update({k: v for k, v in r.items() if v})
                        break
            for k in ("ad", "idare", "il", "ihale_tarihi", "yaklasik", "tur", "ikn", "kaynak_url"):
                if t.get(k) and not ilan.get(k):
                    ilan[k] = t[k]
            kalan = None
            if ilan.get("ihale_tarihi"):
                kalan = (date.fromisoformat(ilan["ihale_tarihi"][:10]) - date.today()).days
            on["kalan"] = kalan
            return " · ".join(x for x in (ilan.get("idare"), ilan.get("il"),
                                          f"ihaleye {kalan} gün" if kalan is not None else None) if x) or "İlan bilgisi az"
        self.calistir_adim("o1", ilan_bilgisi)

        def gecmis():
            idare, konu = ilan.get("idare"), ilan.get("ad")
            on["baglam"] = self.vt_metin("baglam", *(["--idare", idare] if idare else []),
                                         *(["--konu", konu] if konu else []))
            on["tenzilat"] = self.vt_metin("tenzilat", *(["--idare", idare] if idare else []))
            on["rakip"] = self.vt_metin("rakip", *(["--idare", idare] if idare else []))
            with self.vt() as con:
                tz = vt.tenzilat_satirlari(con, idare) if idare else []
                n = con.execute("SELECT COUNT(*) FROM ihaleler WHERE idare LIKE ?",
                                (f"%{idare}%",)).fetchone()[0] if idare else 0
            return f"Bu idarenin {n} analizi, {len(tz)} sonuçlanmış ihale verisi var"
        self.calistir_adim("o2", gecmis)

        def puan():
            import tara
            tarama = ayarlar(self.alan, "tarama")
            a = SimpleNamespace(butce_min=vt.num(tarama.get("butce_min")), butce_max=vt.num(tarama.get("butce_max")))
            r = {"il": ilan.get("il"), "konu": " ".join(x for x in (ilan.get("ad"), ilan.get("benzer_is")) if x),
                 "yaklasik": ilan.get("yaklasik"), "idare": ilan.get("idare"), "tur": ilan.get("tur")}
            with self.vt() as con:
                agirlik = vt.tercih_agirliklari(con)
            liste = lambda v: ",".join(v) if isinstance(v, list) else (v or "")
            on["puan"], on["neden"] = tara.skorla(r, a, tara.liste(liste(tarama.get("iller"))),
                                                 tara.liste(liste(tarama.get("anahtar_kelimeler"))), agirlik)
            return f"Puan {on['puan']}" + (f" ({'; '.join(on['neden'])})" if on["neden"] else
                                           " (eşleşen il, kelime ya da tercih yok)")
        self.calistir_adim("o3", puan)

        def degerlendirme():
            kural = self.kural_karari(on)
            on["karar"], on["gerekce"], on["yz"] = kural[0], kural[1], None
            if not self.surucu:
                return f"{on['karar']} (kural tabanlı; yapay zekâ bağlantısı yok)"
            try:
                metin = self.ajan("koordinator", (
                    "Bu ihale için ÖN İNCELEME yap: ihale dokümanı henüz indirilmedi, yalnızca ilan bilgisi, "
                    "öğrenen veritabanındaki geçmiş ve firma profili var. İlk satır tam olarak "
                    "`**Karar:** Detaylı incele | Dikkatle incele | Geç. <tek cümle gerekçe>` olsun. Ardından "
                    "en fazla 8 madde: firma profiline uygunluk (benzer iş, bölge, büyüklük), zaman yeterliliği, "
                    "idare geçmişi, rakip ve tenzilat beklentisi, detaylı analizde bakılacaklar. Dokümanda "
                    "olmayan bilgiyi uydurma; veri yoksa 'veri yok' yaz. Başlık yazma."),
                    [("İlan bilgisi (takip sitesi)", json.dumps(ilan, ensure_ascii=False, indent=1)),
                     ("Kural tabanlı puan (tara.py)", f"{on['puan']} · {'; '.join(on['neden']) or '-'} · "
                                                     f"kural kararı: {kural[0]}"),
                     ("Geçmiş (vt.py baglam)", on["baglam"]), ("Tenzilat", on["tenzilat"]), ("Rakipler", on["rakip"]),
                     ("Firma profili", self.hafiza("firma-profili.md")),
                     ("Öğrenilenler", self.hafiza("ogrenilenler.md"))])
            except yz.YzHatasi as e:
                return f"{on['karar']} (kural tabanlı; yapay zekâ çalışmadı: {e})"
            m = re.search(r"^\*\*Karar:\*\*\s*([^.\n]+)\.?\s*(.*)$", metin, re.M)
            if m:
                on["karar"], on["gerekce"] = m.group(1).strip(), m.group(2).strip()
                metin = metin.replace(m.group(0), "").strip()
            on["yz"] = metin
            return f"{on['karar']} ({self.yz_ad})"
        self.calistir_adim("o4", degerlendirme)

        def rapor():
            md = self.on_rapor_md(ilan, on)
            yol = self.klasor / f"{self.kod} {takip.ON_EK}.md"
            yol.write_text(md, encoding="utf-8")
            import html_rapor
            html_rapor.olustur(self.klasor, pdf=False, md_yolu=yol)
            return "Ön inceleme raporu panelin Rapor sekmesinde"
        self.calistir_adim("o5", rapor)
        return "takipte" if self.ihale["durum"] in ("analizde", "hesaplanacak") else self.ihale["durum"]

    @staticmethod
    def kural_karari(on: dict) -> tuple[str, str]:
        kalan, puan = on.get("kalan"), on.get("puan") or 0
        if kalan is not None and kalan < 0:
            return "Geç", "İhale tarihi geçmiş."
        if kalan is not None and kalan < 2:
            return "Geç", f"İhaleye {kalan} gün kalmış; detaylı analiz ve teklif hazırlığı için süre yetersiz."
        if puan < 0:
            return "Geç", "Bütçe ya da tercihlerinize göre uygun görünmüyor."
        if puan >= 4 and (kalan is None or kalan >= 5):
            return "Detaylı incele", "İl, iş türü ve tercihlerinizle uyumlu."
        return "Dikkatle incele", "Uyum kısmi; ihale dosyasıyla detaylı analizde netleşir."

    def on_rapor_md(self, ilan: dict, on: dict) -> str:
        def para(v):
            try:
                return f"{float(v):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".") + " (RESMİ, ilan)"
            except (TypeError, ValueError):
                return v
        alanlar = [("İKN", ilan.get("ikn")), ("İş", ilan.get("ad")), ("İdare", ilan.get("idare")),
                   ("İl", ilan.get("il")), ("İhale tarihi", (ilan.get("ihale_tarihi") or "").replace("T", " ") or None),
                   ("Kalan gün", on.get("kalan")), ("İhale türü", ilan.get("ihale_tipi")),
                   ("Benzer iş", ilan.get("benzer_is")), ("Yaklaşık maliyet", para(ilan.get("yaklasik")) if ilan.get("yaklasik") else None),
                   ("Geçici teminat", ilan.get("teminat")), ("İşin süresi", ilan.get("sure")),
                   ("İlan", ilan.get("kaynak_url"))]
        satir = [f"| {a} | {str(v).replace('|', '/')} |" for a, v in alanlar if v not in (None, "")]
        karar_notu = "" if on.get("yz") else " (kural tabanlı ön karar, TAHMİN)"
        md = [f"# Ön İnceleme: {ilan.get('ad') or self.kod}\n",
              f"**Karar:** {on['karar']}. {on['gerekce']}{karar_notu}\n",
              "## İlan bilgileri\n", "| Alan | Değer |", "|---|---|", *satir,
              "\nKaynak: takip sitesindeki ilan (ihale dokümanı henüz okunmadı).\n",
              "## Uygunluk puanı\n",
              f"Puan: **{on['puan']}** (tara.py; il, anahtar kelime, bütçe ve beğen/reddet geçmişinize göre)\n",
              *([f"- {n}" for n in on["neden"]] or ["- Eşleşen il, anahtar kelime ya da tercih yok"])]
        if on.get("yz"):
            md += ["\n## Değerlendirme\n", on["yz"]]
        md += ["\n## Bu idarenin geçmişi, rakip ve tenzilat\n", "### Tenzilat (ARŞİV)\n", on["tenzilat"],
               "\n### Sık giren rakipler (ARŞİV)\n", on["rakip"],
               "\n## Sonraki adım\n",
              "- İhale dosyasını panelden **İhale dosyasını indir** ile indirin (EKAP güvenlik kodunu siz yazarsınız).",
               "- Ardından **Analizi başlat**: doküman okuma, idari/teknik/mali analiz, metraj, BFTC kıyası, "
               "pursantaj, risk, HTML/PDF rapor ve Excel.",
               "\n---\n_Ön inceleme yalnızca ilan bilgisine ve geçmiş kayıtlara dayanır; hukuki görüş değildir._"]
        return "\n".join(md) + "\n"

    # --- detaylı analiz ------------------------------------------------------------------

    def detay(self) -> str:
        if not self.kaynak_dosyalari():
            self.adim("0", "hata", "kaynak/ klasöründe ihale dosyası yok. Önce 'İhale dosyasını indir' "
                                   "ya da Dosyalar sekmesinden yükleyin.")
            raise Durdur("Kaynak dosya yok")
        c = self.calisma
        t = self.ihale

        def hazirlik():
            idare, konu = t.get("idare"), t.get("ad")
            baglam = self.vt_metin("baglam", *(["--idare", idare] if idare else []), *(["--konu", konu] if konu else []))
            (c / "00-baglam.md").write_text(f"{baglam}\n\n## İhale sitesi\n{self.site_durumu()}\n", encoding="utf-8")
            sinir = int(self.analiz.get("belge_karakter") or 400_000)
            b = belge_metni.topla(self.kaynak, sinir)
            (c / "00-belgeler.md").write_text(b["md"], encoding="utf-8")
            try:
                proje = py("proje_oku.py", self.kaynak, zaman=1200)
            except Exception as e:  # çizim okunamasa da analiz sürer
                proje = f"# Proje dosyaları\n\n(okunamadı: {e})\n"
            (c / "00-proje.md").write_text(proje, encoding="utf-8")
            mesaj = f"{b['okunan']}/{b['dosya']} dosya okundu" + (f", {b['sayfa']} sayfa" if b["sayfa"] else "")
            if b["kesilen"]:
                mesaj += f" (metin sınırı aşıldı, {b['kesilen']} karakter okunmadı)"
            if not self.profil_dolu():
                mesaj += (". UYARI: firma profili boş (.sistem/hafiza/firma-profili.md); yeterlilik ve teknik "
                          "uygunluk 'Belirsiz' çıkar, asistanınıza firma bilgilerinizi yazdırın")
            if not self.surucu:
                return (f"{mesaj}. Yapay zekâ bağlantısı yok ({self.yz_ad}); ajan adımları için "
                        "asistanınıza 'Kuyruktaki ihaleleri analiz et' yazın")
            return f"{mesaj} · ajanlar: {self.yz_ad}"
        self.calistir_adim("0", hazirlik)
        if not self.surucu:
            return "hesaplanacak"  # ajan adımları sohbetteki asistanda (takip.py kuyruk)

        belgeler = oku(c / "00-belgeler.md")
        profil = ("Firma profili", self.hafiza("firma-profili.md"))

        def okuyucu():
            with self.vt() as con:  # yeniden analizde ajanın önceki tarihleri tekrarlanmasın
                con.execute("DELETE FROM etkinlikler WHERE kod=? AND kaynak='ajan'", (self.kod,))
            md = self.ajan("dokuman-okuyucu", "01-ozet.md dosyasını yaz. Dokümanda geçen tarihleri `ajanda`, "
                           "ihale bilgilerini `ihale` bloğuyla ver.",
                           [("İhale dokümanları (00-belgeler.md)", belgeler), ("Geçmiş (00-baglam.md)", oku(c / "00-baglam.md"))])
            (c / "01-ozet.md").write_text(md, encoding="utf-8")
            return "Özet çıkarıldı" + (f"; {self.ajanda_sayi} tarih ajandaya eklendi" if self.ajanda_sayi else "")
        self.calistir_adim("1", okuyucu)
        ozet = ("01-ozet.md", oku(c / "01-ozet.md"))
        idare = self.ihale.get("idare")
        tur = self.ihale.get("tur")

        def baglam(ajan):
            return (f"Geçmiş ({ajan} için vt.py baglam)",
                    self.vt_metin("baglam", "--ajan", ajan, *(["--idare", idare] if idare else [])))

        def idari():
            (c / "02-idari.md").write_text(self.ajan("idari-analist", "02-idari.md dosyasını yaz.",
                                                     [ozet, profil, baglam("idari-analist"), ("İhale dokümanları", belgeler)]),
                                           encoding="utf-8")
            return self.tablo_ozeti(c / "02-idari.md", "Eksik", "eksik koşul")

        def teknik():
            (c / "03-teknik.md").write_text(self.ajan("teknik-analist", "03-teknik.md dosyasını yaz.",
                                                      [ozet, profil, baglam("teknik-analist"), ("İhale dokümanları", belgeler)]),
                                            encoding="utf-8")
            return self.tablo_ozeti(c / "03-teknik.md", "Karşılanamıyor", "karşılanamayan gereksinim")

        def mali():
            ek = [("siteler.py durum", self.site_durumu())]
            if idare:
                ek += [("vt.py tenzilat --idare", self.vt_metin("tenzilat", "--idare", idare)),
                       ("vt.py rakip --idare", self.vt_metin("rakip", "--idare", idare))]
            (c / "04-mali.md").write_text(self.ajan("mali-analist", "04-mali.md dosyasını yaz.",
                                                    [ozet, profil, baglam("mali-analist"), *ek, ("İhale dokümanları", belgeler)]),
                                          encoding="utf-8")
            return "Mali tablo hazır"

        def metraj():
            tolerans = ayarlar(self.alan, "metraj").get("tolerans_yuzde") or 5
            md = self.ajan("metraj-analist", (
                f"06-metraj.md dosyasını ve talimattaki CSV'leri `dosya:` bloklarıyla yaz. Tolerans %{tolerans}. "
                "Birim fiyatlıda metraj-idare.csv ve metraj-hesap.csv (poz_no,tanim,birim,miktar[,birim_fiyat]) "
                "şart: fark yüzdelerini motor metraj_kiyas.py ile hesaplar, sen fark yüzdesi yazma. Anahtar "
                "teslimde metraj.csv, bftc.csv, pursantaj.csv, grup-esleme.csv; pursantaj karşılaştırmasını "
                "Excel formülleri yapar."),
                [ozet, baglam("metraj-analist"),
                 ("vt.py pursantaj-ort", self.vt_metin("pursantaj-ort", *(["--tur", tur] if tur else []))),
                 ("Geçmiş birim fiyatlar (vt.py fiyat, kurum-fiyat)", self.fiyat_ozeti(idare)),
                 ("Proje dosyaları (proje_oku.py)", oku(c / "00-proje.md", 120_000)), ("İhale dokümanları", belgeler)])
            (c / "06-metraj.md").write_text(md, encoding="utf-8")
            notlar = []
            if (c / "metraj-idare.csv").exists() and (c / "metraj-hesap.csv").exists():
                kiyas = py("metraj_kiyas.py", c / "metraj-idare.csv", c / "metraj-hesap.csv", tolerans,
                           "--csv", c / "metraj-kiyas.csv")
                with open(c / "06-metraj.md", "a", encoding="utf-8") as f:
                    f.write(f"\n## BFTC kıyası (metraj_kiyas.py, tolerans %{tolerans})\n\n{kiyas}")
                gecmis = self.gecmis_fiyat_ekle(c / "metraj-kiyas.csv")
                if gecmis:
                    notlar.append(f"{gecmis} kalemde geçmiş fiyat")
                eksik = kiyas.count("cetvelde eksik")
                fazla = kiyas.count("cetvelde fazla")
                notlar.append(f"BFTC kıyası: {eksik} kalem cetvelde eksik, {fazla} kalem fazla")
            if (c / "pursantaj.csv").exists():
                notlar.append("pursantaj tablosu hazır")
            csvler = sorted(f.name for f in c.glob("*.csv"))
            return "; ".join(notlar) or (f"{len(csvler)} CSV yazıldı" if csvler else "Metraj notu hazır (CSV yok)")

        isler = {"2a": idari, "2b": teknik, "2c": mali, "2d": metraj}
        hatalar = {}

        def guvenli(k):
            try:
                self.calistir_adim(k, isler[k])
            except Exception as e:
                hatalar[k] = e
        if self.analiz.get("paralel_ajanlar", True):
            with ThreadPoolExecutor(max_workers=4) as ex:
                list(ex.map(guvenli, isler))
        else:
            for k in isler:
                guvenli(k)
        if len(hatalar) == len(isler):
            raise Durdur(f"Analiz ajanları çalışmadı: {next(iter(hatalar.values()))}")

        kisisel = self.kisisel_hesap()
        if kisisel and (c / "04-mali.md").exists():
            with open(c / "04-mali.md", "a", encoding="utf-8") as f:
                f.write(f"\n## Kişisel hesap (kisisel_hesap.py)\n\n{kisisel} (TAHMİN, kişisel kural; sistem tahmini "
                        "değişmez)\n")

        def risk():
            girdi = [(f, oku(c / f)) for f in ("01-ozet.md", "02-idari.md", "03-teknik.md", "04-mali.md", "06-metraj.md")]
            girdi += [("ogrenilenler.md", self.hafiza("ogrenilenler.md")), baglam("risk-denetci")]
            if hatalar:
                girdi.append(("Çalışmayan adımlar", "\n".join(f"- {ADIM_ADI[k]}: {e}" for k, e in hatalar.items())))
            (c / "05-riskler.md").write_text(self.ajan("risk-denetci", "05-riskler.md dosyasını yaz. Sonraki "
                                                       "ihalelere ders olacak bulguları `ders` bloğuyla ver.", girdi),
                                             encoding="utf-8")
            return self.tablo_ozeti(c / "05-riskler.md", "Yüksek", "yüksek risk") + \
                (f" · Kişisel hesap: {kisisel}" if kisisel else "")
        self.calistir_adim("3", risk)

        rapor_md = self.klasor / f"{self.kod} Rapor.md"

        def rapor():
            risk_esigi = self.analiz.get("risk_esigi") or "orta"
            girdi = [(f, oku(c / f)) for f in ("01-ozet.md", "02-idari.md", "03-teknik.md", "04-mali.md",
                                               "06-metraj.md", "05-riskler.md")]
            if kisisel:
                girdi.append(("07-kisisel-hesap.md", oku(c / "07-kisisel-hesap.md")))
            girdi += [("Rapor şablonu (templates/analiz-raporu.md)", oku(SKILL / "templates" / "analiz-raporu.md")),
                      ("siteler.py durum", self.site_durumu())]
            md = self.ajan("rapor-yazari", (
                f"`{self.kod} Rapor.md` içeriğini yaz (şablonla). risk_esigi: {risk_esigi}. Teklif öncesi işleri "
                "`dosya:yapilacaklar.csv` bloğuyla ver (is,son_tarih,sorumlu,durum). Excel, HTML ve PDF'i motor "
                "betikle üretir."), girdi)
            if not re.search(r"^\*\*Karar:\*\*", md, re.M):
                md = "**Karar:** Belirsiz. Rapor yazarı karar satırı vermedi; raporu kontrol edin.\n\n" + md
            rapor_md.write_text(md, encoding="utf-8")
            notlar = []
            try:
                py("excel_rapor.py", self.klasor)
                notlar.append("Excel")
            except Exception as e:
                notlar.append(f"Excel yazılamadı ({e})")
            import html_rapor
            s = html_rapor.olustur(self.klasor, pdf=True, md_yolu=rapor_md)
            notlar.insert(0, "HTML, PDF" if s["pdf"] else "HTML (PDF için Yazdır > PDF)")
            karar = re.search(r"^\*\*Karar:\*\*\s*([^.\n]+)", md, re.M).group(1).strip()
            self.karar = karar
            return f"Karar: {karar} · {', '.join(notlar)} hazır"
        self.calistir_adim("4", rapor)

        def ogrenme():
            t = self.ihale
            py("vt.py", "--vt", self.db, "ihale-kaydet", "--kod", self.kod, "--tarih", date.today().isoformat(),
               *(x for k, v in (("idare", t.get("idare")), ("konu", t.get("ad")), ("tur", t.get("tur")),
                                ("yaklasik", t.get("yaklasik")), ("karar", self.karar)) if v for x in (f"--{k}", str(v))))
            kayit = ["ihale"]
            for csv_ad, komut in (("metraj-hesap.csv", "metraj-yukle"), ("metraj.csv", "metraj-yukle"),
                                  ("pursantaj.csv", "pursantaj-yukle")):
                if (c / csv_ad).exists() and not (komut == "metraj-yukle" and "metraj" in kayit):
                    try:
                        py("vt.py", "--vt", self.db, komut, "--kod", self.kod, c / csv_ad)
                        kayit.append("metraj" if komut == "metraj-yukle" else "pursantaj")
                    except RuntimeError:
                        pass
            for d in self.dersler:
                py("vt.py", "--vt", self.db, "ders-ekle", "--metin", d["metin"], "--ajan", d["ajan"], "--kod", self.kod,
                   *(["--idare", idare] if idare else []))
            gecmis = self.sistem / "hafiza" / "ihale-gecmisi.md"
            if gecmis.parent.is_dir():
                with open(gecmis, "a", encoding="utf-8") as f:
                    f.write(f"- {date.today():%Y-%m-%d} {self.kod} | {t.get('idare') or '-'} | {t.get('ad') or '-'} | "
                            f"karar: {self.karar}\n")
            return f"Veritabanına yazıldı: {', '.join(kayit)}" + (f", {len(self.dersler)} ders" if self.dersler else "")
        self.calistir_adim("5", ogrenme)
        return "rapor_hazir"

    def profil_dolu(self) -> bool:
        """firma-profili.md'de en az bir alan doldurulmuş mu."""
        return bool(re.search(r"^\s*-\s*[^:\n]+:[ \t]*\S", self.hafiza("firma-profili.md"), re.M))

    def fiyat_ozeti(self, idare: str | None) -> str:
        with self.vt() as con:
            return vt.fiyat_ozeti(con, self.kod, idare)

    def gecmis_fiyat_ekle(self, yol: Path) -> int:
        """metraj-kiyas.csv'ye geçmiş ortalama birim fiyatı yazar (Excel 'Geçmiş Birim Fiyat (Ort.)')."""
        with open(yol, encoding="utf-8", newline="") as f:
            satirlar = list(csv.DictReader(f))
        with self.vt() as con:
            gecmis = vt.gecmis_fiyatlar(con, [r["poz_no"] for r in satirlar], self.kod)
        for r in satirlar:
            r["gecmis_fiyat"] = gecmis.get(r["poz_no"], "")
        alanlar = list(satirlar[0].keys()) if satirlar else ["poz_no", "tanim", "birim", "idare", "hesap",
                                                              "birim_fiyat", "gecmis_fiyat"]
        with open(yol, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=alanlar)
            w.writeheader()
            w.writerows(satirlar)
        return len(gecmis)

    def kisisel_hesap(self) -> str | None:
        """Aktif kişisel hesap kuralı varsa metraja uygular (07-kisisel-hesap.md)."""
        with self.vt() as con:
            n = con.execute("SELECT COUNT(*) FROM hesap_kurallari WHERE aktif=1").fetchone()[0]
        csv_ = next((self.calisma / f for f in ("metraj-hesap.csv", "metraj.csv") if (self.calisma / f).exists()), None)
        if not n or not csv_:
            return None
        try:
            return py("kisisel_hesap.py", csv_, "--vt", self.db).strip() or None
        except RuntimeError:
            return None

    @staticmethod
    def tablo_ozeti(dosya: Path, sozcuk: str, ad: str) -> str:
        satirlar = [s for s in oku(dosya).splitlines() if s.startswith("|")]
        n = sum(sozcuk.lower() in s.lower() for s in satirlar)
        return f"{max(len(satirlar) - 2, 0)} satır, {n} {ad}"


# --- Komut satırı -----------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alan", type=Path, help="çalışma alanı (varsayılan: Masaüstü/İhale Analiz)")
    sub = p.add_subparsers(dest="komut", required=True)
    s = sub.add_parser("calistir")
    s.add_argument("--kod", required=True)
    s.add_argument("--tur", choices=["on", "detay"])
    sub.add_parser("kuyruk")
    sub.add_parser("durum")
    s = sub.add_parser("anahtar")
    s.add_argument("--saglayici", required=True, choices=["anthropic", "openai"])
    a = p.parse_args()
    alan = (a.alan or takip.alan_dir()).expanduser().resolve()

    if a.komut == "durum":
        surucu, ad = yz_sec(alan)
        print(f"Yapay zekâ: {ad}" if surucu else f"Yapay zekâ bağlantısı yok: {ad}")
        return
    if a.komut == "anahtar":
        import getpass
        deger = getpass.getpass(f"{a.saglayici} API anahtarı (ekranda görünmez): ").strip()
        if not deger:
            sys.exit("Anahtar girilmedi")
        yz.anahtar_kaydet(a.saglayici, deger)
        print("Anahtar bilgisayarın şifre kasasına kaydedildi")
        return
    if a.komut == "kuyruk":
        con = takip.baglan(alan)
        try:
            kodlar = [r["kod"] for r in con.execute(
                "SELECT kod FROM takip WHERE durum='hesaplanacak' ORDER BY oncelik, eklenme")]
        finally:
            con.close()
        for kod in kodlar:
            print(f"{kod}: başlıyor")
            try:
                Motor(alan, kod).calistir()
                print(f"{kod}: bitti")
            except Exception as e:
                print(f"{kod}: {e}")
        if not kodlar:
            print("Kuyrukta ihale yok")
        return
    try:
        m = Motor(alan, a.kod, a.tur)
        if calisiyor(m.klasor):
            sys.exit(f"{m.kod}: analiz zaten sürüyor")
        m.calistir()
        print(f"{m.kod}: {'ön inceleme' if m.tur == 'on' else 'detaylı analiz'} bitti")
    except Durdur as e:
        sys.exit(f"Durdu: {e}")


if __name__ == "__main__":
    main()
