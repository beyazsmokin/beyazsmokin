# İhale Analiz Skill — Aktarım Belgesi

> Bu dosya başka bir YZ ile projeye devam edebilmek için hazırlanmıştır.
> Okuyunca projeye sıfırdan başlamadan kaldığın yerden devam edebilirsin.
> Tarih: 9 Ekim 2026

---

## 1. Ne Yapıyoruz

**İhale Analiz**, kamu ve özel ihalelerini uçtan uca analiz eden otonom bir skill'dir.
Kullanıcı (FAY) bir ihale dosyası paylaşır ya da panelde "Analizi başlat" der;
skill ajanlar, betikler ve FAY'ın kendi motorlarıyla şunu üretir:

- Katılım kararı (Katıl / Şartlı katıl / Katılma)
- Risk listesi, yeterlilik kontrolü, metraj kıyası veya keşif
- Excel teklif cetveli + HTML/PDF rapor

Sistem her analizden öğrenir ve sonraki ihalelerde bu bilgiyi kullanır.

**Repo:** `https://github.com/beyazsmokin/beyazsmokin`
**Skill klasörü:** `ihale-analiz/`
**FAY'ın kullanıcı adı:** `beyazsmokin`
**FAY'ın makinesi:** HP-Victus-FAY (Windows), masaüstü `~\Desktop`

---

## 2. Klasör Ağacı

```
ihale-analiz/
├── SKILL.md                  ← Orkestratör; platformda kullanılacak asıl skill dosyası
├── AKTARIM.md                ← Bu dosya
├── README.md
├── kurallar.md               ← Tüm ajanların uyduğu temel kurallar
├── kur.bat                   ← Windows kurulum kısayolu
│
├── agents/                   ← Ajan talimatları (her biri .md)
│   ├── koordinator.md
│   ├── tarayici.md
│   ├── dokuman-okuyucu.md
│   ├── idari-analist.md
│   ├── teknik-analist.md
│   ├── mali-analist.md
│   ├── metraj-analist.md
│   ├── risk-denetci.md
│   └── rapor-yazari.md
│
├── platforms/                ← Platform farkları
│   ├── genel-sistem-promptu.md
│   ├── chatgpt.md
│   └── hermes.md
│
├── scripts/                  ← Python betikleri (FAY'ın bilgisayarında çalışır)
│   ├── init_workspace.py     çalışma alanı kurulumu
│   ├── panel.py              web paneli (127.0.0.1:8765)
│   ├── motor.py              analiz motoru
│   ├── yz.py                 YZ bağlantısı (Claude/OpenAI/Hermes)
│   ├── takip.py              panel + ajan ortak veri katmanı
│   ├── takip_sitesi.py       ihale takip sitesi API
│   ├── siteler.py            ihale sitesi giriş paneli
│   ├── vt.py                 öğrenen veritabanı
│   ├── tara.py               ihale tarama + skorlama
│   ├── yeni_ihale.py         ihale klasörü oluşturma
│   ├── proje_oku.py          PDF/DXF/görsel proje dokümanı okuma
│   ├── belge_metni.py        idari/teknik şartname metin çıkarma
│   ├── metraj_kiyas.py       metraj kıyas CSV + geçmiş fiyat
│   ├── kisisel_hesap.py      kullanıcının kendi hesap kuralları
│   ├── excel_rapor.py        Excel teklif cetveli yazıcı
│   ├── sablon_olustur.py     Excel şablonları üretici
│   ├── html_rapor.py         Rapor.md → HTML + PDF
│   ├── dwg_cevirici.py       ODA/ezdxf DWG→DXF çevirici
│   ├── ofis.py               İhale Ofisi motor köprüsü
│   ├── pencere.py            panel pencere yönetimi (pywebview)
│   └── tepsi.py              sistem tepsisi simgesi
│
├── setup/
│   ├── KURULUM.md
│   └── workspace-template/   init_workspace.py bu ağacı kopyalar
│
├── templates/
│   ├── analiz-raporu.md      rapor şablonu
│   └── excel/
│       ├── birim-fiyat.xlsx
│       └── anahtar-teslim.xlsx
│
└── assets/
    ├── ikon.ico
    ├── ikon.png
    └── ikon-kaynak.jpg
```

---

## 3. FAY'ın Windows Makinesindeki Çalışma Alanı

Kurulumdan sonra masaüstünde `İhale Analiz/` klasörü oluşur:

```
Desktop\İhale Analiz\
├── Gelen Dosyalar\           FAY indirdiği ihale dosyalarını buraya bırakır
├── Taramalar\                günlük tarama listeleri
├── Panel.lnk                 simgeli kısayol, paneli açar
├── İhaleler\
│   └── <IKN <ad>\
│       ├── kaynak\           ihale dokümanları
│       ├── calisma\          ajan çıktıları (01-ozet.md … 06-metraj.md, CSV'ler)
│       ├── calisma\durum.json  adım durumları
│       ├── <kod> Rapor.md/.html/.pdf
│       └── <kod> Analiz.xlsx
└── .sistem\                  GİZLİ (Windows: gizli+sistem özniteliği)
    ├── config.yaml
    ├── siteler.json          ihale sitesi kayıtları (şifre YOK, kasada)
    ├── oturumlar\<site>\     tarayıcı oturumu
    ├── hafiza\               firma profili, öğrenilenler, ihale geçmişi
    ├── veritabani\ihale.db   SQLite öğrenen veritabanı
    ├── sablonlar\            Excel şablonları
    └── skill\                bu repo'nun yerel kopyası (ihale-analiz/)
```

FAY'ın diğer projeleri (ayrı repolar, masaüstünde):

```
Desktop\Projeler\
├── Ihale-Ofisi\              ← FAY'ın ön inceleme motoru
│   ├── ihale_akisi.py        keşif/FDU, birim fiyat arşivi, tahmini YM, Monte Carlo SD
│   ├── scraper.py            EKAP veri çekici
│   └── parser.py             veri ayrıştırıcı
└── Ihale-Ofisim\             ← FAY'ın detaylı analiz motoru
    └── ofis detay            doküman alımı, sözleşme türü, teklif cetveli, miktar
                              denetimi, çelişki, YM, pafta/proje metrajı; kendi
                              API anahtarlarını kullanır (Claude girişi gerekmez)
```

`scripts/ofis.py` bu iki motora köprüdür. Ön inceleme `ihale_akisi.py`'yi,
detaylı analiz `ofis detay`'ı çağırır.

---

## 4. Ajanlar ve İş Akışı

Koordinatör ajan tüm akışı yönetir. Her ajan kendi `.md` dosyasındaki
talimatı izler; `kurallar.md` hepsinin uyduğu temel kurallardır.

| Adım | Ajan | Çıktı |
|------|------|-------|
| T | tarayici | `Taramalar/<tarih>.md` |
| 0 | koordinatör | ihale klasörü, veritabanı bağlamı |
| 1 | dokuman-okuyucu | `calisma/01-ozet.md` |
| 2a | idari-analist | `calisma/02-idari.md` |
| 2b | teknik-analist | `calisma/03-teknik.md` |
| 2c | mali-analist | `calisma/04-mali.md`, `07-kisisel-hesap.md` |
| 2d | metraj-analist | `calisma/06-metraj.md` + CSV'ler |
| 3 | risk-denetci | `calisma/05-riskler.md` |
| 4 | rapor-yazari | `<kod> Rapor.md/.html/.pdf`, `<kod> Analiz.xlsx` |
| 5 | koordinatör | veritabanı + hafıza kaydı |

2a, 2b, 2c, 2d **paralel** çalışabilir.

---

## 5. Analiz Motoru

### motor.py — Panel Analizi Kendisi Başlatır

`motor.py` ayrı süreç olarak çalışır; kullanıcı paneldeki "Analizi başlat"a
bastığında panel bunu çağırır.

- **Ön inceleme** (`tur=on`): ihale dosyası gerekmez, ilan bilgisiyle başlar.
  FAY'ın **İhale Ofisi** motoru (`Projeler\Ihale-Ofisi\ihale_akisi.py`)
  kullanılır: keşif/FDU, birim fiyat arşivi, tahmini YM, Monte Carlo SD bandı,
  katılımcı tahmini, kazanan tenzilat ortalaması.
  Çıktı: `<kod> Ön İnceleme Rapor.md/.html`, karar: Detaylı incele / Dikkatle incele / Geç.

- **Detaylı analiz** (`tur=detay`): `kaynak/` doluyken çalışır.
  FAY'ın **İhale Ofisim** motoru (`ofis detay`) kullanılır: doküman alımı,
  sözleşme türü, BFTC, miktar denetimi, çelişki, YM, pafta metrajı.
  Kendi API anahtarlarını kullanır; ayrı bir Claude/ChatGPT girişi gerekmez.

- Kilit dosyası: `calisma/.motor.kilit`
- Adım durumları: `calisma/durum.json` (panel buradan canlı gösterir)

### yz.py — YZ Bağlantısı

`config.yaml > analiz.yz` değerine göre:
| Değer | Ne Kullanır |
|-------|-------------|
| `otomatik` | bilgisayarda `claude` CLI varsa Claude Code, yoksa API |
| `claude-kod` | `claude -p` (stdin; yalnız Read/Glob/Grep) |
| `anthropic` | Anthropic API (claude-opus-5-5, fallback'ler) |
| `openai` | OpenAI uyumlu (ChatGPT veya Hermes/Ollama) |
| `yok` | bağlantısız mod |

API anahtarı ortam değişkeni veya `motor.py anahtar --saglayici anthropic`
ile Windows Kimlik Bilgileri Yöneticisi'ne kaydedilir; sohbette **asla sorma**.

---

## 6. Panel

`scripts/panel.py` → `http://127.0.0.1:8765` — dış sunucu yok, yalnız localhost.
Görev çubuğunda kendi simgesiyle açılır (pywebview + tepsi.py).

### Sekmeler

| Sekme | Ne Gösterir |
|-------|-------------|
| Gösterge | aktif ihaleler, yaklaşan günler, analiz durumu |
| İlanlar | takip sitesinden çekilen ilanlar (TAKİP ET / DOSYA) |
| Sonuçlar | geçmiş ihale sonuçları, rakip/tenzilat |
| Takip | takipteki ihaler, "Analizi başlat" butonu |
| Süreç | seçili ihalenin adım adım analiz ilerlemesi |
| Rapor | HTML rapor okuyucu, PDF/Excel indirme |
| Ajanda | ihale tarihleri, takvime aktar (.ics) |
| Öğrenme | veritabanı istatistikleri |
| Ayarlar | takip sitesi bağlantısı (tek ayar buradadır) |

Panel başlatma: `python .sistem/skill/scripts/panel.py --ayri`
Otomatik açılma: `python .sistem/skill/scripts/panel.py baslangic --ac`

### takip.py — Ortak Veri Katmanı

Panel ve ajanlar arasındaki köprü; `ihale.db` içinde `takip` ve `etkinlikler`
tablolarını kullanır.

- `takip.py adim --kod <kod> --adim <N> --durum basladi|bitti|hata` → adım durumu yazar
- `takip.py etkinlik-ekle` → ajandaya tarih ekler
- `takip.py kuyruk` → "Analizi başlat" bekleyen ihaleler listesi

---

## 7. Veri Kaynakları

### İhale Takip Sitesi

FAY'ın kullandığı takip sitesi: **ihalesitesi.com** (şifre kasada saklı).

`scripts/takip_sitesi.py` ile:
- `liste` → ilan listesi
- `sonuclar` → ihale sonuçları
- `takip-listesi` → takipteki ihaleler
- `takip-et / takip-birak <IKN>` → takip yönetimi
- `bilgi <IKN>` → ihale detayı
- `indir <IKN> --hedef "..."` → EKAP ihale dosyası indirme

### EKAP — Güvenlik Kodu / Captcha

EKAP (ekapv2.kik.gov.tr) Cloudflare Turnstile doğrulaması kullandığı için
otomatik sorgu atılamaz. İhale dosyası indirmek için:

1. Panel "EKAP Dökümanı" butonuna basılır → modal açılır
2. FAY captcha kodunu modal'a kendisi yazar
3. Betik kodu kullanır, dosyayı `kaynak/` klasörüne indirir

FAY'ın kendi indirme motoru: `Desktop\Projeler\Ihale-Ofisi\ekap_indir.py`
(görünür Edge penceresi açar, indirme tamamlandığında kapatır).

**EKAP'a doğrudan API sorgusu atma; captcha'yı otomatik çözmeye çalışma (K-5.10).**

---

## 8. Öğrenme Döngüsü

`scripts/vt.py` ile SQLite `ihale.db`:

**Analizden önce** (her ajan çağrılmadan):
```
vt.py baglam --ajan <ad> --idare "<idare>" --konu "<konu>"
```

**Analizden sonra** (koordinatör):
- `vt.py ihale-kaydet` → ihale kaydı
- `vt.py metraj-yukle` + `vt.py pursantaj-yukle` → CSV'ler
- `vt.py ders-ekle` → yeni ders

**Site verisi** (site bağlıysa):
- `vt.py katilimci-yukle` → katılımcı + teklifler
- `vt.py kurum-fiyat-yukle --kaynak <site>` → kurum birim fiyatları

**Kullanıcı geri bildirimi:**
- `vt.py sonuc` → ihale sonucu (kazanan, teklif)
- `vt.py tercih` → "ilgimi çekti / ilgilenmiyorum"

Kod çalıştırılamayan platformlarda `.sistem/hafiza/` altındaki `.md`
dosyaları kullanılır (`ogrenilenler.md`, `ihale-gecmisi.md`).

---

## 9. Excel Çıktısı

İki sabit şablon, FAY'ın onayladığı yapı. **Şablon yapısını asla değiştirme;**
değişiklik yalnızca FAY isterse `sablon_olustur.py` ile yapılır.

| Şablon | Kullanım |
|--------|----------|
| `birim-fiyat.xlsx` | BFTC (birim fiyat teklif cetvelli) ihaleler |
| `anahtar-teslim.xlsx` | Anahtar teslim / götürü bedel ihaleler |

Anahtar teslim şablonu FAY'ın kendi EGM Gölbaşı altyapı örneğine göre
kurulmuştur (PR #7). "Metraj Mahal Listesi" poz bazlı metrajdır (oda listesi değil).

---

## 10. FAY'ın Kararları ve Tercihleri

| Karar | Açıklama |
|-------|----------|
| **Claude PR'larını kendisi birleştirsin** | FAY onay beklemek istemiyor; Claude PR açınca kendisi merge eder |
| **İhale Ofisi / İhale Ofisim motorları entegre edildi** | Skill aynı işleri yeniden yazmaz, FAY'ın motorlarını çağırır |
| **EKAP MCP entegrasyonu iptal** | Turnstile riski; kullanıcı oturumu yolu seçildi |
| **Captcha FAY'ın kendisi çözer** | Otomatik çözüm ToS/engel riski, yasak (K-5.10) |
| **Panelde tek ayar: takip sitesi** | Diğer teknik ayarlar panelde gösterilmez |
| **Şifre kasada, sohbette asla** | K-10.1; Windows Kimlik Bilgileri Yöneticisi |
| **Anahtar teslim şablonu EGM örneğinden** | FAY'ın kendi proje analiz formatı |
| **YZ sadece Claude CLI veya API** | İlk platform Claude (otomatik mod) |
| **Tarayıcı testleri Playwright** | Panel değişikliklerinde FAY'a tıklatma, Playwright ile test et |
| **Aktif bilgisayar testi RC ile** | "Sistemi bilgisayarda test et" thread'i, HP-Victus-FAY |

---

## 11. Tamamlanan PR'lar (Hepsi Main'de)

| PR | Başlık |
|----|--------|
| #4 | DWG çevirici kontrolü ve kullanıcıya açıklama |
| #7 | Anahtar teslim Excel şablonu EGM örneğine göre yeniden kuruldu |
| #8 | Kurulumda ihale sitesi giriş paneli ve site verisinden rakip/tenzilat analizi |
| #10 | Klasörde simgeli "Panel" kısayolu ve "panel aç" komutu |
| #11 | Panel takip sitesi üzerine |
| #12 | Panel analizi kendisi çalıştırır: analiz motoru, yapay zekâ bağlantısı, ön inceleme |
| #13 | İhale dosyası indirme çalışıyor |
| #14 | Panel penceresi geri gelir |
| #21 | Belge okuma |
| #22 | Zincir kopukluklarını bağla: site sonuçları, geçmiş fiyat, kişisel hesap, İKN |
| #23 | Otomatik ön inceleme |
| #24 | Ön inceleme İhale Ofisi motoru |
| #25 | Detaylı analiz İhale Ofisim motoruyla |
| #26 | Panel: taşan, kesik ve sığmayan metinler düzeltildi |

---

## 12. Açık Maddeler ve Sonraki Adımlar

### Panel Revizyonu (Yüksek Öncelik)

Test sonuçları `/mnt/project-files/Panel-Revizyon-Plani.md` dosyasındadır.
Uygulama sırası:

1. **A1 [P0]** Telefonda İlanlar, Sonuçlar, Taramalar, Ayarlar ve "Yeni ihale" yok →
   alt menüye "Menü/Daha fazla" sekmesi + mobil "+" butonu

2. **B1–B4 [P1]** Yanlış/çelişkili veri:
   - B4: `takip_sitesi.py:97` Python `.title()` Türkçe harfleri bozuyor → düzelt
   - B1: yaklaşık maliyet girilmemişse "0 ₺" yerine "—"
   - B2: tarihi geçmiş ihaleler "Aktif" sayılıyor
   - B3: kuyruktaki ihale "Analiz sürüyor" yazıyor

3. **C1–C3 [P1]** Erişilebilirlik: klavye navigasyonu, kontrast, form etiketleri

4. **D1 [P1]** Kesilen başlıklar: takvim çiplerinde "7 gü…"

5. **E1–E2 [P2]** Yoklama optimizasyonu: site eşitlemesi sayfa açılışında değil
   zamanlı veya düğmeyle

6. Kalan P2 sorunlar, P3 cila

### Detaylı Analiz Yeniden Yapımı (Devam Ediyor)

PR #25 ile İhale Ofisim motoru (`ofis detay`) bağlandı ve ilk uçtan uca test
tamamlandı. FAY'ın geri bildirimi bekleniyordu; "Sistemi bilgisayarda test et"
thread'i `review_ready` durumunda, FAY çevrimdışı.

FAY'ın beklentileri:
- İnşaat mühendisi gibi analiz: keşfin %80'i büyük kalemler, YM, katılımcı/tenzilat
- Sözleşme türüne göre değerlendirme, proje↔BFTC metraj kıyası, projede olup cetvelde olmayan kalemler
- İhale Ofisi ile kalem fiyatlama: arşiv, aynı isimli yakın ihaleler, rayiç/analiz
- Birleşik rapor panel testinden geçmeli

Sonraki adım: FAY geribildirimini verince "Sistemi bilgisayarda test et"
thread'i üzerinden devam edilecek.

### Diğer Açık Maddeler

- **Firma profili panelden düzenlenemiyor** (Ayarlar sayfası)
- **Kurum birim fiyatı için otomatik kaynak yok** (İhale Ofisim arşivi doldurmak gerekiyor)
- **Panelde girilen teklif/kazanan teklif `katilimcilar`'a gitmiyor**

---

## 13. Yalnızca FAY'ın Yapması Gerekenler

Bu adımlar asistan tarafından yapılamaz:

| Adım | Neden FAY Yapmalı |
|------|-------------------|
| **İhale sitesi giriş** | Şifre sohbette/dosyada tutulamaz; `siteler.py panel` ile kasaya kaydedilir |
| **EKAP captcha** | Cloudflare Turnstile insan doğrulaması; otomatik geçilemez |
| **Claude Desktop kurulumu** | `init_workspace.py` skill'i Claude'un skills klasörüne kopyalamıyor; elle kopyalanmalı |
| **ODA File Converter kurulumu** | DWG otomatik okunabilsin diye; DWG varsa gerekli |
| **İhale Ofisim birim fiyat arşivi** | YM hesabı için arşiv FAY tarafından doldurulmalı |
| **İhale Ofisim görsel model anahtarı** | Pafta metrajı için görsel model API anahtarı girilmeli |
| **API anahtarı (bağlantısız YZ)** | `motor.py anahtar --saglayici anthropic` komutu FAY çalıştırır |

---

## 14. Kurulum Adımları (FAY'ın Bilgisayarında)

Henüz kurulmamış bir bilgisayarda:

```bash
# 1. Repo'yu çek
git clone https://github.com/beyazsmokin/beyazsmokin
cd beyazsmokin/ihale-analiz

# 2. Çalışma alanını kur (masaüstüne İhale Analiz\ oluşturur)
python scripts/init_workspace.py
# veya Windows'ta: kur.bat'a çift tıkla

# 3. Python paketleri (eksikler otomatik kurulur ama manuel de yapılabilir)
pip install ezdxf pdfplumber pywebview pystray pillow keyring

# 4. Paneli aç
python scripts/panel.py --ayri

# 5. İhale sitesi girişi (panel içinde veya ayrıca)
python scripts/siteler.py panel
```

FAY'ın bilgisayarında kurulum tamamlandı (6 Ekim 2026);
`Desktop\İhale Analiz\` var, site girişi yapıldı, panel çalışıyor.

---

## 15. Bağlantılar ve Referanslar

- **Repo:** https://github.com/beyazsmokin/beyazsmokin
- **Skill SKILL.md:** `ihale-analiz/SKILL.md` (orkestratör)
- **Panel Revizyon Planı:** `/mnt/project-files/Panel-Revizyon-Plani.md`
- **Sistem Şeması:** https://claude.ai/artifact/B9SDRcUgzqr9QKBQ7kZLH2
- **Mimari Belgesi:** https://claude.ai/code/artifact/cf9d2f98-979c-41fb-9ed7-6530aeed743a
- **PR Geçmişi:** https://github.com/beyazsmokin/beyazsmokin/pulls?state=merged

---

*Bu belge Claude (claude.ai) tarafından 9 Ekim 2026 tarihinde hazırlanmıştır.*
*Projeyi devam ettirmek için önce bu dosyayı, sonra `SKILL.md`'yi oku.*
