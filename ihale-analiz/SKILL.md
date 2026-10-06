---
name: ihale-analiz
description: Kamu ve özel ihale dokümanlarını (idari şartname, teknik şartname, sözleşme tasarısı, birim fiyat cetveli) uçtan uca analiz eder; katılım kararı, risk listesi, yeterlilik kontrolü ve teklif hazırlık planı çıkarır. Kullanıcı bir ihale dosyası paylaştığında, "ihale", "şartname", "EKAP", "teklif", "yeterlilik" dediğinde kullan.
---

# İhale Analiz

Bu skill kendi çalışma klasörünü ve hafızasını kuran, içinde uzman ajanlar
barındıran otonom bir ihale analiz sistemidir. Claude, ChatGPT, Hermes ve
benzeri platformlarda aynı dosyalarla çalışacak şekilde yazılmıştır: tüm
durum düz Markdown/YAML dosyalarında tutulur, platforma özel bir özellik
zorunlu değildir.

## 1. Her çalıştırmada ilk adım: çalışma alanını bul ya da kur

1. Çalışma alanı yolu: kullanıcı başka bir yer söylemediyse
   `~/ihale-analiz-calisma/` (dosya sistemi yoksa sohbetin kendisi, bkz. 1.4).
2. Bu klasörde `config.yaml` **yoksa** bu ilk çalıştırmadır:
   [setup/KURULUM.md](setup/KURULUM.md) talimatını uygula, sonra devam et.
3. Varsa `config.yaml` ve `hafiza/` altındaki dosyaları oku. Analize
   başlamadan önce `hafiza/firma-profili.md` ve `hafiza/ogrenilenler.md`
   mutlaka bağlama alınır.
4. Dosya sistemi erişimi olmayan platformlarda (ör. düz sohbet) hafıza
   dosyalarının içeriği kullanıcıdan yapıştırılması istenir; oturum
   sonunda güncellenmiş hali kullanıcıya tek blok olarak verilir.

## 2. İş akışı

Koordinatör ajan ([agents/koordinator.md](agents/koordinator.md)) akışı
yönetir. Alt ajan çalıştırabilen platformlarda her ajan ayrı çalıştırılır;
çalıştıramayanlarda aynı model ajan dosyalarını sırayla rol olarak üstlenir.

| Adım | Ajan | Çıktı (`ihaleler/<ihale-kodu>/` altında) |
|------|------|-------------------------------------------|
| 1 | [dokuman-okuyucu](agents/dokuman-okuyucu.md) | `01-ozet.md` |
| 2a | [idari-analist](agents/idari-analist.md) | `02-idari.md` |
| 2b | [teknik-analist](agents/teknik-analist.md) | `03-teknik.md` |
| 2c | [mali-analist](agents/mali-analist.md) | `04-mali.md` |
| 3 | [risk-denetci](agents/risk-denetci.md) | `05-riskler.md` |
| 4 | [rapor-yazari](agents/rapor-yazari.md) | `rapor.md` |

2a, 2b ve 2c birbirinden bağımsızdır, paralel çalışabilir.

## 3. Hafıza kuralları

- Her analiz bitince `hafiza/ihale-gecmisi.md` dosyasına bir satır eklenir.
- Kullanıcının düzelttiği ya da öğrettiği her şey (ör. "bu idare hep geç
  ödeme yapar") `hafiza/ogrenilenler.md` dosyasına tarihli madde olarak
  yazılır.
- Firma bilgisi değişirse `hafiza/firma-profili.md` güncellenir.
- Hafıza dosyaları kısa tutulur; 200 satırı geçen dosya özetlenir.

## 4. Çıktı

Son rapor [templates/analiz-raporu.md](templates/analiz-raporu.md)
şablonunu kullanır ve kullanıcıya önce tek cümlelik karar
(Katıl / Şartlı katıl / Katılma) ile sunulur.

## 5. Sınırlar

- Rapor hukuki görüş değildir; bunu raporun sonunda belirt.
- Dokümanda olmayan bir bilgiyi uydurma; "dokümanda bulunamadı" yaz.
- Kullanıcının firma bilgileri çalışma alanı dışına gönderilmez.
