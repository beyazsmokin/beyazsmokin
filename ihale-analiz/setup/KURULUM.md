# İlk Çalıştırma Kurulumu

Bu talimat yalnızca `İhale Analiz/.sistem/config.yaml` bulunmadığında uygulanır.

## Kullanıcının bilgisayarında kod çalıştırabilen platformlar

```bash
python scripts/init_workspace.py              # varsayılan: Masaüstü/İhale Analiz
python scripts/init_workspace.py "D:/Baska"   # özel konum
```

Windows'ta skill klasöründeki `kur.bat` dosyasına çift tıklamak aynı işi yapar.

Betik:
- Masaüstünde `İhale Analiz` klasörünü açar, `Gelen Dosyalar` ve `İhaleler`
  alt klasörlerini kurar.
- Ayarları, hafızayı, veritabanını, Excel şablonlarını ve skill'in bir
  kopyasını gizli `.sistem` klasörüne koyar (Windows: gizli + sistem
  özniteliği, macOS: gizli bayrağı, Linux: nokta ile başlayan ad).
- Klasöre `assets/ikon` simgesini atar (Windows `desktop.ini`, macOS
  NSWorkspace, Linux GNOME `gio`). Simge görünmezse masaüstünü yenilemek
  (F5) yeterlidir.
- Mevcut dosyaların üzerine yazmaz.

## Bilgisayara erişimi olmayan, kum havuzunda çalışan platformlar

Kurulumu kullanıcıya bırak: `kur.bat` (Windows) ya da
`python scripts/init_workspace.py` komutunu kendi bilgisayarında bir kez
çalıştırmasını söyle. Sonra çalışma alanını platforma klasör olarak bağlaması
yeterlidir.

## Dosya sistemi olmayan platformlar

Kullanıcıya hafızanın sohbette tutulacağını söyle, `firma-profili.md`
şablonundaki soruları sor ve oturum sonunda hafızayı tek blok halinde ver.

## Kurulumdan sonra

1. Kullanıcıya firma profili sorularını sor (`.sistem/hafiza/firma-profili.md`).
   Cevap vermek istemediği alanları boş bırak.
2. `.sistem/config.yaml` içinde `platform` alanını doldur.
3. `scripts/dwg_cevirici.py` çalıştır. Çevirici yoksa çıktıdaki açıklamayı
   kullanıcıya kendi sözlerinle ilet: DWG'nin neden çevrilmesi gerektiği,
   ODA File Converter'ı kurarsa DWG'lerin otomatik okunacağı, kurmazsa her
   DWG için DXF ya da PDF halini vermesi gerekeceği. Kurulum betiği aynı
   açıklamayı yazar ve indirme sayfasını açmayı önerir.
4. Kullanıcıya klasörün yerini ve ihale dosyalarını `Gelen Dosyalar`
   klasörüne bırakmasını söyle.
