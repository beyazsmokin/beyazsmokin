# ihale-analiz

İhale dokümanlarını uzman ajanlarla analiz eden, kendi çalışma alanını ve
hafızasını kuran, platformdan bağımsız bir skill.

## Yapı

```
ihale-analiz/
├── SKILL.md                  # ana talimat (Claude skill formatı)
├── kurallar.md               # temel kurallar ve güven etiketleri
├── agents/                   # ajan tanımları (tarayıcı dahil)
├── setup/
│   ├── KURULUM.md            # ilk çalıştırma talimatı
│   └── workspace-template/   # çalışma alanına kopyalanan dosyalar
├── templates/                # rapor şablonu
├── platforms/                # ChatGPT, Hermes ve genel prompt
├── panel/                    # ihale paneli arayüzü (PWA: index.html, app.js, sw.js, manifest)
├── assets/ikon.png|.ico      # klasör simgesi
├── kur.bat                   # Windows: çift tıkla kur
└── scripts/
    ├── init_workspace.py     # masaüstü klasörünü ve simgeyi kurar
    ├── yeni_ihale.py         # Gelen Dosyalar'ı ihale klasörüne taşır
    ├── proje_oku.py          # DWG/DXF/PDF/görsel proje okuma
    ├── dwg_cevirici.py       # DWG çeviricisini bulur, yoksa kullanıcıya açıklar
    ├── metraj_kiyas.py       # idare ve hesap metrajı kıyası
    ├── excel_rapor.py        # Excel raporunu şablona doldurur
    ├── sablon_olustur.py     # BFTC ve anahtar teslim şablonlarını üretir
    ├── siteler.py            # ihale sitesi giriş paneli, şifre kasası, oturum
    ├── takip_sitesi.py       # takip sitesi: ilanlar, sonuçlar, takip listesi, EKAP ihale dosyası
    ├── tepsi.py              # bildirim alanı simgesi, Windows bildirimleri, arka plan izleyici
    ├── ofis.py               # ön incelemede İhale Ofisi motoru: keşif+FDU → birim fiyat arşivi → tahmini YM, katılımcı, SD bandı
    ├── pencere.py            # paneli kendi uygulama penceresinde açar
    ├── panel.py              # ihale paneli sunucusu (yalnızca 127.0.0.1), otomatik başlatma
    ├── takip.py              # takip edilen ihaleler, ajanda, analiz süreci (panel ve ajanların ortak verisi)
    ├── motor.py              # analiz motoru: panelden ön inceleme ve detaylı analizi uçtan uca çalıştırır
    ├── yz.py                 # ajanları çalıştıran yapay zekâ (Claude Code, Claude API, ChatGPT, Hermes)
    ├── belge_metni.py        # ihale dokümanlarının (PDF, DOCX, XLSX, zip) yazısını çıkarır
    ├── html_rapor.py         # raporu HTML'e ve PDF'e çevirir
    ├── tara.py               # ihale listesini profile ve tercihlere göre skorlar
    ├── kisisel_hesap.py      # kişisel hesap kurallarını sistem tahmininin yanına koyar
    └── vt.py                 # öğrenen veritabanı (SQLite)
```

## Kurulum

- **Claude (Desktop / Code):** `ihale-analiz/` klasörünü skills dizinine
  kopyala ya da zip olarak yükle.
- **ChatGPT:** [platforms/chatgpt.md](platforms/chatgpt.md)
- **Hermes ve diğerleri:** [platforms/hermes.md](platforms/hermes.md)

Gerekli: `pip install openpyxl keyring playwright pystray win11toast` (Excel, şifre kasası, takip sitesi, bildirim alanı simgesi ve bildirimler). Metraj için
isteğe bağlı: `pip install ezdxf pdfplumber pillow`. Takip sitesi oturumu
bilgisayardaki Edge ya da Chrome ile açılır; ayrıca tarayıcı indirmek gerekmez.
DWG okumak için ücretsiz ODA File Converter ya da LibreDWG (`dwg2dxf`)
gerekir; kurulum betiği yoksa nedenini anlatır ve indirme sayfasını önerir
(`python scripts/dwg_cevirici.py` ile her zaman kontrol edilebilir).

İlk kullanımda skill masaüstünde özel simgeli **İhale Analiz** klasörünü
kurar, sistem dosyalarını gizli `.sistem` klasörüne koyar ve firma profilini
sorar. Kurulum sırasında tarayıcıda bir giriş paneli açılır: kullanıcı
ihaleleri takip ettiği siteye (EKAP, ihalebul.com ya da başka bir site)
kullanıcı adı ve şifresiyle bağlanır ya da bu adımı atlar. Şifre işletim
sisteminin şifre kasasında tutulur, hiçbir dosyaya yazılmaz. Atlanırsa raporda
kurum birim fiyatı, rakip, katılımcı ve tenzilat analizi yer almaz; yaklaşık
maliyet yalnızca rayiçlerle hesaplanır. İhale dosyaları `Gelen Dosyalar` klasörüne bırakılır; her ihale
`İhaleler/<kod>/` altında kendi klasörüne alınır, çıktılar oraya yazılır.

## İhale paneli

Kurulumdan sonra çalışma alanındaki, klasörle aynı simgeyi taşıyan **Panel**
kısayolu ya da asistana "panel aç" demek (`panel.py --ayri`) paneli kendi uygulama
penceresinde açar (Edge ya da Chrome `--app` kipi; görev çubuğunda panelin simgesi
görünür). Panel tek pencere açılır; zaten açıksa öne gelir. Pencere kapanınca simgesi
bildirim alanında (gizli simgeler) kalır, takip ve hesaplar arka planda sürer. Panel
bilgisayarda çalışır, dış sunucu kullanmaz.

**Mimari: takip sitesi.** Bütün ihale verisi kullanıcının kendi hesabıyla girdiği ihale
takip sitesinden gelir (şimdilik ihalesitesi.com; `scripts/takip_sitesi.py`). Takip
listesi iki yönlüdür: panelden takibe alınan ihale sitede de takibe alınır, bırakılan
sitede de bırakılır, sitede takip edilenler panele gelir. İhale dosyası, ilanın "EKAP
Dökümanı" bağlantısıyla EKAP'ın doküman sayfasından indirilir; EKAP'ın güvenlik kodu
resmi panelde gösterilir, kodu kullanıcı yazar.

**Bildirimler.** Takip edilen ihalenin sonucu geldiğinde, detaylı analiz bittiğinde,
ihale günü yaklaştığında ve analiz hata verdiğinde Windows bildirimi gelir. Bildirime
tıklanınca panel açılır; sonuç bildiriminde sitedeki sonuç panelde pencere olarak gösterilir.

| Bölüm | Ne yapar |
|-------|----------|
| Gösterge | Açık ihaleler, 7 gün içindeki ihale günleri, analiz süreci, son raporlar |
| İhale İlanları | Takip sitesindeki ilanlar, sitenin arama formundaki filtrelerle; satıra tıklayınca ilan penceresi; Takibe ekle ve EKAP ihale dosyasını indir |
| İhale Sonuçları | Kesinleşen sonuçlar: kazanan, sözleşme bedeli, tenzilat |
| Takip Ettiklerim | Takip edilen ihaleler (sitedeki takip listesiyle eşit); İKN ile yeni ihale; ihale başına bilgiler, süreç, rapor, dosyalar ve tarihler |
| Ajanda | Yalnızca takip edilen ihaleler; ay ve liste görünümü; ihale günü, yer görme, açıklama talebi, teminat; 7/3/1 gün kala hatırlatma |
| Süreç | Ajanların adımları canlı (`calisma/durum.json`), günlük kaydı |
| Raporlar | HTML rapor panelde açılır, yazdırılır; PDF ve Excel indirilir |
| Taramalar | Günlük tarama listeleri; tek tıkla takibe alma |
| Öğrenme | Kazanma oranı, tenzilat, rakipler, idareler, dersler, kişisel kurallar, tercih eğilimleri |
| Ayarlar | İhale takip sitesi girişi (diğer ayarlar standart gelir) |

Panel analizi kendisi çalıştırır (`motor.py`): takibe alınan ihalenin **ön incelemesi**
(ilan, idare geçmişi, rakip, tenzilat, uygunluk puanı, kısa karar) hemen yapılır; ihale
dosyası indikten sonra "Analizi başlat" **detaylı analizi** çalıştırır: doküman okuma,
idari, teknik, mali ve metraj ajanları (paralel), BFTC kıyası, pursantaj, kişisel hesap,
risk, HTML/PDF rapor, Excel ve öğrenme kaydı. Her adım Süreç sekmesinde canlı görünür.
Ajanları çalıştıran yapay zekâ `config.yaml` > `analiz.yz` ile seçilir: bilgisayarda
Claude Code kuruluysa o kullanılır (anahtar gerekmez), yoksa Claude API
(`motor.py anahtar --saglayici anthropic`), ChatGPT ya da Hermes/yerel model (OpenAI
uyumlu `analiz.yz_adres`). Bağlantı yoksa ihale kuyruğa alınır ve asistana "kuyruktaki
ihaleleri analiz et" denince işlenir. Güvenlik: panel yalnızca 127.0.0.1'i dinler, başka
adresten gelen ve panelin kendisinden gelmeyen değiştirme isteklerini reddeder,
dosya erişimi `İhaleler/` klasörüyle sınırlıdır, şifre görmez.

## Durum

İskelet (v0.1.0) ve ihale paneli. Paketleme ve testler sonraki adımda.
