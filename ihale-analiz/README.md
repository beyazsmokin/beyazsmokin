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
    ├── panel.py              # ihale paneli sunucusu (yalnızca 127.0.0.1), otomatik başlatma
    ├── takip.py              # takip edilen ihaleler, ajanda, analiz süreci (panel ve ajanların ortak verisi)
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

Gerekli: `pip install openpyxl keyring` (Excel, şifre kasası). Metraj için
isteğe bağlı: `pip install ezdxf pdfplumber pillow`. İhale sitesinde oturum
açıp sayfa çekmek için isteğe bağlı: `pip install playwright` ve
`python -m playwright install chromium`.
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

Kurulumdan sonra çalışma alanındaki **İhale Paneli** kısayolu (ya da
`python .sistem/skill/scripts/panel.py`) paneli tarayıcıda açar. Panel
bilgisayarda çalışır, dış sunucu kullanmaz ve tarayıcıdan uygulama (PWA) olarak
kurulabilir; sunucu kapalıyken son görülen veriler yine açılır.

| Bölüm | Ne yapar |
|-------|----------|
| Gösterge | Açık ihaleler, 7 gün içindeki ihale günleri, analiz süreci, son raporlar, kazanma oranı |
| İhaleler | İhale ekle (dosya yükleme dahil), ara, filtrele, CSV indir; ihale başına bilgiler, süreç, rapor, dosyalar ve tarihler |
| Ajanda | Ay ve liste görünümü; ihale günü, yer görme, açıklama talebi, teminat; 7/3/1 gün kala hatırlatma; `.ics` ile takvime aktarma |
| Süreç | Ajanların adımları canlı (`calisma/durum.json`), günlük kaydı |
| Raporlar | HTML rapor panelde açılır, yazdırılır; PDF ve Excel indirilir |
| Taramalar | Günlük tarama listeleri; tek tıkla takibe alma |
| Öğrenme | Kazanma oranı, tenzilat, rakipler, idareler, dersler, kişisel kurallar, tercih eğilimleri |
| Ayarlar | İhale sitesi girişi, bildirimler, tema, otomatik analiz komutu |

"Analizi başlat" ihaleyi kuyruğa alır; asistana "kuyruktaki ihaleleri analiz et"
denince işlenir. `config.yaml` > `panel.analiz_komutu` tanımlanırsa (ör. Claude
Code: `claude -p 'ihale-analiz: {kod} için analiz zincirini başlat'`) analiz
panelden hemen başlar. Güvenlik: panel yalnızca 127.0.0.1'i dinler, başka
adresten gelen ve panelin kendisinden gelmeyen değiştirme isteklerini reddeder,
dosya erişimi `İhaleler/` klasörüyle sınırlıdır, şifre görmez.

## Durum

İskelet (v0.1.0) ve ihale paneli. Paketleme ve testler sonraki adımda.
