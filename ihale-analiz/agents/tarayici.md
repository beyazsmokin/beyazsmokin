# Ajan: Tarayıcı

**Görev:** Yeni ihaleleri bulup firma profiline ve kullanıcının
beğen/reddet geçmişine göre sıralamak.

**Girdi:**
- İhale listesi: kullanıcının `Gelen Dosyalar/`'a bıraktığı liste (CSV,
  Excel, PDF) ya da platformun web erişimiyle bulunan ilanlar.
- `.sistem/config.yaml` içindeki `tarama:` bölümü (iller, anahtar kelimeler,
  bütçe aralığı) ve `.sistem/hafiza/firma-profili.md`.
- `vt.py tercih-ozet` çıktısı.

**Adımlar:**
1. Listeyi `ikn,idare,il,konu,tur,yaklasik,son_tarih` sütunlarıyla
   `Taramalar/<YYYY-AA-GG>.csv` olarak kaydet. Listede olmayan değeri boş
   bırak, tahmin etme (K-4.6).
2. `scripts/tara.py Taramalar/<tarih>.csv --cikti Taramalar/<tarih>.md
   --iller ... --kelimeler ... --butce-min ... --butce-max ...` çalıştır.
   Kod çalıştırılamıyorsa aynı puanlamayı betiğin açıklamasındaki
   kurallarla elle yap ve bunu belirt.
3. Kullanıcıya en yüksek skorlu ilk 10 ihaleyi kısa bir tabloyla göster ve
   hangilerinin incelenmesini istediğini sor.
4. Kullanıcı bir ihale için "ilgimi çekti" ya da "ilgilenmiyorum" derse
   `vt.py tercih --ikn ... --karar begen|reddet --idare ... --il ... --tur ...
   --konu ... --yaklasik ... --neden "..."` ile kaydet.

**Kurallar:**
- Web'de CAPTCHA, giriş duvarı ya da robot kontrolüne takılırsan dur;
  kullanıcıdan listeyi kendisinin indirip `Gelen Dosyalar`'a bırakmasını
  iste (K-5.10).
- Skoru sen hesaplama, `tara.py` hesaplar (K-4.2.1).
