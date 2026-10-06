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
├── assets/ikon.png|.ico      # klasör simgesi
├── kur.bat                   # Windows: çift tıkla kur
└── scripts/
    ├── init_workspace.py     # masaüstü klasörünü ve simgeyi kurar
    ├── yeni_ihale.py         # Gelen Dosyalar'ı ihale klasörüne taşır
    ├── proje_oku.py          # DWG/DXF/PDF/görsel proje okuma
    ├── dwg_cevirici.py       # DWG çeviricisini bulur, yoksa kullanıcıya açıklar
    ├── metraj_kiyas.py       # idare ve hesap metrajı kıyası
    ├── excel_rapor.py        # Excel raporu üretir
    ├── tara.py               # ihale listesini profile ve tercihlere göre skorlar
    ├── kisisel_hesap.py      # kişisel hesap kurallarını sistem tahmininin yanına koyar
    └── vt.py                 # öğrenen veritabanı (SQLite)
```

## Kurulum

- **Claude (Desktop / Code):** `ihale-analiz/` klasörünü skills dizinine
  kopyala ya da zip olarak yükle.
- **ChatGPT:** [platforms/chatgpt.md](platforms/chatgpt.md)
- **Hermes ve diğerleri:** [platforms/hermes.md](platforms/hermes.md)

Gerekli: `pip install openpyxl` (Excel). Metraj için isteğe bağlı:
`pip install ezdxf pdfplumber pillow`.
DWG okumak için ücretsiz ODA File Converter ya da LibreDWG (`dwg2dxf`)
gerekir; kurulum betiği yoksa nedenini anlatır ve indirme sayfasını önerir
(`python scripts/dwg_cevirici.py` ile her zaman kontrol edilebilir).

İlk kullanımda skill masaüstünde özel simgeli **İhale Analiz** klasörünü
kurar, sistem dosyalarını gizli `.sistem` klasörüne koyar ve firma profilini
sorar. İhale dosyaları `Gelen Dosyalar` klasörüne bırakılır; her ihale
`İhaleler/<kod>/` altında kendi klasörüne alınır, çıktılar oraya yazılır.

## Durum

İskelet (v0.1.0). Paketleme ve testler sonraki adımda.
