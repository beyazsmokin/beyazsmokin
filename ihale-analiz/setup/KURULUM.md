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
- Sonunda tarayıcıda **ihale sitesi giriş panelini** açar (aşağıda).

## Bilgisayara erişimi olmayan, kum havuzunda çalışan platformlar

Kurulumu kullanıcıya bırak: `kur.bat` (Windows) ya da
`python scripts/init_workspace.py` komutunu kendi bilgisayarında bir kez
çalıştırmasını söyle. Sonra çalışma alanını platforma klasör olarak bağlaması
yeterlidir.

## Dosya sistemi olmayan platformlar

Kullanıcıya hafızanın sohbette tutulacağını söyle, `firma-profili.md`
şablonundaki soruları sor ve oturum sonunda hafızayı tek blok halinde ver.
Site girişi bu platformlarda yapılmaz; şifre sohbette istenmez. Kullanıcı
siteden indirdiği sonuç listelerini (katılımcılar, teklifler, birim fiyatlar)
dosya olarak paylaşırsa aynı analizler yapılır.

## Kurulumdan sonra

1. Kullanıcıya firma profili sorularını sor (`.sistem/hafiza/firma-profili.md`).
   Cevap vermek istemediği alanları boş bırak.
2. `.sistem/config.yaml` içinde `platform` alanını doldur.
3. `scripts/dwg_cevirici.py` çalıştır. Çevirici yoksa çıktıdaki açıklamayı
   kullanıcıya kendi sözlerinle ilet: DWG'nin neden çevrilmesi gerektiği,
   ODA File Converter'ı kurarsa DWG'lerin otomatik okunacağı, kurmazsa her
   DWG için DXF ya da PDF halini vermesi gerekeceği. Kurulum betiği aynı
   açıklamayı yazar ve indirme sayfasını açmayı önerir.
4. **İhale sitesi girişi.** Kurulum betiği paneli açmadıysa (kod çalıştıran
   bir ajan kurduysa) `python .sistem/skill/scripts/siteler.py panel` çalıştır.
   Panel tarayıcıda açılır; kullanıcı ihaleleri takip ettiği siteyi (EKAP,
   ihalebul.com ya da adresini yazdığı başka bir site), kullanıcı adını ve
   şifresini girer ya da **Girişi atla** der. Betik kullanıcı bitirene kadar
   bekler. Önce kullanıcıya neden sorulduğunu kendi sözlerinle söyle:
   - Giriş; hızlı ihale analizi, geçmiş ihalelerden kurum birim fiyatı
     tespiti, rakip, katılımcı ve tenzilat analizi için kullanılır.
   - Atlarsa bu bölümler raporda yer almaz ve yaklaşık maliyet analizinde
     kurumların birim fiyatları tespit edilemez; analiz yalnızca rayiç
     fiyatlarla yapılır. Sonra "site girişi ekle" diyerek istediği zaman
     ekleyebilir.
   - Şifre bilgisayarın kendi şifre kasasında (Windows Kimlik Bilgileri
     Yöneticisi, macOS Anahtar Zinciri, Linux Secret Service) saklanır.

   **Şifreyi asla sohbette isteme, sohbete yazdırma, dosyaya, hafızaya,
   veritabanına ya da loga yazma (K-10.1).** Kullanıcı şifreyi sohbete
   yazarsa kullanma, paneli aç ve şifresini orada girmesini, sohbetteki
   mesajı silmesini öner. Panel açılamıyorsa (bilgisayara erişim yoksa)
   girişi atlanmış say ve kullanıcıya `siteler.py panel` komutunu kendi
   bilgisayarında çalıştırmasını söyle.
5. Kullanıcıya klasörün yerini ve ihale dosyalarını `Gelen Dosyalar`
   klasörüne bırakmasını söyle.
