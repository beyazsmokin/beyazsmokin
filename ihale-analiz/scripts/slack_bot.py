#!/usr/bin/env python3
"""FAY ile Slack üzerinden doğal Türkçe konuşan ihale mühendisi botu.

Socket Mode ile çalışır; dışa açık sunucu gerekmez. FAY'ın bilgisayarında
panel.py'nin yanında ayrı süreç olarak başlatılır.

Araçlar (komut yok, sadece Türkçe konuşma):
  - Takibe al / takipten çıkar
  - Ön inceleme başlat / durum sorgula
  - Detaylı analiz başlat / durum sorgula
  - Takip listesi ve ajanda göster
  - EKAP dosyası indir (captcha FAY girer)

Token kurulumu (tek seferlik):
  python slack_bot.py kur --bot-token xoxb-... --app-token xapp-...

Çalıştırma:
  python slack_bot.py [--alan "C:/Users/.../Desktop/İhale Analiz"]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import threading
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
KASA_AD = "ihale-analiz-slack"

# ──────────────────────────────────────────────
# Token yönetimi
# ──────────────────────────────────────────────

def _token_oku(anahtar: str) -> str | None:
    if val := os.environ.get(anahtar):
        return val
    try:
        import keyring
        return keyring.get_password(KASA_AD, anahtar)
    except Exception:
        return None


def _token_yaz(anahtar: str, deger: str) -> None:
    import keyring
    keyring.set_password(KASA_AD, anahtar, deger)


# ──────────────────────────────────────────────
# Çalışma alanı ve betiğe erişim
# ──────────────────────────────────────────────

def _alan_bul() -> Path | None:
    """İhale Analiz klasörünü bul (önce config.yaml, sonra Desktop)."""
    # scripts/ ile aynı repodaki config.yaml'ı dene (kurulum öncesi geliştirme)
    cfg_yol = SCRIPTS.parent / "setup" / "workspace-template" / ".sistem" / "config.yaml"
    # Standart konum
    for aday in [
        Path.home() / "Desktop" / "İhale Analiz",
        Path.home() / "Masaüstü" / "İhale Analiz",
        Path.home() / "OneDrive" / "Desktop" / "İhale Analiz",
    ]:
        if (aday / ".sistem" / "config.yaml").exists():
            return aday
    return None


def _betik(alan: Path, ad: str, *args, capture=True, timeout=30) -> subprocess.CompletedProcess:
    """Belirtilen betiği alan/ dizininde çalıştır."""
    skill = alan / ".sistem" / "skill"
    betik_yolu = skill / "scripts" / ad
    cmd = [sys.executable, str(betik_yolu), *[str(a) for a in args]]
    kw: dict = {"cwd": str(alan), "encoding": "utf-8"}
    if capture:
        kw["capture_output"] = True
    return subprocess.run(cmd, timeout=timeout, **kw)


# ──────────────────────────────────────────────
# Araç fonksiyonları
# ──────────────────────────────────────────────

def _takip_listesi(alan: Path) -> str:
    r = _betik(alan, "takip.py", "liste")
    return (r.stdout or "").strip() or "Takip listesi boş."


def _ajanda(alan: Path) -> str:
    r = _betik(alan, "takip.py", "ajanda", "--gun", "30")
    return (r.stdout or "").strip() or "Ajandada yaklaşan etkinlik yok."


def _takibe_al(alan: Path, ikn: str, ad: str) -> str:
    r = _betik(alan, "takip.py", "ekle", "--kod", ikn, "--ad", ad)
    if r.returncode == 0:
        return f"✅ {ikn} ({ad}) takip listesine eklendi."
    return f"⚠️ Takibe alma hatası:\n{(r.stderr or r.stdout or '').strip()}"


def _takipten_cikar(alan: Path, ikn: str) -> str:
    r = _betik(alan, "takip_sitesi.py", "takip-birak", ikn)
    if r.returncode == 0:
        return f"✅ {ikn} takipten çıkarıldı."
    return f"⚠️ Hata:\n{(r.stderr or r.stdout or '').strip()}"


def _durum_oku(alan: Path, ikn: str) -> str:
    """İhale klasöründen analiz durumunu oku."""
    # IKN → klasör adı: "2026/1234567" → "2026-1234567"
    kod_temiz = ikn.replace("/", "-")
    # İhaleler altındaki klasörü bul
    ihaleler = alan / "İhaleler"
    klasorler = list(ihaleler.glob(f"{kod_temiz}*")) if ihaleler.exists() else []
    if not klasorler:
        return f"⚠️ {ikn} için klasör bulunamadı."
    ihale_kl = klasorler[0]
    durum_dosya = ihale_kl / "calisma" / "durum.json"
    if not durum_dosya.exists():
        return f"ℹ️ {ikn} için analiz henüz başlamadı."
    try:
        d = json.loads(durum_dosya.read_text(encoding="utf-8"))
    except Exception:
        return f"⚠️ durum.json okunamadı."
    tur = d.get("tur", "?")
    asamalar = d.get("adimlar", {})
    bitti = sum(1 for v in asamalar.values() if v.get("durum") == "bitti")
    toplam = len(asamalar)
    son = d.get("son_guncelleme", "")
    return (
        f"📊 *{ikn}* — {tur} analizi\n"
        f"İlerleme: {bitti}/{toplam} adım\n"
        f"Son güncelleme: {son}"
    )


def _analiz_baslat(alan: Path, ikn: str, tur: str, say: object) -> None:
    """Arka planda motor.py çalıştır, tamamlandığında say üzerinden bildir."""
    def _calistir():
        try:
            r = _betik(alan, "motor.py", "calistir", "--kod", ikn, "--tur", tur,
                       capture=False, timeout=120 * 60)
            sonuc = "✅ Analiz tamamlandı." if r.returncode == 0 else "⚠️ Analiz hata verdi."
        except subprocess.TimeoutExpired:
            sonuc = "⏰ Analiz 2 saati aştı, kontrol edin."
        except Exception as e:
            sonuc = f"⚠️ Motor başlatılamadı: {e}"
        say(f"*{ikn}* — {sonuc}")
    threading.Thread(target=_calistir, daemon=True).start()


# ──────────────────────────────────────────────
# NLU: Anthropic API ile niyet tanıma
# ──────────────────────────────────────────────

_ARAC_SEMASI = [
    {
        "name": "takibe_al",
        "description": "Bir ihaleyi takip listesine ekle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ikn": {"type": "string", "description": "İhale kayıt numarası, örn. 2026/1234567"},
                "ad":  {"type": "string", "description": "İhale adı veya kısa açıklaması"},
            },
            "required": ["ikn", "ad"],
        },
    },
    {
        "name": "takipten_cikar",
        "description": "Bir ihaleyi takip listesinden çıkar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ikn": {"type": "string", "description": "İhale kayıt numarası"},
            },
            "required": ["ikn"],
        },
    },
    {
        "name": "on_inceleme",
        "description": "Bir ihale için ön inceleme başlat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ikn": {"type": "string", "description": "İhale kayıt numarası"},
            },
            "required": ["ikn"],
        },
    },
    {
        "name": "detayli_analiz",
        "description": "Bir ihale için detaylı analiz başlat (kaynak klasörünün dolu olması gerekir).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ikn": {"type": "string", "description": "İhale kayıt numarası"},
            },
            "required": ["ikn"],
        },
    },
    {
        "name": "durum_sor",
        "description": "Bir ihale için mevcut analiz durumunu sorgula.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ikn": {"type": "string", "description": "İhale kayıt numarası"},
            },
            "required": ["ikn"],
        },
    },
    {
        "name": "liste_goster",
        "description": "Takip listesindeki ihaleleri göster.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "ajanda_goster",
        "description": "Yaklaşan ihale tarihlerini ve etkinlikleri göster.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_SİSTEM = textwrap.dedent("""
    Sen FAY'ın ihale mühendisi asistanısın. FAY, kamu ihalelerini takip eden bir inşaat firmasının yöneticisi.
    Onunla Türkçe konuşuyorsun — samimi, doğrudan ve profesyonel.

    Eğer FAY bir ihale işlemi istiyorsa (takibe al, analiz başlat, durum sor, liste göster, ajanda göster),
    uygun aracı çağır. Eğer sohbet ediyorsa ya da bilgi soruyorsa, doğrudan cevap ver; araç çağırma.

    İKN formatı genellikle "2026/1234567" ya da "2026-1234567" şeklindedir.
    İKN yoksa ve ihale adı/konusu varsa, "ad" alanına onu yaz ve ikn alanını boş bırakma —
    kullanıcıdan IKN'yi sor.
""").strip()


def _yz_karar(mesajlar: list[dict], anahtar: str) -> tuple[str | None, dict | None]:
    """
    Anthropic API çağrısı.
    Döndürür: (metin_cevap, arac_cagrisi)  — biri None olur.
    arac_cagrisi: {"name": ..., "input": {...}}
    """
    try:
        import anthropic
    except ImportError:
        return ("⚠️ `anthropic` paketi kurulu değil. `pip install anthropic` çalıştırın.", None)

    client = anthropic.Anthropic(api_key=anahtar)
    yanit = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=512,
        system=_SİSTEM,
        tools=_ARAC_SEMASI,  # type: ignore[arg-type]
        messages=mesajlar,
    )
    for blok in yanit.content:
        if blok.type == "tool_use":
            return (None, {"name": blok.name, "input": blok.input})
    metin = " ".join(
        b.text for b in yanit.content if getattr(b, "type", "") == "text"
    ).strip()
    return (metin or "…", None)


# ──────────────────────────────────────────────
# Araç çağrısını gerçekleştir
# ──────────────────────────────────────────────

def _arac_calistir(ad: str, args: dict, alan: Path, bildir) -> str:
    ikn = args.get("ikn", "")
    ihale_ad = args.get("ad", "")

    if ad == "takibe_al":
        if not ikn or not ihale_ad:
            return "❓ İhale kayıt numarasını (IKN) ve adını belirtir misiniz?"
        return _takibe_al(alan, ikn, ihale_ad)

    if ad == "takipten_cikar":
        if not ikn:
            return "❓ Hangi ihaleyi (IKN) takipten çıkarmak istiyorsunuz?"
        return _takipten_cikar(alan, ikn)

    if ad == "on_inceleme":
        if not ikn:
            return "❓ Ön inceleme için IKN'yi belirtir misiniz?"
        bildir(f"⏳ *{ikn}* ön incelemesi başlatılıyor…")
        _analiz_baslat(alan, ikn, "on", bildir)
        return f"🔍 *{ikn}* ön incelemesi arka planda çalışıyor. Tamamlanınca haber vereceğim."

    if ad == "detayli_analiz":
        if not ikn:
            return "❓ Detaylı analiz için IKN'yi belirtir misiniz?"
        bildir(f"⏳ *{ikn}* detaylı analizi başlatılıyor… (kaynak/ klasörünün dolu olması gerekir)")
        _analiz_baslat(alan, ikn, "detay", bildir)
        return f"🔬 *{ikn}* detaylı analizi arka planda çalışıyor. Tamamlanınca haber vereceğim."

    if ad == "durum_sor":
        if not ikn:
            return "❓ Hangi ihalenin (IKN) durumunu sormak istiyorsunuz?"
        return _durum_oku(alan, ikn)

    if ad == "liste_goster":
        return _takip_listesi(alan)

    if ad == "ajanda_goster":
        return _ajanda(alan)

    return f"⚠️ Bilinmeyen araç: {ad}"


# ──────────────────────────────────────────────
# Sohbet geçmişi
# ──────────────────────────────────────────────

class _Gecmis:
    """Kanal başına son N mesajı saklar."""

    def __init__(self, limit: int = 10):
        self._limit = limit
        self._kanal: dict[str, list[dict]] = {}

    def ekle(self, kanal: str, rol: str, icerik: str) -> None:
        lst = self._kanal.setdefault(kanal, [])
        lst.append({"role": rol, "content": icerik})
        if len(lst) > self._limit * 2:
            self._kanal[kanal] = lst[-self._limit * 2:]

    def al(self, kanal: str) -> list[dict]:
        return self._kanal.get(kanal, [])


# ──────────────────────────────────────────────
# Slack Bolt uygulama
# ──────────────────────────────────────────────

def _bot_baslat(alan: Path) -> None:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        sys.exit(
            "slack-bolt kurulu değil. Önce:\n"
            "  pip install slack-bolt\n"
            "çalıştırın."
        )

    bot_token = _token_oku("SLACK_BOT_TOKEN")
    app_token = _token_oku("SLACK_APP_TOKEN")
    api_key   = _token_oku("ANTHROPIC_API_KEY") or _token_oku("OPENAI_API_KEY")

    if not bot_token:
        sys.exit(
            "SLACK_BOT_TOKEN bulunamadı.\n"
            "  python slack_bot.py kur --bot-token xoxb-... --app-token xapp-..."
        )
    if not app_token:
        sys.exit(
            "SLACK_APP_TOKEN bulunamadı.\n"
            "  python slack_bot.py kur --bot-token xoxb-... --app-token xapp-..."
        )
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY bulunamadı.\n"
            "  motor.py anahtar --saglayici anthropic\n"
            "veya ortam değişkeni olarak set edin."
        )

    app = App(token=bot_token)
    gecmis = _Gecmis()

    @app.event("app_mention")
    def mention_handler(event, say):  # noqa: ANN001
        _isle(event, say, app, alan, gecmis, api_key)

    @app.event("message")
    def mesaj_handler(event, say):  # noqa: ANN001
        # DM'lerde (channel_type=im) ve @mention olmayan direkt mesajlarda da çalışsın
        if event.get("channel_type") == "im":
            _isle(event, say, app, alan, gecmis, api_key)

    print(f"İhale mühendisi botu başlatılıyor… (alan: {alan})")
    handler = SocketModeHandler(app, app_token)
    handler.start()


def _isle(event: dict, say, app, alan: Path, gecmis: _Gecmis, api_key: str) -> None:
    kanal = event.get("channel", "")
    metin = event.get("text", "")
    # Bot'un kendi mesajlarını yoksay
    if event.get("bot_id"):
        return
    # @mention etiketini kaldır
    metin = re.sub(r"<@[A-Z0-9]+>", "", metin).strip()
    if not metin:
        return

    gecmis.ekle(kanal, "user", metin)

    def bildir(msg: str) -> None:
        app.client.chat_postMessage(channel=kanal, text=msg)

    try:
        metin_cevap, arac = _yz_karar(gecmis.al(kanal), api_key)
    except Exception as e:
        say(f"⚠️ YZ hatası: {e}")
        return

    if arac:
        cevap = _arac_calistir(arac["name"], arac["input"], alan, bildir)
    else:
        cevap = metin_cevap or "…"

    gecmis.ekle(kanal, "assistant", cevap)
    say(cevap)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="İhale mühendisi Slack botu")
    sub = ap.add_subparsers(dest="komut")

    # kur
    kur_p = sub.add_parser("kur", help="Token'ları kaydet (tek seferlik)")
    kur_p.add_argument("--bot-token", required=True, help="xoxb-… OAuth Bot Token")
    kur_p.add_argument("--app-token", required=True, help="xapp-… App-Level Token")

    # calistir (varsayılan)
    ap.add_argument("--alan", help="İhale Analiz klasörü yolu")

    args = ap.parse_args()

    if args.komut == "kur":
        _token_yaz("SLACK_BOT_TOKEN", args.bot_token)
        _token_yaz("SLACK_APP_TOKEN", args.app_token)
        print("✅ Token'lar kaydedildi.")
        return

    # Alan belirle
    if getattr(args, "alan", None):
        alan = Path(args.alan)
    else:
        alan = _alan_bul()
    if not alan or not alan.exists():
        sys.exit(
            "İhale Analiz klasörü bulunamadı.\n"
            "  python slack_bot.py --alan 'C:/Users/.../Desktop/İhale Analiz'"
        )

    _bot_baslat(alan)


if __name__ == "__main__":
    main()
