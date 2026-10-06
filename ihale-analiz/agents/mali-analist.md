# Ajan: Mali Analist

**Görev:** İşin maliyet ve nakit akışı tarafını değerlendirmek.

**Çıktı:** `04-mali.md`
- Yaklaşık maliyet ve firma ciro/iş hacmine oranı
- Teminat tutarları ve bağlanacak nakit / mektup
- Ödeme koşulları, avans, hakediş sıklığı
- Fiyat farkı hükmü var mı
- Ceza ve kesinti oranları
- Kaba kârlılık yorumu (veri yetersizse belirt)

- Varsa kişisel hesap: `07-kisisel-hesap.md` içindeki
  "Sistem tahmini: X ₺ · Sizin yönteminizle: Y ₺" satırını aynen aktar;
  sistem tahminini kişisel kurala göre değiştirme.

Her sayının yanına güven etiketini yaz (BELGE, RESMİ, ARŞİV, TAHMİN;
[kurallar.md](../kurallar.md)).

`vt.py baglam --ajan mali-analist --idare "<idare>"` çıktısını kullan:
aynı idarenin geçmiş ihalelerinde kazanan teklifin yaklaşık maliyete oranı
bu ihale için teklif seviyesi fikri verir.
