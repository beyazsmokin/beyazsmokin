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
├── Taramalar/                    günlük tarama listeleri ve skorları
├── İhale Paneli                  paneli açan kısayol (Windows .bat, macOS .command, Linux .desktop)
├── İhaleler/
│   └── <ihale-kodu>/             her ihale ve her inceleme kendi klasöründe
│       ├── kaynak/               o ihalenin dokümanları ve çizimleri
│       ├── calisma/              ajan çıktıları (01-ozet.md … 06-metraj.md, CSV'ler)
│       ├── calisma/durum.json  analiz adımlarının durumu (panel canlı gösterir)
│       ├── <ihale-kodu> Rapor.md / .html / .pdf
│       └── <ihale-kodu> Analiz.xlsx
└── .sistem/                      GİZLİ: kullanıcı dokunmaz
    ├── config.yaml
    ├── siteler.json              ihale sitesi kayıtları (şifre YOK, şifre işletim sistemi kasasında)
    ├── oturumlar/<site>/         sitelerin tarayıcı oturumu (çerezler)
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

### İhale sitesi girişi

Kurulumda tarayıcıda bir giriş paneli açılır (`scripts/siteler.py panel`).
Kullanıcı ihaleleri takip ettiği siteyi (EKAP, ihalebul.com ya da başka
bir site) kullanıcı adı ve şifresiyle ekler ya da atlar. Bu giriş hızlı
ihale analizi, geçmiş ihalelerden kurum birim fiyatı tespiti, rakip,
katılımcı ve tenzilat analizi için kullanılır. Atlanırsa bu bölümler
raporda yer almaz ve yaklaşık maliyet yalnızca rayiçlerle hesaplanır;
kullanıcıya bunu açıkça söyle. Şifre yalnızca işletim sisteminin şifre
kasasında durur; sohbette isteme, dosyaya ya da hafızaya yazma (K-10.1).
Ayrıntı: [setup/KURULUM.md](setup/KURULUM.md) adım 4.

### İhale paneli

`scripts/panel.py` kullanıcının bilgisayarında (yalnızca 127.0.0.1) bir web paneli
açar; tarayıcıdan uygulama (PWA) olarak kurulabilir, dış sunucu kullanmaz.
Kullanıcı panelden ihale ekler ve dosyasını yükler, ihale günlerini, yer görme,
açıklama talebi gibi tarihleri ajandada izler (.ics ile takvimine aktarır),
"Analizi başlat" ile ihaleyi kuyruğa alır, analiz sürecini adım adım canlı izler,
HTML raporu panelde okur, PDF ve Excel'i indirir, ihale sonucunu girer.
Panel ve ajanlar aynı veritabanını kullanır; ortak veri katmanı `scripts/takip.py`.

- Kullanıcı "kuyruktaki ihaleleri analiz et" derse `takip.py kuyruk` listesindeki
  her ihale için 2. bölümdeki akışı çalıştır.
- Akış boyunca her adımın başında ve sonunda
  `takip.py adim --kod <kod> --adim <0|1|2a|2b|2c|2d|3|4|5> --durum basladi|bitti|hata [--mesaj "..."]`
  yaz; panel süreci buradan gösterir. Kod çalıştırılamıyorsa adım çıktı dosyalarından
  (`calisma/01-ozet.md` …) çıkarılır.
- Dokümanda geçen tarihleri (yer görme, açıklama talebi son günü, teminat, sözleşme)
  `takip.py etkinlik-ekle` ile ajandaya ekle; ihale tarihini
  `takip.py ekle` / panel kaydına yaz. Hatırlatmaları ajanda kendisi üretir.
- Kullanıcı "paneli aç" derse `panel.py` çalıştır; "panel bilgisayar açılınca
  başlasın" derse `panel.py baslangic --ac`.

## 2. İş akışı

Koordinatör ajan ([agents/koordinator.md](agents/koordinator.md)) akışı
yönetir. Alt ajan çalıştırabilen platformlarda her ajan ayrı çalıştırılır;
çalıştıramayanlarda aynı model ajan dosyalarını sırayla rol olarak üstlenir.

| Adım | Ajan | Çıktı (`İhaleler/<ihale-kodu>/calisma/`) |
|------|------|-------------------------------------------|
| T | [tarayici](agents/tarayici.md) | `Taramalar/<tarih>.md` (kullanıcı "bugün ne çıktı" dediğinde ya da liste bıraktığında) |
| 0 | koordinatör | ihale klasörü (`scripts/yeni_ihale.py`), veritabanından bağlam |
| 1 | [dokuman-okuyucu](agents/dokuman-okuyucu.md) | `01-ozet.md` |
| 2a | [idari-analist](agents/idari-analist.md) | `02-idari.md` |
| 2b | [teknik-analist](agents/teknik-analist.md) | `03-teknik.md` |
| 2c | [mali-analist](agents/mali-analist.md) | `04-mali.md`, varsa `07-kisisel-hesap.md` |
| 2d | [metraj-analist](agents/metraj-analist.md) | `06-metraj.md` ve CSV'ler |
| 3 | [risk-denetci](agents/risk-denetci.md) | `05-riskler.md` |
| 4 | [rapor-yazari](agents/rapor-yazari.md) | `<kod> Rapor.md`, `.html`, `.pdf`, `<kod> Analiz.xlsx` |
| 5 | koordinatör | veritabanına ve hafızaya kayıt |

2a, 2b, 2c ve 2d birbirinden bağımsızdır, paralel çalışabilir. Bir İKN
yazıldığında koordinatör doğrudan 0. adımdan başlar; "analiz zincirini
başlat" denirse 0-5 arası sormadan çalışır.

Her ajan [kurallar.md](kurallar.md) dosyasındaki temel kurallara ve güven
etiketlerine uyar.

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

**İhale sitesinden gelen veri** (site bağlıysa): katılımcılar ve teklifleri
`vt.py katilimci-yukle`, kurum birim fiyatları `vt.py kurum-fiyat-yukle
--kaynak <site>` ile kaydedilir. `vt.py kurum-fiyat`, `vt.py tenzilat` ve
`vt.py rakip` bu veriden birim fiyat geçmişi, tenzilat ve rakip eğilimi
çıkarır; `vt.py baglam --idare` aynı idarenin geçmiş tenzilatını gösterir.

**Kullanıcı geri bildirim verdiğinde** (düzeltme, ihale sonucu, kazanan
teklif): hemen `vt.py ders-ekle` ya da `vt.py sonuc` ile kaydet. Ders,
düzeltilen ajanı etiketler ki aynı hata tekrarlanmasın.

**Beğen / reddet:** kullanıcı bir ihale için "ilgimi çekti" ya da
"ilgilenmiyorum" derse `vt.py tercih` ile kaydet. Tarayıcı skoru
`vt.py tercih-ozet` eğilimlerinden beslenir; bir özellik en az 3 kararda
görülmeden ağırlık almaz.

**Kişisel hesap kuralları:** kullanıcı kendi hesap yöntemini söylerse
("betona hep %15 fire eklerim", "nakliye her zaman %8") kuralı yapıya çevir,
kullanıcıya okutup onayını al ve `vt.py kural-ekle` ile kaydet. İşlemler:
`yuzde_ekle`, `yuzde_cikar`, `tutar_ekle`, `birim_fiyat`. Kurallar sistem
tahminini değiştirmez; `scripts/kisisel_hesap.py` ikisini yan yana verir.

Kod çalıştırılamayan platformlarda aynı bilgiler `.sistem/hafiza/`
altındaki Markdown dosyalarına yazılır (`ogrenilenler.md`,
`ihale-gecmisi.md`).

## 4. Çıktı

Rapor [templates/analiz-raporu.md](templates/analiz-raporu.md) şablonunu izler;
`scripts/html_rapor.py İhaleler/<kod>` aynı raporu panelde açılan HTML'e ve PDF'e
çevirir (içerik değişmez, karar rozet, güven etiketleri renkli işaret olur).
Excel `scripts/excel_rapor.py` betiğiyle teklif türüne göre şablona yazılır:

- **Birim fiyatlı (BFTC)** ihale: `birim-fiyat.xlsx` (Özet, BFTC Kıyas,
  Fiyat Kaynakları, Açık Sorular, Yeterlilik, Teknik, Mali, Riskler, Kişisel
  Hesap, Yapılacaklar)
- **Anahtar teslim / götürü bedel** ihale: `anahtar-teslim.xlsx` (Özet, BFTC,
  Dönemsel BFTC, Teknik Tarifler, Fiyat Kaynakları, Metraj Mahal Listesi,
  Mevcut Mahal Listesi, Pursantaj Keşif Analizi, Grup Eşleme, Açık Sorular,
  Kazı Derinlik Analizi, Yeterlilik, Teknik, Mali, Riskler, Kişisel Hesap,
  Yapılacaklar). BFTC miktarları ve pursantaj payları Metraj Mahal
  Listesi'nden formülle gelir.

**Şablona sadık kal.** Excel çıktısı her zaman bu iki şablondan biridir.
Sayfa, sütun, formül ya da biçim ekleme, silme, değiştirme; ajan çıktıları
şablonun beklediği tablo ve CSV biçimine uyar. Şablonda değişiklik yalnızca
kullanıcı isterse yapılır: `scripts/sablon_olustur.py` güncellenir, şablonlar
yeniden üretilir ve `.sistem/sablonlar/` altındaki kopyalar değiştirilir. Kullanıcıya önce tek cümlelik karar (Katıl / Şartlı katıl /
Katılma), sonra rapor (HTML, PDF) ve Excel dosyasının yolu verilir; panel açıksa
raporun panelde ihalenin Rapor sekmesinde olduğu söylenir.

## 5. Sınırlar

- Rapor hukuki görüş değildir; bunu raporun sonunda belirt.
- Dokümanda olmayan bir bilgiyi uydurma; "dokümanda bulunamadı" yaz.
- Sayıları betikler hesaplar, etiketsiz sayı rapora girmez; ayrıntı
  [kurallar.md](kurallar.md).
- Kullanıcının firma bilgileri ve veritabanı çalışma alanı dışına gönderilmez.
- İhale sitesi şifresi sohbette istenmez, hiçbir dosyaya yazılmaz.
