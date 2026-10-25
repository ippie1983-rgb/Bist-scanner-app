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

st.markdown('<p style="font-size: 24px; font-weight: bold; color: #1E3A8A;">🇹🇷 BIST 100 & Turkse Economie Ultimate Master Scanner</p>', unsafe_allow_html=True)
st.markdown(
    "Gecombineerde **Master News Hub** met **rechtstreekse Turkse kranten-feeds + Google News**, "
    "**slimme inhouds- & persoons-ontdubbeling**, **live koers/RSI/steun-weerstand in elke nieuwskaart**, "
    "**vrije zoekfunctie** en een **toekomstige 30-dagen Macro-Agenda**."
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
    "ISCTR (İş Bankası C)", "ISDMR (İskenderun Demir Çelik)", "ISGYO (IS GYO)", "ISMEN (İş Yatırım)",
    "KAYSE (Kayseri Şeker)", "KCAER (Kocaer Çelik)", "KCHOL (Koç Holding)", "KLSER (Kaleseramik)",
    "KONTR (Kontrolmatik)", "KONYA (Konya Çimento)", "KORDS (Kordsa)", "KOZAA (Koza Anadolu Metal)",
    "KOZAL (Koza Altın)", "KRDMD (Kardemir D)", "KTLEV (Katılımevim)", "LMKDC (Limak Doğu Anadolu Çimento)",
    "MAVI (Mavi Giyim)", "MGROS (Migros)", "MIATK (Mia Teknoloji)", "OBAMS (Oba Makarnacılık)",
    "ODAS (Odaş Elektrik)", "OTKAR (Otokar)", "OYAKC (Oyak Çimento)", "PASEU (Pasifik Eurasia Lojistik)",
    "PEKGY (Peker GYO)", "PETKM (Petkim)", "PGSUS (Pegasus)", "QUAGR (Qua Granite)",
    "REEDR (Reeder Teknoloji)", "SAHOL (Sabancı Holding)", "SASA (Sasa Polyester)", "SDTTR (SDT Uzay en Savunma)",
    "SISE (Şişecam)", "SKBNK (Şekerbank)", "SMRTG (Smart Güneş Enerjisi)", "SOKM (Şok Marketler)",
    "TABGD (TAB Gıda)", "TAVHL (TAV Havalimanları)", "TCELL (Turkcell)", "THYAO (Turkish Airlines)",
    "TKFEN (Tekfen Holding)", "TOASO (Tofaş Oto)", "TTKOM (Türk Telekom)", "TUPRS (Tüpraş)",
    "TURSG (Türkiye Sigorta)", "ULKER (Ülker Bisküvi)", "VAKBN (VakıfBank)", "VESBE (Vestel Beyaz Eşya)",
    "VESTL (Vestel)", "YEOTK (YEO Teknoloji)", "YKBNK (Yapı Kredi)", "YYLGD (Yayla Agro Gıda)",
    "ZOREN (Zorlu Enerji)"
]

ALL_SIDEBAR_OPTIONS = [BIST_INDEX_OPTION] + BIST_100_STOCKS

COMPANY_TO_TICKER_MAP = {
    "türk hava yolları": "THYAO", "turkish airlines": "THYAO",
    "aselsan": "ASELS", "koç holding": "KCHOL", "koc holding": "KCHOL",
    "akbank": "AKBNK", "garanti bbva": "GARAN", "garanti bankası": "GARAN",
    "tüpraş": "TUPRS", "tupras": "TUPRS", "bim mağazalar": "BIMAS",
    "erdemir": "EREGL", "ereğli demir": "EREGL", "şişecam": "SISE",
    "sisecam": "SISE", "sasa polyester": "SASA", "emlak konut": "EKGYO",
    "yapı kredi": "YKBNK", "iş bankası": "ISCTR", "petkim": "PETKM",
    "pegasus": "PGSUS", "tofaş": "TOASO", "arçelik": "ARCLK",
    "enka inşaat": "ENKAI", "kardemir": "KRDMD", "türk telekom": "TTKOM",
    "turkcell": "TCELL", "ford otosan": "FROTO", "migros": "MGROS",
    "şok market": "SOKM", "astor enerji": "ASTOR", "enerjisa": "ENJSA",
    "sabancı holding": "SAHOL", "oyak çimento": "OYAKC", "hektaş": "HEKTS",
    "odaş": "ODAS", "girişim elektrik": "GESAN", "kontrolmatik": "KONTR",
    "halkbank": "HALKB", "vakıfbank": "VAKBN", "alarko": "ALARK",
    "borusan": "BRSAN", "doğuş otomotiv": "DOAS", "doğan holding": "DOHOL",
    "gübre fabrikaları": "GUBRF", "koza altın": "KOZAL", "mavi giyim": "MAVI",
    "otokar": "OTKAR", "tav havalimanları": "TAVHL", "tekfen": "TKFEN",
    "ülker": "ULKER", "vestel": "VESTL", "zorlu enerji": "ZOREN",
    "anadolu efes": "AEFES", "coca-cola içecek": "CCOLA", "çimsa": "CIMSA",
    "deva holding": "DEVA", "eczacıbaşı": "ECILC", "smart güneş": "SMRTG",
    "cw enerji": "CWENE", "europower": "EUPWR", "reeder": "REEDR",
    "tab gıda": "TABGD", "türkiye sigorta": "TURSG", "katılımevim": "KTLEV"
}

DIRECT_TURKISH_RSS_FEEDS = [
    ("📰 Bloomberg HT (Direct)", "https://www.bloomberght.com/rss"),
    ("📰 Habertürk Ekonomi (Direct)", "https://www.haberturk.com/rss/ekonomi.xml"),
    ("📰 NTV Ekonomi (Direct)", "https://www.ntv.com.tr/ekonomi.rss"),
    ("📰 CNN Türk Ekonomi (Direct)", "https://www.cnnturk.com/feed/rss/ekonomi/news"),
    ("📰 Dünya Gazetesi (Direct)", "https://www.dunya.com/rss"),
    ("📰 Cumhuriyet Ekonomi (Direct)", "https://www.cumhuriyet.com.tr/rss/ekonomi.xml"),
    ("📰 T24 Gündem & Politiek (Direct)", "https://t24.com.tr/rss")
]

# --- ZIJBALK: INSTELLINGEN ---
default_env_key = os.environ.get("GEMINI_API_KEY", "")
if not default_env_key:
    try:
        default_env_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_env_key = ""

if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = default_env_key if default_env_key else ""

st.sidebar.header("⚙️ Systeem & Inhouds-Filter")
gemini_key_input = st.sidebar.text_input(
    "Gemini API Key (Optioneel voor extra AI-check):",
    type="password",
    value=st.session_state.gemini_auth
)
st.session_state.gemini_auth = gemini_key_input
st.sidebar.success("✅ Inhouds- & Persoons-Ontdubbeling actief!")

st.sidebar.markdown("---")
st.sidebar.subheader("🔎 Vrije Live Zoekopdracht (Optioneel)")
custom_search_query = st.sidebar.text_input(
    "Zoek specifiek op naam, fonds, politicus of aandeel:",
    value="",
    placeholder="Bijv. Tera, IEYHO, İmamoğlu, kayyum..."
)

st.sidebar.markdown("---")
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
    "Kies BIST 100 Index en/of specifieke aandelen:",
    options=ALL_SIDEBAR_OPTIONS,
    default=default_selection
)

max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)

include_direct_newspaper_rss = st.sidebar.checkbox(
    "⚡ Inclusief rechtstreekse Turkse kranten-feeds (BloombergHT, NTV, T24, Dünya)",
    value=True
)

dedup_strictness = st.sidebar.radio(
    "🧠 Niveau van Inhoudelijke Ontdubbeling:",
    options=[
        "Slim (1 kaart per uniek verhaal/persoon/zaak — aanbevolen)",
        "Maximaal (Groepeer alle artikelen binnen hetzelfde hoofdthema)"
    ],
    index=0
)

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
    "yemek tarifi", "bulmaca", "dedikodu", "futbolcu", "teknik adam", "milli takım"
]

ECONOMIC_POLITICAL_WHITELIST = [
    "ekonomi", "borsa", "bist", "hisse", "spk", "sermaye piyasası", "fon", "tasfiye", "manipülasyon",
    "soruşturma", "operasyon", "gözaltı", "tutuklama", "ev hapsi", "konutu terk etmeme", "kayyum",
    "tmsf", "mal varlığı", "vurgun", "ceza", "görevden alındı", "atama", "resmi gazete",
    "cumhurbaşkanı kararı", "ötv", "tcmb", "merkez bankası", "faiz", "ppk", "enflasyon", "tüik",
    "mehmet şimşek", "şimşek", "erdoğan", "cumhurbaşkanı", "cevdet yılmaz", "karahan", "hazine",
    "maliye", "vergi", "bütçe", "cari açık", "rezerv", "kur", "dolar", "euro", "altın", "gümüş",
    "petrol", "brent", "tahvil", "cds", "kredi notu", "moody", "fitch", "s&p", "yabancı yatırımcı",
    "yabancı takas", "brüt takas", "işlem yasağı", "tedbir", "bedelsiz", "bedelli", "sermaye artırımı",
    "mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte",
    "tunç şatıroğlu", "imf", "dünya bankası", "trump", "abd", "avrupa birliği", "yaptırım", "gümrük",
    "ticaret", "ihracat", "ithalat", "sanayi", "büyüme", "işsizlik", "asgari ücret", "banka",
    "holding", "bilanço", "temettü", "kap", "halka arz", "ihale", "yatırım", "kâr", "zarar", "kredi",
    "belediye", "meclis", "kanun", "yasa", "mahkeme", "adliye", "savcılık",
    "goud", "zilver", "rente", "inflatie", "oorlog", "olie", "geopolitiek", "fed", "ecb"
]

def is_economically_relevant(title, description="", extra_tickers=None, custom_kw=""):
    text = f"{title} {description}".lower()
    for bad in HARD_EXCLUDE_WORDS:
        if re.search(r'\b' + re.escape(bad) + r'\b', text):
            return False
    if custom_kw and custom_kw.strip().lower() in text:
        return True
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
        q = urllib.parse.quote(text[:480])
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

# ==============================================================================
# LIVE MARKTDATA & TECHNISCHE AANDELEN-INDICATOREN
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
    symbols = {
        "BIST 100": "XU100.IS",
        "USD/TRY": "USDTRY=X",
        "EUR/TRY": "EURTRY=X",
        "EUR/USD": "EURUSD=X",
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
    silv_usd = data.get("Zilver Ons ($)", {}).get("price")

    if usd_try and gold_usd:
        gram_gold = (gold_usd * usd_try) / 31.1035
        data["Gram Goud (₺)"] = {
            "price": gram_gold,
            "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]
        }
    else:
        data["Gram Goud (₺)"] = {"price": None, "change": 0.0}

    if usd_try and silv_usd:
        gram_silver = (silv_usd * usd_try) / 31.1035
        data["Gram Zilver (₺)"] = {
            "price": gram_silver,
            "change": data["Zilver Ons ($)"]["change"] + data["USD/TRY"]["change"]
        }
    else:
        data["Gram Zilver (₺)"] = {"price": None, "change": 0.0}

    return data

@st.cache_data(ttl=600, show_spinner=False)
def get_bist_technical_snapshots(tickers_tuple):
    snapshots = {}
    for code in tickers_tuple:
        yf_sym = f"{code}.IS"
        try:
            hist = yf.Ticker(yf_sym).history(period="3mo")
            if hist is not None and len(hist) >= 15:
                close = hist["Close"].astype(float)
                high = hist["High"].astype(float)
                low = hist["Low"].astype(float)
                curr = float(close.iloc[-1])
                prev = float(close.iloc[-2])
                chg_1d = ((curr - prev) / prev) * 100.0 if prev else 0.0
                sma20 = float(close.rolling(20).mean().iloc[-1])

                delta = close.diff()
                gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0

                w_h = float(high.tail(20).max())
                w_l = float(low.tail(20).min())
                pivot = (w_h + w_l + curr) / 3.0
                rng = max(w_h - w_l, curr * 0.02)
                s1 = pivot - (0.382 * rng)
                r1 = pivot + (0.382 * rng)

                snapshots[code] = {
                    "price": round(curr, 2),
                    "change": round(chg_1d, 2),
                    "rsi": round(rsi, 1),
                    "s1": round(s1, 2),
                    "r1": round(r1, 2),
                    "trend": "📈 Opwaarts" if curr >= sma20 else "📉 Onder SMA20"
                }
        except Exception:
            pass
    return snapshots

# ==============================================================================
# SEMANTISCHE INHOUDS-, PERSOONS- & DOSSIER-ENGINE
# ==============================================================================
SEMANTIC_CONCEPT_DICT = {
    "CONCEPT_HUISARREST": [
        "ev hapsi", "ev hapsine", "konutu terk etmeme", "elektronik kelepçe", "adli kontrol şartıyla",
        "huisarrest", "enkelband", "woning niet verlaten", "thuisdetentie", "huisarrest opgelegd"
    ],
    "CONCEPT_ARRESTATIE_JUSTITIE": [
        "tutuklandı", "tutuklama", "gözaltı", "gözaltına", "şafak operasyonu", "savcılık ifadeye",
        "gearresteerd", "aangehouden", "in hechtenis", "celstraf", "gevangenis", "opgepakt"
    ],
    "CONCEPT_FONDS_MANIPULATIE": [
        "fon soruşturması", "fon skandalı", "fon vurgunu", "fon tasfiye", "borsa manipülasyon",
        "manipülasyon soruşturması", "fondsschandaal", "beursmanipulatie", "manipulatie-onderzoek"
    ],
    "CONCEPT_SPK_MAATREGEL": [
        "işlem yasağı", "brüt takas", "tedbir kararı", "vbts", "kredili işlem yasağı", "spk bülteni",
        "idari para cezası", "handelsverbod", "handelsrestrictie", "spk boete"
    ],
    "CONCEPT_KAYYUM_BESLAG": [
        "kayyum", "tmsf", "mal varlığına el konuldu", "el koyma", "curator aangesteld", "beslag gelegd"
    ],
    "CONCEPT_ONTSLAG_BENOEMING": [
        "görevden alındı", "görevden alma", "atama kararı", "istifa etti", "ontslagen", "afgetreden", "benoemingsbesluit"
    ],
    "CONCEPT_BURG_GEMEENTE": [
        "belediye başkanı", "belediyesine", "burgemeester", "gemeente onderzoek"
    ],
    "CONCEPT_RESMI_GAZETE_BELASTING": [
        "resmi gazete", "cumhurbaşkanı kararı", "ötv zammı", "vergi düzenlemesi", "staatsblad", "belastingverhoging"
    ],
    "CONCEPT_TCMB_RENTE": [
        "faiz kararı", "ppk toplantısı", "politika faizi", "merkez bankası faiz", "fatih karahan",
        "rentebesluit", "beleidsrente", "tcmb rente"
    ],
    "CONCEPT_INFLATIE_TUIK": [
        "enflasyon rakamları", "tüfe", "tüik enflasyon", "enflasyon beklentisi", "inflatiecijfers", "consumentenprijzen"
    ],
    "CONCEPT_CDS_KREDIETNOOT": [
        "cds primi", "kredi notu", "fitch", "moody's", "s&p", "yabancı yatırımcı", "yabancı takas",
        "kredietwaardigheid", "risicopremie", "buitenlandse beleggers"
    ],
    "CONCEPT_GOUD_ZILVER": [
        "altın fiyatları", "gram altın", "ons altın", "çeyrek altın", "gümüş fiyatları",
        "goudprijs", "zilverprijs", "edelmetalen", "recordhoogte goud"
    ],
    "CONCEPT_FED_VS_TRUMP": [
        "jerome powell", "fed faiz", "fomc", "donald trump", "abd yaptırım", "gümrük vergisi",
        "amerikaanse rente", "importtarieven", "handelsoorlog"
    ],
    "CONCEPT_OORLOG_OLIE": [
        "orta doğu", "israil", "iran", "ukrayna", "rusya", "brent petrol", "petrol fiyatları",
        "midden-oosten", "olieprijs", "geopolitieke spanning"
    ],
    "CONCEPT_KAP_DIVIDEND_BILANCO": [
        "bilanço", "net kar", "çeyrek karı", "temettü", "bedelsiz sermaye", "bedelli sermaye",
        "kwartaalcijfers", "nettowinst", "dividenduitkering", "aandelensplitsing"
    ]
}

FAMOUS_PERSONS_AND_INSTITUTIONS = [
    "mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte",
    "tunç şatıroğlu", "mehmet şimşek", "fatih karahan", "recep tayyip erdoğan", "erdoğan",
    "cevdet yılmaz", "ekrem imamoğlu", "mansur yavaş", "özgür özel", "donald trump", "jerome powell"
]

STOPWORDS_ALL = {
    "de", "het", "een", "en", "van", "in", "op", "voor", "met", "aan", "tot", "bij", "naar", "over",
    "door", "uit", "als", "dat", "die", "dit", "zijn", "was", "wordt", "werden", "heeft", "hebben",
    "niet", "ook", "nog", "wel", "maar", "dan", "wat", "wie", "hoe", "na", "onder", "tegen", "rond",
    "bir", "ve", "ile", "için", "bu", "şu", "da", "den", "mi", "mı", "mu", "mü", "ama", "fakat",
    "ancak", "gibi", "kadar", "sonra", "önce", "üzere", "göre", "karşı", "rağmen", "son", "dakika",
    "haber", "haberleri", "flaş", "şok", "yeni", "gelişme", "açıklama", "açıklaması", "karar",
    "kararı", "belli", "oldu", "geldi", "verildi", "yapıldı", "dedi", "söyledi", "hakkında",
    "kapsamında", "ilişkin", "olarak", "devam", "ediyor", "etti", "çıktı", "büyük", "önemli",
    "kritik", "piyasa", "piyasalar", "ekonomi", "borsa", "istanbul", "türkiye", "turkse", "nieuws",
    "eski", "voormalig", "voormalige", "başkan", "başkanı", "voorzitter", "directeur"
}

COMMON_CAPITALIZED_IGNORE = {
    "son", "dakika", "flaş", "şok", "türkiye", "istanbul", "ankara", "izmir", "borsa", "bist",
    "spk", "tcmb", "merkez", "bankası", "resmi", "gazete", "hisse", "kap", "tüik", "fed", "abd",
    "avrupa", "altın", "gümüş", "dolar", "euro", "petrol", "yeni", "kritik", "dev", "büyük",
    "breaking", "turkse", "president", "minister", "beurs", "vandaag", "gisteren"
}

def normalize_tr(text):
    if not text:
        return ""
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return text.translate(tr_map).lower()

def extract_proper_entities_and_numbers(title_orig, title_nl):
    entities = set()
    for txt in [title_orig, title_nl]:
        tokens = re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}\b', txt)
        for tok in tokens:
            norm_tok = normalize_tr(tok)
            if norm_tok in COMMON_CAPITALIZED_IGNORE or norm_tok in STOPWORDS_ALL:
                continue
            entities.add(norm_tok[:5] if len(norm_tok) >= 5 else norm_tok)
    numbers = set(re.findall(r'\b\d+\b', f"{title_orig} {title_nl}"))
    return entities, numbers

def analyze_article_semantics(item, all_bist_tickers):
    full_text_raw = f"{item.get('title_orig', '')} {item.get('desc_orig', '')} {item.get('title_nl', '')} {item.get('desc_nl', '')}".lower()
    full_text_norm = normalize_tr(full_text_raw)

    matched_tickers = set()
    for comp_name, tick in COMPANY_TO_TICKER_MAP.items():
        if comp_name in full_text_raw or normalize_tr(comp_name) in full_text_norm:
            matched_tickers.add(tick.upper())
    for tick in all_bist_tickers:
        t_low = tick.lower()
        if re.search(r'\b' + re.escape(t_low) + r'\b', full_text_raw):
            matched_tickers.add(tick.upper())

    matched_persons = set()
    for person in FAMOUS_PERSONS_AND_INSTITUTIONS:
        if person in full_text_raw or normalize_tr(person) in full_text_norm:
            matched_persons.add(normalize_tr(person))

    proper_entities, numbers = extract_proper_entities_and_numbers(
        item.get("title_orig", ""), item.get("title_nl", "")
    )

    matched_concepts = []
    for concept_key, phrases in SEMANTIC_CONCEPT_DICT.items():
        for phrase in phrases:
            if phrase in full_text_raw or normalize_tr(phrase) in full_text_norm:
                matched_concepts.append(concept_key)
                break

    words = re.findall(r'[a-z0-9]{4,}', full_text_norm)
    core_stems = set()
    for w in words:
        if w in STOPWORDS_ALL:
            continue
        stem = w[:5]
        if stem not in STOPWORDS_ALL:
            core_stems.add(stem)

    if "CONCEPT_HUISARREST" in matched_concepts:
        story_cluster = "CLUSTER_HUISARREST_ZAAK"
        topic_readable = "⚖️ Dossier: Huisarrest & Justitiële Maatregel"
    elif "CONCEPT_FONDS_MANIPULATIE" in matched_concepts:
        story_cluster = "CLUSTER_FONDS_SCHANDAAL"
        topic_readable = "🚨 Dossier: Fondsschandaal & Manipulatie"
    elif "CONCEPT_KAYYUM_BESLAG" in matched_concepts:
        story_cluster = "CLUSTER_KAYYUM_TMSF"
        topic_readable = "🏛️ Dossier: Kayyum / TMSF Beslaglegging"
    elif "CONCEPT_SPK_MAATREGEL" in matched_concepts:
        stock_part = "_".join(sorted(matched_tickers)) if matched_tickers else "ALGEMEEN"
        story_cluster = f"CLUSTER_SPK_MAATREGEL_{stock_part}"
        topic_readable = f"⚠️ Dossier: SPK Handelsmaatregel ({stock_part})"
    elif "CONCEPT_ARRESTATIE_JUSTITIE" in matched_concepts and "CONCEPT_BURG_GEMEENTE" in matched_concepts:
        story_cluster = "CLUSTER_BURGEMEESTER_JUSTITIE"
        topic_readable = "🏛️ Dossier: Gemeente / Bestuurders Onderzoek"
    elif "CONCEPT_ARRESTATIE_JUSTITIE" in matched_concepts:
        story_cluster = "CLUSTER_ARRESTATIE_OPERATIE"
        topic_readable = "🚓 Dossier: Justitiële Operatie & Arrestaties"
    elif "CONCEPT_ONTSLAG_BENOEMING" in matched_concepts or "CONCEPT_RESMI_GAZETE_BELASTING" in matched_concepts:
        story_cluster = "CLUSTER_RESMI_GAZETE_BESLUIT"
        topic_readable = "📜 Dossier: Resmi Gazete / Overheidsbesluit"
    elif matched_persons and any(p in matched_persons for p in ["mahfi egilmez", "ozgur demirtas", "emre alkin", "hakan kara", "islam memis", "isik okte", "tunc satiroglu"]):
        econ_name = sorted(list(matched_persons))[0]
        story_cluster = f"CLUSTER_ECONOOM_{econ_name}"
        topic_readable = f"🧠 Analyse: {econ_name.title()}"
    elif matched_tickers:
        stock_part = "_".join(sorted(matched_tickers))
        concept_part = matched_concepts[0] if matched_concepts else "NIEUWS"
        story_cluster = f"CLUSTER_AANDEEL_{stock_part}_{concept_part}"
        topic_readable = f"🏢 Aandeel Dossier: {', '.join(sorted(matched_tickers))}"
    elif "CONCEPT_TCMB_RENTE" in matched_concepts:
        story_cluster = "CLUSTER_TCMB_RENTEBESLUIT"
        topic_readable = "🏦 Dossier: TCMB Rentebeleid"
    elif "CONCEPT_INFLATIE_TUIK" in matched_concepts:
        story_cluster = "CLUSTER_TUIK_INFLATIE"
        topic_readable = "📊 Dossier: Turkse Inflatiecijfers (TÜİK)"
    elif "CONCEPT_CDS_KREDIETNOOT" in matched_concepts:
        story_cluster = "CLUSTER_CDS_BUITENLANDS_KAPITAAL"
        topic_readable = "🌐 Dossier: CDS-Premie & Kredietbeoordelaars"
    elif "CONCEPT_GOUD_ZILVER" in matched_concepts:
        story_cluster = "CLUSTER_GOUD_ZILVER_MARKT"
        topic_readable = "🥇 Dossier: Goud- & Zilvermarkt"
    elif "CONCEPT_FED_VS_TRUMP" in matched_concepts:
        story_cluster = "CLUSTER_FED_TRUMP_VS"
        topic_readable = "🇺🇸 Dossier: VS / Fed / Trump Beleid"
    elif "CONCEPT_OORLOG_OLIE" in matched_concepts:
        story_cluster = "CLUSTER_GEOPOLITIEK_OLIE"
        topic_readable = "🌍 Dossier: Geopolitiek & Olieprijs"
    else:
        story_cluster = None
        topic_readable = "📰 Algemeen Economisch Bericht"

    item["_matched_tickers"] = matched_tickers
    item["_matched_persons"] = matched_persons
    item["_proper_entities"] = proper_entities
    item["_numbers"] = numbers
    item["_matched_concepts"] = set(matched_concepts)
    item["_core_stems"] = core_stems
    item["_story_cluster"] = story_cluster
    item["topic_readable"] = topic_readable
    return item

def deduplicate_by_semantic_content(enriched_list, max_mode=False):
    unique_items = []
    seen_links = set()

    sorted_candidates = sorted(
        enriched_list,
        key=lambda x: (x["priority_level"], -len(x.get("desc_orig", "")), -x["datetime"].timestamp())
    )

    for item in sorted_candidates:
        norm_link = item["link"].split("?")[0].strip()
        if norm_link in seen_links:
            continue

        c_cluster = item.get("_story_cluster")
        c_concepts = item.get("_matched_concepts", set())
        c_tickers = item.get("_matched_tickers", set())
        c_persons = item.get("_matched_persons", set())
        c_entities = item.get("_proper_entities", set())
        c_numbers = item.get("_numbers", set())
        c_stems = item.get("_core_stems", set())
        c_title_norm = normalize_tr(item.get("title_nl", ""))

        duplicate_of = None

        for existing in unique_items:
            ex_cluster = existing.get("_story_cluster")
            ex_concepts = existing.get("_matched_concepts", set())
            ex_tickers = existing.get("_matched_tickers", set())
            ex_persons = existing.get("_matched_persons", set())
            ex_entities = existing.get("_proper_entities", set())
            ex_numbers = existing.get("_numbers", set())
            ex_stems = existing.get("_core_stems", set())
            ex_title_norm = normalize_tr(existing.get("title_nl", ""))

            shared_stems = len(c_stems & ex_stems)
            overlap_ratio = shared_stems / max(1, min(len(c_stems), len(ex_stems))) if (c_stems and ex_stems) else 0.0
            shared_entities = bool(c_entities & ex_entities)
            shared_numbers = bool(c_numbers & ex_numbers)
            conflicting_tickers = bool(c_tickers and ex_tickers and not (c_tickers & ex_tickers))

            if c_cluster and ex_cluster and c_cluster == ex_cluster and not conflicting_tickers:
                if max_mode:
                    duplicate_of = existing
                    break
                if shared_entities or shared_numbers or shared_stems >= 1 or not c_entities or not ex_entities:
                    duplicate_of = existing
                    break

            if c_persons and ex_persons and (c_persons & ex_persons) and (c_concepts & ex_concepts):
                duplicate_of = existing
                break

            if c_tickers and ex_tickers and (c_tickers & ex_tickers) and ((c_concepts & ex_concepts) or overlap_ratio >= 0.25):
                duplicate_of = existing
                break

            if overlap_ratio >= 0.34 and not conflicting_tickers:
                duplicate_of = existing
                break

            if (c_concepts & ex_concepts) and (shared_entities or shared_numbers or shared_stems >= 2) and not conflicting_tickers:
                duplicate_of = existing
                break

            if difflib.SequenceMatcher(None, c_title_norm, ex_title_norm).ratio() >= 0.48:
                duplicate_of = existing
                break

        if duplicate_of is not None:
            existing_sources = [s["name"] for s in duplicate_of["extra_source_links"]]
            if item["source"] != duplicate_of["source"] and item["source"] not in existing_sources:
                duplicate_of["extra_source_links"].append({"name": item["source"], "link": item["link"]})
            duplicate_of["merged_count"] = duplicate_of.get("merged_count", 1) + 1
        else:
            seen_links.add(norm_link)
            item["extra_source_links"] = []
            item["merged_count"] = 1
            unique_items.append(item)

    return unique_items

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
        sectors.insert(0, f"🎯 Specifiek aandeel: {', '.join(sorted(mentioned_stocks))}")
    if not sectors:
        sectors.append("📈 Brede BIST 100 Markt & USD/TRY")

    sector_str = " · ".join(sectors[:3])

    if any(w in combined_text for w in ["tutuklama", "gözaltı", "soruşturma", "ceza", "işlem yasağı", "brüt takas", "kayyum", "skandal", "vurgun", "yaptırım", "zarar", "düşüş", "ev hapsi", "huisarrest", "konutu terk etmeme"]):
        badge_html = "🔴 HOOG RISICO / KOERSDRUK OP SPECULATIEVE FONDSEN"
        sentiment_type = "neg"
    elif any(w in combined_text for w in ["rekor kar", "temettü", "bedelsiz", "ihale", "anlaşma", "not artışı", "yabancı girişi", "büyüme", "yatırım"]):
        badge_html = "🟢 POSITIEVE KATALYSATOR VOOR KOERS"
        sentiment_type = "pos"
    elif any(w in combined_text for w in ["resmi gazete", "vergi", "ötv", "faiz kararı", "enflasyon", "trump", "fed"]):
        badge_html = "⚠️ BELEID & MACRO-IMPACT OP BIST 100"
        sentiment_type = "warn"
    else:
        badge_html = "⚖️ MARKT- & ANALISTEN DUIDING"
        sentiment_type = "info"

    return badge_html, sector_str, sentiment_type

def build_jip_en_janneke_analysis(title_orig, title_nl, desc_nl, category_tag, matched_tickers):
    combined = f"{title_orig} {title_nl} {desc_nl}".lower()
    badge_html, sector_str, sentiment_type = detect_sector_and_badge(combined, matched_tickers)

    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "spk bülteni", "bedelsiz", "bedelli", "sermaye artırımı"]):
        jip_summary = (
            f"Beurswaakhond SPK of Borsa İstanbul heeft een officieel besluit genomen: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Dit gaat over handelsrestricties of goedkeuring van een aandelensplitsing.'}"
        )
        econ_impact = (
            f"Bij een **handelsverbod of brüt takas** droogt de speculatieve handel op. "
            f"Een goedgekeurde **gratis aandelensplitsing (bedelsiz)** wekt daarentegen vaak enthousiasme bij particuliere beleggers."
        )
        card_type = "scandal" if ("yasağı" in combined or "brüt" in combined or "ceza" in combined) else "positive"

    elif any(w in combined for w in ["fon", "spk", "manipülasyon", "manipulatie", "tutuklama", "gözaltı", "aangehouden", "gearresteerd", "tasfiye", "tmsf", "mal varlığı", "soruşturma", "onderzoek", "ev hapsi", "huisarrest", "konutu terk etmeme", "elektronik kelepçe"]):
        jip_summary = (
            f"Justitie en beurswaakhond SPK grijpen in bij lopende onderzoeken en maatregelen zoals huisarrest, enkelband of arrestaties: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Er vinden juridische stappen, huisarresten of ondervragingen plaats rondom betrokken partijen.'}"
        )
        econ_impact = (
            f"Dit soort juridische maatregelen zorgt voor onrust bij speculatieve fondsen. "
            f"Voor de gevestigde **BIST 100-bedrijven** zuivert dit de markt en ondersteunt het op termijn het vertrouwen van grote instellingen."
        )
        card_type = "scandal"

    elif any(w in combined for w in ["resmi gazete", "cumhurbaşkanı kararı", "ötv", "vergi", "görevden alma", "atama kararları"]):
        jip_summary = (
            f"Nieuw officieel overheidsbesluit gepubliceerd in het Turkse Staatsblad (*Resmi Gazete*): *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuwe wetgeving, belastingmaatregelen of benoemingen zijn van kracht geworden.'}"
        )
        econ_impact = (
            f"Besluiten in de *Resmi Gazete* hebben direct effect bij beursopening. "
            f"Belastingverhogingen raken specifieke sectoren, terwijl nieuwe steunmaatregelen koerswinst stimuleren."
        )
        card_type = "news"

    elif any(w in combined for w in ["mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu"]):
        jip_summary = (
            f"Een vooraanstaande Turkse econoom of marktstrateeg deelt een scherpe analyse: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Onafhankelijke duiding over inflatie, rente of de goudmarkt.'}"
        )
        econ_impact = (
            f"Deze economen worden op de voet gevolgd door beleggers. "
            f"Hun waarschuwingen sturen direct het dagelijkse sentiment op de **BIST 100**."
        )
        card_type = "news"

    elif any(w in combined for w in ["cds", "yabancı yatırımcı", "yabancı takas", "fitch", "moody", "s&p", "kredi notu"]):
        jip_summary = (
            f"Belangrijk signaal over het vertrouwen van internationale beleggers in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuws over de Turkse CDS-risicopremie of buitenlandse kapitaalstromen.'}"
        )
        econ_impact = (
            f"Grote buitenlandse fondsen kopen de zwaargewichten in de **BIST 100**. "
            f"Een dalende CDS-premie of buitenlandse instroom is de sterkste brandstof voor een brede beursrally."
        )
        card_type = "positive" if any(w in combined for w in ["giriş", "artış", "düşüş", "olumlu", "not artışı"]) else "news"

    elif any(w in combined for w in ["belediye", "burgemeester", "kayyum", "görevden alındı", "ontslagen", "erdoğan", "chp", "ak parti", "siyaset", "meclis"]):
        jip_summary = (
            f"Politieke of bestuurlijke ontwikkeling in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Politieke spanningen of juridische stappen tegen bestuurders.'}"
        )
        econ_impact = (
            f"Politieke onrust zorgt ervoor dat beleggers tijdelijk op de rem trappen. "
            f"Banken en holdings reageren hier gevoelig op, terwijl men vaker schuilt in **Gram Goud** en **USD/TRY**."
        )
        card_type = "scandal"

    elif any(w in combined for w in ["trump", "abd", "vs", "amerika", "yaptırım", "sanctie", "israil", "iran", "rusya", "oorlog", "midden-oosten", "navo", "nato"]):
        jip_summary = (
            f"Geopolitiek en diplomatiek nieuws met marktimpact: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Ontwikkelingen rond de VS/Trump, sancties of regionale spanningen.'}"
        )
        econ_impact = (
            f"Spanningen met de VS of onrust in het Midden-Oosten drijven de prijs van **Goud en Zilver** op. "
            f"Op de BIST 100 profiteert defensie (**ASELS**), terwijl luchtvaart last kan krijgen van duurdere kerosine."
        )
        card_type = "news"

    else:
        jip_summary = (
            f"Economisch en financieel nieuws: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Actuele berichtgeving over beleid, kwartaalcijfers (KAP) of de handel op Borsa İstanbul.'}"
        )
        econ_impact = (
            f"Geeft directe richting aan de waardering van **BIST 100-aandelen**. "
            f"Dalende inflatie en sterke cijfers ondersteunen de koersen."
        )
        card_type = "news"

    return jip_summary, econ_impact, card_type, badge_html, sector_str, sentiment_type

def calculate_article_priority_and_sort_key(item):
    cat = item.get("category", "")
    text = f"{item.get('title_orig', '')} {item.get('title_nl', '')} {item.get('desc_orig', '')}".lower()

    if "🔎 Vrije Zoekopdracht" in cat:
        priority_level = 1
        priority_label = "🔎 Prio 1: Eigen Zoekopdracht"
    elif any(k in cat for k in ["Fondsschandaal", "SPK Bulletin", "Politiek", "Resmi Gazete"]) or \
         any(w in text for w in ["fon", "spk", "manipülasyon", "tutuklama", "gözaltı", "kayyum", "resmi gazete", "ev hapsi", "huisarrest", "konutu terk etmeme", "işlem yasağı", "brüt takas"]):
        priority_level = 1
        priority_label = "🔥 Prio 1: Schandaal & Marktschokken"
    elif any(k in cat for k in ["BIST 100", "Top-Economen", "CDS-Premie", "Direct"]) or \
         any(w in text for w in ["tcmb", "merkez bankası", "faiz", "enflasyon", "mehmet şimşek", "bist 100", "cds"]):
        priority_level = 2
        priority_label = "📈 Prio 2: Macro & BIST 100"
    elif "Aandelennieuws" in cat or item.get("_matched_tickers"):
        priority_level = 3
        priority_label = "🏢 Prio 3: Bedrijfsnieuws (KAP)"
    else:
        priority_level = 4
        priority_label = "🌍 Prio 4: Globaal & Edelmetalen"

    item["priority_level"] = priority_level
    item["priority_label"] = priority_label
    return priority_level

# ==============================================================================
# RSS HARVESTING FUNCTIES
# ==============================================================================
def fetch_google_rss_feed(args):
    category_label, query, lang, max_items, max_days, extra_tickers, custom_kw = args
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

            if not is_economically_relevant(clean_title, clean_desc, extra_tickers, custom_kw):
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

def fetch_direct_newspaper_rss(args):
    source_label, url, max_days, extra_tickers, custom_kw = args
    items = []
    now_utc = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw_bytes = resp.read()
        root = ET.fromstring(raw_bytes)

        for item in root.findall(".//item")[:18]:
            raw_title = clean_html_text(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            pub_str = item.findtext("pubDate") or ""
            raw_desc = clean_html_text(item.findtext("description") or "")

            if not raw_title or not link:
                continue

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

            if not is_economically_relevant(raw_title, raw_desc, extra_tickers, custom_kw):
                continue

            items.append({
                "category": source_label,
                "title_orig": raw_title,
                "desc_orig": raw_desc[:350],
                "source": source_label.replace("📰 ", "").replace(" (Direct)", ""),
                "link": link,
                "datetime": dt,
                "date_str": dt.strftime("%d-%m-%Y %H:%M"),
                "lang": "tr"
            })
            if len(items) >= 8:
                break
    except Exception:
        pass
    return items

def enrich_articles_with_dutch_summaries(items, all_bist_codes):
    def process_one(item):
        if item["lang"] == "tr":
            title_nl = translate_to_nl(item["title_orig"])
            desc_nl = translate_to_nl(item["desc_orig"]) if item["desc_orig"] and len(item["desc_orig"]) > 15 else ""
        else:
            title_nl = item["title_orig"]
            desc_nl = item["desc_orig"]

        item["title_nl"] = title_nl
        item["desc_nl"] = desc_nl

        analyze_article_semantics(item, all_bist_codes)

        jip_sum, econ_imp, card_cls, badge_html, sector_str, sent_type = build_jip_en_janneke_analysis(
            item["title_orig"], title_nl, desc_nl, item["category"], item.get("_matched_tickers", set())
        )
        item["jip_summary"] = jip_sum
        item["econ_impact"] = econ_imp
        item["card_type"] = card_cls
        item["badge_html"] = badge_html
        item["sector_str"] = sector_str
        item["sentiment_type"] = sent_type

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
                "De Amerikaanse centrale bank (Fed) maakt haar nieuwe rentebesluit bekend, "
                "gevolgd door de toelichting van voorzitter Jerome Powell."
            ),
            "econ_impact": (
                "Dit is het belangrijkste wereldwijde moment van de week. "
                "Een hint op lagere rentes is direct positief voor **Goud, Zilver** en opkomende markten zoals **Borsa İstanbul (BIST 100)**."
            ),
            "link": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        },
        {
            "date": datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc).date(),
            "time_str": "29-10-2026 (Hele dag)",
            "title": "🇹🇷 Cumhuriyet Bayramı (Dag van de Republiek) — Borsa İstanbul Gesloten",
            "jip_summary": (
                "Vanwege de nationale feestdag in Turkije is **Borsa İstanbul (BIST)** op 29 oktober gesloten."
            ),
            "econ_impact": (
                "Handelaren verkopen voor de feestdag vaak een deel van hun aandelen om geen kredietrente over de vrije dagen te betalen."
            ),
            "link": "https://www.borsaistanbul.com/tr/sayfa/143/resmi-tatil-gunleri"
        },
        {
            "date": datetime(2026, 11, 3, 7, 0, tzinfo=timezone.utc).date(),
            "time_str": "03-11-2026 (10:00 TR)",
            "title": "🇹🇷 TÜİK Turkse Inflatiecijfers (CPI / TÜFE Oktober)",
            "jip_summary": (
                "Het Turkse statistiekbureau (TÜİK) publiceert de officiële maandelijkse en jaarlijkse inflatiecijfers over oktober."
            ),
            "econ_impact": (
                "Bepaalt of de Turkse Centrale Bank (TCMB) de rente kan verlagen. "
                "Valt de inflatie lager uit, dan schieten **BIST 100 bankaandelen** omhoog."
            ),
            "link": "https://www.tuik.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 6, 7, 30, tzinfo=timezone.utc).date(),
            "time_str": "06-11-2026 (10:30 TR)",
            "title": "🇹🇷 TCMB 4e Inflatieverslag (Enflasyon Raporu) — Toespraak Fatih Karahan",
            "jip_summary": (
                "De gouverneur van de Turkse Centrale Bank presenteert de nieuwe inflatievoorspellingen."
            ),
            "econ_impact": (
                "Beleggers letten op signalen over het rentepad en de Lira."
            ),
            "link": "https://www.tcmb.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "09-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Kwartaalcijfers (Niet-Geconsolideerde BIST Bedrijven)",
            "jip_summary": (
                "Laatste dag waarop niet-geconsolideerde beursbedrijven hun derdekwartaalcijfers publiceren op KAP."
            ),
            "econ_impact": (
                "Zorgt voor koersbewegingen per individueel aandeel op basis van winstmarges."
            ),
            "link": "https://www.kap.org.tr/"
        },
        {
            "date": datetime(2026, 11, 11, 13, 30, tzinfo=timezone.utc).date(),
            "time_str": "11-11-2026 (16:30 TR)",
            "title": "🇺🇸 Amerikaanse Inflatiecijfers (US CPI Oktober)",
            "jip_summary": (
                "Publicatie van de Amerikaanse consumentenprijzen."
            ),
            "econ_impact": (
                "Directe koersbepaler voor **Goud en Zilver**. Lagere Amerikaanse inflatie stuwt edelmetalen."
            ),
            "link": "https://www.bls.gov/cpi/"
        },
        {
            "date": datetime(2026, 11, 19, 11, 0, tzinfo=timezone.utc).date(),
            "time_str": "19-11-2026 (14:00 TR)",
            "title": "🇹🇷 TCMB Rentebesluit (PPK Toplantısı & Faiz Kararı)",
            "jip_summary": (
                "Het Monetair Beleidscomité van de Turkse Centrale Bank maakt het rentebesluit bekend."
            ),
            "econ_impact": (
                "Hét belangrijkste binnenlandse macro-moment voor de **USD/TRY wisselkoers**, **Gram Goud** en de **BIST 100 Index**."
            ),
            "link": "https://www.tcmb.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "20-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Geconsolideerde Kwartaalcijfers (Holdings & Banken)",
            "jip_summary": (
                "Uiterste datum waarop grote holdings (KCHOL, SAHOL) hun volledige kwartaalcijfers bekendmaken."
            ),
            "econ_impact": (
                "Sluit het cijferseizoen af en bepaalt de leiders in de **BIST 100** richting het jaareinde."
            ),
            "link": "https://www.kap.org.tr/"
        }
    ]

    future_events = [ev for ev in scheduled_events if today <= ev["date"] <= end_date]
    future_events.sort(key=lambda x: x["date"])
    return future_events

# ==============================================================================
# HOOFDPROGRAMMA
# ==============================================================================
st.markdown("### 📊 Live Marktoverzicht (BIST 100, Valuta & Edelmetalen in $ en ₺)")
market_data = get_live_market_snapshot()
market_items = list(market_data.items())

for row_slice in [market_items[:5], market_items[5:10]]:
    cols = st.columns(len(row_slice))
    for i, (name, info) in enumerate(row_slice):
        with cols[i]:
            if info["price"] is not None:
                st.metric(label=name, value=f"{info['price']:,.2f}", delta=f"{info['change']:+.2f}%")
            else:
                st.metric(label=name, value="N/B")

st.markdown("---")

st.markdown("### 🤖 Start de Ultimate Master Scanner")
st.markdown(
    "Scant en sorteert al het **Turkse en internationale beursnieuws** op **prioriteit** "
    "met **inhoudelijke ontdubbeling** (geen dubbele artikelen)."
)

# Initialiseer session state
if "master_enriched" not in st.session_state:
    st.session_state.master_enriched = None
if "total_raw_count" not in st.session_state:
    st.session_state.total_raw_count = 0
if "removed_dups_count" not in st.session_state:
    st.session_state.removed_dups_count = 0
if "stock_tech_map" not in st.session_state:
    st.session_state.stock_tech_map = {}
if "upcoming_agenda" not in st.session_state:
    st.session_state.upcoming_agenda = []

if st.button("🚀 Start Volledige Master Analyse", type="primary"):
    is_bist100_general = BIST_INDEX_OPTION in selected_tickers
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    all_bist_codes = [t.split(" ")[0] for t in BIST_100_STOCKS]
    tickers_str = ", ".join(tickers_clean) if tickers_clean else "Alle BIST 100 Hoofdfondsen"

    with st.spinner("📡 Ophalen van Google News + rechtstreekse Turkse kranten-feeds, inhoudelijk ontdubbelen en live aandelendata koppelen..."):
        rss_tasks = [
            (
                "🚨 Fondsschandaal, SPK & Beurs-Operaties",
                '("fon soruşturması" OR "SPK" OR "manipülasyon" OR "borsa operasyon" OR "fon tasfiye" OR "TMSF" OR "ev hapsi")',
                "tr", 12, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "⚠️ SPK Bulletin, Brüt Takas, Handelsverboden & Bedelsiz",
                '("SPK bülteni" OR "işlem yasağı" OR "brüt takas" OR "tedbir kararı" OR "bedelsiz sermaye artırımı")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "📜 Resmi Gazete (Staatsblad), Belastingen (ÖTV) & Besluiten",
                '("Resmi Gazete" OR "Cumhurbaşkanı Kararı" OR "ÖTV" OR "vergi düzenlemesi") AND ("ekonomi" OR "atama" OR "görevden" OR "vergi" OR "borsa")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "🏛️ Politiek, Justitie, Burgemeesters & Ontslagen",
                '("görevden alındı" OR "kayyum" OR "gözaltı" OR "tutuklama" OR "belediye başkanı" OR "ev hapsi" OR "konutu terk etmeme") AND ("ekonomi" OR "borsa" OR "SPK" OR "fon" OR "holding" OR "başkan")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "🧠 Turkse Top-Economen & Marktstrategen",
                '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Emre Alkin" OR "Hakan Kara" OR "İslam Memiş" OR "Işık Ökte" OR "Tunç Şatıroğlu")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "🌐 CDS-Premie, Kredietwaardigheid & Buitenlands Kapitaal",
                '("CDS primi" OR "yabancı yatırımcı" OR "yabancı takas" OR "Fitch" OR "Moody\'s" OR "kredi notu") AND ("Türkiye" OR "borsa" OR "BIST")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "🌍 Geopolitiek, Trump/VS, Sancties & Diplomatie",
                '("Trump" OR "ABD" OR "yaptırım" OR "BRICS" OR "İsrail" OR "İran") AND ("Türkiye" OR "ekonomi" OR "piyasa" OR "dolar" OR "ticaret")',
                "tr", 10, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "📈 BIST 100, TCMB, Rente & Top-Media",
                '("Borsa İstanbul" OR "BIST 100" OR "TCMB" OR "Mehmet Şimşek" OR "enflasyon" OR "faiz kararı")',
                "tr", 12, max_days_slider, tickers_clean, custom_search_query
            ),
            (
                "🌍 Wereldnieuws, Oorlog & Energie (NL)",
                '(oorlog OR Midden-Oosten OR Oekraïne OR geopolitiek OR olieprijs OR sancties)',
                "nl", 10, max_days_slider, [], custom_search_query
            ),
            (
                "🥇 Goud, Zilver & Centrale Banken (NL)",
                '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen OR inflatie)',
                "nl", 10, max_days_slider, [], custom_search_query
            )
        ]

        if custom_search_query and custom_search_query.strip():
            q_clean = custom_search_query.strip()
            rss_tasks.insert(0, (
                f"🔎 Vrije Zoekopdracht: '{q_clean}'",
                f'"{q_clean}"',
                "tr", 12, max_days_slider, tickers_clean, q_clean
            ))

        if tickers_clean:
            batch_size = 5
            for i in range(0, min(len(tickers_clean), 35), batch_size):
                batch = tickers_clean[i:i + batch_size]
                or_stocks = " OR ".join(batch)
                rss_tasks.append((
                    f"🏢 Aandelennieuws & KAP ({', '.join(batch)})",
                    f"({or_stocks}) AND (hisse OR KAP OR bilanço OR temettü OR yatırım)",
                    "tr", 6, max_days_slider, batch, custom_search_query
                ))

        with ThreadPoolExecutor(max_workers=12) as executor:
            google_results = list(executor.map(fetch_google_rss_feed, rss_tasks))
            direct_results = []
            if include_direct_newspaper_rss:
                direct_tasks = [
                    (label, url, max_days_slider, tickers_clean, custom_search_query)
                    for label, url in DIRECT_TURKISH_RSS_FEEDS
                ]
                direct_results = list(executor.map(fetch_direct_newspaper_rss, direct_tasks))

        raw_all_items = []
        for res_list in google_results + direct_results:
            raw_all_items.extend(res_list)

        total_raw_count = len(raw_all_items)
        master_enriched = enrich_articles_with_dutch_summaries(raw_all_items, all_bist_codes)

        is_max_mode = dedup_strictness.startswith("Maximaal")
        master_enriched = deduplicate_by_semantic_content(master_enriched, max_mode=is_max_mode)
        removed_dups_count = total_raw_count - len(master_enriched)

        all_mentioned_tickers = set(tickers_clean[:12])
        for it in master_enriched:
            for tk in it.get("_matched_tickers", set()):
                all_mentioned_tickers.add(tk)
        stock_tech_map = get_bist_technical_snapshots(tuple(sorted(all_mentioned_tickers)[:25]))

        if sort_mode == "Puur op Datum (Allernieuwste bovenaan)":
            master_enriched.sort(key=lambda x: -x["datetime"].timestamp())
        else:
            master_enriched.sort(key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))

        upcoming_agenda = get_upcoming_30_day_agenda()

        st.session_state.master_enriched = master_enriched
        st.session_state.total_raw_count = total_raw_count
        st.session_state.removed_dups_count = removed_dups_count
        st.session_state.stock_tech_map = stock_tech_map
        st.session_state.upcoming_agenda = upcoming_agenda

# Render resultaten vanuit session_state
if st.session_state.master_enriched is not None:
    master_enriched = st.session_state.master_enriched
    total_raw_count = st.session_state.total_raw_count
    removed_dups_count = st.session_state.removed_dups_count
    stock_tech_map = st.session_state.stock_tech_map
    upcoming_agenda = st.session_state.upcoming_agenda

    pos_count = sum(1 for x in master_enriched if x.get("sentiment_type") == "pos")
    neg_count = sum(1 for x in master_enriched if x.get("sentiment_type") == "neg")
    warn_count = sum(1 for x in master_enriched if x.get("sentiment_type") == "warn")
    scandal_count = sum(1 for x in master_enriched if x["priority_level"] == 1)

    st.success(
        f"✅ Ultimate Master Analyse voltooid! Van de **{total_raw_count}** opgehaalde berichten "
        f"zijn **{removed_dups_count} dubbele berichten samengevoegd**. Er staan nu **{len(master_enriched)} unieke dossiers** klaar."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"🌐 Agent 1: Master News Hub ({len(master_enriched)} Unieke Dossiers)",
        "🕵️‍♂️ Agent 2: Fact-Check & Koers-Matrix",
        "💡 Agent 3: Beleggingsadvies",
        "⚖️ Agent 4: Risico-Audit",
        f"📅 Agent 5: Komende 30-Dagen Agenda ({len(upcoming_agenda)})"
    ])

    with tab1:
        st.markdown("### 🌐 Agent 1: Master News Hub (Met Live Aandelen-Chips & Inhoudelijke Ontdubbeling)")

        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("🟢 Positieve Katalysatoren", f"{pos_count} dossiers")
        s_col2.metric("🔴 Hoog Risico / Schandaal / Druk", f"{neg_count} dossiers")
        s_col3.metric("⚠️ Beleid & Macro-Impact", f"{warn_count} dossiers")
        s_col4.metric("🧹 Samengevoegde Duplicaten", f"{removed_dups_count} artikelen")

        f_col1, f_col2 = st.columns([2, 2])
        with f_col1:
            prio_filter = st.selectbox(
                "🔍 Filter op prioriteit / categorie:",
                [
                    "Alle Unieke Dossiers",
                    "🔥 Prio 1: Schandalen, Justitie & Eigen Zoekopdracht",
                    "📈 Prio 2: Macro, Resmi Gazete & BIST 100",
                    "🏢 Prio 3: Bedrijfsnieuws (KAP)",
                    "🌍 Prio 4: Globaal & Edelmetalen"
                ],
                index=0
            )
        with f_col2:
            inline_filter = st.text_input("⚡ Snel filteren binnen de geladen resultaten:", value="", placeholder="Typ een woord om direct te filteren...")

        if prio_filter == "🔥 Prio 1: Schandalen, Justitie & Eigen Zoekopdracht":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 1]
        elif prio_filter == "📈 Prio 2: Macro, Resmi Gazete & BIST 100":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 2]
        elif prio_filter == "🏢 Prio 3: Bedrijfsnieuws (KAP)":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 3]
        elif prio_filter == "🌍 Prio 4: Globaal & Edelmetalen":
            filtered_master = [x for x in master_enriched if x["priority_level"] == 4]
        else:
            filtered_master = master_enriched

        if inline_filter.strip():
            q_in = inline_filter.strip().lower()
            filtered_master = [
                x for x in filtered_master
                if q_in in x["title_nl"].lower() or q_in in x["title_orig"].lower() or q_in in x["jip_summary"].lower()
            ]

        if filtered_master:
            export_lines = [f"# BIST 100 & Turkse Economie Master Rapport ({datetime.now().strftime('%d-%m-%Y %H:%M')})\n"]
            for idx, item in enumerate(filtered_master, 1):
                # Gebruik schone Streamlit containers voor elke nieuwskaart (geen breekbare HTML meer!)
                with st.container(border=True):
                    # Top-balk met meta-info
                    st.caption(f"**{item['priority_label']}** &nbsp;|&nbsp; **{item['topic_readable']}** &nbsp;|&nbsp; {item['badge_html']} &nbsp;|&nbsp; #{idx} | 🕒 {item['date_str']} | Bron: {item['source']}")
                    
                    # Titel & Originele kop
                    st.markdown(f"### {item['title_nl']}")
                    st.markdown(f"<span style='font-size: 12px; color: #64748b;'>Originele kop: {item['title_orig']}</span>", unsafe_allow_html=True)

                    # Extra bronnen indien samengevoegd
                    extra_links = item.get("extra_source_links", [])
                    if extra_links:
                        links_anchors = " · ".join([
                            f'<a href="{es["link"]}" target="_blank" style="color: #334155; text-decoration: underline;">{es["name"]}</a>'
                            for es in extra_links[:5]
                        ])
                        st.markdown(f"<span style='font-size: 12px; color: #475569;'>🧠 <em>Zelfde inhoud ook gemeld door: {links_anchors} — automatisch samengevoegd tot 1 dossier.</em></span>", unsafe_allow_html=True)

                    # Geraakte sectoren
                    st.markdown(f"**🎯 Geraakte Sectoren / Markten:** {item['sector_str']}")

                    # Technische aandelen-chips (indien van toepassing)
                    chips_html_list = []
                    for tk in sorted(item.get("_matched_tickers", set())):
                        snap = stock_tech_map.get(tk)
                        if snap and snap.get("price") is not None:
                            chg_color = "#166534" if snap["change"] >= 0 else "#991b1b"
                            chips_html_list.append(
                                f'<span class="stock-chip" style="background:#f1f5f9; padding:4px 8px; border-radius:6px; font-size:12px; margin-right:6px; display:inline-block; border:1px solid #cbd5e1;">'
                                f'📊 <strong>{tk}</strong>: ₺{snap["price"]:,.2f} '
                                f'(<span style="color:{chg_color};font-weight:bold;">{snap["change"]:+.2f}%</span>) '
                                f'| RSI: <strong>{snap["rsi"]}</strong> | S1: ₺{snap["s1"]} / R1: ₺{snap["r1"]} | {snap["trend"]}'
                                f'</span>'
                            )
                    if chips_html_list:
                        st.markdown(f"<div style='margin: 6px 0;'>{''.join(chips_html_list)}</div>", unsafe_allow_html=True)

                    st.divider()

                    # Compacte uitschuifbare Jip-en-Janneke analyse (neemt geen onnodige ruimte in beslag)
                    with st.expander("🗣️ Bekijk Jip-en-Janneketaal Analyse & Beursimpact"):
                        st.markdown(f"**Wat is er aan de hand:**\n{item['jip_summary']}")
                        st.markdown(f"**Economisch vooruitzicht & Beursimpact:**\n{item['econ_impact']}")

                    # Link naar originele bron
                    st.markdown(f"🔗 [Klik hier om het originele hoofd-artikel te openen ({item['source']})]({item['link']})")

                export_lines.append(
                    f"## #{idx} [{item['priority_label']}] {item['title_nl']} ({item['date_str']} - {item['source']})\n"
                    f"- Originele kop: {item['title_orig']}\n"
                    f"- Geraakte Sectoren: {item['sector_str']}\n"
                    f"- Jip-en-Janneketaal: {item['jip_summary']}\n"
                    f"- Economische impact: {item['econ_impact']}\n"
                    f"- Bronlink: {item['link']}\n\n"
                )

            st.download_button(
                label="📥 Download Volledig Nieuws- & Analyse Dossier (.md / Tekst)",
                data="\n".join(export_lines),
                file_name=f"BIST100_Master_Dossier_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )
        else:
            st.warning("Geen artikelen gevonden voor dit filter.")

    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: De Waarheids-Filter & Live Technische Aandelen-Matrix")
        st.markdown(
            f"- ✅ **Dubbele Bron-laag Actief:** Google News RSS + rechtstreekse Turkse kranten-feeds.\n"
            f"- ✅ **Slimme Persoons- & Dossier-Ontdubbeling:** Van de `{total_raw_count}` artikelen zijn `{removed_dups_count}` berichten met dezelfde strekking samengevoegd.\n"
            f"- ✅ **Koersdata Verificatie:** BIST 100 (`{market_data.get('BIST 100', {}).get('price', 0):,.0f}`), USD/TRY (`₺{market_data.get('USD/TRY', {}).get('price', 0):,.2f}`)."
        )

        if stock_tech_map:
            st.markdown("#### 📊 Live Technische Matrix (Koers, RSI & Steun/Weerstand van Geselecteerde / Genoemde BIST-Aandelen)")
            tech_rows = []
            for tk, sn in stock_tech_map.items():
                tech_rows.append({
                    "Ticker": tk,
                    "Koers (₺)": sn["price"],
                    "Dagmutatie (%)": sn["change"],
                    "RSI (14)": sn["rsi"],
                    "Steun S1 (₺)": sn["s1"],
                    "Weerstand R1 (₺)": sn["r1"],
                    "Trend (vs SMA20)": sn["trend"]
                })
            st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### 💡 Agent 3: Concreet Beleggingsadvies in Jip-en-Janneketaal")
        st.markdown(
            "- **Gebruik de nieuwe Koers/RSI-chips in Agent 1:** Zie je positief KAP-nieuws bij een BIST 100-aandeel waarvan de **RSI tussen 35 en 60** ligt en de koers boven Steun **S1** noteert? Dat biedt technisch de veiligste instap.\n"
            "- **Vermijd Prio-1 Schandaalfondsen:** Blijf weg bij kleine fondsen die in een SPK-handelsverbod zitten."
        )

    with tab4:
        st.markdown("### ⚖️ Agent 4: Eindcontrole & Risico-Audit")
        st.warning(
            f"**Belangrijkste Risico's:**\n"
            f"1. **Toezicht- en Schandaalrisico ({scandal_count} unieke Prio-1 dossiers).**\n"
            f"2. **Valutarisico en volatiliteit.**"
        )

    with tab5:
        st.markdown("### 📅 Agent 5: Toekomstige 30-Dagen Macro-Agenda (Oplopend)")
        if upcoming_agenda:
            for idx, ev in enumerate(upcoming_agenda, 1):
                days_left = (ev["date"] - datetime.now(timezone.utc).date()).days
                days_label = "Vandaag!" if days_left == 0 else f"Over {days_left} dagen"
                with st.container(border=True):
                    st.markdown(f"**#{idx} | 📅 Datum: {ev['time_str']} ({days_label})**")
                    st.markdown(f"### {ev['title']}")
                    st.divider()
                    st.markdown(f"**Wat gaat er gebeuren:**\n{ev['jip_summary']}")
                    st.markdown(f"**Economisch vooruitzicht & Beursimpact:**\n{ev['econ_impact']}")
                    st.markdown(f"🔗 [Klik hier voor de officiële bron & kalenderpagina]({ev['link']})")
        else:
            st.info("Geen geplande macro-evenementen gevonden binnen de komende 30 dagen.")

else:
    st.info("👈 Kies in de zijbalk je instellingen (of typ een vrije zoekopdracht) en klik op **Start Volledige Master Analyse**.")
