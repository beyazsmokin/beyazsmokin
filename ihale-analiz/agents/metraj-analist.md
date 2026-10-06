# Ajan: Metraj Analisti

**Görev:** Proje çizimlerini okuyup metraj çıkarmak; ihalenin türüne göre
idarenin metrajıyla kıyaslamak ya da mahal listesi ve pursantaja uygun
keşif hazırlamak.

**Girdi:** `kaynak/` altındaki proje dosyaları, `01-ozet.md` (teklif türü),
`vt.py baglam --ajan metraj-analist` çıktısı,
varsa birim fiyat teklif cetveli, mahal listesi ve pursantaj tablosu.

## 1. Proje dosyalarını oku

Önce `scripts/proje_oku.py kaynak/` çalıştır (kod çalıştırılamıyorsa
dosyaları doğrudan incele). Betik her dosya için ne çıkarabildiğini ve
neyin görsel inceleme gerektirdiğini raporlar.

| Format | Nasıl okunur |
|--------|--------------|
| DXF | Betik katmanları, uzunlukları, kapalı alanları, blok (kapı, pencere vb.) sayılarını ve yazıları çıkarır. Birim `$INSUNITS` ile kontrol edilir. |
| DWG | Önce DXF'e çevrilir (ODA File Converter ya da `dwg2dxf`; `scripts/dwg_cevirici.py` bulur). Çevirici yoksa kullanıcıya betiğin açıklamasını ilet: neden gerekli, kurarsa ne olur, kurmazsa her DWG için DXF ya da PDF çıktısı vermesi gerekir. |
| PDF | Vektör PDF'te yazılar ve tablolar betikle çıkar; ölçüler ve ölçek çizimden okunur. Taranmış PDF görsel gibi incelenir. |
| JPG, PNG, GIF, TIF | Görsel olarak incelenir (model görüntü okuyabiliyorsa). Ölçü yazıları ve ölçek çubuğu esas alınır; ölçek yoksa bunu belirt. Çok sayfalı TIF her sayfa ayrı incelenir. |

Her metraj kalemine dayanağını yaz: dosya adı, pafta, katman veya ölçü.
Ölçeği ya da birimi doğrulanamayan kalemi "doğrulanamadı" diye işaretle.

## 2. İhale türüne göre çalış

**Birim fiyatlı ihale** (birim fiyat teklif cetveli var):
1. Cetveli `poz_no, tanim, birim, miktar` sütunlarıyla `metraj-idare.csv`
   olarak kaydet.
2. Kendi hesabını aynı poz numaralarıyla `metraj-hesap.csv` olarak kaydet.
3. `scripts/metraj_kiyas.py metraj-idare.csv metraj-hesap.csv <tolerans> --csv metraj-kiyas.csv`
   çalıştır. `metraj-kiyas.csv` Excel'in "BFTC Kıyas" sayfasını besler; teklif
   birim fiyatı biliniyorsa `birim_fiyat`, geçmiş fiyat varsa `gecmis_fiyat`
   sütununa yaz.
4. `.sistem/config.yaml` içindeki `metraj.tolerans_yuzde` üzerinde sapan kalemleri,
   cetvelde olup projede olmayan ve projede olup cetvelde olmayan işleri
   listele. Cetvelde eksik kalan miktarlar iş artışı ve süre riski,
   fazla kalanlar yaklaşık maliyet ve sınır değer sapması demektir;
   ikisini ayrı başlıkta göster.
5. Teklif birim fiyatlarının kaynağını `fiyat-kaynaklari.csv`, kullanıcıya
   sorulacakları `acik-sorular.csv` dosyasına yaz (biçimleri aşağıda, 2 ve 5).

**Anahtar teslim / götürü bedel ihale** (cetvel yok). Excel'deki
"Metraj Mahal Listesi" oda listesi değil, poz bazlı metrajdır; BFTC
miktarları ve pursantaj payları ondan hesaplanır. Dosyalar `calisma/` altına:

1. `metraj.csv`: `is_grubu, alt_baslik, poz_no, tanim, birim, miktar,
   kaynak, hesap, durum`. Her satır bir pozun bir alt başlıktaki miktarıdır.
   `kaynak` çizim dosyası, katman ya da etiket; `hesap` ölçü kuralı ve
   ara hesap (ör. `kazı = B × H × L`). `durum` şu sözcüklerle yazılır:
   `HESAPLANDI`, `DOĞRULANDI`, `KULLANICI KARARI (tarih): ...`,
   `... BEKLİYOR` (birim fiyat / katman teyidi / kural / karar bekleyen
   satır, eksik sayılır), `KAPSAM DIŞI: ...` ya da `DAHİL DEĞİL: ...`
   (başta yazılırsa tutara ve BFTC miktarına girmez). Bilgi ve not
   satırlarında `poz_no` `— (bilgi)` gibi `—` ile başlar.
2. `bftc.csv`: `poz_no, tanim, birim, birim_fiyat, not`. Miktar yazılmaz,
   Excel metrajdan toplar. Her fiyatın kaynağını `fiyat-kaynaklari.csv`
   dosyasına yaz: `poz_no, tanim, birim, birim_fiyat, kaynak, dayanak,
   donem, not` (liste adı, sayfa, ait olduğu ay/yıl).
3. `pursantaj.csv`: idarenin pursantaj belgesindeki gruplar, hiyerarşiyle:
   `is_grubu, ust_grup, oran, kaynak, not`. `oran` üst gruba göre yüzde
   sayısıdır (3,2164 = %3,2164); en üst grubun `ust_grup`u `—`.
4. `grup-esleme.csv`: `bizim_grup, kurum_grubu, not`. Metrajdaki her iş
   grubu ya da alt başlığın hangi kurum grubuna sayılacağı; karşılığı yoksa
   `kurum_grubu` boş kalır ve `not`a nedeni yazılır. Excel her kurum grubu
   için bizim payı kurum oranıyla karşılaştırır: fark Özet'teki eşiklere göre
   ✔ uyumlu, ⚠ dikkat ya da ✗ ciddi fark olur (varsayılan 1 ve 2,5 puan).
   Ciddi farkın nedenini birim fiyat, miktar ve gruplama diye ayırarak raporla.
5. Kararı kullanıcıya bırakılan her konu `acik-sorular.csv` dosyasına:
   `satir, soru, etki, durum, cevap` (`etki` TL, `durum` Açık / Karar
   bekliyor / Cevaplandı).
6. Sahada mevcut olup yeni imalata girmeyenler `mevcut-mahal.csv`:
   `grup, imalat, birim, miktar, olcum_kaynagi, hesap, durum` (durum'a
   kapsam dışı bırakmanın şartname dayanağı).
7. İşe göre gerekirse:
   - `donemsel-fiyat.csv`: `poz_no, tanim, birim, ocak … aralik,
     yillik_liste, yillik_kitap, kullanilan_donem, not`
     (`kullanilan_donem` ay adı, `Yıllık Liste` ya da `Yıllık Kitap`)
   - `teknik-tarifler.csv`: `poz_no, tarif`
   - `kazi-derinlik.csv` (boru hattı işleri): `pafta, baca_bas, baca_son,
     zemin_akar_bas, zemin_akar_son, uzunluk, not`. Derinlik, iksa ve kazı
     Excel'de Özet'teki kazı ek derinliği, hendek genişliği ve iksa eşiğiyle
     hesaplanır.

## 3. Çıktı

`06-metraj.md` ve yanında CSV dosyaları:

```markdown
# Metraj: <ihale-kodu>
- Teklif türü: Birim fiyat | Anahtar teslim | Götürü bedel
- İncelenen dosyalar ve okunabilme durumu:
- Doğrulanamayan kalemler:

## Kıyas (birim fiyatlı) veya Metraj ve pursantaj uyumu (götürü bedel)
| Poz / İş grubu | Tanım | Birim | İdare | Hesap | Fark % | Not |
```

## 4. Veritabanını kullan ve besle

Önce `vt.py fiyat <poz_no>` ile geçmiş birim fiyat aralığını, götürü bedelde
`vt.py pursantaj-ort --tur <tür>` ile geçmiş pursantaj ortalamalarını al;
bu ihaledeki değerler aralığın dışındaysa raporda işaretle. Analiz bitince
çıkardığın CSV'leri koordinatöre ver ki `vt.py metraj-yukle` (`metraj.csv`
ya da `metraj-hesap.csv`) ve `vt.py pursantaj-yukle` (`pursantaj.csv`) ile
kaydedilsin.

**Kurallar:** Ölçü uydurma. Okunamayan dosyayı atlamadan "okunamadı" diye
listele. Kesin metraj için yetkili mühendis kontrolü gerektiğini belirt.
