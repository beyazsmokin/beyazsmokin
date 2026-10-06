#!/usr/bin/env python3
"""Ajanları çalıştıran yapay zekâ bağlantısı (panelden başlatılan analiz için).

Panel "Analizi başlat" dediğinde `motor.py` her ajanın talimatını (agents/*.md) ve girdilerini
buradaki bağlantıyla bir yapay zekâya verir, cevabı ajanın çıktı dosyasına yazar.

Bağlantılar (`config.yaml` > analiz.yz; `otomatik` bu sırayla ilk bulunanı seçer):
  claude-kod  Bilgisayarda Claude Code kuruluysa (`claude` komutu). Hesabınızla çalışır,
              anahtar gerekmez; ajan kaynak dosyaları (PDF, görsel) kendisi de okuyabilir.
  anthropic   Claude API. `pip install anthropic` ve anahtar: ANTHROPIC_API_KEY ortam
              değişkeni ya da `motor.py anahtar --saglayici anthropic` (şifre kasasına yazar).
  openai      OpenAI uyumlu her sunucu: ChatGPT (api.openai.com), Hermes / yerel modeller
              (Ollama, LM Studio: analiz.yz_adres: http://localhost:11434/v1). analiz.yz_model şart.
  yok         Yapay zekâ çalıştırılmaz; ajan adımları sohbetteki asistana bırakılır.

API anahtarı hiçbir dosyaya, loga ya da çıktıya yazılmaz (K-10.1).
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

KASA = "ihale-analiz"
CLAUDE_MODEL = "claude-opus-5-5"


class YzHatasi(RuntimeError):
    pass


def anahtar(saglayici: str) -> str | None:
    ortam = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}[saglayici]
    if os.environ.get(ortam):
        return os.environ[ortam]
    try:
        import keyring
        return keyring.get_password(KASA, saglayici)
    except Exception:
        return None


def anahtar_kaydet(saglayici: str, deger: str) -> None:
    import keyring
    keyring.set_password(KASA, saglayici, deger)


class Surucu:
    ad = ""
    dosya_okur = False  # True ise ajan kaynak klasöründeki dosyaları kendisi açabilir

    def sor(self, sistem: str, istek: str, klasor) -> str:
        raise NotImplementedError


class ClaudeKod(Surucu):
    """Claude Code'u başsız (`claude -p`) çalıştırır; yalnızca okuma araçlarına izin verilir."""
    ad = "Claude Code"
    dosya_okur = True

    def __init__(self, komut: str, model: str | None):
        self.komut, self.model = komut, model

    def sor(self, sistem, istek, klasor):
        # talimat da girdiyle birlikte stdin'den verilir: Windows'ta claude.cmd çok satırlı
        # komut satırı argümanını bozar
        istek = f"<talimat>\n{sistem}\n</talimat>\n\n{istek}"
        argv = [self.komut, "-p", "--output-format", "text",
                "--allowedTools", "Read,Glob,Grep", "--disallowedTools", "Bash,Write,Edit,NotebookEdit"]
        if self.model:
            argv += ["--model", self.model]
        try:
            r = subprocess.run(argv, input=istek, capture_output=True, text=True, encoding="utf-8",
                               cwd=klasor, timeout=45 * 60,
                               **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
        except subprocess.TimeoutExpired:
            raise YzHatasi("Claude Code 45 dakikada cevap vermedi")
        except OSError as e:
            raise YzHatasi(f"Claude Code çalıştırılamadı: {e}")
        if r.returncode or not r.stdout.strip():
            hata = (r.stderr or r.stdout or "").strip().splitlines()
            raise YzHatasi(f"Claude Code hata verdi: {hata[-1] if hata else r.returncode}")
        return r.stdout


class Anthropic(Surucu):
    ad = "Claude API"

    def __init__(self, model: str | None):
        import anthropic  # noqa: F401  (kurulu değilse seçilmez)
        self.model = model or CLAUDE_MODEL

    def sor(self, sistem, istek, klasor):
        import anthropic
        client = anthropic.Anthropic(api_key=anahtar("anthropic"), max_retries=3)
        try:
            with client.beta.messages.stream(
                model=self.model, max_tokens=64000, system=sistem,
                messages=[{"role": "user", "content": istek}],
                thinking={"type": "adaptive"}, output_config={"effort": "high"},
                betas=["server-side-fallback-2026-07-01"], extra_body={"fallbacks": "default"},
            ) as akis:
                m = akis.get_final_message()
        except anthropic.AuthenticationError:
            raise YzHatasi("Claude API anahtarı geçersiz (`motor.py anahtar --saglayici anthropic`)")
        except anthropic.RateLimitError:
            raise YzHatasi("Claude API kullanım sınırına takıldı; biraz sonra yeniden deneyin")
        except anthropic.APIStatusError as e:
            raise YzHatasi(f"Claude API hatası ({e.status_code}): {e.message}")
        except anthropic.APIConnectionError:
            raise YzHatasi("Claude API'ye bağlanılamadı (internet bağlantısını kontrol edin)")
        if m.stop_reason == "refusal":
            raise YzHatasi("Claude bu isteği yanıtlamadı (güvenlik reddi)")
        metin = "".join(b.text for b in m.content if b.type == "text")
        if m.stop_reason == "max_tokens":
            metin += "\n\n> UYARI: cevap uzunluk sınırında kesildi.\n"
        return metin


class OpenAIUyumlu(Surucu):
    """ChatGPT ya da OpenAI uyumlu sunucu (Hermes için Ollama / LM Studio)."""

    def __init__(self, adres: str, model: str):
        self.adres, self.model = adres.rstrip("/"), model
        self.ad = "ChatGPT" if "openai.com" in adres else f"{model} ({adres})"

    def sor(self, sistem, istek, klasor):
        govde = json.dumps({"model": self.model, "messages": [
            {"role": "system", "content": sistem}, {"role": "user", "content": istek}]}).encode()
        bas = {"Content-Type": "application/json"}
        k = anahtar("openai")
        if k:
            bas["Authorization"] = f"Bearer {k}"
        req = urllib.request.Request(f"{self.adres}/chat/completions", govde, bas)
        try:
            with urllib.request.urlopen(req, timeout=45 * 60) as r:
                veri = json.load(r)
        except urllib.error.HTTPError as e:
            raise YzHatasi(f"{self.ad} hatası ({e.code}): {e.read()[:300].decode('utf-8', 'replace')}")
        except OSError as e:
            raise YzHatasi(f"{self.ad} sunucusuna bağlanılamadı: {e}")
        try:
            return veri["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise YzHatasi(f"{self.ad} beklenmeyen cevap verdi")


def sec(ayarlar: dict) -> tuple[Surucu | None, str]:
    """(sürücü, açıklama) döner. Sürücü yoksa açıklama nedenini söyler."""
    tercih = (ayarlar.get("yz") or "otomatik").lower()
    model = ayarlar.get("yz_model") or None
    adres = ayarlar.get("yz_adres") or None
    if tercih == "yok":
        return None, "Yapay zekâ bağlantısı kapalı (config.yaml > analiz.yz: yok)"
    nedenler = []
    if tercih in ("otomatik", "claude-kod"):
        komut = shutil.which("claude")
        if komut:
            return ClaudeKod(komut, model), "Claude Code"
        nedenler.append("Claude Code kurulu değil")
    if tercih in ("otomatik", "anthropic"):
        if anahtar("anthropic"):
            try:
                return Anthropic(model), "Claude API"
            except ImportError:
                nedenler.append("Claude API için `pip install anthropic` gerekli")
        else:
            nedenler.append("Claude API anahtarı yok")
    if tercih in ("otomatik", "openai"):
        if adres or anahtar("openai"):
            if model:
                s = OpenAIUyumlu(adres or "https://api.openai.com/v1", model)
                return s, s.ad
            nedenler.append("OpenAI uyumlu bağlantı için analiz.yz_model yazılmalı")
        elif tercih == "openai":
            nedenler.append("OpenAI anahtarı ya da analiz.yz_adres yok")
    return None, "; ".join(nedenler) or f"Bilinmeyen bağlantı: {tercih}"
