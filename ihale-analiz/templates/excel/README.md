# Excel şablonları

| Dosya | Ne zaman |
|-------|----------|
| `birim-fiyat.xlsx` | Birim fiyat teklif cetvelli (BFTC) ihaleler |
| `anahtar-teslim.xlsx` | Anahtar teslim / götürü bedel ihaleler |

Şablonlar `scripts/sablon_olustur.py` ile üretilir; elle düzenlenmez.
Değişiklik gerekiyorsa o betik güncellenip yeniden çalıştırılır.

Kurulumda bu klasör `.sistem/sablonlar/` altına kopyalanır.
`scripts/excel_rapor.py` şablonu teklif türüne göre seçer ve yalnızca gizli
`_harita` sayfasında tanımlı sütunlara yazar.

## Beklenen analiz dosyaları (`İhaleler/<kod>/calisma/`)

| Sayfa | Kaynak |
|-------|--------|
| Özet | `01-ozet.md` alanları, rapordaki karar satırı |
| BFTC Kıyas | `metraj-kiyas.csv`: poz_no, tanim, birim, idare, hesap, birim_fiyat, gecmis_fiyat, not |
| Fiyat Kaynakları (iki şablon) | `fiyat-kaynaklari.csv`: poz_no, tanim, birim, birim_fiyat, kaynak, dayanak, donem, not |
| Açık Sorular (iki şablon) | `acik-sorular.csv`: satir, soru, etki, durum, cevap |
| BFTC (anahtar teslim) | `bftc.csv`: poz_no, tanim, birim, birim_fiyat, not (miktar metrajdan formülle) |
| Dönemsel BFTC | `donemsel-fiyat.csv`: poz_no, tanim, birim, ocak … aralik, yillik_liste, yillik_kitap, kullanilan_donem, not |
| Teknik Tarifler | `teknik-tarifler.csv`: poz_no, tarif |
| Metraj Mahal Listesi | `metraj.csv`: is_grubu, alt_baslik, poz_no, tanim, birim, miktar, kaynak, hesap, durum |
| Mevcut Mahal Listesi | `mevcut-mahal.csv`: grup, imalat, birim, miktar, olcum_kaynagi, hesap, durum |
| Pursantaj Keşif Analizi | `pursantaj.csv`: is_grubu, ust_grup, oran (üst gruba göre yüzde sayısı), kaynak, not |
| Grup Eşleme | `grup-esleme.csv`: bizim_grup, kurum_grubu, not |
| Kazı Derinlik Analizi | `kazi-derinlik.csv`: pafta, baca_bas, baca_son, zemin_akar_bas, zemin_akar_son, uzunluk, not |
| Yeterlilik | `02-idari.md` tablosu: Koşul, Madde, Firma durumu, Not |
| Teknik | `03-teknik.md` tablosu: Gereksinim, Madde, Durum, Not |
| Mali | `04-mali.md` tablosu: Kalem, Değer, Kaynak, Not |
| Riskler | `05-riskler.md` tablosu: Risk, Kaynak, Seviye, Önlem |
| Kişisel Hesap | `kisisel-hesap.csv` (kisisel_hesap.py çıktısı) |
| Yapılacaklar | `yapilacaklar.csv`: is, son_tarih, sorumlu, durum |
