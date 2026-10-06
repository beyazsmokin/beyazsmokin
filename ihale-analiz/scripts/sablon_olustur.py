#!/usr/bin/env python3
"""Excel rapor şablonlarını üretir. Şablonun tek kaynağı bu dosyadır.

Kullanım: python3 sablon_olustur.py [cikti-klasoru]   (varsayılan: templates/excel)

Üretir:
  birim-fiyat.xlsx     BFTC'li (birim fiyat teklif cetvelli) ihaleler
  anahtar-teslim.xlsx  Anahtar teslim / götürü bedel ihaleler

Her şablonda gizli "_harita" sayfası, hangi sayfa sütununun hangi analiz
dosyasından doldurulacağını tanımlar; excel_rapor.py yalnızca bu haritaya
göre yazar, şablonun yapısını değiştirmez. Şablonda değişiklik isteniyorsa
bu dosya güncellenip yeniden çalıştırılır.
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

SURUM = "1.0"
SATIR = 500                      # veri satırı kapasitesi
BAS = 5                          # ilk veri satırı (1 başlık, 2 açıklama, 3 toplam, 4 sütun adları)
SON = BAS + SATIR - 1

LACIVERT = "163460"
TOPRAK = "C8A57A"
GIRIS = PatternFill("solid", fgColor="FFFFFF")
HESAP = PatternFill("solid", fgColor="EEF1F6")
TOPLAM = PatternFill("solid", fgColor="F3E9DA")
BASLIK = PatternFill("solid", fgColor=LACIVERT)
SUTUN = PatternFill("solid", fgColor="2B4C7E")
INCE = Side(style="thin", color="D0D5DD")
KENAR = Border(left=INCE, right=INCE, top=INCE, bottom=INCE)
PARA = '#,##0.00'
MIKTAR = '#,##0.000'
YUZDE = '0.0%'

KIRMIZI = PatternFill("solid", fgColor="F4C7C3")
TURUNCU = PatternFill("solid", fgColor="FCD9B6")
SARI = PatternFill("solid", fgColor="FCE8B2")
YESIL = PatternFill("solid", fgColor="D9EAD3")


def baslik(ws, metin, aciklama, genislik):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=genislik)
    c = ws.cell(1, 1, metin)
    c.font = Font(bold=True, size=14, color="FFFFFF")
    c.fill = BASLIK
    c.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 28
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=genislik)
    c = ws.cell(2, 1, aciklama)
    c.font = Font(italic=True, size=9, color="667085")
    c.alignment = Alignment(wrap_text=True, vertical="top", indent=1)
    ws.row_dimensions[2].height = 30


def tablo(ws, sutunlar, toplamlar=()):
    """sutunlar: (başlık, genişlik, biçim, formül şablonu veya None). Formülde {r} satır no."""
    for j, (ad, gen, bicim, formul) in enumerate(sutunlar, 1):
        harf = get_column_letter(j)
        c = ws.cell(4, j, ad)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = SUTUN
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = KENAR
        ws.column_dimensions[harf].width = gen
        for r in range(BAS, SON + 1):
            h = ws.cell(r, j)
            if formul:
                h.value = formul.format(r=r)
                h.fill = HESAP
            if bicim:
                h.number_format = bicim
            h.border = KENAR
            h.alignment = Alignment(vertical="top", wrap_text=bicim is None)
    ws.row_dimensions[4].height = 32
    ws.cell(3, 1, "TOPLAM").font = Font(bold=True)
    for j in range(1, len(sutunlar) + 1):
        ws.cell(3, j).fill = TOPLAM
        ws.cell(3, j).border = KENAR
    for j in toplamlar:
        harf = get_column_letter(j)
        c = ws.cell(3, j, f"=SUM({harf}{BAS}:{harf}{SON})")
        c.font = Font(bold=True)
        c.number_format = sutunlar[j - 1][2] or PARA
    ws.freeze_panes = ws.cell(BAS, 1)
    ws.auto_filter.ref = f"A4:{get_column_letter(len(sutunlar))}{SON}"
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.print_title_rows = "4:4"


def secim(ws, sutun, secenekler):
    dv = DataValidation(type="list", formula1='"' + ",".join(secenekler) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{sutun}{BAS}:{sutun}{SON}")


def renk(ws, aralik, kurallar):
    for metin, dolgu in kurallar:
        ws.conditional_formatting.add(
            aralik, FormulaRule(formula=[f'ISNUMBER(SEARCH("{metin}",{aralik.split(":")[0]}))'], fill=dolgu))


TOLERANSLAR = {  # Özet'teki ad -> (tanımlı ad, varsayılan)
    "Metraj Toleransı": ("MetrajTol", 0.05),
    "Pursantaj Toleransı (puan)": ("PursantajTol", 0.02),
}


def ozet(wb, tur, sonuc_satirlari, toleranslar):
    ws = wb.active
    ws.title = "Özet"
    baslik(ws, f"İHALE ANALİZ RAPORU · {tur}",
           "Beyaz hücreler analizden doldurulur, gri hücreler hesaplanır. Karar ve gerekçe raporun ilk satırıdır.", 5)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 48
    ws.column_dimensions["C"].width = 4
    ws.column_dimensions["D"].width = 30
    alanlar = [
        ("İhale Kayıt No (İKN)", None), ("İdare", None), ("İşin Adı", None), ("İhale Usulü", None),
        ("Teklif Türü", None), ("İhale Tarihi ve Saati", None), ("Yaklaşık Maliyet", PARA),
        ("Geçici Teminat Oranı", YUZDE), ("Geçici Teminat Tutarı", PARA), ("İşin Süresi", None),
        ("İşin Yeri", None), ("Karar", None), ("Karar Gerekçesi", None),
        *[(ad, YUZDE) for ad in toleranslar], ("Analiz Tarihi", "dd.mm.yyyy"),
    ]
    r = 4
    ws.cell(3, 1, "İHALE BİLGİLERİ").font = Font(bold=True, color=LACIVERT, size=11)
    satir = {}
    for ad, bicim in alanlar:
        a = ws.cell(r, 1, ad)
        a.font = Font(bold=True)
        a.border = KENAR
        b = ws.cell(r, 2)
        b.border = KENAR
        b.alignment = Alignment(wrap_text=True, vertical="top")
        if bicim:
            b.number_format = bicim
        satir[ad] = r
        r += 1
    ym, oran = satir["Yaklaşık Maliyet"], satir["Geçici Teminat Oranı"]
    ws.cell(satir["Geçici Teminat Tutarı"], 2, f'=IF(OR(B{ym}="",B{oran}=""),"",B{ym}*B{oran})').fill = HESAP
    for ad in toleranslar:
        isim, varsayilan = TOLERANSLAR[ad]
        ws.cell(satir[ad], 2, varsayilan)
        wb.defined_names[isim] = DefinedName(isim, attr_text=f"'Özet'!$B${satir[ad]}")
    k = ws.cell(satir["Karar"], 2)
    k.font = Font(bold=True, size=12)
    dv = DataValidation(type="list", formula1='"Katıl,Şartlı katıl,Katılma"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(k.coordinate)
    ws.conditional_formatting.add(k.coordinate, CellIsRule(operator="equal", formula=['"Katıl"'], fill=YESIL))
    ws.conditional_formatting.add(k.coordinate, CellIsRule(operator="equal", formula=['"Şartlı katıl"'], fill=SARI))
    ws.conditional_formatting.add(k.coordinate, CellIsRule(operator="equal", formula=['"Katılma"'], fill=KIRMIZI))

    wb.defined_names["YaklasikMaliyet"] = DefinedName("YaklasikMaliyet", attr_text=f"'Özet'!$B${ym}")

    ws.cell(3, 4, "SONUÇ ÖZETİ").font = Font(bold=True, color=LACIVERT, size=11)
    r = 4
    for ad, formul, bicim in sonuc_satirlari:
        a = ws.cell(r, 4, ad)
        a.font = Font(bold=True)
        a.border = KENAR
        b = ws.cell(r, 5, formul)
        b.fill = HESAP
        b.border = KENAR
        b.number_format = bicim
        r += 1
    ws.column_dimensions["E"].width = 22
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return satir


def ortak_sayfalar(wb):
    ws = wb.create_sheet("Yeterlilik")
    baslik(ws, "YETERLİLİK KONTROLÜ", "İdari şartnamedeki katılım ve yeterlilik koşullarının firma profiliyle karşılaştırması.", 5)
    tablo(ws, [("Sıra", 6, None, None), ("Koşul", 50, None, None), ("Şartname Maddesi", 16, None, None),
               ("Firma Durumu", 16, None, None), ("Not", 50, None, None)])
    secim(ws, "D", ["Karşılıyor", "Eksik", "Belirsiz"])
    renk(ws, f"D{BAS}:D{SON}", [("Eksik", KIRMIZI), ("Belirsiz", SARI), ("Karşılıyor", YESIL)])

    ws = wb.create_sheet("Teknik")
    baslik(ws, "TEKNİK DEĞERLENDİRME", "Teknik şartname gereksinimleri, karşılanamayan ve rekabeti kısıtlayan maddeler.", 5)
    tablo(ws, [("Sıra", 6, None, None), ("Gereksinim", 50, None, None), ("Şartname Maddesi", 16, None, None),
               ("Durum", 18, None, None), ("Not", 50, None, None)])
    secim(ws, "D", ["Karşılanıyor", "Karşılanamıyor", "Belirsiz", "Kısıtlayıcı"])
    renk(ws, f"D{BAS}:D{SON}", [("Karşılanamıyor", KIRMIZI), ("Kısıtlayıcı", TURUNCU), ("Belirsiz", SARI)])

    ws = wb.create_sheet("Mali")
    baslik(ws, "MALİ DEĞERLENDİRME", "Teminat, ödeme, avans, fiyat farkı, ceza ve kârlılık kalemleri.", 5)
    tablo(ws, [("Sıra", 6, None, None), ("Kalem", 36, None, None), ("Değer", 22, None, None),
               ("Kaynak", 18, None, None), ("Not", 56, None, None)])

    ws = wb.create_sheet("Riskler")
    baslik(ws, "RİSK LİSTESİ", "Risk denetçisinin derecelendirdiği riskler ve önlemler.", 5)
    tablo(ws, [("Sıra", 6, None, None), ("Risk", 50, None, None), ("Kaynak", 18, None, None),
               ("Seviye", 12, None, None), ("Önlem", 50, None, None)])
    secim(ws, "D", ["Düşük", "Orta", "Yüksek"])
    renk(ws, f"D{BAS}:D{SON}", [("Yüksek", KIRMIZI), ("Orta", SARI), ("Düşük", YESIL)])

    ws = wb.create_sheet("Kişisel Hesap")
    baslik(ws, "KİŞİSEL HESAP",
           "Kullanıcının kendi hesap kurallarıyla bulunan tutarın sistem tahminiyle karşılaştırması "
           "(kisisel_hesap.py çıktısı).", 10)
    tablo(ws, [("Sıra", 6, None, None), ("Poz No", 16, None, None), ("Tanım", 40, None, None),
               ("Birim", 8, None, None), ("Miktar", 13, MIKTAR, None), ("Birim Fiyat", 14, PARA, None),
               ("Sistem Tutarı", 17, PARA, None), ("Kişisel Tutar", 17, PARA, None),
               ("Fark", 15, PARA, '=IF(OR(G{r}="",H{r}=""),"",H{r}-G{r})'),
               ("Uygulanan Kurallar", 36, None, None)], toplamlar=(7, 8, 9))

    ws = wb.create_sheet("Yapılacaklar")
    baslik(ws, "TEKLİF ÖNCESİ YAPILACAKLAR", "Teklif verilmeden tamamlanacak işler.", 5)
    tablo(ws, [("Sıra", 6, None, None), ("İş", 56, None, None), ("Son Tarih", 14, "dd.mm.yyyy", None),
               ("Sorumlu", 20, None, None), ("Durum", 14, None, None)])
    secim(ws, "E", ["Bekliyor", "Devam ediyor", "Tamam"])
    renk(ws, f"E{BAS}:E{SON}", [("Tamam", YESIL), ("Devam", SARI)])


ORTAK_HARITA = [
    # sayfa, kaynak, sütun başlığı, alan adları (| ile alternatif)
    ("Özet", "alanlar:01-ozet.md", "İhale Kayıt No (İKN)", "İKN|İhale kayıt no|İhale kodu"),
    ("Özet", "alanlar:01-ozet.md", "İdare", "İdare"),
    ("Özet", "alanlar:01-ozet.md", "İşin Adı", "İşin adı|İşin adı / niteliği / miktarı|İş"),
    ("Özet", "alanlar:01-ozet.md", "İhale Usulü", "İhale usulü"),
    ("Özet", "alanlar:01-ozet.md", "Teklif Türü", "Teklif türü|Teklif türü (birim fiyat / götürü bedel)"),
    ("Özet", "alanlar:01-ozet.md", "İhale Tarihi ve Saati", "İhale tarihi ve saati|İhale tarihi"),
    ("Özet", "alanlar:01-ozet.md", "Yaklaşık Maliyet", "Yaklaşık maliyet|Yaklaşık maliyet (açıklanmışsa)"),
    ("Özet", "alanlar:01-ozet.md", "Geçici Teminat Oranı", "Geçici teminat oranı"),
    ("Özet", "alanlar:01-ozet.md", "İşin Süresi", "İşin süresi|İşin süresi / yeri"),
    ("Özet", "alanlar:01-ozet.md", "İşin Yeri", "İşin yeri"),
    ("Özet", "karar:rapor", "Karar", "karar"),
    ("Özet", "karar:rapor", "Karar Gerekçesi", "gerekce"),
    ("Özet", "karar:rapor", "Analiz Tarihi", "tarih"),
    ("Yeterlilik", "tablo:02-idari.md", "Sıra", "#sira"),
    ("Yeterlilik", "tablo:02-idari.md", "Koşul", "Koşul"),
    ("Yeterlilik", "tablo:02-idari.md", "Şartname Maddesi", "Madde"),
    ("Yeterlilik", "tablo:02-idari.md", "Firma Durumu", "Firma durumu|Firma durumu (Karşılıyor / Eksik / Belirsiz)|Durum"),
    ("Yeterlilik", "tablo:02-idari.md", "Not", "Not"),
    ("Teknik", "tablo:03-teknik.md", "Sıra", "#sira"),
    ("Teknik", "tablo:03-teknik.md", "Gereksinim", "Gereksinim"),
    ("Teknik", "tablo:03-teknik.md", "Şartname Maddesi", "Madde"),
    ("Teknik", "tablo:03-teknik.md", "Durum", "Durum"),
    ("Teknik", "tablo:03-teknik.md", "Not", "Not"),
    ("Mali", "tablo:04-mali.md", "Sıra", "#sira"),
    ("Mali", "tablo:04-mali.md", "Kalem", "Kalem"),
    ("Mali", "tablo:04-mali.md", "Değer", "Değer"),
    ("Mali", "tablo:04-mali.md", "Kaynak", "Kaynak|Madde"),
    ("Mali", "tablo:04-mali.md", "Not", "Not"),
    ("Riskler", "tablo:05-riskler.md", "Sıra", "#sira"),
    ("Riskler", "tablo:05-riskler.md", "Risk", "Risk"),
    ("Riskler", "tablo:05-riskler.md", "Kaynak", "Kaynak"),
    ("Riskler", "tablo:05-riskler.md", "Seviye", "Seviye|Seviye (Düşük/Orta/Yüksek)"),
    ("Riskler", "tablo:05-riskler.md", "Önlem", "Önlem"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Sıra", "#sira"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Poz No", "poz_no"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Tanım", "tanim"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Birim", "birim"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Miktar", "miktar"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Birim Fiyat", "birim_fiyat"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Sistem Tutarı", "sistem_tutar"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Kişisel Tutar", "kisisel_tutar"),
    ("Kişisel Hesap", "csv:kisisel-hesap.csv", "Uygulanan Kurallar", "uygulanan_kurallar"),
    ("Yapılacaklar", "csv:yapilacaklar.csv", "Sıra", "#sira"),
    ("Yapılacaklar", "csv:yapilacaklar.csv", "İş", "is"),
    ("Yapılacaklar", "csv:yapilacaklar.csv", "Son Tarih", "son_tarih"),
    ("Yapılacaklar", "csv:yapilacaklar.csv", "Sorumlu", "sorumlu"),
    ("Yapılacaklar", "csv:yapilacaklar.csv", "Durum", "durum"),
]


def harita(wb, satirlar, tur):
    ws = wb.create_sheet("_harita")
    ws.append(["sablon", tur, "surum", SURUM])
    ws.append(["sayfa", "kaynak", "sütun başlığı", "alan"])
    for s in satirlar:
        ws.append(list(s))
    ws.sheet_state = "hidden"


def birim_fiyat(cikti: Path):
    wb = Workbook()
    K = "'BFTC Kıyas'"
    ozet(wb, "BİRİM FİYAT (BFTC)", [
        ("İdare Yaklaşık Maliyet", f"={K}!J3", PARA),
        ("Teklif tutarı (hesap miktarı)", f"={K}!K3", PARA),
        ("İdare YM / açıklanan yaklaşık maliyet", f'=IF(OR(YaklasikMaliyet="",{K}!J3=0),"",{K}!J3/YaklasikMaliyet)', YUZDE),
        ("Kalem sayısı", f'=COUNTA({K}!B{BAS}:B{SON})', "0"),
        ("Cetvelde eksik kalem", f'=COUNTIF({K}!L{BAS}:L{SON},"Cetvelde eksik")', "0"),
        ("Cetvelde fazla kalem", f'=COUNTIF({K}!L{BAS}:L{SON},"Cetvelde fazla")', "0"),
        ("Projede bulunamayan", f'=COUNTIF({K}!L{BAS}:L{SON},"Projede bulunamadı")', "0"),
        ("Cetvelde olmayan iş", f'=COUNTIF({K}!L{BAS}:L{SON},"Cetvelde yok")', "0"),
        ("Yüksek risk", f'=COUNTIF(Riskler!D{BAS}:D{SON},"Yüksek")', "0"),
        ("Eksik yeterlilik", f'=COUNTIF(Yeterlilik!D{BAS}:D{SON},"Eksik")', "0"),
        ("Sistem tahmini (kişisel hesap)", "='Kişisel Hesap'!G3", PARA),
        ("Sizin yönteminizle", "='Kişisel Hesap'!H3", PARA),
    ], toleranslar=["Metraj Toleransı"])

    ws = wb.create_sheet("BFTC Kıyas")
    baslik(ws, "BİRİM FİYAT TEKLİF CETVELİ · METRAJ KIYASI",
           "İdare miktarı cetvelden, hesaplanan miktar projeden gelir. Durum, Özet sayfasındaki metraj toleransına göre "
           "hesaplanır. Teklif birim fiyatı girildiğinde tutarlar oluşur.", 14)
    tablo(ws, [
        ("Sıra No", 7, None, None),
        ("Poz No", 16, None, None),
        ("İş Kalemi Tanımı", 44, None, None),
        ("Birim", 8, None, None),
        ("İdare Miktarı", 14, MIKTAR, None),
        ("Hesaplanan Miktar", 14, MIKTAR, None),
        ("Fark", 13, MIKTAR, '=IF(OR(E{r}="",F{r}=""),"",F{r}-E{r})'),
        ("Fark %", 9, YUZDE, '=IF(OR(E{r}="",F{r}="",E{r}=0),"",(F{r}-E{r})/E{r})'),
        ("Teklif Birim Fiyatı", 14, PARA, None),
        ("Tutar (İdare Miktarı)", 17, PARA, '=IF(OR(E{r}="",I{r}=""),"",E{r}*I{r})'),
        ("Tutar (Hesap Miktarı)", 17, PARA, '=IF(OR(F{r}="",I{r}=""),"",F{r}*I{r})'),
        ("Durum", 18, None,
         '=IF(B{r}="","",IF(E{r}="","Cetvelde yok",IF(F{r}="","Projede bulunamadı",'
         'IF(H{r}>MetrajTol,"Cetvelde eksik",IF(H{r}<-MetrajTol,"Cetvelde fazla","Uygun")))))'),
        ("Geçmiş Birim Fiyat (Ort.)", 15, PARA, None),
        ("Not", 40, None, None),
    ], toplamlar=(10, 11))
    renk(ws, f"L{BAS}:L{SON}", [("Cetvelde eksik", TURUNCU), ("Cetvelde fazla", SARI),
                                ("Projede bulunamadı", KIRMIZI), ("Cetvelde yok", KIRMIZI), ("Uygun", YESIL)])
    # teklif fiyatı geçmiş ortalamadan %20'den fazla sapıyorsa işaretle
    ws.conditional_formatting.add(
        f"I{BAS}:I{SON}",
        FormulaRule(formula=[f'AND(ISNUMBER(I{BAS}),ISNUMBER(M{BAS}),M{BAS}>0,ABS(I{BAS}/M{BAS}-1)>0.2)'], fill=SARI))

    ortak_sayfalar(wb)
    harita(wb, ORTAK_HARITA + [
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Sıra No", "#sira"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Poz No", "poz_no"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "İş Kalemi Tanımı", "tanim"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Birim", "birim"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "İdare Miktarı", "idare"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Hesaplanan Miktar", "hesap"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Teklif Birim Fiyatı", "birim_fiyat"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Geçmiş Birim Fiyat (Ort.)", "gecmis_fiyat"),
        ("BFTC Kıyas", "csv:metraj-kiyas.csv", "Not", "not"),
    ], "birim-fiyat")
    wb.save(cikti / "birim-fiyat.xlsx")


def anahtar_teslim(cikti: Path):
    wb = Workbook()
    ozet(wb, "ANAHTAR TESLİM / GÖTÜRÜ BEDEL", [
        ("Keşif toplamı", "='Keşif'!H3", PARA),
        ("Keşif / yaklaşık maliyet", '=IF(OR(YaklasikMaliyet="",\'Keşif\'!H3=0),"",\'Keşif\'!H3/YaklasikMaliyet)', YUZDE),
        ("Mahal sayısı", f"=COUNTA('Mahal Listesi'!C{BAS}:C{SON})", "0"),
        ("Toplam taban alanı (m²)", "='Mahal Listesi'!D3", '#,##0.00'),
        ("Pursantaj toplamı", "=Pursantaj!B3", YUZDE),
        ("Finansman yükü olan iş grubu", f'=COUNTIF(Pursantaj!F{BAS}:F{SON},"Finansman yükü*")', "0"),
        ("Yüksek risk", f'=COUNTIF(Riskler!D{BAS}:D{SON},"Yüksek")', "0"),
        ("Eksik yeterlilik", f'=COUNTIF(Yeterlilik!D{BAS}:D{SON},"Eksik")', "0"),
        ("Sistem tahmini (kişisel hesap)", "='Kişisel Hesap'!G3", PARA),
        ("Sizin yönteminizle", "='Kişisel Hesap'!H3", PARA),
    ], toleranslar=["Pursantaj Toleransı (puan)"])

    ws = wb.create_sheet("Mahal Listesi")
    baslik(ws, "MAHAL LİSTESİ",
           "Projeden ya da idarenin mahal listesinden çıkarılan mahaller. Duvar alanı çevre × yükseklikten hesaplanır "
           "(kapı ve pencere boşlukları düşülmemiştir).", 13)
    tablo(ws, [
        ("Kat", 8, None, None),
        ("Mahal No", 10, None, None),
        ("Mahal Adı", 26, None, None),
        ("Taban Alanı (m²)", 12, '#,##0.00', None),
        ("Çevre (m)", 10, '#,##0.00', None),
        ("Yükseklik (m)", 10, '#,##0.00', None),
        ("Duvar Alanı (m²)", 12, '#,##0.00', '=IF(OR(E{r}="",F{r}=""),"",E{r}*F{r})'),
        ("Kapı Adedi", 8, "0", None),
        ("Pencere Adedi", 8, "0", None),
        ("Döşeme Kaplaması", 20, None, None),
        ("Duvar Kaplaması", 20, None, None),
        ("Tavan Kaplaması", 20, None, None),
        ("Not", 30, None, None),
    ], toplamlar=(4, 7, 8, 9))

    ws = wb.create_sheet("Keşif")
    baslik(ws, "KEŞİF",
           "Mahal listesinden çıkarılan keşif kalemleri. İş grubu, Pursantaj sayfasındaki iş grubu adıyla birebir aynı "
           "yazılmalıdır; pursantaj uyumu buna göre hesaplanır.", 10)
    tablo(ws, [
        ("Sıra No", 7, None, None),
        ("İş Grubu", 22, None, None),
        ("Poz / Kalem No", 16, None, None),
        ("Tanım", 44, None, None),
        ("Birim", 8, None, None),
        ("Miktar", 13, MIKTAR, None),
        ("Birim Fiyat", 14, PARA, None),
        ("Tutar", 17, PARA, '=IF(OR(F{r}="",G{r}=""),"",F{r}*G{r})'),
        ("Mahal", 18, None, None),
        ("Not", 30, None, None),
    ], toplamlar=(8,))

    ws = wb.create_sheet("Pursantaj")
    baslik(ws, "PURSANTAJ UYUMU",
           "İdarenin pursantaj oranları ile keşifte her iş grubunun maliyet payı karşılaştırılır. Keşif payı pursantajdan "
           "yüksekse iş grubu yapıldığında ödenen tutar maliyeti karşılamaz (finansman yükü).", 6)
    tablo(ws, [
        ("İş Grubu", 30, None, None),
        ("Pursantaj Oranı", 13, YUZDE, None),
        ("Keşif Tutarı", 17, PARA, f'=IF(A{{r}}="","",SUMIF(\'Keşif\'!$B${BAS}:$B${SON},A{{r}},\'Keşif\'!$H${BAS}:$H${SON}))'),
        ("Keşif Payı", 11, YUZDE, '=IF(OR(A{r}="",\'Keşif\'!$H$3=0),"",C{r}/\'Keşif\'!$H$3)'),
        ("Fark (puan)", 11, YUZDE, '=IF(OR(B{r}="",D{r}=""),"",D{r}-B{r})'),
        ("Değerlendirme", 34, None,
         '=IF(E{r}="","",IF(E{r}>PursantajTol,"Finansman yükü: maliyet ödemeden önde",'
         'IF(E{r}<-PursantajTol,"Lehte: ödeme maliyetten önde","Uyumlu")))'),
    ], toplamlar=(2, 3))
    renk(ws, f"F{BAS}:F{SON}", [("Finansman", KIRMIZI), ("Lehte", YESIL), ("Uyumlu", YESIL)])
    ws.conditional_formatting.add(
        "B3", FormulaRule(formula=['AND(B3<>0,ABS(B3-1)>0.001)'], fill=KIRMIZI))

    ortak_sayfalar(wb)
    harita(wb, ORTAK_HARITA + [
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Kat", "kat"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Mahal No", "mahal_no"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Mahal Adı", "mahal_adi"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Taban Alanı (m²)", "alan"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Çevre (m)", "cevre"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Yükseklik (m)", "yukseklik"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Kapı Adedi", "kapi"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Pencere Adedi", "pencere"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Döşeme Kaplaması", "doseme"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Duvar Kaplaması", "duvar"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Tavan Kaplaması", "tavan"),
        ("Mahal Listesi", "csv:mahal-listesi.csv", "Not", "not"),
        ("Keşif", "csv:kesif.csv", "Sıra No", "#sira"),
        ("Keşif", "csv:kesif.csv", "İş Grubu", "is_grubu"),
        ("Keşif", "csv:kesif.csv", "Poz / Kalem No", "poz_no"),
        ("Keşif", "csv:kesif.csv", "Tanım", "tanim"),
        ("Keşif", "csv:kesif.csv", "Birim", "birim"),
        ("Keşif", "csv:kesif.csv", "Miktar", "miktar"),
        ("Keşif", "csv:kesif.csv", "Birim Fiyat", "birim_fiyat"),
        ("Keşif", "csv:kesif.csv", "Mahal", "mahal"),
        ("Keşif", "csv:kesif.csv", "Not", "not"),
        ("Pursantaj", "csv:pursantaj.csv", "İş Grubu", "is_grubu"),
        ("Pursantaj", "csv:pursantaj.csv", "Pursantaj Oranı", "oran%"),
    ], "anahtar-teslim")
    wb.save(cikti / "anahtar-teslim.xlsx")


def main() -> None:
    cikti = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "templates" / "excel"
    cikti.mkdir(parents=True, exist_ok=True)
    birim_fiyat(cikti)
    anahtar_teslim(cikti)
    print(f"Şablonlar: {cikti}")


if __name__ == "__main__":
    main()
