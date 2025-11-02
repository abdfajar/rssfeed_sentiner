import streamlit as st
import feedparser
import ssl
from datetime import datetime, date, timedelta
import re
import pandas as pd

# Handle SSL certificate verification issues
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# Daftar RSS feed portal berita Indonesia
RSS_FEEDS = {
    "ANTARA - Top News": "https://www.antaranews.com/rss/top-news",
    "ANTARA - Ekonomi": "https://www.antaranews.com/rss/ekonomi",
    "Detik - Berita": "https://news.detik.com/berita/rss",
    "Detik - Finance": "https://finance.detik.com/rss",
    "Kompas": "https://rss.kompas.com/api/feed/social?apikey=bc58c81819dff4b8d5c53540a2fc7ffd83e6314a",
    "Kontan - Keuangan": "https://rss.kontan.co.id/news/keuangan",
    "Kontan - Nasional": "https://rss.kontan.co.id/news/nasional",
    "Suara - Bisnis": "https://www.suara.com/rss/bisnis",
    "Suara - News": "https://www.suara.com/rss/news",
    "Liputan 6": "https://feed.liputan6.com/rss/news",
    "Tempo - Nasional": "http://rss.tempo.co/nasional",
    "Tempo - Bisnis": "http://rss.tempo.co/bisnis",
    "CNN Indonesia - Ekonomi": "https://www.cnnindonesia.com/ekonomi/rss",
    "CNN Indonesia - Nasional": "https://www.cnnindonesia.com/nasional/rss",
    "CNBC Indonesia - News": "https://www.cnbcindonesia.com/news/rss",
    "CNBC Indonesia - Market": "https://www.cnbcindonesia.com/market/rss/",
    "Republika Online": "https://www.republika.co.id/rss",
    "Media Indonesia": "https://mediaindonesia.com/feed",
    "JawaPos - Nasional": "https://www.jawapos.com/nasional/rss",
    "JawaPos - Ekonomi": "https://www.jawapos.com/ekonomi/rss",
    "Kumparan": "https://lapi.kumparan.com/v2.0/rss/",
    "Tirto": "https://tirto.id/sitemap/r/google-discover",
    "VICE Indonesia": "https://www.vice.com/id_id/rss",
    "Coconuts Jakarta": "http://coconuts.co/jakarta/feed/"
}

def parse_feed(feed_url):
    """Mengambil dan parsing RSS feed"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        
        for entry in feed.entries:
            # Handle kemungkinan field yang missing
            title = entry.get('title', 'No Title')
            link = entry.get('link', '')
            published = entry.get('published', '')
            summary = entry.get('summary', '')
            
            # Jika tidak ada summary, gunakan description
            if not summary:
                summary = entry.get('description', 'No summary available')
            
            # Clean summary dari tag HTML
            summary = re.sub('<[^<]+?>', '', summary)
            
            # Konversi tanggal ke datetime object untuk filtering
            published_date = None
            published_dt = None
            if published:
                try:
                    # Coba parsing dari format RSS standar
                    published_dt = datetime(*entry.published_parsed[:6])
                    published_date = published_dt.date()
                except:
                    try:
                        # Coba parsing dari format string
                        published_dt = datetime.strptime(published, '%a, %d %b %Y %H:%M:%S %Z')
                        published_date = published_dt.date()
                    except:
                        published_date = None
                        published_dt = None
            
            articles.append({
                'title': title,
                'link': link,
                'published': published,
                'published_date': published_date,
                'published_dt': published_dt,
                'summary': summary
            })
        
        return articles
    except Exception as e:
        st.error(f"Error parsing feed {feed_url}: {e}")
        return []

def get_all_news_dataframe(selected_feeds):
    """Mengambil semua berita dan menyimpan dalam dataframe"""
    if not selected_feeds:
        return pd.DataFrame(), "⚠️ Pilih setidaknya satu portal berita"
    
    all_articles_data = []
    
    for feed_name in selected_feeds:
        if feed_name in RSS_FEEDS:
            with st.spinner(f"Mengambil data dari {feed_name}..."):
                articles = parse_feed(RSS_FEEDS[feed_name])
                for article in articles:
                    # Simpan data dengan metadata yang diminta
                    article_data = {
                        'sumber_artikel': feed_name,
                        'judul_artikel': article['title'],
                        'url_artikel': article['link'],
                        'date_stamp': article['published_dt'] if article['published_dt'] else None,
                        'published_date': article['published_date'],
                        'published_string': article['published'],
                        'summary': article['summary']
                    }
                    all_articles_data.append(article_data)
    
    # Buat dataframe dari semua artikel
    if all_articles_data:
        df = pd.DataFrame(all_articles_data)
        
        # Urutkan berdasarkan tanggal
        df = df.sort_values('date_stamp', ascending=False)
        
        info_message = f"✅ **Data berhasil diambil!**  \n📊 **Total artikel:** {len(df)} dari {len(selected_feeds)} portal berita"
        return df, info_message
    else:
        return pd.DataFrame(), "❌ Tidak ada artikel yang ditemukan"

def filter_dataframe(df, query, filter_type, custom_days):
    """Filter dataframe berdasarkan pencarian dan tanggal"""
    if df.empty:
        return pd.DataFrame(), "⚠️ Tidak ada data yang tersedia"
    
    # Buat copy dataframe untuk filtering
    filtered_df = df.copy()
    
    # Filter berdasarkan kata kunci
    if query:
        query_lower = query.lower()
        keyword_mask = (
            filtered_df['judul_artikel'].str.lower().str.contains(query_lower, na=False) |
            filtered_df['summary'].str.lower().str.contains(query_lower, na=False)
        )
        filtered_df = filtered_df[keyword_mask]
    
    # Filter berdasarkan tanggal
    if filter_type != "Semua Artikel":
        today = date.today()
        
        if filter_type == "Hari Ini":
            start_date = today
            end_date = today
        elif filter_type == "Kemarin":
            start_date = today - timedelta(days=1)
            end_date = today
        elif filter_type == "Satu minggu terakhir":
            start_date = today - timedelta(days=7)
            end_date = today
        elif filter_type == "Satu bulan terakhir":
            start_date = today - timedelta(days=30)
            end_date = today
        elif filter_type == "custom" and custom_days and custom_days > 0:
            start_date = today - timedelta(days=custom_days)
            end_date = today
        else:
            start_date = None
            end_date = None
        
        if start_date and end_date:
            # Konversi start_date dan end_date ke datetime untuk perbandingan
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            date_mask = (
                (filtered_df['date_stamp'] >= start_dt) & 
                (filtered_df['date_stamp'] <= end_dt)
            )
            filtered_df = filtered_df[date_mask]
    
    # Format output
    if filtered_df.empty:
        info_message = f"❌ **Tidak ada artikel yang sesuai dengan filter**  \n"
        if query:
            info_message += f"🔎 **Kata kunci:** '{query}'  \n"
        if filter_type != "Semua Artikel":
            info_message += f"📅 **Filter waktu:** {filter_type}"
            if filter_type == "custom" and custom_days:
                info_message += f" ({custom_days} hari)"
        return pd.DataFrame(), info_message
    
    # Urutkan berdasarkan tanggal
    filtered_df = filtered_df.sort_values('date_stamp', ascending=False)
    
    # Info summary
    info_message = f"🔍 **Hasil Pencarian**  \n"
    info_message += f"📊 **Ditemukan {len(filtered_df)} artikel**  \n"
    
    if query:
        info_message += f"🔎 **Kata kunci:** '{query}'  \n"
    
    if filter_type != "Semua Artikel":
        info_message += f"📅 **Filter waktu:** {filter_type}"
        if filter_type == "custom" and custom_days:
            info_message += f" ({custom_days} hari)"
    else:
        info_message += f"📅 **Filter waktu:** Semua artikel"
    
    return filtered_df, info_message

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="RSS Reader Berita Indonesia",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar untuk pengaturan
with st.sidebar:
    st.title("📰 RSS Reader")
    st.markdown("Aplikasi untuk membaca berita terbaru dari berbagai portal berita Indonesia")
    
    st.markdown("---")
    st.subheader("⚙️ Pengaturan")
    
    # Pilih portal berita
    selected_feeds = st.multiselect(
        "Pilih Portal Berita",
        options=list(RSS_FEEDS.keys()),
        default=list(RSS_FEEDS.keys())[:4],
        help="Pilih portal berita yang ingin ditampilkan"
    )
    
    # Tombol untuk mengambil semua berita
    if st.button("📋 Tampilkan Semua Berita", type="primary", use_container_width=True):
        with st.spinner("Mengambil data berita..."):
            df, message = get_all_news_dataframe(selected_feeds)
            st.session_state.df = df
            st.session_state.info_message = message
    
    st.markdown("---")
    st.subheader("🔍 Filter & Pencarian")
    
    # Pilihan filter waktu
    time_filter = st.selectbox(
        "Filter Berdasarkan Waktu",
        options=["Semua Artikel", "Hari Ini", "Kemarin", "Satu minggu terakhir", "Satu bulan terakhir", "custom"],
        index=0,
        help="Pilih rentang waktu untuk memfilter artikel"
    )
    
    # Input untuk custom days
    custom_days = None
    if time_filter == "custom":
        custom_days = st.number_input(
            "... hari lalu",
            min_value=1,
            max_value=365,
            value=7,
            help="Masukkan jumlah hari yang ingin ditampilkan"
        )
    
    # Input pencarian
    search_query = st.text_input(
        "Kata Kunci Pencarian",
        placeholder="Masukkan kata kunci (contoh: politik, olahraga, ekonomi)...",
        help="Cari artikel berdasarkan kata kunci dalam judul atau ringkasan"
    )
    
    # Tombol terapkan filter
    if st.button("🔎 Terapkan Filter", use_container_width=True):
        if 'df' in st.session_state and not st.session_state.df.empty:
            filtered_df, filter_message = filter_dataframe(
                st.session_state.df, search_query, time_filter, custom_days
            )
            st.session_state.filtered_df = filtered_df
            st.session_state.filter_message = filter_message
        else:
            st.warning("Silakan klik 'Tampilkan Semua Berita' terlebih dahulu")
    
    st.markdown("---")
    st.subheader("ℹ️ Cara Penggunaan:")
    st.markdown("""
    1. Pilih portal berita
    2. Klik **Tampilkan Semua Berita** (data akan disimpan)
    3. Gunakan filter waktu dan kata kunci
    4. Klik **Terapkan Filter** untuk melihat hasil
    """)

# Konten utama
st.title("📰 RSS Feed Reader - Portal Berita Indonesia")
st.markdown("Klik