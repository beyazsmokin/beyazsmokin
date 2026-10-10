# İhale Mühendisi Slack Botu — Kurulum

Botu bir kez kurmanız yeterli; sonra bilgisayarınızda arka planda çalışır.

---

## 1. Slack Uygulamasını Oluşturun (5 dakika)

1. https://api.slack.com/apps adresine gidin
2. **Create New App** → **From an app manifest** seçin
3. Workspace'inizi seçin
4. `setup/slack-app-manifest.json` dosyasının içeriğini YAML bölümüne yapıştırın  
   *(JSON olarak yapıştırırsanız JSON sekmesini kullanın)*
5. **Create** → **Install to Workspace** → **Allow**

---

## 2. Token'ları Alın

### Bot Token (xoxb-…)
**OAuth & Permissions** sayfasından **Bot User OAuth Token**'ı kopyalayın.

### App-Level Token (xapp-…)
**Basic Information** → **App-Level Tokens** → **Generate Token and Scopes**  
Scope olarak `connections:write` ekleyin → oluşturulan token'ı kopyalayın.

---

## 3. Python Paketini Kurun

```cmd
pip install slack-bolt anthropic
```

---

## 4. Token'ları Kaydedin (tek seferlik)

```cmd
cd "Desktop\İhale Analiz\.sistem\skill"
python scripts\slack_bot.py kur --bot-token xoxb-... --app-token xapp-...
```

Token'lar Windows Kimlik Bilgileri Yöneticisi'ne kaydedilir; şifre dosyada tutulmaz.

---

## 5. Botu Başlatın

```cmd
python scripts\slack_bot.py
```

Panel.lnk ile aynı şekilde başlangıca eklemek için:

```cmd
python scripts\panel.py baslangic --ac
```

> `panel.py` başlarken `slack_bot.py`'yi de otomatik başlatır (bir sonraki PR'da eklenecek).

---

## 6. Slack'te Botu Ekleyin

Konuşmak istediğiniz kanalda:  
`/invite @ihale-muhendisi`

veya doğrudan DM açın: **İhale Mühendisi** → **Send Message**

---

## Konuşma Örnekleri

```
2026/1771435 nolu ihaleyi takibe al, Anaokulu onarımı
```
```
Kaç ihale takip ediyorum?
```
```
Ajanda ne diyor bu hafta?
```
```
2026/1771435 ön incelemesini başlat
```
```
Şu anki analizin durumu nedir?
```

---

## Sorun Giderme

| Hata | Çözüm |
|------|-------|
| `slack-bolt kurulu değil` | `pip install slack-bolt` |
| `SLACK_BOT_TOKEN bulunamadı` | Adım 4'ü tekrarlayın |
| `ANTHROPIC_API_KEY bulunamadı` | `motor.py anahtar --saglayici anthropic` çalıştırın |
| `İhale Analiz klasörü bulunamadı` | `python slack_bot.py --alan "C:\Users\...\Desktop\İhale Analiz"` |
