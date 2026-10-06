# ChatGPT (Custom GPT) Kurulumu

1. Yeni bir GPT oluştur, **Instructions** alanına
   [genel-sistem-promptu.md](genel-sistem-promptu.md) içeriğini yapıştır.
2. **Knowledge** bölümüne `agents/`, `templates/`, `scripts/` ve
   `setup/workspace-template/` altındaki dosyaları yükle. DWG dosyaları
   ChatGPT'de çevrilemez; kullanıcıdan DXF veya PDF istenir.
3. **Code Interpreter** açıksa çalışma alanı `/mnt/data/İhale Analiz/`
   altında kurulur. ChatGPT oturumları arası dosya saklamadığı için
   kullanıcı her oturumun başında `.sistem` klasörünü (özellikle
   `veritabani/ihale.db`) zip olarak yükler, sonunda güncel halini indirir.
   Asıl klasör kullanıcının masaüstündedir; ChatGPT onun kopyasıyla çalışır.
4. İhale sitesi girişi ChatGPT'de yapılmaz ve şifre sohbette istenmez.
   Kullanıcı siteye girişi kendi bilgisayarında `siteler.py panel` ile kurar
   ya da siteden indirdiği sonuç listelerini yükler; yüklemezse rakip,
   katılımcı, tenzilat ve kurum birim fiyatı bölümleri raporda yer almaz.
