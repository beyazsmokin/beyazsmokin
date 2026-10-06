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
- Etiketsiz sayıyı rapora alma (K-3.1). Kişisel hesap varsa mali bölümde
  "Sistem tahmini: X ₺ · Sizin yönteminizle: Y ₺" satırını göster.
- "Piyasa ve rakip analizi" bölümünü `04-mali.md` içindeki site verisinden
  doldur. Site girişi yoksa bölümü silme; şablondaki "site girişi yok"
  metnini yaz ki kullanıcı neyin eksik kaldığını görsün.
- Kod çalıştırılamıyorsa Excel yerine CSV dosyalarını ve rapordaki
  tabloları ver.
