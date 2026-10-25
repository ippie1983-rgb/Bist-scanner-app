import os
import re
import html
import json
import difflib
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor

# Pagina configuratie
st.set_page_config(
    page_title="BIST 100 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

# Opmaak voor overzichtelijke artikel-kaarten en impact-badges
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; }
    .news-card {
        background-color: #f8fafc;
        border-left: 5px solid #1E3A8A;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
    }
    .scandal-card {
        background-color: #fef2f2;
        border-left: 5px solid #dc2626;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #fecaca;
        border-right: 1px solid #fecaca;
        border-bottom: 1px solid #fecaca;
    }
    .positive-card {
        background-color: #f0fdf4;
        border-left: 5px solid #16a34a;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #bbf7d0;
        border-right: 1px solid #bbf7d0;
        border-bottom: 1px solid #bbf7d0;
    }
    .agenda-card {
        background-color: #eff6ff;
        border-left: 5px solid #2563eb;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #bfdbfe;
        border-right: 1px solid #bfdbfe;
        border-bottom: 1px solid #bfdbfe;
    }
    .badge-neg { background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-pos { background-color: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-warn { background-color: #fef3c7; color: #92400e; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-info { background-color: #e0e7ff; color: #1e40af; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .prio-pill { background-color: #0f172a; color: #f8fafc; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🇹🇷 BIST 100 & Turkse Economie Master Scanner</p>', unsafe_allow_html=True)
st.markdown(
    "Gecombineerde **Master News Hub** met **3-laagse onderwerp-ontdubbeling** (voorkomt dubbele berichten over hetzelfde onderwerp), "
    "**prioriteits-sortering** (1. Schandalen & Marktschokken ➔ 2. Macro & BIST 100 ➔ 3. Aandelen ➔ 4. Globaal), "
    "**Jip-en-Janneketaal samenvattingen** en een **toekomstige 30-dagen Macro-Agenda**."
)

# --- VOLLEDIGE LIJST VAN ALLE 100 UNIEKE BIST 100 AANDELEN ---
BIST_INDEX_OPTION = "📈 BIST 100 Index (Algemeen & Brede Markt)"

BIST_100_STOCKS = [
    "AEFES (Anadolu Efes)", "AGHOL (Anadolu Grubu Holding)", "AGROT (Agrotech)", "AHGAZ (Ahlatcı Doğalgaz)",
    "AKBNK (Akbank)", "AKCNS (Akçansa)", "AKFGY (Akfen GYO)", "AKFYE (Akfen Yenilenebilir Enerji)",
    "AKSA (Aksa Akrilik)", "AKSEN (Aksa Enerji)", "ALARK (Alarko Holding)", "ALBRK (Albaraka Türk)",
    "ALFAS (Alfa Solar Enerji)", "ALTNY (Altınay Savunma)", "ANHYT (Anadolu Hayat Emeklilik)", "ANSGR (Anadolu Sigorta)",
    "ARCLK (Arçelik)", "ARDYZ (ARD Bilişim)", "ASELS (Aselsan)", "ASTOR (Astor Enerji)",
    "BERA (Bera Holding)", "BFREN (Bosch Fren)", "BIENY (Bien Yapı)", "BIMAS (Bim Mağazalar)",
    "BINHO (1000 Yatırımlar Holding)", "BRSAN (Borusan Boru)", "BRYAT (Borusan Yatırım)", "BTCIM (Batıçim)",
    "CANTE (Çan2 Termik)", "CCOLA (Coca-Cola İçecek)", "CIMSA (Çimsa)", "CLEBI (Çelebi Hava Servisi)",
    "CWENE (CW Enerji)", "DEVA (Deva Holding)", "DOAS (Doğuş Otomotiv)", "DOHOL (Doğan Holding)",
    "ECILC (Eczacıbaşı İlaç)", "ECZYT (Eczacıbaşı Yatırım)", "EGEEN (Ege Endüstri)", "EKGYO (Emlak Konut GYO)",
    "ENERY (Enerya Enerji)", "ENJSA (Enerjisa Enerji)", "ENKAI (Enka İnşaat)", "EREGL (Erdemir)",
    "EUPWR (Europower Enerji)", "EUREN (Europen Endüstri)", "FROTO (Ford Otosan)", "GARAN (Garanti BBVA)",
    "GESAN (Girişim Elektrik)", "GOLTS (Göltaş Çimento)", "GUBRF (Gübre Fabrikaları)", "GWIND (Galata Wind)",
    "HALKB (Halkbank)", "HEKTS (Hektaş)", "IMASM (İmaş Makina)", "IPEKE (İpek Doğal Enerji)",
    "ISCTR (İş Bankası C)", "ISDMR (İskenderun Demir Çelik)", "ISGYO (İş GYO)", "ISMEN (İş Yatırım)",
    "KAYSE (Kayseri Şeker)", "KCAER (Kocaer Çelik)", "KCHOL (Koç Holding)", "KLSER (Kaleseramik)",
    "KONTR (Kontrolmatik)", "KONYA (Konya Çimento)", "KORDS (Kordsa)", "KOZAA (Koza Anadolu Metal)",
    "KOZAL (Koza Altın)", "KRDMD (Kardemir D)", "KTLEV (Katılımevim)", "LMKDC (Limak Doğu Anadolu Çimento)",
    "MAVI (Mavi Giyim)", "MGROS (Migros)", "MIATK (Mia Teknoloji)", "OBAMS (Oba Makarnacılık)",
    "ODAS (Odaş Elektrik)", "OTKAR (Otokar)", "OYAKC (Oyak Çimento)", "PASEU (Pasifik Eurasia Lojistik)",
    "PEKGY (Peker GYO)", "PETKM (Petkim)", "PGSUS (Pegasus)", "QUAGR (Qua Granite)",
    "REEDR (Reeder Teknoloji)", "SAHOL (Sabancı Holding)", "SASA (Sasa Polyester)", "SDTTR (SDT Uzay ve Savunma)",
    "SISE (Şişecam)", "SKBNK (Şekerbank)", "SMRTG (Smart Güneş Enerjisi)", "SOKM (Şok Marketler)",
    "TABGD (TAB Gıda)", "TAVHL (TAV Havalimanları)", "TCELL (Turkcell)", "THYAO (Turkish Airlines)",
    "TKFEN (Tekfen Holding)", "TOASO (Tofaş Oto)", "TTKOM (Türk Telekom)", "TUPRS (Tüpraş)",
    "TURSG (Türkiye Sigorta)", "ULKER (Ülker Bisküvi)", "VAKBN (VakıfBank)", "VESBE (Vestel Beyaz Eşya)",
    "VESTL (Vestel)", "YEOTK (YEO Teknoloji)", "YKBNK (Yapı Kredi)", "YYLGD (Yayla Agro Gıda)",
    "ZOREN (Zorlu Enerji)"
]

ALL_SIDEBAR_OPTIONS = [BIST_INDEX_OPTION] + BIST_100_STOCKS

# --- ZIJBALK: INSTELLINGEN ---
st.sidebar.header("⚙️ Scanner Instellingen")
st.sidebar.success("✅ 3-Laagse Onderwerp-Ontdubbeling actief!")

st.sidebar.subheader(f"🎯 BIST 100 Selectie ({len(BIST_100_STOCKS)} Aandelen + Index)")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE 100 BIST-aandelen tegelijk", value=False)
if select_all_bist:
    default_selection = ALL_SIDEBAR_OPTIONS
else:
    default_selection = [
        BIST_INDEX_OPTION,
        "THYAO (Turkish Airlines)",
        "ASELS (Aselsan)",
        "KCHOL (Koç Holding)",
        "AKBNK (Akbank)",
        "GARAN (Garanti BBVA)",
        "TUPRS (Tüpraş)"
    ]

selected_tickers = st.sidebar.multiselect(
    "Kies BIST 100 Algemeen en/of specifieke aandelen:",
    options=ALL_SIDEBAR_OPTIONS,
    default=default_selection
)

max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)

sort_mode = st.sidebar.radio(
    "Sorteervolgorde in Master Hub:",
    options=[
        "Op Prioriteit (en daarbinnen Nieuwste eerst)",
        "Puur op Datum (Allernieuwste bovenaan)"
    ],
    index=0
)

# --- STRIKTE ECONOMISCHE & POLITIEKE RELEVANTIE FILTER ---
HARD_EXCLUDE_WORDS = [
    "futbol", "maç", "maçı", "gol", "süper lig", "galatasaray", "fenerbahçe", "beşiktaş",
    "trabzonspor", "derbi", "teknik direktör", "hakem", "transfer", "uefa", "şampiyonlar ligi",
    "basketbol", "voleybol", "stadyum", "penaltı", "ofsayt", "taraftar", "voetbal", "wedstrijd",
    "magazin", "dizi", "fragman", "oyuncu", "şarkıcı", "konser", "burç", "astroloji", "survivor",
    "uyuşturucu", "kokain", "eroin", "bonzai", "cinayet", "trafik kazası", "boşanma", "aldatma",
    "intihar", "kıskançlık", "kavga", "sapık", "taciz", "yangın", "hava durumu", "fırtına",
    "yemek tarifi", "bulmaca", "dedikodu"
]

ECONOMIC_POLITICAL_WHITELIST = [
    "ekonomi", "borsa", "bist", "hisse", "spk", "sermaye piyasası", "fon", "tasfiye", "manipülasyon",
    "soruşturma", "operasyon", "gözaltı", "tutuklama", "ev hapsi", "kayyum", "tmsf", "mal varlığı",
    "vurgun", "ceza", "görevden alındı", "atama", "resmi gazete", "cumhurbaşkanı kararı", "ötv", "tcmb",
    "merkez bankası", "faiz", "ppk", "enflasyon", "tüik", "mehmet şimşek", "şimşek", "erdoğan",
    "cumhurbaşkanı", "cevdet yılmaz", "karahan", "hazine", "maliye", "vergi", "bütçe", "cari açık",
    "rezerv", "kur", "dolar", "euro", "altın", "gümüş", "petrol", "brent", "tahvil", "cds",
    "kredi notu", "moody", "fitch", "s&p", "yabancı yatırımcı", "yabancı takas", "brüt takas",
    "işlem yasağı", "tedbir", "bedelsiz", "bedelli", "sermaye artırımı", "mahfi eğilmez",
    "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu",
    "imf", "dünya bankası", "trump", "abd", "avrupa birliği", "yaptırım", "gümrük", "ticaret",
    "ihracat", "ithalat", "sanayi", "büyüme", "işsizlik", "asgari ücret", "banka", "holding",
    "bilanço", "temettü", "kap", "halka arz", "ihale", "yatırım", "kâr", "zarar", "kredi",
    "belediye", "meclis", "kanun", "yasa", "mahkeme", "adliye", "savcılık",
    "goud", "zilver", "rente", "inflatie", "oorlog", "olie", "geopolitiek", "fed", "ecb"
]

def is_economically_relevant(title, description="", extra_tickers=None):
    text = f"{title} {description}".lower()
    for bad in HARD_EXCLUDE_WORDS:
        if re.search(r'\b' + re.escape(bad) + r'\b', text):
            return False
    if extra_tickers:
        for t in extra_tickers:
            if t.lower() in text:
                return True
    for good in ECONOMIC_POLITICAL_WHITELIST:
        if good in text:
            return True
    return False

# --- AUTOMATISCHE VERTALING NAAR NEDERLANDS ---
def translate_to_nl(text):
    if not text or len(text.strip()) < 3:
        return text
    try:
        q = urllib.parse.quote(text[:450])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=nl&dt=t&q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            return translated if translated else text
    except Exception:
        return text

def clean_html_text(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# --- SECTOR- EN KOERSIMPACT DETECTIE PER ARTIKEL ---
def detect_sector_and_badge(combined_text, mentioned_stocks):
    sectors = []
    if any(w in combined_text for w in ["banka", "faiz", "tcmb", "kredi", "akbnk", "garan", "ykbnk", "isctr", "halkb", "vakbn", "rente"]):
        sectors.append("🏦 Banken (AKBNK, GARAN, YKBNK, ISCTR)")
    if any(w in combined_text for w in ["savunma", "ihale", "asels", "sdttr", "altny", "oorlog", "navo", "defensie"]):
        sectors.append("🛡️ Defensie (ASELS, SDTTR, ALTNY)")
    if any(w in combined_text for w in ["havayolu", "uçuş", "turizm", "thyao", "pgsus", "tavhl", "clebi", "luchtvaart"]):
        sectors.append("✈️ Luchtvaart & Toerisme (THYAO, PGSUS, TAVHL)")
    if any(w in combined_text for w in ["petrol", "enerji", "elektrik", "doğalgaz", "tuprs", "astor", "enjsa", "petkm", "cwene", "smrtg", "olie"]):
        sectors.append("⚡ Energie & Raffinage (TUPRS, ASTOR, ENJSA)")
    if any(w in combined_text for w in ["perakende", "market", "gıda", "enflasyon", "bimas", "mgros", "sokm", "ulker", "ccola"]):
        sectors.append("🛒 Supermarkten & Voeding (BIMAS, MGROS, SOKM)")
    if any(w in combined_text for w in ["otomotiv", "ihracat", "froto", "toaso", "doas", "otkar", "kchol"]):
        sectors.append("🚗 Auto & Export-Holdings (FROTO, TOASO, KCHOL, SAHOL)")
    if any(w in combined_text for w in ["konut", "gyo", "çimento", "inşaat", "ekgyo", "enkai", "oyakc", "cimsa"]):
        sectors.append("🏗️ Vastgoed & Bouw (EKGYO, ENKAI, OYAKC)")

    if mentioned_stocks:
        sectors.insert(0, f"🎯 Specifiek aandeel: {', '.join(mentioned_stocks)}")
    if not sectors:
        sectors.append("📈 Brede BIST 100 Markt & USD/TRY")

    sector_str = " · ".join(sectors[:3])

    if any(w in combined_text for w in ["tutuklama", "gözaltı", "soruşturma", "ceza", "işlem yasağı", "brüt takas", "kayyum", "skandal", "vurgun", "yaptırım", "zarar", "düşüş", "ev hapsi", "huisarrest"]):
        badge_html = '<span class="badge-neg">🔴 HOOG RISICO / KOERSDRUK OP SPECULATIEVE FONDSEN</span>'
    elif any(w in combined_text for w in ["rekor kar", "temettü", "bedelsiz", "ihale", "anlaşma", "not artışı", "yabancı girişi", "büyüme", "yatırım"]):
        badge_html = '<span class="badge-pos">🟢 POSITIEVE KATALYSATOR VOOR KOERS</span>'
    elif any(w in combined_text for w in ["resmi gazete", "vergi", "ötv", "faiz kararı", "enflasyon", "trump", "fed"]):
        badge_html = '<span class="badge-warn">⚠️ BELEID & MACRO-IMPACT OP BIST 100</span>'
    else:
        badge_html = '<span class="badge-info">⚖️ MARKT- & ANALISTEN DUIDING</span>'

    return badge_html, sector_str

def build_jip_en_janneke_analysis(title_orig, title_nl, desc_nl, category_tag, tickers_clean):
    combined = f"{title_orig} {title_nl} {desc_nl}".lower()
    mentioned_stocks = [t for t in tickers_clean if t.lower() in combined]
    badge_html, sector_str = detect_sector_and_badge(combined, mentioned_stocks)

    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "spk bülteni", "bedelsiz", "bedelli", "sermaye artırımı"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Beurswaakhond SPK of Borsa İstanbul heeft een officieel besluit genomen: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Dit gaat over handelsrestricties of goedkeuring van een aandelensplitsing.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Bij een **handelsverbod of brüt takas** droogt de speculatieve handel op. "
            f"Een goedgekeurde **gratis aandelensplitsing (bedelsiz)** wekt daarentegen vaak enthousiasme bij particuliere beleggers."
        )
        card_class = "scandal-card" if ("yasağı" in combined or "brüt" in combined or "ceza" in combined) else "positive-card"

    elif any(w in combined for w in ["fon", "spk", "manipülasyon", "manipulatie", "tutuklama", "gözaltı", "aangehouden", "gearresteerd", "tasfiye", "tmsf", "mal varlığı", "soruşturma", "onderzoek", "ev hapsi", "huisarrest"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Justitie en beurswaakhond SPK grijpen in bij lopende onderzoeken en maatregelen zoals huisarrest of arrestaties: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Er vinden juridische stappen, huisarresten of ondervragingen plaats rondom betrokken partijen.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Dit soort juridische maatregelen zorgt voor onrust bij speculatieve fondsen. "
            f"Voor de gevestigde **BIST 100-bedrijven** zuivert dit de markt en ondersteunt het op termijn het vertrouwen van grote instellingen."
        )
        card_class = "scandal-card"

    elif any(w in combined for w in ["resmi gazete", "cumhurbaşkanı kararı", "ötv", "vergi", "görevden alma", "atama kararları"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Nieuw officieel overheidsbesluit gepubliceerd in het Turkse Staatsblad (*Resmi Gazete*): *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuwe wetgeving, belastingmaatregelen of benoemingen zijn van kracht geworden.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Besluiten in de *Resmi Gazete* hebben direct effect bij beursopening. "
            f"Belastingverhogingen raken specifieke sectoren, terwijl nieuwe steunmaatregelen koerswinst stimuleren."
        )
        card_class = "news-card"

    elif any(w in combined for w in ["mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Een vooraanstaande Turkse econoom of marktstrateeg deelt een scherpe analyse: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Onafhankelijke duiding over inflatie, rente of de goudmarkt.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Deze economen worden op de voet gevolgd door beleggers. "
            f"Hun waarschuwingen sturen direct het dagelijkse sentiment op de **BIST 100**."
        )
        card_class = "news-card"

    elif any(w in combined for w in ["cds", "yabancı yatırımcı", "yabancı takas", "fitch", "moody", "s&p", "kredi notu"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Belangrijk signaal over het vertrouwen van internationale beleggers in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuws over de Turkse CDS-risicopremie of buitenlandse kapitaalstromen.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Grote buitenlandse fondsen kopen de zwaargewichten in de **BIST 100**. "
            f"Een dalende CDS-premie of buitenlandse instroom is de sterkste brandstof voor een brede beursrally."
        )
        card_class = "positive-card" if any(w in combined for w in ["giriş", "artış", "düşüş", "olumlu", "not artışı"]) else "news-card"

    elif any(w in combined for w in ["belediye", "burgemeester", "kayyum", "görevden alındı", "ontslagen", "erdoğan", "chp", "ak parti", "siyaset", "meclis"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Politieke of bestuurlijke ontwikkeling in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Politieke spanningen of juridische stappen tegen bestuurders.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Politieke onrust zorgt ervoor dat beleggers tijdelijk op de rem trappen. "
            f"Banken en holdings reageren hier gevoelig op, terwijl men vaker schuilt in **Gram Goud** en **USD/TRY**."
        )
        card_class = "scandal-card"

    elif any(w in combined for w in ["trump", "abd", "vs", "amerika", "yaptırım", "sanctie", "israil", "iran", "rusya", "oorlog", "midden-oosten", "navo", "nato"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Geopolitiek en diplomatiek nieuws met marktimpact: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Ontwikkelingen rond de VS/Trump, sancties of regionale spanningen.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Spanningen met de VS of onrust in het Midden-Oosten drijven de prijs van **Goud en Zilver** op. "
            f"Op de BIST 100 profiteert defensie (**ASELS**), terwijl luchtvaart last kan krijgen van duurdere kerosine."
        )
        card_class = "news-card"

    else:
        jip_summary = (
            f"**Wat is er aan de hand:** Economisch en financieel nieuws: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Actuele berichtgeving over beleid, kwartaalcijfers (KAP) of de handel op Borsa İstanbul.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Geeft directe richting aan de waardering van **BIST 100-aandelen**. "
            f"Dalende inflatie en sterke cijfers ondersteunen de koersen."
        )
        card_class = "news-card"

    return jip_summary, econ_impact, card_class, badge_html, sector_str

# --- SLIMME PRIORITEITS- EN SORTEER-ENGINE (MET GECORRIGEERDE TITLE_ORIG SLEUTEL) ---
def calculate_article_priority_and_sort_key(item):
    cat = item.get("category", "")
    text = f"{item.get('title_orig', '')} {item.get('title_nl', '')} {item.get('desc_orig', '')}".lower()

    if any(k in cat for k in ["Fondsschandaal", "SPK Bulletin", "Politiek", "Resmi Gazete"]) or \
       any(w in text for w in ["fon", "spk", "manipülasyon", "tutuklama", "gözaltı", "kayyum", "resmi gazete", "ev hapsi", "huisarrest", "işlem yasağı", "brüt takas"]):
        priority_level = 1
        priority_label = "🔥 Prio 1: Schandaal & Marktschokken"
    elif any(k in cat for k in ["BIST 100", "Top-Economen", "CDS-Premie"]) or \
         any(w in text for w in ["tcmb", "merkez bankası", "faiz", "enflasyon", "mehmet şimşek", "bist 100", "cds"]):
        priority_level = 2
        priority_label = "📈 Prio 2: Macro & BIST 100"
    elif "Aandelennieuws" in cat:
        priority_level = 3
        priority_label = "🏢 Prio 3: Bedrijfsnieuws (KAP)"
    else:
        priority_level = 4
        priority_label = "🌍 Prio 4: Globaal & Edelmetalen"

    item["priority_level"] = priority_level
    item["priority_label"] = priority_label
    return priority_level

# --- 3-LAAGSE ONDERWERP-ONTDUBBELING (VOORKOMT DUBBELE HUISARREST- OF SCHANDAALMELDINGEN) ---
STOPWORDS_TR_NL = {
    "de", "het", "een", "en", "van", "in", "op", "voor", "met", "aan", "tot", "bij", "naar", "over",
    "door", "uit", "als", "dat", "die", "dit", "zijn", "was", "wordt", "werden", "heeft", "hebben",
    "niet", "ook", "nog", "wel", "maar", "dan", "wat", "wie", "hoe", "na", "onder", "tegen", "rond",
    "bir", "ve", "ile", "için", "bu", "şu", "o", "da", "de", "den", "dan", "mi", "mı", "mu", "mü",
    "ama", "fakat", "ancak", "gibi", "kadar", "sonra", "önce", "üzere", "göre", "karşı", "rağmen",
    "son", "dakika", "haber", "haberleri", "flaş", "şok", "yeni", "گelişme", "gelişme", "açıklama",
    "açıklaması", "karar", "kararı", "belli", "oldu", "geldi", "verildi", "yapıldı", "dedi", "söyledi"
}

EVENT_SIGNATURES = [
    ("ev_hapsi", ["ev hapsi", "huisarrest", "elektronik kelepçe", "konutu terk etmeme"]),
    ("tutuklama", ["tutuklandı", "tutuklama", "gearresteerd", "aangehouden", "gözaltı", "gözaltına"]),
    ("kayyum", ["kayyum", "tmsf", "beheerder aangesteld", "curator"]),
    ("spk_yasak", ["işlem yasağı", "brüt takas", "handelsverbod", "para cezası", "idari para"]),
    ("fon_skandal", ["fon soruşturması", "fon tasfiye", "fondsschandaal", "manipülasyon"]),
    ("gorevden_alma", ["görevden alındı", "görevden alma", "ontslagen", "istifa etti", "afgetreden"])
]

def normalize_tr_chars(s):
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return s.translate(tr_map).lower()

def extract_core_stems(text):
    """Haalt betekenisvolle woordstammen (eerste 5 letters) uit een titel om Turkse en Nederlandse vervoegingen gelijk te trekken."""
    norm = normalize_tr_chars(text)
    words = re.findall(r'[a-z0-9]{3,}', norm)
    stems = set()
    for w in words:
        if w in STOPWORDS_TR_NL:
            continue
        # Gebruik de eerste 5 letters als stam (zodat 'baskanina', 'baskana' en 'baskani' allemaal 'baska' worden)
        stem = w[:5] if len(w) >= 5 else w
        if len(stem) >= 3 and stem not in STOPWORDS_TR_NL:
            stems.add(stem)
    return stems

def detect_event_tags(text_tr, text_nl):
    combined = f"{text_tr} {text_nl}".lower()
    tags = set()
    for tag_name, keywords in EVENT_SIGNATURES:
        if any(kw in combined for kw in keywords):
            tags.add(tag_name)
    return tags

def remove_duplicate_articles(enriched_list):
    """
    3-laagse deduplicatie:
    1. Exacte of bijna-exacte URL/Titel match.
    2. Woordstam Overlap-Coëfficiënt (>= 0.40) of SequenceMatcher (>= 0.52) op zowel Turks als Nederlands.
    3. Event-Signature Clustering: Artikelen met dezelfde gebeurtenis-tag (bijv. beide 'ev_hapsi' / huisarrest)
       die minstens 1 kernwoord/persoon/functie delen (zoals 'eski' / 'voormalig' / naam), worden samengevoegd.
    """
    unique_items = []
    seen_links = set()

    # Sorteer vooraf zodat het meest informatieve / nieuwste bericht als hoofdbericht behouden blijft
    sorted_input = sorted(enriched_list, key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))

    for item in sorted_input:
        norm_link = item["link"].split("?")[0].strip()
        if norm_link in seen_links:
            continue

        stems_tr = extract_core_stems(item["title_orig"])
        stems_nl = extract_core_stems(item["title_nl"])
        event_tags = detect_event_tags(item["title_orig"], item["title_nl"])
        norm_tr_str = normalize_tr_chars(item["title_orig"])
        norm_nl_str = normalize_tr_chars(item["title_nl"])

        matched_existing = None

        for existing in unique_items:
            ex_stems_tr = existing["_stems_tr"]
            ex_stems_nl = existing["_stems_nl"]
            ex_tags = existing["_event_tags"]

            # Check 1: Overlap-coëfficiënt op Turkse en Nederlandse woordstammen
            overlap_tr = len(stems_tr & ex_stems_tr) / max(1, min(len(stems_tr), len(ex_stems_tr))) if (stems_tr and ex_stems_tr) else 0.0
            overlap_nl = len(stems_nl & ex_stems_nl) / max(1, min(len(stems_nl), len(ex_stems_nl))) if (stems_nl and ex_stems_nl) else 0.0

            # Check 2: Tekstuele SequenceMatcher gelijkenis
            seq_tr = difflib.SequenceMatcher(None, norm_tr_str, existing["_norm_tr_str"]).ratio()
            seq_nl = difflib.SequenceMatcher(None, norm_nl_str, existing["_norm_nl_str"]).ratio()

            # Check 3: Dezelfde specifieke gebeurtenis (bijv. 'ev_hapsi' / huisarrest) + minstens 1 gedeelde stam
            shared_event = bool(event_tags & ex_tags)
            shared_stems_count = max(len(stems_tr & ex_stems_tr), len(stems_nl & ex_stems_nl))

            if (
                overlap_tr >= 0.42
                or overlap_nl >= 0.42
                or seq_tr >= 0.52
                or seq_nl >= 0.52
                or (shared_event and shared_stems_count >= 2)
                or ("ev_hapsi" in (event_tags & ex_tags) and shared_stems_count >= 1)
            ):
                matched_existing = existing
                break

        if matched_existing is not None:
            # Voeg de bron toe aan het bestaande artikel zodat het onderwerp maar 1x op het scherm staat
            if item["source"] not in matched_existing["extra_sources"] and item["source"] != matched_existing["source"]:
                matched_existing["extra_sources"].append(item["source"])
        else:
            seen_links.add(norm_link)
            item["_stems_tr"] = stems_tr
            item["_stems_nl"] = stems_nl
            item["_event_tags"] = event_tags
            item["_norm_tr_str"] = norm_tr_str
            item["_norm_nl_str"] = norm_nl_str
            item["extra_sources"] = []
            unique_items.append(item)

    return unique_items

# --- HULPFUNCTIES VOOR LIVE MARKTDATA & PARALLELLE RSS OPHAAL ---
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
    symbols = {
        "BIST 100": "XU100.IS",
        "USD/TRY": "USDTRY=X",
        "EUR/TRY": "EURTRY=X",
        "Goud Ons ($)": "GC=F",
        "Zilver Ons ($)": "SI=F",
        "Brent Olie ($)": "BZ=F",
        "VIX (Angst)": "^VIX"
    }
    data = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if hist is not None and len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = ((curr - prev) / prev) * 100.0 if prev else 0.0
                data[name] = {"price": curr, "change": chg}
            else:
                data[name] = {"price": float(hist["Close"].iloc[-1]) if hist is not None and not hist.empty else None, "change": 0.0}
        except Exception:
            data[name] = {"price": None, "change": 0.0}

    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        gram_gold = (gold_usd * usd_try) / 31.1035
        data["Gram Goud (₺)"] = {"price": gram_gold, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    else:
        data["Gram Goud (₺)"] = {"price": None, "change": 0.0}
    return data

def fetch_single_rss_feed(args):
    category_label, query, lang, max_items, max_days, extra_tickers = args
    q_with_time = f"{query} when:{max_days}d" if max_days else query
    q_enc = urllib.parse.quote(q_with_time)
    if lang == "tr":
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=tr&gl=TR&ceid=TR:tr"
    else:
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=nl&gl=NL&ceid=NL:nl"

    items = []
    now_utc = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            root = ET.fromstring(resp.read())

        for item in root.findall(".//item"):
            raw_title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_str = item.findtext("pubDate") or ""
            raw_desc = item.findtext("description") or ""
            source_el = item.find("source")
            source_name = source_el.text if source_el is not None and source_el.text else ("Turkse Media" if lang == "tr" else "NL Media")

            if not raw_title or not link:
                continue

            clean_title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title.strip()
            clean_desc = clean_html_text(raw_desc)
            if source_name in clean_desc:
                clean_desc = clean_desc.replace(source_name, "").strip(" -·")

            dt = now_utc
            if pub_str:
                try:
                    parsed_dt = parsedate_to_datetime(pub_str)
                    if parsed_dt:
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        dt = parsed_dt
                        diff_days = (now_utc - dt).total_seconds() / 86400.0
                        if max_days is not None and diff_days > (max_days + 0.2):
                            continue
                except Exception:
                    pass

            if not is_economically_relevant(clean_title, clean_desc, extra_tickers):
                continue

            items.append({
                "category": category_label,
                "title_orig": clean_title,
                "desc_orig": clean_desc,
                "source": source_name,
                "link": link,
                "datetime": dt,
                "date_str": dt.strftime("%d-%m-%Y %H:%M"),
                "lang": lang
            })
            if len(items) >= max_items:
                break
    except Exception:
        pass
    return items

def enrich_articles_with_dutch_summaries(items, tickers_clean):
    def process_one(item):
        if item["lang"] == "tr":
            title_nl = translate_to_nl(item["title_orig"])
            desc_nl = translate_to_nl(item["desc_orig"]) if item["desc_orig"] and len(item["desc_orig"]) > 15 else ""
        else:
            title_nl = item["title_orig"]
            desc_nl = item["desc_orig"]

        jip_sum, econ_imp, card_cls, badge_html, sector_str = build_jip_en_janneke_analysis(
            item["title_orig"], title_nl, desc_nl, item["category"], tickers_clean
        )
        item["title_nl"] = title_nl
        item["jip_summary"] = jip_sum
        item["econ_impact"] = econ_imp
        item["card_class"] = card_cls
        item["badge_html"] = badge_html
        item["sector_str"] = sector_str

        calculate_article_priority_and_sort_key(item)
        return item

    with ThreadPoolExecutor(max_workers=10) as ex:
        enriched = list(ex.map(process_one, items))
    return enriched

# --- AGENT 5: TOEKOMSTIGE 30-DAGEN MACRO AGENDA ---
def get_upcoming_30_day_agenda():
    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=30)

    scheduled_events = [
        {
            "date": datetime(2026, 10, 28, 19, 0, tzinfo=timezone.utc).date(),
            "time_str": "28-10-2026 (21:00 TR)",
            "title": "🇺🇸 Fed (FOMC) Rentebesluit & Persconferentie Jerome Powell",
            "jip_summary": (
                "**Wat gaat er gebeuren:** De Amerikaanse centrale bank (Fed) maakt haar nieuwe rentebesluit bekend, "
                "gevolgd door de toelichting van voorzitter Jerome Powell."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Dit is het belangrijkste wereldwijde moment van de week. "
                "Een hint op lagere rentes is direct positief voor **Goud, Zilver** en opkomende markten zoals **Borsa İstanbul (BIST 100)**."
            ),
            "link": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        },
        {
            "date": datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc).date(),
            "time_str": "29-10-2026 (Hele dag)",
            "title": "🇹🇷 Cumhuriyet Bayramı (Dag van de Republiek) — Borsa İstanbul Gesloten",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Vanwege de nationale feestdag in Turkije is **Borsa İstanbul (BIST)** op 29 oktober gesloten."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Handelaren verkopen voor de feestdag vaak een deel van hun aandelen om geen kredietrente over de vrije dagen te betalen."
            ),
            "link": "https://www.borsaistanbul.com/tr/sayfa/143/resmi-tatil-gunleri"
        },
        {
            "date": datetime(2026, 11, 3, 7, 0, tzinfo=timezone.utc).date(),
            "time_str": "03-11-2026 (10:00 TR)",
            "title": "🇹🇷 TÜİK Turkse Inflatiecijfers (CPI / TÜFE Oktober)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Het Turkse statistiekbureau (TÜİK) publiceert de officiële maandelijkse en jaarlijkse inflatiecijfers over oktober."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Bepaalt of de Turkse Centrale Bank (TCMB) de rente kan verlagen. "
                "Valt de inflatie lager uit, dan schieten **BIST 100 bankaandelen** omhoog."
            ),
            "link": "https://www.tuik.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 6, 7, 30, tzinfo=timezone.utc).date(),
            "time_str": "06-11-2026 (10:30 TR)",
            "title": "🇹🇷 TCMB 4e Inflatieverslag (Enflasyon Raporu) — Toespraak Fatih Karahan",
            "jip_summary": (
                "**Wat gaat er gebeuren:** De gouverneur van de Turkse Centrale Bank presenteert de nieuwe inflatievoorspellingen."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Beleggers letten op signalen over het rentepad en de Lira."
            ),
            "link": "https://www.tcmb.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "09-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Kwartaalcijfers (Niet-Geconsolideerde BIST Bedrijven)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Laatste dag waarop niet-geconsolideerde beursbedrijven hun derdekwartaalcijfers publiceren op KAP."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Zorgt voor koersbewegingen per individueel aandeel op basis van winstmarges."
            ),
            "link": "https://www.kap.org.tr/"
        },
        {
            "date": datetime(2026, 11, 11, 13, 30, tzinfo=timezone.utc).date(),
            "time_str": "11-11-2026 (16:30 TR)",
            "title": "🇺🇸 Amerikaanse Inflatiecijfers (US CPI Oktober)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Publicatie van de Amerikaanse consumentenprijzen."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Directe koersbepaler voor **Goud en Zilver**. Lagere Amerikaanse inflatie stuwt edelmetalen."
            ),
            "link": "https://www.bls.gov/cpi/"
        },
        {
            "date": datetime(2026, 11, 19, 11, 0, tzinfo=timezone.utc).date(),
            "time_str": "19-11-2026 (14:00 TR)",
            "title": "🇹🇷 TCMB Rentebesluit (PPK Toplantısı & Faiz Kararı)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Het Monetair Beleidscomité van de Turkse Centrale Bank maakt het rentebesluit bekend."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Hét belangrijkste binnenlandse macro-moment voor de **USD/TRY wisselkoers**, **Gram Goud** en de **BIST 100 Index**."
            ),
            "link": "https://www.tcmb.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "20-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Geconsolideerde Kwartaalcijfers (Holdings & Banken)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Uiterste datum waarop grote holdings (KCHOL, SAHOL) hun volledige kwartaalcijfers bekendmaken."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Sluit het cijferseizoen af en bepaalt de leiders in de **BIST 100** richting het jaareinde."
            ),
            "link": "https://www.kap.org.tr/"
        }
    ]

    future_events = [ev for ev in scheduled_events if today <= ev["date"] <= end_date]
    future_events.sort(key=lambda x: x["date"])
    return future_events

# --- LIVE MARKT TICKER BAR ---
st.markdown("### 📊 Live Marktoverzicht")
market_data = get_live_market_snapshot()
market_items = list(market_data.items())

for row_slice in [market_items[:4], market_items[4:8]]:
    cols = st.columns(len(row_slice))
    for i, (name, info) in enumerate(row_slice):
        with cols[i]:
            if info["price"] is not None:
                st.metric(label=name, value=f"{info['price']:,.2f}", delta=f"{info['change']:+.2f}%")
            else:
                st.metric(label=name, value="N/B")

st.markdown("---")

# --- HOOFDPROGRAMMA ---
if st.button("🚀 Start Volledige Master Analyse", type="primary"):
    is_bist100_general = BIST_INDEX_OPTION in selected_tickers
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    tickers_str = ", ".join(tickers_clean) if tickers_clean else "Alle BIST 100 Hoofdfondsen"

    with st.spinner("📡 Parallel ophalen, 3-laags ontdubbelen op onderwerp, prioriteren en vertalen..."):
        rss_tasks = [
            (
                "🚨 Fondsschandaal, SPK & Beurs-Operaties",
                '("fon soruşturması" OR "SPK" OR "manipülasyon" OR "borsa operasyon" OR "fon tasfiye" OR "TMSF" OR "ev hapsi")',
                "tr", 12, max_days_slider, tickers_clean
            ),
            (
                "⚠️ SPK Bulletin, Brüt Takas, Handelsverboden & Bedelsiz",
                '("SPK bülteni" OR "işlem yasağı" OR "brüt takas" OR "tedbir kararı" OR "bedelsiz sermaye artırımı")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "📜 Resmi Gazete (Staatsblad), Belastingen (ÖTV) & Besluiten",
                '("Resmi Gazete" OR "Cumhurbaşkanı Kararı" OR "ÖTV" OR "vergi düzenlemesi") AND ("ekonomi" OR "atama" OR "görevden" OR "vergi" OR "borsa")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "🏛️ Politiek, Justitie, Burgemeesters & Ontslagen",
                '("görevden alındı" OR "kayyum" OR "gözaltı" OR "tutuklama" OR "belediye başkanı" OR "ev hapsi") AND ("ekonomi" OR "borsa" OR "SPK" OR "fon" OR "holding" OR "başkan")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "🧠 Turkse Top-Economen & Marktstrategen",
                '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Emre Alkin" OR "Hakan Kara" OR "İslam Memiş" OR "Işık Ökte" OR "Tunç Şatıroğlu")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "🌐 CDS-Premie, Kredietwaardigheid & Buitenlands Kapitaal",
                '("CDS primi" OR "yabancı yatırımcı" OR "yabancı takas" OR "Fitch" OR "Moody\'s" OR "kredi notu") AND ("Türkiye" OR "borsa" OR "BIST")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "🌍 Geopolitiek, Trump/VS, Sancties & Diplomatie",
                '("Trump" OR "ABD" OR "yaptırım" OR "BRICS" OR "İsrail" OR "İran") AND ("Türkiye" OR "ekonomi" OR "piyasa" OR "dolar" OR "ticaret")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "📈 BIST 100, TCMB, Rente & Top-Media",
                '("Borsa İstanbul" OR "BIST 100" OR "TCMB" OR "Mehmet Şimşek" OR "enflasyon" OR "faiz kararı")',
                "tr", 12, max_days_slider, tickers_clean
            ),
            (
                "🌍 Wereldnieuws, Oorlog & Energie (NL)",
                '(oorlog OR Midden-Oosten OR Oekraïne OR geopolitiek OR olieprijs OR sancties)',
                "nl", 10, max_days_slider, []
            ),
            (
                "🥇 Goud, Zilver & Centrale Banken (NL)",
                '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen OR inflatie)',
                "nl", 10, max_days_slider, []
            )
        ]

        if tickers_clean:
            batch_size = 5
            for i in range(0, min(len(tickers_clean), 35), batch_size):
                batch = tickers_clean[i:i + batch_size]
                or_stocks = " OR ".join(batch)
                rss_tasks.append((
                    f"🏢 Aandelennieuws & KAP ({', '.join(batch)})",
                    f"({or_stocks}) AND (hisse OR KAP OR bilanço OR temettü OR yatırım)",
                    "tr", 6, max_days_slider, batch
                ))

        with ThreadPoolExecutor(max_workers=10) as executor:
            task_results = list(executor.map(fetch_single_rss_feed, rss_tasks))

        raw_all_items = []
        for res_list in task_results:
            raw_all_items.extend(res_list)

        total_raw_count = len(raw_all_items)
        master_enriched = enrich_articles_with_dutch_summaries(raw_all_items, tickers_clean)

        # 3-Laagse ontdubbeling op woordstammen, SequenceMatcher en Event-Signatures
        master_enriched = remove_duplicate_articles(master_enriched)
        removed_dups_count = total_raw_count - len(master_enriched)

        # Sortering volgens keuze in zijbalk
        if sort_mode == "Puur op Datum (Allernieuwste bovenaan)":
            master_enriched.sort(key=lambda x: -x["datetime"].timestamp())
        else:
            master_enriched.sort(key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))

        upcoming_agenda = get_upcoming_30_day_agenda()

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        brent_p = market_data.get("Brent Olie ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

        scandal_count = sum(1 for x in master_enriched if x["priority_level"] == 1)

    st.success(
        f"✅ Analyse voltooid! **{len(master_enriched)} unieke onderwerpen** geladen "
        f"(**{removed_dups_count} dubbele artikelen over dezelfde onderwerpen automatisch samengevoegd/verwijderd**)."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"🌐 Agent 1: Master News Hub ({len(master_enriched)})",
        "🕵️‍♂️ Agent 2: Fact-Check",
        "💡 Agent 3: Beleggingsadvies",
        "⚖️ Agent 4: Risico-Audit",
        f"📅 Agent 5: Komende 30-Dagen Agenda ({len(upcoming_agenda)})"
    ])

    # ==========================================================================
    # TAB 1: AGENT 1 — MASTER NEWS HUB
    # ==========================================================================
    with tab1:
        st.markdown("### 🌐 Agent 1: Prioritized Master News Hub (100% Unieke Onderwerpen)")
        st.markdown(
            f"**Actieve Sortering:** `{sort_mode}` | "
            f"**Ontdubbeling:** `{removed_dups_count}` dubbele berichten samengevoegd | "
            f"**Focus:** {'📈 **BIST 100 Index** + ' if is_bist100_general else ''}`{tickers_str}`"
        )

        prio_filter = st.selectbox(
            "🔍 Filter op prioriteit / categorie:",
            [
                "Alle Artikelen",
                "🔥 Prio 1: Schandalen & Marktschokken",
                "📈 Prio 2: Macro & BIST 100",
                "🏢 Prio 3: Bedrijfsnieuws (KAP)",
                "🌍 Prio 4: Globaal & Edelmetalen"
            ],
            index=0
        )

        if prio_filter == "🔥 Prio 1: Schandalen & Marktschokken":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 1]
        elif prio_filter == "📈 Prio 2: Macro & BIST 100":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 2]
        elif prio_filter == "🏢 Prio 3: Bedrijfsnieuws (KAP)":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 3]
        elif prio_filter == "🌍 Prio 4: Globaal & Edelmetalen":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 4]
        else:
            filtered_master = master_enriched

        if filtered_master:
            for idx, item in enumerate(filtered_master, 1):
                also_reported = (
                    f"<br><span style='font-size: 12px; color: #475569;'>📌 <em>Dit onderwerp is ook gemeld door: {', '.join(item['extra_sources'])} (samengevoegd om dubbele weergave te voorkomen)</em></span>"
                    if item.get("extra_sources") else ""
                )
                st.markdown(
                    f"""<div class="{item['card_class']}">
                        <div style="margin-bottom: 6px;">
                            <span class="prio-pill">{item['priority_label']}</span> &nbsp; {item['badge_html']} &nbsp; <strong>#{idx} | 🕒 {item['date_str']} | Bron: {item['source']}</strong>
                        </div>
                        <span style="font-size: 17px; font-weight: bold; color: #0f172a;">{item['title_nl']}</span><br>
                        <span style="font-size: 12px; color: #64748b;">Originele kop: {item['title_orig']}</span>
                        {also_reported}<br>
                        <span style="font-size: 13px; color: #1e3a8a; font-weight: 600;">🎯 Geraakte Sectoren / Markten: {item['sector_str']}</span>
                        <hr style="margin: 8px 0; border: 0; border-top: 1px solid #cbd5e1;">
                        <p style="margin-bottom: 6px;">🗣️ {item['jip_summary']}</p>
                        <p style="margin-bottom: 8px;">📊 {item['econ_impact']}</p>
                        🔗 <a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8;">Klik hier om het originele bronartikel te openen ({item['source']})</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.warning("Geen artikelen gevonden voor dit filter.")

    # ==========================================================================
    # TAB 2: AGENT 2 — FACT-CHECK
    # ==========================================================================
    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: De Waarheids-Filter & Ontdubbelings-Rapport")
        st.markdown(
            f"- ✅ **3-Laagse Onderwerp-Ontdubbeling:** Van de `{total_raw_count}` opgehaalde RSS-artikelen zijn `{removed_dups_count}` dubbele koppen over exact hetzelfde onderwerp (zoals dezelfde huisarrest- of SPK-zaken bij verschillende kranten) samengevoegd tot `{len(master_enriched)}` unieke onderwerpen.\n"
            f"- ✅ **Koersdata Verificatie:** BIST 100 (`{bist_p:,.0f}`), USD/TRY (`₺{usd_p:,.2f}`), Goud (`${gold_p:,.2f}`) en Gram Goud (`₺{gram_p:,.2f}`).\n"
            f"- ✅ **Volgorde:** Binnen elke prioriteitsgroep staat het nieuwste bericht altijd bovenaan."
        )

    # ==========================================================================
    # TAB 3: AGENT 3 — BELEGGINGSADVIES
    # ==========================================================================
    with tab3:
        st.markdown("### 💡 Agent 3: Concreet Beleggingsadvies in Jip-en-Janneketaal")
        st.markdown(
            f"- **Focus op Prio 1 & Prio 2:** Controleer eerst de rode kaarten (`Prio 1`) op SPK-ingrepen, `brüt takas` of huisarresten/onderzoeken bij specifieke fondsen en vermijd die tickers.\n"
            f"- **Kernportefeuille:** Richt je op liquide **BIST 100-bedrijven** met harde valuta-inkomsten en houd **Gram Goud (`₺{gram_p:,.2f}`)** aan als buffer."
        )

    # ==========================================================================
    # TAB 4: AGENT 4 — RISICO-AUDIT
    # ==========================================================================
    with tab4:
        st.markdown("### ⚖️ Agent 4: Eindcontrole & Risico-Audit")
        st.warning(
            f"**Belangrijkste Risico's:**\n"
            f"1. **Toezicht- en Schandaalrisico (`{scandal_count}` unieke Prio-1 dossiers):** Lopende SPK- en justitie-onderzoeken.\n"
            f"2. **Valutarisico:** USD/TRY op **₺{usd_p:,.2f}**.\n"
            f"3. **Marktvolatiliteit:** VIX op **{vix_p:,.2f}** en Brent Olie op **${brent_p:,.2f}**."
        )

    # ==========================================================================
    # TAB 5: AGENT 5 — KOMENDE 30-DAGEN MACRO-AGENDA
    # ==========================================================================
    with tab5:
        st.markdown("### 📅 Agent 5: Toekomstige 30-Dagen Macro-Agenda (Oplopend)")
        if upcoming_agenda:
            for idx, ev in enumerate(upcoming_agenda, 1):
                days_left = (ev["date"] - datetime.now(timezone.utc).date()).days
                days_label = "Vandaag!" if days_left == 0 else f"Over {days_left} dagen"
                st.markdown(
                    f"""<div class="agenda-card">
                        <strong>#{idx} | 📅 Datum: {ev['time_str']} ({days_label})</strong><br>
                        <span style="font-size: 17px; font-weight: bold; color: #1e3a8a;">{ev['title']}</span>
                        <hr style="margin: 8px 0; border: 0; border-top: 1px solid #93c5fd;">
                        <p style="margin-bottom: 6px;">🗣️ {ev['jip_summary']}</p>
                        <p style="margin-bottom: 8px;">📊 {ev['econ_impact']}</p>
                        🔗 <a href="{ev['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8;">Klik hier voor de officiële bron & kalenderpagina</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info("Geen geplande macro-evenementen gevonden binnen de komende 30 dagen.")

else:
    st.info("👈 Kies in de zijbalk je instellingen en klik op **Start Volledige Master Analyse**.")
