// İhale Analiz paneli. Bağımlılık yok; veriler bu bilgisayardaki panel.py sunucusundan gelir.
"use strict";

const $ = (s, k = document) => k.querySelector(s);
const $$ = (s, k = document) => [...k.querySelectorAll(s)];
const e = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];
const TUR_AD = { birim_fiyat: "Birim fiyatlı", anahtar_teslim: "Anahtar teslim", goturu_bedel: "Götürü bedel", karma: "Karma" };

const S = { sabit: null, cevrimdisi: false, sayac: null, yoklama: null, ihaleFiltre: "aktif", ihaleAra: "",
  ihaleSira: "tarih", ajandaAy: null, ajandaSecili: null, ajandaGorunum: "ay", detaySekme: "genel" };

const IKON = {
  gosterge: '<path d="M3 13h8V3H3zm10 8h8V11h-8zM3 21h8v-6H3zm10-18v6h8V3z"/>',
  ihaleler: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  ajanda: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  raporlar: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M8 7h8M8 11h6"/>',
  taramalar: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  ogrenme: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/>',
  ayarlar: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
};
const svg = (ad) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${IKON[ad]}</svg>`;
const SAYFALAR = [
  ["gosterge", "Gösterge", ""], ["ihaleler", "İhaleler", "ihaleler"], ["ajanda", "Ajanda", "ajanda"],
  ["raporlar", "Raporlar", "raporlar"], ["taramalar", "Taramalar", "taramalar"], ["ogrenme", "Öğrenme", "ogrenme"],
  ["ayarlar", "Ayarlar", "ayarlar"],
];

// --- Yardımcılar -------------------------------------------------------------------

async function api(yol, secenek = {}) {
  const ist = { method: secenek.method || "GET", headers: { "X-Ihale-Panel": "1" } };
  if (secenek.govde !== undefined) {
    ist.headers["Content-Type"] = "application/json";
    ist.body = JSON.stringify(secenek.govde);
  }
  let y;
  try {
    y = await fetch("/api/" + yol, ist);
  } catch {
    cevrimdisi(true);
    throw new Error("Panel sunucusuna ulaşılamadı. panel.py çalışıyor mu?");
  }
  cevrimdisi(y.headers.get("X-Onbellek") === "1");
  const veri = await y.json().catch(() => ({}));
  if (!y.ok) throw new Error(veri.hata || `Hata ${y.status}`);
  return veri;
}

function cevrimdisi(durum) {
  S.cevrimdisi = durum;
  $("#cevrimdisi").hidden = !durum;
}

function bildir(metin, hata = false) {
  const d = document.createElement("div");
  d.className = "bildirim" + (hata ? " hata" : "");
  d.textContent = metin;
  $("#bildirimler").append(d);
  setTimeout(() => d.remove(), hata ? 7000 : 4000);
}

const para = (v) => v == null || v === "" ? "—" : new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(v);
const kisaPara = (v) => {
  if (!v) return "0 ₺";
  if (v >= 1e9) return (v / 1e9).toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " milyar ₺";
  if (v >= 1e6) return (v / 1e6).toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " milyon ₺";
  return para(v);
};
const gunFarki = (iso) => {
  const b = new Date(); b.setHours(0, 0, 0, 0);
  const t = new Date(iso.slice(0, 10) + "T00:00:00");
  return Math.round((t - b) / 864e5);
};
const tarihYaz = (iso, saatli = true) => {
  if (!iso) return "—";
  const [g, s] = iso.split("T");
  const [y, a, d] = g.split("-");
  return `${+d} ${AYLAR[+a - 1]} ${y}` + (saatli && s ? ` ${s.slice(0, 5)}` : "");
};
const zamanYaz = (iso) => iso ? new Date(iso).toLocaleString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
const isoGun = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const boyut = (b) => b < 1024 ? b + " B" : b < 1048576 ? (b / 1024).toFixed(0) + " KB" : (b / 1048576).toFixed(1) + " MB";
const durumRozet = (d) => `<span class="rozet-d d-${e(d)}">${e(S.sabit.durumlar[d] || d)}</span>`;
const kodUrl = (kod) => encodeURIComponent(kod);

function kalanYaz(iso) {
  if (!iso) return "";
  const n = gunFarki(iso);
  const sinif = n <= 2 ? "yakin" : n <= 7 ? "orta" : "";
  const metin = n < 0 ? `${-n} gün önce` : n === 0 ? "Bugün" : n === 1 ? "Yarın" : `${n} gün kaldı`;
  return `<span class="kalan ${n >= 0 ? sinif : ""}">${metin}</span>`;
}

function tarihKutu(iso, ihale = false) {
  const [y, a, d] = iso.slice(0, 10).split("-");
  return `<div class="tarih-kutu${ihale ? " ihale" : ""}"><b>${+d}</b><small>${AYLAR[+a - 1].slice(0, 3)}</small></div>`;
}

function yolBilgisi() {
  const h = location.hash.replace(/^#\/?/, "");
  const [yol, sorgu] = h.split("?");
  const parca = yol.split("/").map(decodeURIComponent);
  return { sayfa: parca[0] || "", parca, sorgu: new URLSearchParams(sorgu || "") };
}

// --- Kabuk ------------------------------------------------------------------------

function menuCiz(sayfa, rozet = {}) {
  const ogeler = SAYFALAR.map(([ikon, ad, yol]) => {
    const r = rozet[yol] ? `<span class="rozet">${rozet[yol]}</span>` : "";
    return `<a href="#/${yol}" class="${sayfa === yol ? "aktif" : ""}">${svg(ikon)}${ad}${r}</a>`;
  });
  $("#menu").innerHTML = ogeler.join("");
  $("#alt-menu").innerHTML = SAYFALAR.filter(([, , y]) => ["", "ihaleler", "ajanda", "raporlar", "ogrenme"].includes(y))
    .map(([ikon, ad, yol]) => `<a href="#/${yol}" class="${sayfa === yol ? "aktif" : ""}">${svg(ikon)}${ad}</a>`).join("");
}

async function yonlendir() {
  clearInterval(S.yoklama);
  const { sayfa, sorgu } = yolBilgisi();
  menuCiz(sayfa === "ihale" ? "ihaleler" : sayfa);
  const kap = $("#icerik");
  try {
    if (!S.sabit) S.sabit = await api("sabitler");
    const sayfalar = { "": gosterge, ihaleler, ihale: ihaleDetay, ajanda, raporlar, taramalar,
      tarama: taramaDetay, ogrenme, ayarlar };
    await (sayfalar[sayfa] || gosterge)(kap, sorgu);
    if (sorgu.get("yeni")) ihaleFormu();
  } catch (h) {
    kap.innerHTML = `<div class="kart bos">${e(h.message)}</div>`;
  }
  window.scrollTo(0, 0);
}

function baslik(metin) {
  $("#baslik").textContent = metin;
  document.title = metin === "Gösterge" ? "İhale Analiz" : `${metin} · İhale Analiz`;
}

// --- Gösterge ---------------------------------------------------------------------

async function gosterge(kap) {
  baslik("Gösterge");
  const o = await api("ozet");
  const buHafta = o.yaklasan.filter((x) => x.tur === "ihale" && gunFarki(x.tarih) <= 7).length;
  const b = o.basari;
  menuCiz("", { ihaleler: o.sayac.hesaplanacak + o.sayac.analizde || "" });
  kap.innerHTML = `
  <div class="izgara k4">
    <div class="kart gosterge"><small>Açık ihale</small><b>${o.acik_sayi}</b><span>Toplam ${kisaPara(o.acik_butce)} yaklaşık maliyet</span></div>
    <div class="kart gosterge"><small>7 gün içinde ihale</small><b>${buHafta}</b><span>${o.yaklasan.length} yaklaşan kayıt (14 gün)</span></div>
    <div class="kart gosterge"><small>Analiz sürecinde</small><b>${o.sayac.hesaplanacak + o.sayac.analizde}</b><span>${o.sayac.hesaplanacak} kuyrukta, ${o.sayac.analizde} çalışıyor</span></div>
    <div class="kart gosterge"><small>Kazanma oranı</small><b>${b.oran == null ? "—" : "%" + b.oran}</b><span>${b.kazanilan} kazanıldı, ${b.kaybedilen} kaybedildi</span></div>
  </div>
  <div class="izgara k3-1" style="margin-top:16px">
    <div class="kart"><h2>Yaklaşan tarihler <a class="sag" href="#/ajanda">Ajanda</a></h2>
      <div class="liste">${o.yaklasan.length ? o.yaklasan.map(olaySatir).join("") : '<div class="bos">Önümüzdeki 14 günde kayıt yok. İhale eklerken ihale tarihini girin; ajanda kendiliğinden dolar.</div>'}</div>
    </div>
    <div class="izgara" style="align-content:start">
      <div class="kart"><h2>Analiz süreci</h2>
        <div class="liste">${o.analizde.length ? o.analizde.map((a) => `
          <a class="satir" href="#/ihale/${kodUrl(a.kod)}"><div class="govde"><b>${e(a.ad || a.kod)}</b>
          <small>${a.aktif ? e(a.aktif) + " çalışıyor" : a.durum === "hesaplanacak" ? "Kuyrukta bekliyor" : "Analizde"}</small>
          <div class="ilerleme" style="margin-top:6px"><i style="width:${a.yuzde}%"></i></div></div>
          <span class="kalan">%${a.yuzde}</span></a>`).join("") : '<div class="bos">Şu an analiz edilen ihale yok.</div>'}</div>
      </div>
      <div class="kart"><h2>Son raporlar <a class="sag" href="#/raporlar">Tümü</a></h2>
        <div class="liste">${o.raporlar.length ? o.raporlar.map((r) => `
          <a class="satir" href="#/ihale/${kodUrl(r.kod)}?sekme=rapor"><span class="uzanti">HTML</span><div class="govde"><b>${e(r.ad || r.kod)}</b>
          <small>${e(zamanYaz(new Date(r.zaman * 1000).toISOString()))}</small></div></a>`).join("") : '<div class="bos">Henüz rapor yok.</div>'}</div>
      </div>
    </div>
  </div>`;
  hatirlat(o.yaklasan);
}

function olaySatir(o) {
  const tur = S.sabit.etkinlik_turleri[o.tur] || o.tur;
  const hedef = o.kod ? `#/ihale/${kodUrl(o.kod)}` : "#/ajanda";
  return `<a class="satir" href="${hedef}">${tarihKutu(o.tarih, o.tur === "ihale")}
    <div class="govde"><b>${e(o.baslik)}</b><small>${e(tur)}${o.saat ? " · " + e(o.saat) : ""}${o.aciklama ? " · " + e(o.aciklama) : ""}</small></div>
    ${kalanYaz(o.tarih)}</a>`;
}

// --- İhaleler ----------------------------------------------------------------------

const FILTRELER = {
  aktif: ["Aktif", (d) => !S.sabit.kapali.includes(d)],
  surec: ["Analiz", (d) => ["hesaplanacak", "analizde", "rapor_hazir"].includes(d)],
  teklif: ["Teklif verildi", (d) => d === "teklif_verildi"],
  kapanan: ["Sonuçlanan", (d) => S.sabit.kapali.includes(d)],
  tumu: ["Tümü", () => true],
};

async function ihaleler(kap) {
  baslik("İhaleler");
  const liste = await api("ihaleler");
  const ciz = () => {
    const ara = S.ihaleAra.toLocaleLowerCase("tr");
    let s = liste.filter((t) => FILTRELER[S.ihaleFiltre][1](t.durum))
      .filter((t) => !ara || [t.kod, t.ad, t.idare, t.il].some((v) => (v || "").toLocaleLowerCase("tr").includes(ara)));
    const sira = { tarih: (a, b) => (a.ihale_tarihi || "9").localeCompare(b.ihale_tarihi || "9"),
      maliyet: (a, b) => (b.yaklasik || 0) - (a.yaklasik || 0), oncelik: (a, b) => a.oncelik - b.oncelik,
      eklenme: (a, b) => (b.eklenme || "").localeCompare(a.eklenme || "") }[S.ihaleSira];
    s = s.sort(sira);
    $("#ihale-tablo").innerHTML = s.length ? `<div class="tablo-kap"><table class="tablo"><thead><tr>
      <th>İhale</th><th class="gizle-mobil">İdare</th><th data-sirala="tarih">İhale tarihi</th>
      <th class="sayi gizle-mobil" data-sirala="maliyet">Yaklaşık maliyet</th><th>Durum</th></tr></thead><tbody>
      ${s.map((t) => `<tr data-git="#/ihale/${kodUrl(t.kod)}"><td><b>${e(t.ad || t.kod)}</b><small>${e(t.kod)} <span class="oncelik">${"★".repeat(4 - (t.oncelik || 2))}</span></small></td>
      <td class="gizle-mobil">${e(t.idare || "—")}<small>${e(t.il || "")}</small></td>
      <td>${tarihYaz(t.ihale_tarihi)}<small>${t.ihale_tarihi && !S.sabit.kapali.includes(t.durum) ? kalanYaz(t.ihale_tarihi) : ""}</small></td>
      <td class="sayi gizle-mobil">${para(t.yaklasik)}</td><td>${durumRozet(t.durum)}</td></tr>`).join("")}
      </tbody></table></div>` : `<div class="bos">${liste.length ? "Bu filtrede ihale yok." : "Henüz ihale yok. <b>Yeni ihale</b> ile ekleyin ya da dosyaları Gelen Dosyalar klasörüne bırakıp asistanınızdan analiz isteyin."}</div>`;
    $$(".cip", kap).forEach((c) => c.classList.toggle("secili", c.dataset.filtre === S.ihaleFiltre));
  };
  const say = (k) => liste.filter((t) => FILTRELER[k][1](t.durum)).length;
  kap.innerHTML = `<div class="araclar">
      <div class="cipler">${Object.entries(FILTRELER).map(([k, [ad]]) => `<button class="cip" data-filtre="${k}">${ad}<span class="n">${say(k)}</span></button>`).join("")}</div>
      <input type="search" id="ihale-ara" placeholder="Ara: ad, kod, idare, il" value="${e(S.ihaleAra)}">
      <select id="ihale-sira" style="width:auto"><option value="tarih">İhale tarihine göre</option><option value="maliyet">Maliyete göre</option>
      <option value="oncelik">Önceliğe göre</option><option value="eklenme">Son eklenen</option></select>
      <span style="flex:1"></span>
      <button class="dugme" data-eylem="csv">CSV indir</button>
      <button class="dugme ana-d" data-eylem="yeni-ihale">Yeni ihale</button></div>
    <div class="kart" id="ihale-tablo" style="padding:6px 8px"></div>`;
  $("#ihale-sira").value = S.ihaleSira;
  kap.onclick = (ev) => {
    const f = ev.target.closest("[data-filtre]");
    if (f) { S.ihaleFiltre = f.dataset.filtre; ciz(); }
    const sr = ev.target.closest("[data-sirala]");
    if (sr) { S.ihaleSira = sr.dataset.sirala; $("#ihale-sira").value = S.ihaleSira; ciz(); }
    const tr = ev.target.closest("[data-git]");
    if (tr) location.hash = tr.dataset.git;
    if (ev.target.closest('[data-eylem="csv"]')) csvIndir(liste);
  };
  $("#ihale-ara").oninput = (ev) => { S.ihaleAra = ev.target.value; ciz(); };
  $("#ihale-sira").onchange = (ev) => { S.ihaleSira = ev.target.value; ciz(); };
  ciz();
}

function csvIndir(liste) {
  const kolon = ["kod", "ikn", "ad", "idare", "il", "tur", "yaklasik", "ihale_tarihi", "durum", "oncelik", "teklif", "kazanan_teklif", "notlar"];
  const satir = [kolon.join(";"), ...liste.map((t) => kolon.map((k) => `"${String(t[k] ?? "").replace(/"/g, '""')}"`).join(";"))];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + satir.join("\r\n")], { type: "text/csv" }));
  a.download = `ihaleler-${isoGun(new Date())}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// --- İhale formu -------------------------------------------------------------------

function ihaleFormu(t = null, onEk = {}) {
  const d = { ...(t || {}), ...onEk };
  const pen = $("#pencere");
  const durumlar = Object.entries(S.sabit.durumlar).map(([k, v]) => `<option value="${k}">${e(v)}</option>`).join("");
  pen.innerHTML = `<form method="dialog" id="ihale-form">
    <h2>${t ? "İhaleyi düzenle" : "Yeni ihale"}</h2>
    <div class="izgara-form">
      <label class="alan genis">İhale adı (işin adı)<input type="text" name="ad" required value="${e(d.ad)}" placeholder="ör. Okul binası güçlendirme işi"></label>
      ${t ? "" : `<label class="alan">İKN ya da kısa kod<input type="text" name="kod" value="${e(d.kod)}" placeholder="2026/123456"></label>`}
      <label class="alan">İdare<input type="text" name="idare" value="${e(d.idare)}"></label>
      <label class="alan">İl<input type="text" name="il" value="${e(d.il)}"></label>
      <label class="alan">Teklif türü<select name="tur"><option value="">Bilinmiyor</option>${Object.entries(TUR_AD).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label>
      <label class="alan">Yaklaşık maliyet (₺)<input type="text" inputmode="decimal" name="yaklasik" value="${e(d.yaklasik ?? "")}" placeholder="2.500.000"></label>
      <label class="alan">İhale tarihi ve saati<input type="datetime-local" name="ihale_tarihi" value="${e((d.ihale_tarihi || "").length === 10 ? d.ihale_tarihi + "T10:00" : d.ihale_tarihi || "")}"></label>
      <label class="alan">Öncelik<select name="oncelik"><option value="1">Yüksek</option><option value="2">Normal</option><option value="3">Düşük</option></select></label>
      ${t ? `<label class="alan">Durum<select name="durum">${durumlar}</select></label>` : ""}
      <label class="alan genis">İlan bağlantısı<input type="url" name="kaynak_url" value="${e(d.kaynak_url)}" placeholder="https://"></label>
      <label class="alan genis">Notlar<textarea name="notlar">${e(d.notlar)}</textarea></label>
      ${t ? "" : `<label class="alan genis">İhale dosyaları (şartname, cetvel, proje; zip olabilir)<input type="file" name="dosyalar" multiple></label>
      <label class="onay genis"><input type="checkbox" name="analiz"> Ekledikten sonra analizi başlat (hesaplanacak)</label>`}
    </div>
    <div class="dugmeler"><button class="dugme" value="iptal" formnovalidate>Vazgeç</button><button class="dugme ana-d" value="kaydet">${t ? "Kaydet" : "Ekle"}</button></div>
  </form>`;
  const f = $("#ihale-form");
  f.tur.value = d.tur || "";
  f.oncelik.value = d.oncelik || 2;
  if (t) f.durum.value = d.durum;
  pen.showModal();
  f.onsubmit = async (ev) => {
    if (ev.submitter?.value !== "kaydet") return;
    ev.preventDefault();
    const veri = Object.fromEntries(["ad", "kod", "idare", "il", "tur", "yaklasik", "ihale_tarihi", "oncelik", "durum", "kaynak_url", "notlar"]
      .filter((k) => f[k]).map((k) => [k, f[k].value]));
    if (veri.yaklasik) veri.yaklasik = veri.yaklasik.replace(/\s|₺/g, "");
    const dugme = ev.submitter;
    dugme.disabled = true;
    try {
      if (t) {
        await api(`ihaleler/${kodUrl(t.kod)}`, { method: "PUT", govde: veri });
        pen.close();
        bildir("Kaydedildi");
        yonlendir();
      } else {
        const { kod } = await api("ihaleler", { method: "POST", govde: veri });
        for (const dosya of f.dosyalar.files) await dosyaYukle(kod, dosya);
        if (f.analiz.checked) {
          const s = await api(`ihaleler/${kodUrl(kod)}/analiz`, { method: "POST" });
          bildir(s.mesaj);
        } else bildir("İhale takibe alındı");
        pen.close();
        location.hash = `#/ihale/${kodUrl(kod)}`;
      }
    } catch (h) {
      bildir(h.message, true);
      dugme.disabled = false;
    }
  };
}

async function dosyaYukle(kod, dosya) {
  const y = await fetch(`/api/ihaleler/${kodUrl(kod)}/dosya`, {
    method: "POST", body: dosya, headers: { "X-Ihale-Panel": "1", "X-Dosya-Adi": encodeURIComponent(dosya.name) },
  });
  const v = await y.json().catch(() => ({}));
  if (!y.ok) throw new Error(`${dosya.name}: ${v.hata || "yüklenemedi"}`);
  return v;
}

// --- İhale detayı --------------------------------------------------------------------

async function ihaleDetay(kap, sorgu) {
  const kod = yolBilgisi().parca[1];
  const v = await api(`ihaleler/${kodUrl(kod)}`);
  const t = v.ihale;
  baslik(t.ad || t.kod);
  if (sorgu.get("sekme")) S.detaySekme = sorgu.get("sekme");
  const rapor = v.dosyalar.raporlar;
  const html = rapor.find((r) => r.ad.endsWith(" Rapor.html"));
  const md = rapor.find((r) => r.ad.endsWith(" Rapor.md"));
  const dosyaUrl = (yol) => `/dosya/${kodUrl(kod)}/${yol.split("/").map(encodeURIComponent).join("/")}`;
  const sekmeler = [["genel", "Genel"], ["surec", `Süreç · %${v.surec.yuzde}`], ["rapor", "Rapor"],
    ["dosyalar", `Dosyalar · ${v.dosyalar.kaynak.length}`], ["ajanda", `Ajanda · ${v.etkinlikler.length}`]];
  const kapali = S.sabit.kapali.includes(t.durum);
  const surecte = ["hesaplanacak", "analizde"].includes(t.durum);

  kap.innerHTML = `
  <div class="baslik-blok"><div class="govde">
    <h2>${e(t.ad || t.kod)}</h2>
    <div class="meta"><span>${e(t.kod)}</span>${t.idare ? `<span>${e(t.idare)}</span>` : ""}${t.il ? `<span>${e(t.il)}</span>` : ""}
    <span>${durumRozet(t.durum)}</span>${t.ihale_tarihi ? `<span>İhale: <b>${tarihYaz(t.ihale_tarihi)}</b> ${kapali ? "" : kalanYaz(t.ihale_tarihi)}</span>` : ""}</div></div>
    <div class="dugmeler">
      ${kapali ? "" : `<button class="dugme ana-d" data-eylem="analiz" ${surecte ? "disabled" : ""}>${surecte ? "Analiz sürüyor" : md ? "Yeniden analiz et" : "Analizi başlat"}</button>`}
      <button class="dugme" data-eylem="duzenle">Düzenle</button>
      <button class="dugme" data-eylem="klasor">Klasörü aç</button>
      <button class="dugme tehlike" data-eylem="sil">Takipten çıkar</button>
    </div></div>
  <div class="sekmeler">${sekmeler.map(([k, ad]) => `<button data-sekme="${k}" class="${S.detaySekme === k ? "aktif" : ""}">${ad}</button>`).join("")}</div>
  <div id="sekme-icerik"></div>`;

  const sekmeCiz = () => {
    const y = $("#sekme-icerik");
    $$(".sekmeler button", kap).forEach((b) => b.classList.toggle("aktif", b.dataset.sekme === S.detaySekme));
    if (S.detaySekme === "genel") {
      const ogrenen = v.analiz;
      y.innerHTML = `<div class="izgara k3-1"><div class="kart"><h2>Bilgiler</h2><dl class="bilgi">
        <dt>İKN / kod</dt><dd>${e(t.ikn || t.kod)}</dd>
        <dt>İdare</dt><dd>${e(t.idare || "—")}</dd><dt>İl</dt><dd>${e(t.il || "—")}</dd>
        <dt>Teklif türü</dt><dd>${e(TUR_AD[t.tur] || t.tur || "—")}</dd>
        <dt>Yaklaşık maliyet</dt><dd>${para(t.yaklasik)}</dd>
        <dt>İhale tarihi</dt><dd>${tarihYaz(t.ihale_tarihi)}</dd>
        <dt>Öncelik</dt><dd>${["", "Yüksek", "Normal", "Düşük"][t.oncelik || 2]}</dd>
        ${t.kaynak_url ? `<dt>İlan</dt><dd><a href="${e(t.kaynak_url)}" target="_blank" rel="noopener noreferrer">${e(t.kaynak_url)}</a></dd>` : ""}
        ${ogrenen?.karar ? `<dt>Analiz kararı</dt><dd>${e(ogrenen.karar)}</dd>` : ""}
        <dt>Notlar</dt><dd style="white-space:pre-wrap">${e(t.notlar || "—")}</dd>
        <dt>Eklenme</dt><dd>${e(zamanYaz(t.eklenme))}</dd></dl></div>
        <div class="izgara" style="align-content:start">
        <div class="kart"><h2>Durum</h2>
          <div class="cipler">${["takipte", "teklif_verildi", "katilinmadi"].map((d) => `<button class="cip ${t.durum === d ? "secili" : ""}" data-durum="${d}">${e(S.sabit.durumlar[d])}</button>`).join("")}</div>
          <p class="not">Analiz durumları (hesaplanacak, analizde, rapor hazır) süreçten kendiliğinden güncellenir.</p></div>
        <div class="kart"><h2>İhale sonucu</h2>
          <form id="sonuc-form" class="izgara-form">
            <label class="alan genis">Sonuç<select name="durum"><option value="">Seçin</option><option value="kazanildi">Kazanıldı</option>
            <option value="kaybedildi">Kaybedildi</option><option value="katilinmadi">Katılınmadı</option><option value="iptal">İptal edildi</option></select></label>
            <label class="alan">Bizim teklif (₺)<input type="text" inputmode="decimal" name="teklif" value="${e(t.teklif ?? "")}"></label>
            <label class="alan">Kazanan teklif (₺)<input type="text" inputmode="decimal" name="kazanan_teklif" value="${e(t.kazanan_teklif ?? "")}"></label>
            <div class="genis dugmeler"><button class="dugme ana-d">Sonucu kaydet</button></div>
          </form><p class="not">Sonuç öğrenen veritabanına yazılır; sonraki analizlerde bu idare ve tenzilat için kullanılır.</p></div>
        </div></div>`;
      const f = $("#sonuc-form");
      if (kapali) f.durum.value = t.durum;
      f.onsubmit = async (ev) => {
        ev.preventDefault();
        if (!f.durum.value) return bildir("Sonucu seçin", true);
        try {
          await api(`ihaleler/${kodUrl(kod)}`, { method: "PUT", govde: { durum: f.durum.value,
            teklif: f.teklif.value.replace(/\s|₺/g, ""), kazanan_teklif: f.kazanan_teklif.value.replace(/\s|₺/g, "") } });
          bildir("Sonuç kaydedildi");
          yonlendir();
        } catch (h) { bildir(h.message, true); }
      };
    } else if (S.detaySekme === "surec") {
      surecCiz(y, v.surec, t.durum);
    } else if (S.detaySekme === "rapor") {
      y.innerHTML = html ? `<div class="araclar">
          <a class="dugme" href="${dosyaUrl(html.yol)}" target="_blank" rel="noopener">Yeni sekmede aç</a>
          <button class="dugme" data-eylem="yazdir">Yazdır / PDF kaydet</button>
          ${rapor.filter((r) => /\.(pdf|xlsx)$/i.test(r.ad)).map((r) => `<a class="dugme" href="${dosyaUrl(r.yol)}" download>${r.ad.endsWith(".pdf") ? "PDF indir" : "Excel indir"}</a>`).join("")}
          <span style="flex:1"></span><button class="dugme" data-eylem="rapor">HTML/PDF'i yenile</button>
          <small class="not">Oluşturma: ${e(zamanYaz(html.zaman))}</small></div>
          <iframe class="rapor-cerceve" id="rapor-cerceve" src="${dosyaUrl(html.yol)}" title="Analiz raporu"></iframe>`
        : md ? `<div class="kart bos">Markdown rapor hazır, HTML hali henüz oluşturulmadı.<div class="dugmeler" style="justify-content:center;margin-top:12px">
          <button class="dugme ana-d" data-eylem="rapor">HTML ve PDF raporu oluştur</button></div></div>`
        : `<div class="kart bos">Rapor henüz yok. ${surecte ? "Analiz sürüyor; rapor adımı bitince burada açılır." : "Analizi başlatın; rapor yazarı ajan bitirince HTML rapor burada görünür, PDF ve Excel indirilebilir."}</div>`;
    } else if (S.detaySekme === "dosyalar") {
      y.innerHTML = `<div class="izgara k2"><div class="kart"><h2>İhale dosyaları (kaynak)</h2>
        <label class="yukleme-alani" id="yukle"><input type="file" multiple hidden id="yukle-girdi">
        Dosyaları buraya sürükleyin ya da tıklayıp seçin<br><small>Şartname, cetvel, proje çizimleri, zip arşivleri</small></label>
        <div style="margin-top:12px">${v.dosyalar.kaynak.map((f) => dosyaSatir(f, dosyaUrl)).join("") || '<div class="bos">Henüz dosya yok.</div>'}</div></div>
        <div class="kart"><h2>Çıktılar</h2>${rapor.map((f) => dosyaSatir(f, dosyaUrl)).join("") || '<div class="bos">Henüz çıktı yok.</div>'}</div></div>`;
      const alan = $("#yukle");
      const gonder = async (dosyalar) => {
        for (const f of dosyalar) {
          try {
            const r = await dosyaYukle(kod, f);
            bildir(r.uyari ? `${f.name}: ${r.uyari}` : `${f.name} yüklendi`, !!r.uyari);
          } catch (h) { bildir(h.message, true); }
        }
        yonlendir();
      };
      $("#yukle-girdi").onchange = (ev) => gonder(ev.target.files);
      alan.ondragover = (ev) => { ev.preventDefault(); alan.classList.add("uzerinde"); };
      alan.ondragleave = () => alan.classList.remove("uzerinde");
      alan.ondrop = (ev) => { ev.preventDefault(); alan.classList.remove("uzerinde"); gonder(ev.dataTransfer.files); };
    } else if (S.detaySekme === "ajanda") {
      y.innerHTML = `<div class="kart"><h2>Bu ihalenin tarihleri <span class="sag"><button class="dugme kucuk ana-d" data-eylem="etkinlik">Tarih ekle</button></span></h2>
        <div class="liste">${t.ihale_tarihi ? olaySatir({ tarih: t.ihale_tarihi.slice(0, 10), saat: t.ihale_tarihi.slice(11, 16), tur: "ihale", baslik: "İhale günü", kod: null }) : ""}
        ${v.etkinlikler.map((o) => `<div class="satir">${tarihKutu(o.tarih)}<div class="govde"><b class="${o.tamam ? "olay tamam" : ""}" style="${o.tamam ? "background:none;border:0;padding:0" : ""}">${e(o.baslik)}</b>
          <small>${e(S.sabit.etkinlik_turleri[o.tur] || o.tur)}${o.saat ? " · " + e(o.saat) : ""}${o.kaynak === "ajan" ? " · şartnameden" : ""}</small></div>
          ${kalanYaz(o.tarih)}<button class="dugme kucuk" data-tamam="${o.id}" data-deger="${o.tamam ? 0 : 1}">${o.tamam ? "Geri al" : "Tamam"}</button>
          <button class="dugme kucuk tehlike" data-etk-sil="${o.id}" aria-label="Sil">Sil</button></div>`).join("")}
        ${!t.ihale_tarihi && !v.etkinlikler.length ? '<div class="bos">Tarih yok. İhale tarihini Düzenle ile girin; yer görme, açıklama talebi gibi tarihleri buradan ekleyin. Doküman okuyucu ajan şartnamedeki tarihleri kendisi ekler.</div>' : ""}</div></div>`;
    }
  };
  sekmeCiz();

  kap.onclick = async (ev) => {
    const s = ev.target.closest("[data-sekme]");
    if (s) { S.detaySekme = s.dataset.sekme; return sekmeCiz(); }
    const dr = ev.target.closest("[data-durum]");
    if (dr) {
      await api(`ihaleler/${kodUrl(kod)}`, { method: "PUT", govde: { durum: dr.dataset.durum } }).catch((h) => bildir(h.message, true));
      return yonlendir();
    }
    const tm = ev.target.closest("[data-tamam]");
    if (tm) { await api(`etkinlikler/${tm.dataset.tamam}`, { method: "PUT", govde: { tamam: tm.dataset.deger === "1" } }); return yonlendir(); }
    const es = ev.target.closest("[data-etk-sil]");
    if (es) { if (confirm("Bu tarih silinsin mi?")) { await api(`etkinlikler/${es.dataset.etkSil}`, { method: "DELETE" }); yonlendir(); } return; }
    const ey = ev.target.closest("[data-eylem]")?.dataset.eylem;
    if (!ey) return;
    try {
      if (ey === "analiz") {
        const r = await api(`ihaleler/${kodUrl(kod)}/analiz`, { method: "POST" });
        bildir(r.mesaj);
        S.detaySekme = "surec";
        yonlendir();
      } else if (ey === "duzenle") ihaleFormu(t);
      else if (ey === "klasor") await api("klasor", { method: "POST", govde: { yol: `İhaleler/${kod}` } });
      else if (ey === "sil") {
        if (confirm("İhale takipten çıkarılsın mı? Klasördeki dosyalar silinmez.")) {
          await api(`ihaleler/${kodUrl(kod)}`, { method: "DELETE" });
          bildir("Takipten çıkarıldı. Dosyalar klasörde duruyor.");
          location.hash = "#/ihaleler";
        }
      } else if (ey === "rapor") {
        bildir("Rapor oluşturuluyor…");
        const r = await api(`ihaleler/${kodUrl(kod)}/rapor`, { method: "POST" });
        bildir(r.mesaj);
        S.detaySekme = "rapor";
        yonlendir();
      } else if (ey === "yazdir") $("#rapor-cerceve").contentWindow.print();
      else if (ey === "etkinlik") etkinlikFormu({ kod });
    } catch (h) { bildir(h.message, true); }
  };

  if (surecte) {
    S.yoklama = setInterval(async () => {
      if (document.hidden) return;
      try {
        const r = await api(`ihaleler/${kodUrl(kod)}/surec`);
        if (r.durum !== t.durum) return yonlendir();
        v.surec = r.surec;
        if (S.detaySekme === "surec") surecCiz($("#sekme-icerik"), r.surec, r.durum);
        const b = $('[data-sekme="surec"]');
        if (b) b.textContent = `Süreç · %${r.surec.yuzde}`;
      } catch { /* sunucu kapalı */ }
    }, 4000);
  }
}

function dosyaSatir(f, dosyaUrl) {
  const uz = (f.ad.split(".").pop() || "").slice(0, 4);
  return `<div class="dosya-sat"><span class="uzanti">${e(uz)}</span><span class="ad">${e(f.yol)}</span>
    <small>${boyut(f.boyut)}</small><a class="dugme kucuk" href="${dosyaUrl(f.yol)}" target="_blank" rel="noopener">Aç</a></div>`;
}

function surecCiz(y, s, durum) {
  const etiket = { bekliyor: "Bekliyor", calisiyor: "Çalışıyor", bitti: "Tamamlandı", hata: "Hata" };
  y.innerHTML = `<div class="izgara k3-1"><div class="kart"><h2>Analiz adımları <span class="sag kalan">%${s.yuzde}</span></h2>
    <div class="ilerleme" style="margin-bottom:18px"><i style="width:${s.yuzde}%"></i></div>
    <ol class="surec">${s.adimlar.map((a) => `<li class="${a.durum}"><span class="nokta">${a.durum === "bitti" ? "✓" : a.durum === "hata" ? "!" : e(a.adim)}</span>
      <div><b>${e(a.ad)}</b><small>${e(a.ajan)} · ${etiket[a.durum]}${a.zaman ? " · " + e(zamanYaz(a.zaman)) : ""}</small>
      ${a.mesaj ? `<div class="mesaj">${e(a.mesaj)}</div>` : ""}</div></li>`).join("")}</ol></div>
    <div class="izgara" style="align-content:start">
    ${durum === "hesaplanacak" ? `<div class="kart"><h2>Kuyrukta</h2><p class="not">İhale analiz kuyruğunda. Yapay zekâ asistanınıza şunu yazın:</p>
      <div class="kopya"><span>Kuyruktaki ihaleleri analiz et</span><button class="dugme kucuk" data-kopya="Kuyruktaki ihaleleri analiz et">Kopyala</button></div>
      <p class="not">Otomatik başlatmak için config.yaml içinde <code>panel.analiz_komutu</code> tanımlanabilir (Ayarlar).</p></div>` : ""}
    <div class="kart"><h2>Günlük</h2>${s.gunluk.length ? `<div class="gunluk">${s.gunluk.slice().reverse().map((g) => `${e(zamanYaz(g.zaman))} · ${e(g.adim)} · ${e(g.durum)}${g.mesaj ? " · " + e(g.mesaj) : ""}`).join("<br>")}</div>` : '<p class="not">Ajanlar adım başlatıp bitirdikçe kayıtlar burada görünür.</p>'}</div>
    </div></div>`;
}

// --- Ajanda ------------------------------------------------------------------------

async function ajanda(kap) {
  baslik("Ajanda");
  const bugun = new Date();
  if (!S.ajandaAy) S.ajandaAy = new Date(bugun.getFullYear(), bugun.getMonth(), 1);
  if (!S.ajandaSecili) S.ajandaSecili = isoGun(bugun);
  const ay = S.ajandaAy;
  const ilk = new Date(ay.getFullYear(), ay.getMonth(), 1);
  const bas = new Date(ilk); bas.setDate(1 - ((ilk.getDay() + 6) % 7));
  const son = new Date(bas); son.setDate(bas.getDate() + 41);
  const liste = S.ajandaGorunum === "liste";
  const aralikBas = liste ? isoGun(bugun) : isoGun(bas);
  const aralikSon = liste ? isoGun(new Date(bugun.getTime() + 90 * 864e5)) : isoGun(son);
  const olaylar = await api(`ajanda?bas=${aralikBas}&son=${aralikSon}`);
  const gunde = {};
  olaylar.forEach((o) => (gunde[o.tarih] ||= []).push(o));

  const govde = liste ? `<div class="kart"><h2>Önümüzdeki 90 gün</h2><div class="liste">${olaylar.length ? olaylar.map((o) => olaySatirAjanda(o)).join("") : '<div class="bos">Kayıt yok.</div>'}</div></div>`
    : `<div class="izgara k3-1"><div><div class="takvim">${GUNLER.map((g) => `<div class="gb">${g}</div>`).join("")}
      ${Array.from({ length: 42 }, (_, i) => {
        const d = new Date(bas); d.setDate(bas.getDate() + i);
        const iso = isoGun(d);
        const o = gunde[iso] || [];
        return `<div class="gun${d.getMonth() !== ay.getMonth() ? " disari" : ""}${iso === isoGun(bugun) ? " bugun" : ""}${iso === S.ajandaSecili ? " secili" : ""}" data-gun="${iso}">
          <span class="no">${d.getDate()}</span>${o.slice(0, 3).map((x) => `<div class="olay t-${e(x.tur)}${x.tamam ? " tamam" : ""}" title="${e(x.baslik)}">${x.saat ? e(x.saat) + " " : ""}${e(x.baslik)}</div>`).join("")}
          ${o.length > 3 ? `<span class="fazla">+${o.length - 3} daha</span>` : ""}</div>`;
      }).join("")}</div>
      <div class="lejant"><span style="--c:var(--vurgu)">İhale günü</span><span style="--c:var(--amber)">Hatırlatma</span>
      <span style="--c:var(--mor)">Yer görme / açıklama talebi</span><span style="--c:var(--yesil)">Teminat, sözleşme, doküman</span></div></div>
      <div class="kart" style="align-self:start"><h2>${tarihYaz(S.ajandaSecili)}<span class="sag"><button class="dugme kucuk ana-d" data-eylem="etkinlik">Ekle</button></span></h2>
      <div class="liste">${(gunde[S.ajandaSecili] || []).map((o) => olaySatirAjanda(o)).join("") || '<div class="bos">Bu gün kayıt yok.</div>'}</div></div></div>`;

  kap.innerHTML = `<div class="takvim-ust">
      ${liste ? "<h2>Yaklaşanlar</h2>" : `<button class="dugme simge" data-ay="-1" aria-label="Önceki ay">‹</button><h2>${AYLAR[ay.getMonth()]} ${ay.getFullYear()}</h2>
      <button class="dugme simge" data-ay="1" aria-label="Sonraki ay">›</button><button class="dugme kucuk" data-ay="0">Bugün</button>`}
      <span style="flex:1"></span>
      <div class="cipler"><button class="cip ${liste ? "" : "secili"}" data-gorunum="ay">Ay</button><button class="cip ${liste ? "secili" : ""}" data-gorunum="liste">Liste</button></div>
      <a class="dugme" href="/takvim.ics" download title="Outlook, Google Takvim ya da telefon takvimine aktarın">Takvime aktar (.ics)</a>
      <button class="dugme ana-d" data-eylem="etkinlik">Tarih ekle</button></div>${govde}`;

  kap.onclick = async (ev) => {
    const a = ev.target.closest("[data-ay]");
    if (a) {
      const n = +a.dataset.ay;
      S.ajandaAy = n === 0 ? new Date(bugun.getFullYear(), bugun.getMonth(), 1) : new Date(ay.getFullYear(), ay.getMonth() + n, 1);
      if (n === 0) S.ajandaSecili = isoGun(bugun);
      return ajanda(kap);
    }
    const g = ev.target.closest("[data-gun]");
    if (g) { S.ajandaSecili = g.dataset.gun; return ajanda(kap); }
    const gr = ev.target.closest("[data-gorunum]");
    if (gr) { S.ajandaGorunum = gr.dataset.gorunum; return ajanda(kap); }
    const tm = ev.target.closest("[data-tamam]");
    if (tm) { ev.preventDefault(); await api(`etkinlikler/${tm.dataset.tamam}`, { method: "PUT", govde: { tamam: tm.dataset.deger === "1" } }); return ajanda(kap); }
    if (ev.target.closest('[data-eylem="etkinlik"]')) etkinlikFormu({ tarih: S.ajandaSecili }, () => ajanda(kap));
  };
}

function olaySatirAjanda(o) {
  const duzenlenir = typeof o.id === "number";
  const tur = S.sabit.etkinlik_turleri[o.tur] || o.tur;
  const ad = o.ihale_ad && o.tur !== "ihale" && o.tur !== "hatirlatma" ? ` · ${o.ihale_ad}` : "";
  return `<div class="satir">${tarihKutu(o.tarih, o.tur === "ihale")}<div class="govde">
    <b>${o.kod ? `<a href="#/ihale/${kodUrl(o.kod)}">${e(o.baslik)}</a>` : e(o.baslik)}</b>
    <small>${e(tur)}${o.saat ? " · " + e(o.saat) : ""}${e(ad)}${o.aciklama ? " · " + e(o.aciklama) : ""}</small></div>
    ${o.tamam ? '<span class="kalan">Tamam</span>' : kalanYaz(o.tarih)}
    ${duzenlenir ? `<button class="dugme kucuk" data-tamam="${o.id}" data-deger="${o.tamam ? 0 : 1}">${o.tamam ? "Geri al" : "Tamam"}</button>` : ""}</div>`;
}

async function etkinlikFormu(on = {}, sonra = yonlendir) {
  const ihaleler = await api("ihaleler");
  const pen = $("#pencere");
  pen.innerHTML = `<form method="dialog" id="etk-form"><h2>Tarih ekle</h2><div class="izgara-form">
    <label class="alan genis">Başlık<input type="text" name="baslik" placeholder="ör. Yer görme, teminat mektubu bankadan alınacak"></label>
    <label class="alan">Tür<select name="tur">${Object.entries(S.sabit.etkinlik_turleri).filter(([k]) => k !== "ihale").map(([k, v]) => `<option value="${k}">${e(v)}</option>`).join("")}</select></label>
    <label class="alan">İhale<select name="kod"><option value="">Genel (ihaleye bağlı değil)</option>${ihaleler.filter((t) => !S.sabit.kapali.includes(t.durum)).map((t) => `<option value="${e(t.kod)}">${e(t.ad || t.kod)}</option>`).join("")}</select></label>
    <label class="alan">Tarih<input type="date" name="tarih" required value="${e(on.tarih || isoGun(new Date()))}"></label>
    <label class="alan">Saat (isteğe bağlı)<input type="time" name="saat"></label>
    <label class="alan genis">Açıklama<input type="text" name="aciklama"></label></div>
    <div class="dugmeler"><button class="dugme" value="iptal" formnovalidate>Vazgeç</button><button class="dugme ana-d" value="kaydet">Ekle</button></div></form>`;
  const f = $("#etk-form");
  if (on.kod) f.kod.value = on.kod;
  f.tur.value = "hatirlatma";
  pen.showModal();
  f.onsubmit = async (ev) => {
    if (ev.submitter?.value !== "kaydet") return;
    ev.preventDefault();
    try {
      await api("etkinlikler", { method: "POST", govde: { baslik: f.baslik.value, tur: f.tur.value, kod: f.kod.value,
        tarih: f.tarih.value, saat: f.saat.value, aciklama: f.aciklama.value } });
      pen.close();
      bildir("Ajandaya eklendi");
      sonra($("#icerik"));
    } catch (h) { bildir(h.message, true); }
  };
}

// --- Raporlar ----------------------------------------------------------------------

async function raporlar(kap) {
  baslik("Raporlar");
  const liste = await api("ihaleler");
  const detay = await Promise.all(liste.map((t) => api(`ihaleler/${kodUrl(t.kod)}`).catch(() => null)));
  const satir = detay.filter(Boolean).flatMap((d) => {
    const r = d.dosyalar.raporlar.filter((f) => / Rapor\.(html|md)$/.test(f.ad));
    if (!r.length) return [];
    const html = r.find((f) => f.ad.endsWith(".html"));
    const ek = d.dosyalar.raporlar.filter((f) => /\.(pdf|xlsx)$/i.test(f.ad));
    return [{ t: d.ihale, html, md: r.find((f) => f.ad.endsWith(".md")), ek, zaman: (html || r[0]).zaman }];
  }).sort((a, b) => b.zaman.localeCompare(a.zaman));
  const url = (kod, yol) => `/dosya/${kodUrl(kod)}/${encodeURIComponent(yol)}`;
  kap.innerHTML = `<div class="kart" style="padding:6px 8px">${satir.length ? `<div class="tablo-kap"><table class="tablo"><thead><tr>
    <th>İhale</th><th class="gizle-mobil">Durum</th><th>Oluşturma</th><th>Dosyalar</th></tr></thead><tbody>
    ${satir.map((s) => `<tr data-git="#/ihale/${kodUrl(s.t.kod)}?sekme=rapor"><td><b>${e(s.t.ad || s.t.kod)}</b><small>${e(s.t.idare || s.t.kod)}</small></td>
      <td class="gizle-mobil">${durumRozet(s.t.durum)}</td><td>${e(zamanYaz(s.zaman))}</td>
      <td><div class="dugmeler">${s.html ? '<span class="uzanti">HTML</span>' : '<span class="uzanti">MD</span>'}
      ${s.ek.map((f) => `<a class="dugme kucuk" href="${url(s.t.kod, f.yol)}" download>${f.ad.endsWith(".pdf") ? "PDF" : "Excel"}</a>`).join("")}</div></td></tr>`).join("")}
    </tbody></table></div>` : '<div class="bos">Henüz rapor yok. Bir ihale için analizi başlattığınızda rapor burada listelenir.</div>'}</div>`;
  kap.onclick = (ev) => {
    if (ev.target.closest("a")) return;
    const tr = ev.target.closest("[data-git]");
    if (tr) location.hash = tr.dataset.git;
  };
}

// --- Taramalar ------------------------------------------------------------------

async function taramalar(kap) {
  baslik("Taramalar");
  const liste = await api("taramalar");
  kap.innerHTML = `<div class="kart"><h2>Günlük taramalar</h2><div class="liste">${liste.length ? liste.map((t) => `
    <a class="satir" href="#/tarama/${encodeURIComponent(t.ad)}"><span class="uzanti">MD</span><div class="govde"><b>${e(t.ad)}</b>
    <small>${e(zamanYaz(new Date(t.zaman * 1000).toISOString()))}</small></div></a>`).join("")
    : '<div class="bos">Henüz tarama yok. Asistanınıza "bugün ne çıktı?" deyin ya da ihale listesini Gelen Dosyalar\'a bırakın; tarayıcı ajan skorlu listeyi buraya yazar.</div>'}</div></div>`;
}

async function taramaDetay(kap) {
  const ad = yolBilgisi().parca[1];
  baslik(`Tarama: ${ad}`);
  const [t, takipte] = await Promise.all([api(`taramalar/${encodeURIComponent(ad)}`), api("ihaleler")]);
  const kodlar = new Set(takipte.flatMap((x) => [x.kod, x.ikn]));
  if (!t.satirlar.length) {
    kap.innerHTML = `<div class="kart"><pre style="white-space:pre-wrap">${e(t.metin)}</pre></div>`;
    return;
  }
  kap.innerHTML = `<div class="araclar"><a class="dugme" href="#/taramalar">‹ Taramalar</a><span class="not">Skor; firma profili, filtreler ve beğen/reddet geçmişinizden hesaplanır.</span></div>
  <div class="kart" style="padding:6px 8px"><div class="tablo-kap"><table class="tablo"><thead><tr><th class="sayi">Skor</th><th>İhale</th>
  <th class="gizle-mobil">İdare</th><th class="sayi gizle-mobil">Yaklaşık maliyet</th><th>Son tarih</th><th></th></tr></thead><tbody>
  ${t.satirlar.map((r, i) => {
    const ikn = r.ikn || "";
    const var_ = kodlar.has(ikn) || kodlar.has(ikn.replace(/\//g, "-"));
    return `<tr><td class="sayi"><b>${e(r.skor)}</b></td><td><b>${e(r.konu)}</b><small>${e(ikn)} · ${e(r.il)} · ${e(TUR_AD[r.tur] || r.tur)}</small>
      <small>${e(r.neden)}</small></td><td class="gizle-mobil">${e(r.idare)}</td><td class="sayi gizle-mobil">${/^[\d.,]+$/.test(r.yaklasik || "") ? para(Number(String(r.yaklasik).replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", "."))) : e(r.yaklasik)}</td><td>${e(r.son_tarih)}</td>
      <td>${var_ ? '<span class="rozet-d d-takipte">Takipte</span>' : `<button class="dugme kucuk ana-d" data-takibe="${i}">Takibe al</button>`}</td></tr>`;
  }).join("")}</tbody></table></div></div>`;
  kap.onclick = (ev) => {
    const b = ev.target.closest("[data-takibe]");
    if (!b) return;
    const r = t.satirlar[+b.dataset.takibe];
    ihaleFormu(null, { kod: r.ikn, ad: r.konu, idare: r.idare, il: r.il, tur: r.tur, yaklasik: r.yaklasik, ihale_tarihi: (r.son_tarih || "").replace(" ", "T") });
  };
}

// --- Öğrenme -------------------------------------------------------------------

async function ogrenme(kap) {
  baslik("Öğrenme");
  const o = await api("ogrenme");
  const b = o.basari;
  const enCok = Math.max(1, ...o.aylik.map((a) => a.n));
  const islem = { yuzde_ekle: "% ekle", yuzde_cikar: "% çıkar", tutar_ekle: "₺ ekle", birim_fiyat: "birim fiyat" };
  kap.innerHTML = `<div class="izgara k4">
    <div class="kart gosterge"><small>Analiz edilen ihale</small><b>${b.analiz}</b><span>${o.sayi.metraj} metraj kalemi öğrenildi</span></div>
    <div class="kart gosterge"><small>Kazanma oranı</small><b>${b.oran == null ? "—" : "%" + b.oran}</b><span>${b.kazanilan} / ${b.kazanilan + b.kaybedilen} sonuçlanan</span></div>
    <div class="kart gosterge"><small>Ortalama kazanan tenzilat</small><b>${o.tenzilat.ort_kazanan == null ? "—" : "%" + o.tenzilat.ort_kazanan.toLocaleString("tr-TR")}</b><span>${o.tenzilat.ihale} ihalenin site verisi (ARŞİV)</span></div>
    <div class="kart gosterge"><small>Öğrenilen ders</small><b>${o.sayi.dersler}</b><span>${o.sayi.tercihler} beğen/reddet kararı</span></div></div>
  <div class="izgara k2" style="margin-top:16px">
    <div class="kart"><h2>Aylık analiz ve kazanım</h2>${o.aylik.length ? `<div class="cubuklar">${o.aylik.map((a) => `<div class="cubuk" title="${e(a.ay)}: ${a.n} analiz, ${a.k || 0} kazanıldı">
      <span class="n">${a.n}</span><div class="yigin" style="height:${(a.n / enCok) * 120}px"><i style="height:${((a.k || 0) / a.n) * 100}%;background:var(--yesil)"></i><i style="flex:1;background:var(--vurgu);opacity:.35"></i></div>
      <small>${AYLAR[+a.ay.slice(5) - 1].slice(0, 3)}</small></div>`).join("")}</div>
      <div class="lejant"><span style="--c:var(--yesil)">Kazanılan</span><span style="--c:color-mix(in srgb,var(--vurgu) 35%,transparent)">Diğer analizler</span></div>` : '<div class="bos">Henüz veri yok.</div>'}</div>
    <div class="kart"><h2>Sık girilen idareler</h2>${o.idareler.length ? `<div class="liste">${o.idareler.map((i) => `<div class="satir"><div class="govde"><b>${e(i.idare)}</b></div><span class="kalan">${i.n} ihale · ${i.k || 0} kazanıldı</span></div>`).join("")}</div>` : '<div class="bos">Henüz veri yok.</div>'}</div>
    <div class="kart"><h2>Rakipler <span class="sag not">site verisi, ARŞİV</span></h2>${o.rakipler.length ? `<div class="tablo-kap"><table class="tablo"><thead><tr><th>Firma</th><th class="sayi">İhale</th><th class="sayi">Kazanma</th><th class="sayi">Ort. tenzilat</th></tr></thead><tbody>
      ${o.rakipler.map((r) => `<tr><td>${e(r.firma)}</td><td class="sayi">${r.n}</td><td class="sayi">${r.k || 0}</td><td class="sayi">${r.tz == null ? "—" : "%" + r.tz.toFixed(2)}</td></tr>`).join("")}</tbody></table></div>`
      : '<div class="bos">Rakip verisi yok. İhale sitesi girişi yapılırsa katılımcı ve teklifler buraya gelir (Ayarlar).</div>'}</div>
    <div class="kart"><h2>Kişisel hesap kurallarınız</h2>${o.kurallar.length ? `<div class="liste">${o.kurallar.map((k) => `<div class="satir"><div class="govde"><b>${e(k.ad)}</b>
      <small>${e(k.kapsam || "tüm kalemler")} · ${e(k.deger)} ${e(islem[k.islem] || k.islem)}${k.kaynak_cumle ? ` · "${e(k.kaynak_cumle)}"` : ""}</small></div></div>`).join("")}</div>`
      : '<div class="bos">Kural yok. Asistana "betona hep %15 fire eklerim" gibi söylediğinizde kural olur; sistem tahmini değişmez, yanında gösterilir.</div>'}</div>
    <div class="kart"><h2>Son öğrenilen dersler</h2>${o.dersler.length ? `<div class="liste">${o.dersler.map((d) => `<div class="satir"><div class="govde"><b style="white-space:normal">${e(d.metin)}</b>
      <small>${e(d.tarih)}${d.ajan ? " · " + e(d.ajan) : ""}${d.idare ? " · " + e(d.idare) : ""} · ${d.kullanim} kez kullanıldı</small></div></div>`).join("")}</div>` : '<div class="bos">Henüz ders yok.</div>'}</div>
    <div class="kart"><h2>Tercih eğilimleri</h2>${o.tercihler.length ? `<div class="liste">${o.tercihler.map((t) => `<div class="satir"><div class="govde"><b>${e(t.alan)}: ${e(t.deger)}</b>
      <small>${t.begen} beğeni, ${t.ret} ret</small></div><span class="kalan ${t.agirlik < 0 ? "yakin" : ""}" style="${t.agirlik > 0 ? "color:var(--yesil)" : ""}">${t.agirlik > 0 ? "+" : ""}${t.agirlik}</span></div>`).join("")}</div>`
      : '<div class="bos">Bir özellik en az 3 kararda görülünce burada ağırlık alır.</div>'}</div></div>`;
}

// --- Ayarlar -------------------------------------------------------------------

async function ayarlar(kap) {
  baslik("Ayarlar");
  const [s, o] = await Promise.all([api("siteler"), api("ozet")]);
  const izin = "Notification" in window ? Notification.permission : "yok";
  const kurulu = matchMedia("(display-mode: standalone)").matches;
  kap.innerHTML = `<div class="izgara k2">
    <div class="kart"><h2>İhale sitesi girişi</h2>
      ${s.siteler.length ? `<div class="liste">${s.siteler.map((x) => `<div class="satir"><div class="govde"><b>${e(x.ad)}</b><small>${e(x.kullanici)} · ${x.sifre_kasada ? "şifre bilgisayarın kasasında" : "şifre kaydedilmedi"}</small></div></div>`).join("")}</div>`
        : `<p class="not">${s.durum === "atlandi" ? "Site girişi atlandı." : "Henüz site eklenmedi."} Girişsiz raporda şunlar yer almaz:</p><ul class="not">${s.eksik.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`}
      <div class="dugmeler"><button class="dugme ana-d" data-eylem="siteler">Site giriş panelini aç</button></div>
      <p class="not">Şifreler yalnızca bilgisayarınızın şifre kasasında durur; bu panel şifreyi görmez ve saklamaz.</p></div>
    <div class="kart"><h2>Uygulama</h2>
      <p class="not">${kurulu ? "Panel uygulama olarak kurulu." : "Chrome ya da Edge adres çubuğundaki <b>Uygulamayı yükle</b> simgesiyle paneli masaüstü uygulaması gibi kurabilirsiniz. Telefonda kullanılmaz; panel yalnızca bu bilgisayarda çalışır."}</p>
      <div class="dugmeler">${S.kurIstegi ? '<button class="dugme ana-d" data-eylem="kur">Uygulamayı yükle</button>' : ""}
      <button class="dugme" data-eylem="bildirim" ${izin === "granted" || izin === "yok" ? "disabled" : ""}>${izin === "granted" ? "Hatırlatmalar açık" : izin === "yok" ? "Tarayıcı bildirimi desteklemiyor" : "Hatırlatmaları aç"}</button></div>
      <p class="not">Hatırlatmalar, panel açıkken ihale gününden 7, 3 ve 1 gün önce (config.yaml <code>panel.hatirlatma_gun</code>) bildirim gösterir.
      Bilgisayar açılınca panelin kendiliğinden başlaması için: <code>python panel.py baslangic --ac</code></p></div>
    <div class="kart"><h2>Analizi otomatik başlatma</h2>
      ${o.kuyruk_komutu ? `<p class="not">Analizi başlat dendiğinde şu komut çalışır:</p><div class="kopya"><span>${e(o.kuyruk_komutu)}</span></div>`
        : `<p class="not">Şu an <b>Analizi başlat</b> ihaleyi kuyruğa alır; asistanınıza "kuyruktaki ihaleleri analiz et" yazdığınızda analiz başlar ve süreç panelde canlı görünür.</p>
        <p class="not">Bilgisayarda Claude Code gibi komut satırından çalışan bir asistan varsa <code>.sistem/config.yaml</code> içinde örneğin şunu yazın:</p>
        <div class="kopya"><span>analiz_komutu: "claude -p 'ihale-analiz: {kod} için analiz zincirini başlat'"</span></div>`}</div>
    <div class="kart"><h2>Çalışma alanı</h2><dl class="bilgi"><dt>Klasör</dt><dd>${e(o.alan)}</dd><dt>Takvim</dt><dd><a href="/takvim.ics" download>ihale-ajandasi.ics</a> (Outlook, Google Takvim, telefon)</dd>
      <dt>Tema</dt><dd><div class="cipler">${[["", "Sistem"], ["acik", "Açık"], ["koyu", "Koyu"]].map(([k, v]) => `<button class="cip ${(localStorageAl("tema") || "") === k ? "secili" : ""}" data-tema-sec="${k}">${v}</button>`).join("")}</div></dd></dl>
      <div class="dugmeler" style="margin-top:12px"><button class="dugme" data-eylem="alan-ac">Klasörü aç</button></div></div></div>`;
  kap.onclick = async (ev) => {
    const tm = ev.target.closest("[data-tema-sec]");
    if (tm) { temaUygula(tm.dataset.temaSec); return ayarlar(kap); }
    const ey = ev.target.closest("[data-eylem]")?.dataset.eylem;
    try {
      if (ey === "siteler") bildir((await api("siteler", { method: "POST" })).mesaj);
      if (ey === "bildirim") { await Notification.requestPermission(); ayarlar(kap); }
      if (ey === "kur") kur();
      if (ey === "alan-ac") await api("klasor", { method: "POST", govde: { yol: "." } });
    } catch (h) { bildir(h.message, true); }
  };
}

// --- Tema, kurulum, hatırlatma --------------------------------------------------------

function localStorageAl(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localStorageYaz(k, v) { try { localStorage.setItem(k, v); } catch { /* gizli pencere */ } }

function temaUygula(t) {
  if (t) document.documentElement.dataset.tema = t; else delete document.documentElement.dataset.tema;
  localStorageYaz("tema", t || "");
}

async function hatirlat(yaklasan) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const gun = isoGun(new Date());
  const kayit = JSON.parse(localStorageAl("bildirilen") || "{}");
  const kayitBugun = kayit[gun] || [];
  const kayitSw = navigator.serviceWorker && await navigator.serviceWorker.getRegistration();
  for (const o of yaklasan) {
    const n = gunFarki(o.tarih);
    if (n > 1 || n < 0 || kayitBugun.includes(o.id)) continue;
    const baslikM = `${n === 0 ? "Bugün" : "Yarın"}: ${o.baslik}`;
    const secenek = { body: [S.sabit.etkinlik_turleri[o.tur], o.saat, o.aciklama].filter(Boolean).join(" · "),
      icon: "/ikon-192.png", tag: String(o.id), data: { url: o.kod ? `/#/ihale/${kodUrl(o.kod)}` : "/#/ajanda" } };
    if (kayitSw) kayitSw.showNotification(baslikM, secenek); else new Notification(baslikM, secenek);
    kayitBugun.push(o.id);
  }
  localStorageYaz("bildirilen", JSON.stringify({ [gun]: kayitBugun }));
}

async function kur() {
  if (!S.kurIstegi) return;
  S.kurIstegi.prompt();
  await S.kurIstegi.userChoice;
  S.kurIstegi = null;
  $("#kur-dugme").hidden = true;
}

window.addEventListener("beforeinstallprompt", (ev) => {
  ev.preventDefault();
  S.kurIstegi = ev;
  $("#kur-dugme").hidden = false;
});

document.addEventListener("click", (ev) => {
  const k = ev.target.closest("[data-kopya]");
  if (k) { navigator.clipboard?.writeText(k.dataset.kopya).then(() => bildir("Kopyalandı")); return; }
  const ey = ev.target.closest("[data-eylem]")?.dataset.eylem;
  if (ey === "yeni-ihale" && !ev.target.closest("#icerik")) ihaleFormu();
  else if (ey === "yeni-ihale" && ev.target.closest(".araclar")) ihaleFormu();
  else if (ey === "tema") {
    const koyu = document.documentElement.dataset.tema === "koyu" ||
      (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);
    temaUygula(koyu ? "acik" : "koyu");
  }
});
$("#kur-dugme").onclick = kur;
$("#pencere").addEventListener("click", (ev) => { if (ev.target.id === "pencere") ev.target.close(); });

temaUygula(localStorageAl("tema") || "");
window.addEventListener("hashchange", yonlendir);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && yolBilgisi().sayfa === "") yonlendir();
});
setInterval(() => { if (!document.hidden) api("ozet").then((o) => hatirlat(o.yaklasan)).catch(() => {}); }, 30 * 60 * 1000);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
yonlendir();
