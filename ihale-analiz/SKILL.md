---
name: ihale-analiz
description: Kamu ve özel ihale dokümanlarını (idari ve teknik şartname, sözleşme tasarısı, birim fiyat cetveli, mahal listesi, pursantaj, DWG/DXF/PDF/görsel proje çizimleri) uçtan uca analiz eder; katılım kararı, risk listesi, yeterlilik kontrolü, metraj kıyası veya keşif ve Excel rapor çıkarır, her analizden öğrenir. Kullanıcı bir ihale dosyası paylaştığında, "ihale", "şartname", "EKAP", "teklif", "yeterlilik", "metraj", "keşif", "pursantaj" dediğinde kullan.
---

# İhale Analiz

Bu skill masaüstünde kendi simgeli klasörünü kuran, sistem dosyalarını
gizli tutan, içinde uzman ajanlar barındıran ve her analizden öğrenen
otonom bir ihale analiz sistemidir. Claude, ChatGPT, Hermes ve benzeri
platformlarda aynı dosyalarla çalışır: durum düz Markdown/YAML dosyalarında
ve tek bir SQLite veritabanında tutulur.

## 1. Çalışma alanı

```
Masaüstü/İhale Analiz/            (özel simgeli klasör)
├── Gelen Dosyalar/               kullanıcı indirdiği ihale dosyalarını buraya bırakır
├── İhaleler/
│   └── <ihale-kodu>/             her ihale ve her inceleme kendi klasöründe
│       ├── kaynak/               o ihalenin dokümanları ve çizimleri
│       ├── calisma/              ajan çıktıları (01-ozet.md … 06-metraj.md, CSV'ler)
│       ├── <ihale-kodu> Rapor.md
│       └── <ihale-kodu> Analiz.xlsx
└── .sistem/                      GİZLİ: kullanıcı dokunmaz
    ├── config.yaml
    ├── hafiza/                   firma profili, öğrenilenler, ihale geçmişi
    ├── veritabani/ihale.db       öğrenen veritabanı
    ├── sablonlar/                Excel şablonları
    └── skill/                    bu skill'in kurulu kopyası (ajanlar, betikler)
```

Her çalıştırmada ilk adım:

1. Masaüstünde `İhale Analiz/.sistem/config.yaml` var mı bak (kullanıcı
   başka yer söylediyse orası).
2. **Yoksa** ilk çalıştırmadır: [setup/KURULUM.md](setup/KURULUM.md)
   talimatını uygula.
3. Varsa `config.yaml` ve `.sistem/hafiza/` dosyalarını oku.
4. `.sistem/` içindeki dosyaları kullanıcıya açma, taşıma ya da silme
   önerme; kullanıcı yalnızca `Gelen Dosyalar` ve `İhaleler` ile çalışır.
5. Dosya sistemi olmayan platformlarda hafıza sohbette tutulur
   (bkz. KURULUM.md).

## 2. İş akışı

Koordinatör ajan ([agents/koordinator.md](agents/koordinator.md)) akışı
yönetir. Alt ajan çalıştırabilen platformlarda her ajan ayrı çalıştırılır;
çalıştıramayanlarda aynı model ajan dosyalarını sırayla rol olarak üstlenir.

| Adım | Ajan | Çıktı (`İhaleler/<ihale-kodu>/calisma/`) |
|------|------|-------------------------------------------|
| 0 | koordinatör | ihale klasörü (`scripts/yeni_ihale.py`), veritabanından bağlam |
| 1 | [dokuman-okuyucu](agents/dokuman-okuyucu.md) | `01-ozet.md` |
| 2a | [idari-analist](agents/idari-analist.md) | `02-idari.md` |
| 2b | [teknik-analist](agents/teknik-analist.md) | `03-teknik.md` |
| 2c | [mali-analist](agents/mali-analist.md) | `04-mali.md` |
| 2d | [metraj-analist](agents/metraj-analist.md) | `06-metraj.md` ve CSV'ler |
| 3 | [risk-denetci](agents/risk-denetci.md) | `05-riskler.md` |
| 4 | [rapor-yazari](agents/rapor-yazari.md) | `<kod> Rapor.md`, `<kod> Analiz.xlsx` |
| 5 | koordinatör | veritabanına ve hafızaya kayıt |

2a, 2b, 2c ve 2d birbirinden bağımsızdır, paralel çalışabilir.

## 3. Öğrenme döngüsü

Sistem her analizle gelişir. Betik: `.sistem/skill/scripts/vt.py`.

**Analizden önce** her ajan kendi bağlamını alır:
`vt.py baglam --ajan <ajan-adı> --idare "<idare>" --konu "<konu>"`.
Bu çıktı ajanın girdisine eklenir; geçmiş dersler, aynı idarenin önceki
ihaleleri ve sonuçları buradan gelir. Metraj ve mali ajanlar ayrıca
`vt.py fiyat <poz>` ve `vt.py pursantaj-ort --tur <tür>` ile geçmiş birim
fiyat ve pursantaj ortalamalarını kullanır.

**Analizden sonra** koordinatör kaydeder:
- `vt.py ihale-kaydet` (kod, idare, konu, tür, yaklaşık maliyet, karar)
- `vt.py metraj-yukle` ve `vt.py pursantaj-yukle` (varsa CSV'ler)
- Analizde ortaya çıkan, sonraki ihalelerde işe yarayacak her bilgi için
  `vt.py ders-ekle` (hangi ajanı ilgilendiriyorsa `--ajan` ile)

**Kullanıcı geri bildirim verdiğinde** (düzeltme, ihale sonucu, kazanan
teklif): hemen `vt.py ders-ekle` ya da `vt.py sonuc` ile kaydet. Ders,
düzeltilen ajanı etiketler ki aynı hata tekrarlanmasın.

Kod çalıştırılamayan platformlarda aynı bilgiler `.sistem/hafiza/`
altındaki Markdown dosyalarına yazılır (`ogrenilenler.md`,
`ihale-gecmisi.md`).

## 4. Çıktı

Rapor [templates/analiz-raporu.md](templates/analiz-raporu.md) şablonunu,
Excel `scripts/excel_rapor.py` betiğini kullanır (`.sistem/sablonlar/analiz.xlsx`
varsa ona yazar). Kullanıcıya önce tek cümlelik karar (Katıl / Şartlı katıl /
Katılma), sonra iki dosyanın yolu verilir.

## 5. Sınırlar

- Rapor hukuki görüş değildir; bunu raporun sonunda belirt.
- Dokümanda olmayan bir bilgiyi uydurma; "dokümanda bulunamadı" yaz.
- Kullanıcının firma bilgileri ve veritabanı çalışma alanı dışına gönderilmez.
