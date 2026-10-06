"""Panelin bildirim alanı (gizli simgeler) simgesi, Windows bildirimleri ve arka plan izleyicisi.

Panel penceresi kapatılınca sunucu çalışmayı sürdürür: simge görev çubuğunun bildirim
alanında durur, takip ve hesaplar arka planda devam eder. Simgeye çift tıklamak paneli açar.

Bildirim gönderilen olaylar (her biri bir kez):
  - takip edilen ihalenin sonucu sitede göründü (kazanan bilgisi geldi),
  - ihalenin detaylı analizi bitti, rapor hazır,
  - ihale günü yarın ya da bugün,
  - analiz bir adımda hata verdi.

Bildirime tıklanınca panel açılır; sonuç bildiriminde sitedeki sonuç panelde pencere olarak,
diğerlerinde ilgili ihale gösterilir.

Gerekli: pip install pystray pillow win11toast. Yoksa panel simgesiz çalışır, bildirimler panel
açıkken tarayıcı bildirimiyle gösterilir.
"""
import json
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import takip

IZLEME_SN = 60
SITE_IZLEME_SN = 30 * 60


class Tepsi:
    def __init__(self, alan: Path, adres: str, ac, kapat, goster=None):
        self.alan = alan
        self.adres = adres
        self.ac = ac          # paneli açar (tek pencere)
        self.kapat = kapat    # sunucuyu durdurur
        self.goster = goster  # bildirime tıklanınca: paneli açar ve ilgili pencereyi gösterir
        self.simge = None
        self.kayit = alan / ".sistem" / "bildirilenler.json"

    # --- Simge ------------------------------------------------------------------------
    def baslat(self) -> bool:
        try:
            import pystray
            from PIL import Image
        except ImportError:
            return False
        resim = Image.open(Path(__file__).resolve().parent.parent / "assets" / "ikon.png")
        menu = pystray.Menu(pystray.MenuItem("Paneli aç", lambda *_: self.ac(), default=True),
                            pystray.MenuItem("Paneli tamamen kapat", lambda *_: self._cik()))
        self.simge = pystray.Icon("ihale-analiz", resim, "İhale Analiz", menu)
        threading.Thread(target=self.simge.run, daemon=True).start()
        threading.Thread(target=self._izle, daemon=True).start()
        return True

    def _cik(self):
        if self.simge:
            self.simge.stop()
        self.kapat()

    def bildir(self, baslik: str, metin: str, hedef: dict | None = None) -> None:
        """Windows bildirimi. Tıklanınca panel açılır ve `hedef` panelde gösterilir."""
        try:
            from win11toast import toast
        except ImportError:
            toast = None
        if toast:
            ikon = Path(__file__).resolve().parent.parent / "assets" / "ikon.png"
            tikla = (lambda *_: self.goster(hedef)) if (self.goster and hedef) else (lambda *_: self.ac())
            threading.Thread(target=lambda: toast(baslik, metin, icon=str(ikon), on_click=tikla),
                             daemon=True).start()
        elif self.simge:
            try:
                self.simge.notify(metin, baslik)
            except Exception:
                pass

    # --- Bir kez bildirilenler ----------------------------------------------------------
    def _oku(self) -> set:
        try:
            return set(json.loads(self.kayit.read_text(encoding="utf-8")))
        except Exception:
            return set()

    def _bir_kez(self, anahtar: str, baslik: str, metin: str, hedef: dict | None = None) -> None:
        gorulen = self._oku()
        if anahtar in gorulen:
            return
        gorulen.add(anahtar)
        self.kayit.write_text(json.dumps(sorted(gorulen)[-2000:], ensure_ascii=False), encoding="utf-8")
        self.bildir(baslik, metin, hedef)

    # --- İzleyici ------------------------------------------------------------------------
    def _izle(self):
        son_site = 0.0
        while True:
            try:
                self._yerel_kontrol()
                if time.time() - son_site > SITE_IZLEME_SN:
                    son_site = time.time()
                    self._site_kontrol()
            except Exception:
                pass
            time.sleep(IZLEME_SN)

    def _yerel_kontrol(self):
        con = takip.baglan(self.alan)
        try:
            ihaleler = takip.liste(con)
        finally:
            con.close()
        bugun = date.today()
        for t in ihaleler:
            ad = t["ad"] or t["kod"]
            if t["durum"] == "rapor_hazir":
                self._bir_kez(f"rapor:{t['kod']}", "Analiz bitti", f"{ad}: rapor hazır.",
                              {"tur": "ihale", "kod": t["kod"], "sekme": "rapor"})
            s = takip.surec(takip.ihale_klasoru(self.alan, t["kod"]))
            for a in s["adimlar"]:
                if a["durum"] == "hata":
                    self._bir_kez(f"hata:{t['kod']}:{a['adim']}", "Analizde hata", f"{ad}: {a['ad']} adımı hata verdi.",
                                  {"tur": "ihale", "kod": t["kod"], "sekme": "surec"})
            if t["ihale_tarihi"] and t["durum"] not in takip.KAPALI:
                gun = date.fromisoformat(t["ihale_tarihi"][:10])
                saat = t["ihale_tarihi"][11:16]
                hedef = {"tur": "ihale", "kod": t["kod"], "sekme": "genel"}
                if gun == bugun + timedelta(days=1):
                    self._bir_kez(f"yarin:{t['kod']}:{gun}", "İhale yarın", f"{ad} · {saat}", hedef)
                elif gun == bugun:
                    self._bir_kez(f"bugun:{t['kod']}:{gun}", "İhale bugün", f"{ad} · {saat}", hedef)

    def _site_kontrol(self):
        """Takip edilen ihalelerin sonucu sitede yayımlandıysa bildirir."""
        import takip_sitesi
        sistem = self.alan / ".sistem"
        if not takip_sitesi.site_kayitli(sistem):
            return
        con = takip.baglan(self.alan)
        try:
            izlenen = {t["ikn"] for t in takip.liste(con) if t["ikn"] and t["durum"] not in takip.KAPALI}
        finally:
            con.close()
        if not izlenen:
            return
        for r in takip_sitesi.sonuclar(sistem, gun=7):
            if r["ikn"] in izlenen:
                self._bir_kez(f"sonuc:{r['ikn']}", "İhale sonucu geldi",
                              f"{r['ad']} ({r['ikn']}): {r['kazanan'] or 'sonuç yayımlandı'}", {"tur": "sonuc", "ilan": r})
