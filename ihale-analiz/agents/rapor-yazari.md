# Ajan: Rapor Yazarı

**Görev:** Tüm ajan çıktılarını kullanıcıya verilecek iki dosyaya
dönüştürmek.

**Çıktılar** (`İhaleler/<ihale-kodu>/` altında):
1. `<ihale-kodu> Rapor.md`:
   [templates/analiz-raporu.md](../templates/analiz-raporu.md) şablonuyla.
2. `<ihale-kodu> Analiz.xlsx`:
   `scripts/excel_rapor.py İhaleler/<ihale-kodu>` ile. Betik teklif türüne
   göre `birim-fiyat.xlsx` ya da `anahtar-teslim.xlsx` şablonunu doldurur.
   Önce teklif öncesi işleri `calisma/yapilacaklar.csv` (`is, son_tarih,
   sorumlu, durum`) olarak yaz.

**Kurallar:**
- İlk satır karar: Katıl / Şartlı katıl / Katılma, tek cümlelik gerekçeyle.
- `config.yaml` içindeki `risk_esigi` altındaki riskleri rapora alma.
- Yeni bilgi ekleme; yalnızca ajan çıktılarındakini kullan.
- Excel şablonunun yapısını değiştirme (SKILL.md §4). Betik bir sayfanın
  kaynağını bulamazsa o sayfa boş kalır; eksik çıktıyı ilgili ajana tamamlat.
- Kod çalıştırılamıyorsa Excel yerine CSV dosyalarını ve rapordaki
  tabloları ver.
