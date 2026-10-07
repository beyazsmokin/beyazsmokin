"""Kullanıcının kendi ihale motoruyla (Ihale-Ofisi) ön inceleme hesapları.

Bilgisayarda Ihale-Ofisi kuruluysa ön inceleme onun `ihale_akisi.py` hattını çağırır:
ilan sayfasındaki keşif ve FDU tablosu → güvenilir birim fiyat arşiviyle eşleştirme →
tersine mühendislikle tahmini yaklaşık maliyet → idarenin geçmişinden katılımcı tahmini →
Monte Carlo sınır değer bandı. İhale onun veritabanında yoksa önce kendi tarama ve
ayrıştırma betikleri (scraper.py, parser.py) çalıştırılır.

Yer: config.yaml > analiz.ofis_yolu; boşsa Masaüstü/Projeler/Ihale-Ofisi denenir.
Kurulu değilse ön inceleme bu bölümü atlar (başka kullanıcılarda olduğu gibi).
"""
import json
import subprocess
import sys
from pathlib import Path


def bul(yol: str | None = None) -> Path | None:
    adaylar = [Path(yol).expanduser()] if yol else []
    adaylar.append(Path.home() / "Desktop" / "Projeler" / "Ihale-Ofisi")
    try:
        import init_workspace
        adaylar.append(init_workspace.desktop_dir() / "Projeler" / "Ihale-Ofisi")
    except Exception:
        pass
    return next((p for p in adaylar if (p / "ihale_akisi.py").is_file()), None)


def _calistir(kok: Path, *args, zaman: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, args)], cwd=kok, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=zaman,
                          env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                          **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))


def _akis(kok: Path, ikn: str) -> dict | None:
    r = _calistir(kok, "ihale_akisi.py", ikn, "--json")
    for satir in reversed((r.stdout or "").splitlines()):
        if satir.startswith("{"):
            try:
                return json.loads(satir)
            except json.JSONDecodeError:
                return None
    return None


def on_inceleme(ikn: str, site_id: str | None = None, yol: str | None = None, bildir=lambda m: None) -> dict | None:
    """Ihale-Ofisi ön inceleme sonucu (dict) ya da kurulu değilse None. Hata olursa {"hata": ...}."""
    kok = bul(yol)
    if not kok:
        return None
    try:
        sonuc = _akis(kok, ikn)
        if sonuc is None or not (sonuc.get("durum") or {}).get("kesif_kalem"):
            # ihale onun veritabanında yok ya da keşfi ayrıştırılmamış: kendi betikleriyle tamamla
            bildir("İhale Ofisi veritabanı güncelleniyor")
            if sonuc is None:
                _calistir(kok, "scraper.py", "--gun", "14", "--tur", "YAPIM", zaman=900)
            for _ in range(2):  # ilk çalıştırma ilan sayfasını arşivler, ikincisi ayrıştırır
                if not site_id:
                    break
                _calistir(kok, "parser.py", "--ih", site_id, zaman=600)
                sonuc = _akis(kok, ikn) or sonuc
                if sonuc and (sonuc.get("durum") or {}).get("kesif_kalem"):
                    break
        if sonuc is None:
            return {"hata": "İhale Ofisi bu ihaleyi bulamadı ya da keşfini ayrıştıramadı (yalnızca yapım işleri)."}
        sonuc["kaynak"] = str(kok)
        return sonuc
    except subprocess.TimeoutExpired:
        return {"hata": "İhale Ofisi zamanında yanıt vermedi."}
    except OSError as e:
        return {"hata": f"İhale Ofisi çalıştırılamadı: {e}"}


def _tl(v) -> str:
    try:
        return f"{float(v):,.0f} ₺".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def md(o: dict) -> list[str]:
    """Ön inceleme raporuna eklenecek Markdown bölümü."""
    if o.get("hata"):
        return ["\n## Yaklaşık maliyet ve sınır değer (İhale Ofisi)\n", f"Hesaplanamadı: {o['hata']}"]
    d, sim = o.get("durum") or {}, o.get("simulasyon") or {}
    ym = o.get("ym_gercek")
    satir = [
        ("Yaklaşık maliyet", f"{_tl(ym)} (RESMİ, sonuçtan)" if ym else
         f"{_tl(o.get('ym_tahmini'))} (TAHMİN; birim fiyat arşivi, eşleşme {o.get('eslesme')})"),
        ("Keşif / FDU", f"{d.get('kesif_kalem', 0)} kalem · FDU {'var' if d.get('fdu_var') else 'yok'}"),
        ("Gerçek sınır değer", f"{_tl(o.get('sd_gercek'))} · N={o.get('n')}" if o.get("sd_gercek") else None),
        ("Katılımcı tahmini", f"{sim.get('katilimci_tahmin')} (band {sim.get('band', [None, None])[0]}–"
                              f"{sim.get('band', [None, None])[1]})" if sim.get("katilimci_tahmin") else None),
        ("Sınır değer (Monte Carlo)", f"medyan {_tl(sim.get('sd_medyan'))} · p10–p90 {_tl((sim.get('sd_band') or [None])[0])}"
                                      f" – {_tl((sim.get('sd_band') or [None, None])[1])}" if sim.get("sd_medyan") else None),
        ("Kazanan tenzilat ortalaması", f"%{sim.get('kazanan_tenzilat')}" if sim.get("kazanan_tenzilat") else None),
    ]
    out = ["\n## Yaklaşık maliyet ve sınır değer (İhale Ofisi)\n", "| Alan | Değer |", "|---|---|",
           *[f"| {a} | {v} |" for a, v in satir if v]]
    kalemler = o.get("en_buyuk_5") or []
    if kalemler:
        out += ["\n### En büyük 5 kalem (tahmini tutar)\n", "| Poz | Kalem | Miktar | Birim fiyat | Tutar | Dayanak |",
                "|---|---|---:|---:|---:|---|"]
        for k in kalemler:
            out.append(f"| {k.get('poz_no')} | {(k.get('poz_adi') or '')[:70]} | {k.get('miktar')} {k.get('birim') or ''} | "
                       f"{_tl(k.get('ym_bf'))} | {_tl(k.get('tutar'))} | {k.get('yontem') or 'eşleşme yok'} |")
    out.append("\n_Hesap: İhale Ofisi `ihale_akisi.py` (keşif + FDU → birim fiyat arşivi → tahmini YM → "
               "katılımcı tahmini → Monte Carlo SD). Tahminler TAHMİN etiketlidir._")
    return out


# --- İhale Ofisim (ofis paketi): detaylı analiz ---------------------------------------------

def ofisim_bul(yol: str | None = None) -> Path | None:
    """İhale Ofisim deposu: config analiz.ofisim_yolu ya da Masaüstü/Projeler/ihale-ofisim."""
    adaylar = [Path(yol).expanduser()] if yol else []
    adaylar.append(Path.home() / "Desktop" / "Projeler" / "ihale-ofisim")
    try:
        import init_workspace
        adaylar.append(init_workspace.desktop_dir() / "Projeler" / "ihale-ofisim")
    except Exception:
        pass
    return next((p for p in adaylar if (p / "ofis" / "detay.py").is_file()), None)


def detay(kok: Path, ikn: str, dosya: Path, cikti: Path, is_adi: str = "", zaman: int = 3600) -> dict:
    """`python -m ofis detay` çalıştırır: doküman alımı, sözleşme türü, teklif cetveli, miktar
    denetimi, çelişki taraması, yaklaşık maliyet, pafta ve proje metrajı, denetim; PDF rapor ve
    teklif Excel'i üretir. Dönüş: {"cikti": metin, "adimlar": [(işaret, ad, mesaj)], "pdf", "excel"}."""
    import re
    cikti.mkdir(parents=True, exist_ok=True)
    r = _calistir(kok, "-m", "ofis", "detay", ikn, dosya, "--cikti", cikti,
                  *(["--is-adi", is_adi] if is_adi else []), zaman=zaman)
    metin = (r.stdout or "") + (("\n" + r.stderr) if r.returncode and r.stderr else "")
    adimlar = [(m.group(1), m.group(2).strip(), m.group(3).strip())
               for m in re.finditer(r"^ ([+\-!x]) (\S.*?)\s{2,}(\S.*)$", metin, re.M)]
    yol = lambda etiket: (re.search(rf"^{etiket}\s*:\s*(.+)$", metin, re.M) or [None, None])[1]
    return {"cikti": metin, "adimlar": adimlar, "kod": r.returncode,
            "pdf": yol("Rapor"), "excel": yol("Excel")}
