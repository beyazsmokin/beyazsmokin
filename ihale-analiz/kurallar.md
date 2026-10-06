# Temel Kurallar

Her ajan bu kurallara uyar. Kurallar FAY Ai Agent'tan aynen alınmıştır;
numaraları oradaki gibidir.

| Kural | Anlamı |
|-------|--------|
| K-4.2.1 | Hiçbir sayı modelin cümlesinden gelmez. Model alanları doldurur, aritmetiği betik yapar (`vt.py`, `metraj_kiyas.py`, `kisisel_hesap.py`, `tara.py`). |
| K-4.6 | Değer uydurulmaz. Çıktı "yarım" olabilir, "yanlış" olamaz. Bulunamayan bilgi "dokümanda bulunamadı" diye yazılır. |
| K-3.1 | Rapora giren her sayı bir güven etiketi taşır (aşağıda). Etiketsiz sayı rapora giremez. |
| K-3.5 | Kaynak veri tahminle düzeltilmez. Şüpheli değer işaretlenir; silinmez, değiştirilmez. |
| K-9.2 | Çelişen veri varsa kullanıcıya sorulur, ajan kendisi seçmez. |
| K-5.10 | CAPTCHA ve robot kontrolleri asla otomatik aşılmaz. Takılınca dur, kullanıcıdan dosyayı indirip `Gelen Dosyalar`'a bırakmasını iste. |
| K-10.1 | API anahtarı ve şifre hafıza dosyalarına, veritabanına, loglara ve paketlere yazılmaz. İhale sitesi şifreleri yalnızca işletim sisteminin şifre kasasında durur (`siteler.py`); sohbette istenmez, ekrana yazdırılmaz. |
| K-12.4 | Sabit dosya yolu yoktur. Yollar çalışma alanına göredir. |

## Güven etiketleri

| Etiket | Ne zaman |
|--------|----------|
| BELGE | Değer bu ihalenin kendi dokümanından ya da projesinden ölçülerek alındı. |
| RESMİ | Değer resmi bir kaynaktan geldi (Bakanlık birim fiyatı, TÜİK endeksi, mevzuat). |
| ARŞİV | Değer veritabanındaki geçmiş ihalelerden geldi (`vt.py fiyat`, `pursantaj-ort`, ihale sitesinden alınan `kurum-fiyat`, `tenzilat`, `rakip`; kaynak site adıyla). |
| TAHMİN | Değer görselden okundu, varsayımla hesaplandı ya da kullanıcının kişisel kuralıyla üretildi. |

Geçmişten öğrenilen bir değer (ARŞİV, TAHMİN) BELGE değerinin yerine asla
geçmez; yalnızca yanında karşılaştırma olarak gösterilir.

## Kişisel hesap

Kullanıcının kişisel hesap kuralları (`vt.py kural-ekle`) sistem tahminini
değiştirmez. Rapor ikisini her zaman yan yana gösterir:

> Sistem tahmini: X ₺ · Sizin yönteminizle: Y ₺
