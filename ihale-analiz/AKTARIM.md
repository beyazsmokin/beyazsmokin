# İhale Analiz Skill — Aktarım Belgesi

> Bu dosya başka bir YZ ile projeye devam edebilmek için hazırlanmıştır.
> Okuyunca projeye sıfırdan başlamadan kaldığın yerden devam edebilirsin.
> Tarih: 9 Ekim 2026 (güncellenmiş)

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
├── panel/                    ← PWA arayüz dosyaları (HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── style.css
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
│   └── <IKN> <ad>\
│       ├── kaynak\           ihale dokümanları (EKAP zip içindeki dosyalar)
│       ├── calisma\          ajan çıktıları (01-ozet.md … 06-metraj.md, CSV'ler)
│       ├── calisma\durum.json  adım durumları (panel canlı gösterir)
│       ├── calisma\.motor.kilit  kilit dosyası (çift çalışma engeli)
│       ├── <kod> Rapor.md/.html/.pdf
│       └── <kod> Analiz.xlsx
└── .sistem\                  GİZLİ (Windows: gizli+sistem özniteliği)
    ├── config.yaml
    ├── siteler.json          ihale sitesi kayıtları (şifre YOK; kasada saklanır)
    ├── oturumlar\<site>\     tarayıcı oturumu (Chrome profili)
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
│   ├── ekap_indir.py         EKAP indirme motoru (görünür Edge penceresi açar)
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
  Birim fiyat arşivi başlangıç sayıları: 16.928 güvenilir birim fiyat,
  290.000 keşif kalemi, 124.000 katılımcı kaydı.
  Çıktı: `<kod> Ön İnceleme Rapor.md/.html`, karar: Detaylı incele / Dikkatle incele / Geç.
  Takipte olan ihale panelden "Analizi başlat"a basılmadan önce de otomatik
  ön incelemeye girer (PR #23).

- **Detaylı analiz** (`tur=detay`): `kaynak/` doluyken çalışır.
  FAY'ın **İhale Ofisim** motoru (`ofis detay`) kullanılır: doküman alımı,
  sözleşme türü, BFTC, miktar denetimi, çelişki, YM, pafta metrajı.
  Kendi API anahtarlarını kullanır; ayrı bir Claude/ChatGPT girişi gerekmez (PR #25).
  **NOT:** Detaylı analiz yeniden yapımı henüz tamamlanmadı — bkz. Bölüm 12.

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
Panel tek örnekli (single-instance): zaten açıksa yeni pencere açmaz, mevcut
pencereyi öne getirir. Önemli düzeltme: `panel aç` komutu daha önce "İhale Analiz"
adlı Dosya Gezgini penceresini eşleştiriyordu; artık yalnızca panelin kendi
penceresiyle eşleşiyor (PR #14).

### Sol Menü Bölümleri (Masaüstü)

| Bölüm | Ne Gösterir |
|-------|-------------|
| **Gösterge** | aktif ihaleler, yaklaşan günler, analiz durumu |
| **İhale İlanları** | takip sitesinden çekilen güncel ilanlar |
| **İhale Sonuçları** | geçmiş ihale sonuçları, rakip/tenzilat |
| **Takip Ettiklerim** | takipteki ihaleler, "Analizi başlat" butonu |
| **Süreç** | seçili ihalenin adım adım analiz ilerlemesi (canlı) |
| **Rapor** | HTML rapor okuyucu, PDF/Excel indirme |
| **Ajanda** | yalnızca takipteki ihalelerin tarihleri görünür |
| **Öğrenme** | veritabanı istatistikleri |
| **Ayarlar** | takip sitesi bağlantısı (tek ayar buradadır) |

> Not: İhale İlanları, İhale Sonuçları, Takip Ettiklerim üç **ayrı bölüm**dür
> (aynı sayfanın sekmeleri değil). Ajanda yalnızca takipteki ihaleleri gösterir;
> takip edilmeyen ilanlar ajandada çıkmaz.

### Mobil (Dar Ekran)

Alt navigasyonda: Gösterge, İlanlar, Takip, Ajanda ve "Daha fazla" (gizli sayfalar için).
Yeni ihale eklemek için ekranın sağ altındaki **+** butonu (PR #16).

### İndirme Düğmesi Davranışı

"Dosya" butonu (EKAP dosyası indirme):
- İndirme sürerken düğme arka planı dolma animasyonuyla ilerler (% ilerleme).
- Tamamlandığında düğme yeşile döner, metin **"Dosyayı aç"** olur (PR #15).
- "Doğrudan temin" formatındaki (IKN `26DT…`) ihaleler için EKAP dokümanı
  yoktur; bu ihalerde "Dosya" butonu hiç gösterilmez (PR #16).

### Bildirimler

Panel kapandığında simge gizli simgelerde kalır. Windows toast bildirimleri:
- Analiz sonucu geldiğinde
- Analiz tamamlandığında
- İhale günü yaklaşınca
- Analiz hata verdiğinde

Bildirime tıklamak paneli öne getirir ve ilgili ihaleyi gösterir (PR #11).

### Filtreler

İhale İlanları ve Sonuçlar sayfalarındaki filtreler ihalesitesi.com arama
formuyla uyumludur: işin türü, idare adı, yaklaşık maliyet aralığı, tarih aralığı,
şehir, ihale türü. Sıralama ve sayfalama da mevcut (PR #19).

### Panel Başlatma

```
# Ayrı süreç, anında döner (normal kullanım)
python .sistem/skill/scripts/panel.py --ayri

# Bilgisayar açılışında otomatik başlat
python .sistem/skill/scripts/panel.py baslangic --ac
```

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
- `liste` → ilan listesi (ihalesitesi.com filtreleriyle uyumlu)
- `sonuclar` → ihale sonuçları
- `takip-listesi` → takipteki ihaleler
- `takip-et / takip-birak <IKN>` → takip yönetimi
- `bilgi <IKN>` → ihale detayı
- `indir <IKN> --hedef "..."` → EKAP ihale dosyası indirme

**Çift yönlü takip eşitlemesi (PR #11):** Panelden "Takibe Al" basıldığında
ihale hem yerel veritabanına hem ihalesitesi.com'un "Takip Ettiklerim"
listesine eklenir. Tersine, siteden takibe alınan ilanlar da panele yansır.

**Şehir adı büyük-küçük harf (PR #16):** `takip_sitesi.py:97`'de Python
`.title()` Türkçe karakterleri bozuyordu (örn. "Eski̇şehi̇r"). TR-aware yardımcı
fonksiyon ile düzeltildi.

### EKAP — Güvenlik Kodu / Captcha

EKAP (ekapv2.kik.gov.tr) Cloudflare Turnstile doğrulaması kullandığı için
otomatik sorgu atılamaz. İhale dosyası indirme akışı:

1. Panel'de ilgili ihalede **"EKAP Dökümanı"** butonuna basılır → modal açılır
2. Modal içinde **İlan Bilgileri** sekmesine gidilir
3. En son tarihe ait satıra tıklanır → önizleme modalı açılır
4. Önizleme modal alt kısmındaki **"İhale Dokümanını İndir"** butonuna tıklanır
5. EKAP sayfası açılır; FAY captcha kodunu pencereye kendisi yazar (3 dakika beklenir)
6. Betik kodu kullanır, dosyayı `kaynak/` klasörüne indirir (nested zip; iç zip'teki
   belgeler de açılır, .doc dosyaları dönüştürülür — PR #21)

FAY'ın kendi indirme motoru: `Desktop\Projeler\Ihale-Ofisi\ekap_indir.py`
(görünür Edge penceresi açar, indirme tamamlandığında kapatır).

**EKAP'a doğrudan API sorgusu atma; captcha'yı otomatik çözmeye çalışma (K-5.10).**

IKN formatı `26DT…` (doğrudan temin) olan ihaleler için EKAP dokümanı olmaz;
bu ihalelerde "EKAP Dökümanı" / "Dosya" butonu gösterilmez.

Geçmişe ait bir ihaleyi arama: yalnızca aktif ilan listesinde değil, sonuçlarda da aranır.

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

**Ders tekrarı engeli (PR #22):** Aynı ders daha önce eklendiyse tekrar eklenmez.

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
| **Tarayıcı testleri Playwright** | Panel değişikliklerinde FAY'a tıklatma; Playwright ile kendin test et |
| **Aktif bilgisayar testi RC ile** | "Sistemi bilgisayarda test et" thread'i, HP-Victus-FAY |
| **Panel: 3 ayrı bölüm** | İhale İlanları / İhale Sonuçları / Takip Ettiklerim ayrı sol menü öğeleri (sekme değil) |
| **Ajanda yalnızca takiptekiler** | Takip edilmeyen ilanlar ajandada görünmez |
| **İhale Ofisim kendi API anahtarı** | Detaylı analizde Claude girişi gerekmez |
| **Doğrudan temin (26DT…)** | Bu formattaki ihaleler için "Dosya/EKAP" butonu gösterilmez |

---

## 11. Tamamlanan PR'lar (Hepsi Main'de)

| PR | Başlık / İçerik |
|----|-----------------|
| #1 | Skill iskeleti: SKILL.md, kurallar.md, ajan .md dosyaları, init_workspace.py |
| #2 | kurallar.md, tarayici ajanı, tara.py |
| #3 | Ajan talimatları ve temel betikler |
| #4 | DWG çevirici kontrolü ve kullanıcıya açıklama |
| #5 | belge_metni.py, proje_oku.py, vt.py başlangıcı |
| #6 | Excel şablonları: birim-fiyat.xlsx, sablon_olustur.py |
| #7 | Anahtar teslim Excel şablonu EGM örneğine göre yeniden kuruldu |
| #8 | Kurulumda ihale sitesi giriş paneli ve site verisinden rakip/tenzilat analizi |
| #9 | PWA ihale paneli: panel.py (127.0.0.1:8765), takip.py, html_rapor.py |
| #10 | Klasörde simgeli "Panel" kısayolu ve "panel aç" komutu |
| #11 | Panel takip sitesi üzerine: 3 bölüm, çift yönlü takip, single-instance, bildirimler |
| #12 | Panel analizi kendisi çalıştırır: analiz motoru, yapay zekâ bağlantısı, ön inceleme |
| #13 | İhale dosyası indirme çalışıyor (EKAP akışı + nested zip) |
| #14 | Panel penceresi geri gelir: single-instance düzeltmesi (Dosya Gezgini çakışması giderildi) |
| #15 | İndirme düğmesi dolan fon animasyonu + yeşil "Dosyayı aç" butonu |
| #16 | Mobil menü (alt nav + "Daha fazla" + "+" butonu); yanlış veri düzeltmeleri: 0₺ null, tarihi geçmiş aktif sayılıyor, şehir TR büyük harf hatası |
| #17 | Klavye erişilebilirliği (tab, enter, escape), kontrast oranları, form etiketleri |
| #18 | Ajanda sadeleştirme (yalnızca takiptekiler), yoklama optimizasyonu, eşitleme yan etkileri |
| #19 | Daha fazla filtre (ihalesitesi.com formuyla uyumlu), sıralama seçenekleri, sayfalama, boş durumlar |
| #20 | F cilası: hover efektleri, geçiş animasyonları, yükleme göstergeleri, responsive ince ayarlar |
| #21 | Belge okuma: EKAP nested zip, .doc dönüştürme, doğrudan temin format tanıma |
| #22 | Zincir kopukluklarını bağla: site sonuçları vt'ye, geçmiş fiyat metraj ajanına, kişisel hesap 04-mali.md sonuna, özette İKN, boş firma profili uyarısı, ders tekrarı engeli |
| #23 | Otomatik ön inceleme: takibe alınan ihale otomatik kuyruğa girer |
| #24 | Ön inceleme İhale Ofisi motoru entegrasyonu |
| #25 | Detaylı analiz İhale Ofisim motoruyla; ilk uçtan uca test tamamlandı |
| #26 | Panel görsel taşma düzeltmeleri: 12 taşan/kesik metin sorunu (container query, kirp sınıfı, yapışkan sütun kaldırıldı) |
| #27 | AKTARIM.md ilk sürüm (eksik bilgilerle; bu güncelleme yerine geçer) |

---

## 12. Açık Maddeler ve Sonraki Adımlar

### Detaylı Analiz Yeniden Yapımı (Devam Ediyor — Yüksek Öncelik)

PR #25 ile İhale Ofisim motoru (`ofis detay`) bağlandı ve ilk uçtan uca test
tamamlandı. Makine 2026-10-07T03:05:44Z'de çevrimdışı oldu; iş yarıda kaldı.

FAY'ın beklentileri (geri bildirim: "inşaat mühendisi gibi toparlama"):
- Keşfin %80'ini oluşturan büyük kalemler öne çıkarılmalı
- Yaklaşık maliyet, katılımcı/tenzilat analizi ön planda
- Sözleşme türüne göre değerlendirme
- Proje↔BFTC metraj kıyası; projede olup cetvelde olmayan kalemler
- İhale Ofisi ile kalem fiyatlama: arşiv, aynı isimli yakın ihaleler, rayiç/analiz
- Birleşik raporun panel Playwright testinden geçmesi

Sonraki adım: "Sistemi bilgisayarda test et" thread'inde devam edilecek.

### Diğer Açık Maddeler

- **Firma profili panelden düzenlenemiyor** (Ayarlar sayfasında düzenleme formu yok)
- **Kurum birim fiyatı için otomatik kaynak yok** (İhale Ofisim arşivinin FAY tarafından doldurulması gerekiyor)
- **Panelde girilen teklif/kazanan teklif `katilimcilar` tablosuna gitmiyor**

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

## 14. Temel Kurallar (Bunları Asla İhlal Etme)

| Kural | İçerik |
|-------|--------|
| **K-10.1** | Şifreyi asla sohbette isteme, sohbete yazdırma, dosyaya/hafızaya/loga yazma. Kullanıcı sohbete yazarsa kullanma; paneli aç, şifresini orada girmesini söyle. |
| **K-5.10** | EKAP güvenlik kodunu (captcha) kullanıcı yazar; otomatik çözmeye çalışma. EKAP'a doğrudan API sorgusu atma. |
| **API anahtarı** | API anahtarını sohbette asla sorma; `motor.py anahtar --saglayici anthropic` komutunu FAY'ın kendisinin çalıştırmasını söyle. |
| **Playwright testi** | Panel değişikliklerini Playwright ile kendin test et; FAY'a tıklatma. Yalnızca captcha, e-Devlet veya şifre gereken adımlarda FAY'dan yardım iste. |

---

## 15. Kurulum Adımları (FAY'ın Bilgisayarında)

FAY'ın bilgisayarında kurulum tamamlandı (6 Ekim 2026);
`Desktop\İhale Analiz\` var, site girişi yapıldı, panel çalışıyor.

Henüz kurulmamış bir bilgisayarda:

```bash
# 1. Repo'yu çek
git clone https://github.com/beyazsmokin/beyazsmokin
cd beyazsmokin/ihale-analiz

# 2. Çalışma alanını kur (masaüstüne İhale Analiz\ oluşturur)
python scripts/init_workspace.py
# veya Windows'ta: kur.bat'a çift tıkla

# 3. Python paketleri (eksikler otomatik kurulur ama manuel de yapılabilir)
pip install ezdxf pdfplumber pywebview pystray pillow keyring playwright

# 4. Paneli aç
python scripts/panel.py --ayri

# 5. İhale sitesi girişi (panel içinde veya ayrıca)
python scripts/siteler.py panel
```

---

## 16. Bağlantılar ve Referanslar

- **Repo:** https://github.com/beyazsmokin/beyazsmokin
- **Skill SKILL.md:** `ihale-analiz/SKILL.md` (orkestratör)
- **Panel Revizyon Planı (tamamlandı):** `/mnt/project-files/Panel-Revizyon-Plani.md`
- **Sistem Şeması:** https://claude.ai/artifact/B9SDRcUgzqr9QKBQ7kZLH2
- **Mimari Belgesi:** https://claude.ai/code/artifact/cf9d2f98-979c-41fb-9ed7-6530aeed743a
- **PR Geçmişi:** https://github.com/beyazsmokin/beyazsmokin/pulls?state=merged

---

*Bu belge Claude (claude.ai) tarafından 9 Ekim 2026 tarihinde hazırlanmış,*
*aynı gün tam thread taraması yapılarak kapsamlı biçimde güncellenmiştir.*
*Projeyi devam ettirmek için önce bu dosyayı, sonra `SKILL.md`'yi oku.*
