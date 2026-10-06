# Hermes ve Diğer Yerel / Masaüstü Ajanlar

Skill klasörünü desteklemeyen platformlarda:

1. [genel-sistem-promptu.md](genel-sistem-promptu.md) içeriğini sistem
   promptu olarak ver.
2. Ajanın dosya erişimi varsa bu repodaki `ihale-analiz/` klasörünün yolunu
   promptta belirt; ajan dosyaları oradan okur.
3. Dosya erişimi yoksa ajan dosyalarını sistem promptunun sonuna ekle.
4. Ajan kullanıcının bilgisayarında komut çalıştırabiliyorsa panel ona
   doğrudan iş verebilir: `.sistem/config.yaml` > `panel.analiz_komutu` alanına
   ajanın komut satırı çağrısını yazın (ör. `hermes run "ihale-analiz: {kod}
   için analiz zincirini başlat"`). Paneldeki "Analizi başlat" bu komutu çalıştırır.
