# ihale-analiz

İhale dokümanlarını uzman ajanlarla analiz eden, kendi çalışma alanını ve
hafızasını kuran, platformdan bağımsız bir skill.

## Yapı

```
ihale-analiz/
├── SKILL.md                  # ana talimat (Claude skill formatı)
├── agents/                   # ajan tanımları
├── setup/
│   ├── KURULUM.md            # ilk çalıştırma talimatı
│   └── workspace-template/   # çalışma alanına kopyalanan dosyalar
├── templates/                # rapor şablonu
├── platforms/                # ChatGPT, Hermes ve genel prompt
└── scripts/init_workspace.py # çalışma alanı kurulum betiği
```

## Kurulum

- **Claude (Desktop / Code):** `ihale-analiz/` klasörünü skills dizinine
  kopyala ya da zip olarak yükle.
- **ChatGPT:** [platforms/chatgpt.md](platforms/chatgpt.md)
- **Hermes ve diğerleri:** [platforms/hermes.md](platforms/hermes.md)

İlk kullanımda skill `~/ihale-analiz-calisma/` klasörünü kurar ve firma
profilini sorar.

## Durum

İskelet (v0.1.0). Paketleme ve testler sonraki adımda.
