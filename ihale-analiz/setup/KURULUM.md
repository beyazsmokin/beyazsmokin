# İlk Çalıştırma Kurulumu

Bu talimat yalnızca çalışma alanında `config.yaml` bulunmadığında uygulanır.

## Kod çalıştırabilen platformlar

```bash
python3 scripts/init_workspace.py            # varsayılan: ~/ihale-analiz-calisma
python3 scripts/init_workspace.py /baska/yol # özel konum
```

Betik `setup/workspace-template/` içeriğini hedefe kopyalar, mevcut
dosyaların üzerine yazmaz.

## Kod çalıştıramayan ama dosya yazabilen platformlar

`setup/workspace-template/` altındaki her dosyayı aynı göreli yolla
çalışma alanına elle oluştur.

## Dosya sistemi olmayan platformlar

Kullanıcıya hafızanın sohbette tutulacağını söyle, `firma-profili.md`
şablonundaki soruları sor ve oturum sonunda hafızayı tek blok halinde ver.

## Kurulumdan sonra

1. Kullanıcıya firma profili sorularını sor (`hafiza/firma-profili.md`).
   Cevap vermek istemediği alanları boş bırak.
2. `config.yaml` içinde `kurulum_tarihi` ve `platform` alanlarını doldur.
3. Kullanıcıya kurulumun bittiğini ve çalışma alanının yolunu söyle.
