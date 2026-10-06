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
| Mahal Listesi | `mahal-listesi.csv`: kat, mahal_no, mahal_adi, alan, cevre, yukseklik, kapi, pencere, doseme, duvar, tavan, not |
| Keşif | `kesif.csv`: is_grubu, poz_no, tanim, birim, miktar, birim_fiyat, mahal, not |
| Pursantaj | `pursantaj.csv`: is_grubu, oran (yüzde puanı) |
| Yeterlilik | `02-idari.md` tablosu: Koşul, Madde, Firma durumu, Not |
| Teknik | `03-teknik.md` tablosu: Gereksinim, Madde, Durum, Not |
| Mali | `04-mali.md` tablosu: Kalem, Değer, Kaynak, Not |
| Riskler | `05-riskler.md` tablosu: Risk, Kaynak, Seviye, Önlem |
| Kişisel Hesap | `kisisel-hesap.csv` (kisisel_hesap.py çıktısı) |
| Yapılacaklar | `yapilacaklar.csv`: is, son_tarih, sorumlu, durum |
