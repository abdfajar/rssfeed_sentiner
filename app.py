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
            content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
            author = entry.get('author', '')
            
            # Jika tidak ada summary, gunakan description
            if not summary:
                summary = entry.get('description', 'No summary available')
            
            # Clean summary dari tag HTML
            summary = re.sub('<[^<]+?>', '', summary)
            content = re.sub('<[^<]+?>', '', content)
            
            # Konversi tanggal ke datetime object
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
                'summary': summary,
                'content': content,
                'author': author,
                'full_content': title + ". " + (content if content else summary)
            })
        
        return articles
    except Exception as e:
        st.error(f"Error parsing feed {feed_url}: {e}")
        return []

def get_all_news_dataframe(selected_feeds):
    """Mengambil semua berita dan menyimpan dalam dataframe"""
    if not selected_feeds:
        st.warning("⚠️ Pilih setidaknya satu portal berita")
        return pd.DataFrame()
    
    all_articles_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, feed_name in enumerate(selected_feeds):
        if feed_name in RSS_FEEDS:
            status_text.text(f"🔄 Mengambil data dari: {feed_name}")
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
                    'summary': article['summary'],
                    'content': article['content'],
                    'author': article['author'],
                    'full_content': article['full_content']
                }
                all_articles_data.append(article_data)
            
            progress_bar.progress((idx + 1) / len(selected_feeds))
    
    status_text.empty()
    progress_bar.empty()
    
    # Buat dataframe dari semua artikel
    if all_articles_data:
        df = pd.DataFrame(all_articles_data)
        # Urutkan berdasarkan tanggal
        df = df.sort_values('date_stamp', ascending=False)
        return df
    else:
        st.error("❌ Tidak ada artikel yang ditemukan")
        return pd.DataFrame()

def filter_dataframe(df, query, filter_type, custom_days):
    """Filter dataframe berdasarkan pencarian dan tanggal"""
    if df.empty:
        st.warning("⚠️ Tidak ada data yang tersedia")
        return df
    
    filtered_df = df.copy()
    
    # Filter berdasarkan kata kunci
    if query:
        query_lower = query.lower()
        keyword_mask = (
            filtered_df['judul_artikel'].str.lower().str.contains(query_lower, na=False) |
            filtered_df['summary'].str.lower().str.contains(query_lower, na=False) |
            filtered_df['content'].str.lower().str.contains(query_lower, na=False)
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
    
    return filtered_df

def display_article_detail(article):
    """Menampilkan detail metadata artikel yang terpilih"""
    st.subheader("📋 Detail Metadata Artikel")
    
    # Tampilkan dalam bentuk columns untuk layout yang lebih rapi
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Informasi Artikel")
        st.write(f"**📰 Judul:** {article['judul_artikel']}")
        st.write(f"**🏢 Sumber:** {article['sumber_artikel']}")
        st.write(f"**📅 Tanggal Publikasi:** {article['published_string']}")
        st.write(f"**👤 Penulis:** {article['author'] if article['author'] else 'Tidak tersedia'}")
        
        st.markdown("### Ringkasan")
        st.write(article['summary'])
    
    with col2:
        st.markdown("### Metadata Teknis")
        st.write(f"**🔗 URL:**")
        st.code(article['url_artikel'], language='text')
        
        st.write(f"**📊 Date Stamp:**")
        if article['date_stamp']:
            st.code(article['date_stamp'].strftime('%Y-%m-%d %H:%M:%S'), language='text')
        else:
            st.code("Tidak tersedia", language='text')
        
        st.write(f"**📝 Panjang Konten:**")
        content_length = len(article['content']) if article['content'] else 0
        summary_length = len(article['summary']) if article['summary'] else 0
        st.code(f"Konten: {content_length} karakter\nRingkasan: {summary_length} karakter", language='text')
    
    # Tombol untuk membuka artikel
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn2:
        st.link_button("📖 Baca Artikel Lengkap", article['url_artikel'], use_container_width=True)
    
    # Tampilkan konten lengkap jika tersedia
    if article['content'] and len(article['content']) > len(article['summary']):
        with st.expander("📄 Lihat Konten Lengkap"):
            st.write(article['content'])

def display_articles_with_selection(df, title, key_suffix):
    """Menampilkan artikel dalam format dataframe dengan selection"""
    if df.empty:
        st.warning(f"❌ Tidak ada artikel untuk {title}")
        return None
    
    # Buat dataframe untuk display
    display_df = df[['sumber_artikel', 'judul_artikel', 'url_artikel', 'published_string']].copy()
    display_df.columns = ['Sumber', 'Judul Artikel', 'URL', 'Tanggal Publikasi']
    
    # Potong judul yang terlalu panjang untuk display
    display_df['Judul Artikel Display'] = display_df['Judul Artikel'].apply(
        lambda x: x[:80] + '...' if len(x) > 80 else x
    )
    
    # Buat pilihan untuk selectbox
    article_options = [
        f"{row['Judul Artikel Display']} | {row['Sumber']} | {row['Tanggal Publikasi']}" 
        for _, row in display_df.iterrows()
    ]
    
    # Tampilkan dataframe
    st.dataframe(
        display_df[['Sumber', 'Judul Artikel Display', 'Tanggal Publikasi']],
        use_container_width=True,
        hide_index=True
    )
    
    # Selectbox untuk memilih artikel
    st.subheader("🔍 Pilih Artikel untuk Detail")
    selected_article_idx = st.selectbox(
        f"Pilih artikel dari {title}:",
        options=range(len(df)),
        format_func=lambda x: article_options[x],
        key=f"select_{key_suffix}"
    )
    
    if selected_article_idx is not None:
        selected_article = df.iloc[selected_article_idx]
        return selected_article
    
    return None

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="RSS Reader Berita Indonesia",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar untuk pengaturan
with st.sidebar:
    st.title("⚙️ Pengaturan")
    
    st.subheader("📊 Portal Berita")
    selected_feeds = st.multiselect(
        "Pilih portal berita:",
        options=list(RSS_FEEDS.keys()),
        default=list(RSS_FEEDS.keys())[:4],
        help="Pilih portal berita yang ingin ditampilkan"
    )
    
    if st.button("📋 Tampilkan Semua Berita", type="primary", use_container_width=True):
        with st.spinner("Mengambil data berita..."):
            st.session_state.df = get_all_news_dataframe(selected_feeds)
    
    st.divider()
    
    st.subheader("🔍 Filter & Pencarian")
    
    # Pilihan filter waktu
    filter_type = st.radio(
        "Filter Berdasarkan Waktu:",
        options=["Semua Artikel", "Hari Ini", "Kemarin", "Satu minggu terakhir", "Satu bulan terakhir", "custom"],
        index=0,
        help="Pilih rentang waktu untuk memfilter artikel"
    )
    
    custom_days = None
    if filter_type == "custom":
        custom_days = st.number_input(
            "... hari lalu",
            min_value=1,
            max_value=365,
            value=7,
            help="Masukkan jumlah hari yang ingin ditampilkan"
        )
    
    search_query = st.text_input(
        "Kata Kunci Pencarian:",
        placeholder="Masukkan kata kunci (contoh: politik, olahraga, ekonomi)...",
        help="Cari artikel berdasarkan kata kunci dalam judul atau ringkasan"
    )
    
    st.divider()
    
    st.subheader("ℹ️ Cara Penggunaan:")
    st.markdown("""
    1. **Pilih portal berita** di sidebar
    2. **Klik 'Tampilkan Semua Berita'** untuk mengambil data
    3. **Gunakan filter** waktu dan kata kunci
    4. **Pilih artikel** dari tabel untuk melihat detail metadata
    """)

# Main content
st.title("📰 RSS Reader - Portal Berita Indonesia")
st.markdown("Aplikasi untuk membaca berita terbaru dari berbagai portal berita Indonesia")

# Inisialisasi session state
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'selected_article_all' not in st.session_state:
    st.session_state.selected_article_all = None
if 'selected_article_search' not in st.session_state:
    st.session_state.selected_article_search = None

# Tampilkan data berdasarkan filter
if not st.session_state.df.empty:
    # Filter data
    filtered_df = filter_dataframe(st.session_state.df, search_query, filter_type, custom_days)
    
    # Tampilkan informasi summary
    col1, col2, col_3 = st.columns(3)
    
    with col1:
        st.metric("Total Artikel", len(st.session_state.df))
    
    with col2:
        st.metric("Artikel Difilter", len(filtered_df))
    
    with col_3:
        if search_query:
            st.metric("Kata Kunci", f"'{search_query}'")
        else:
            st.metric("Filter Waktu", filter_type)
    
    # Tampilkan tab untuk berbagai view
    tab1, tab2 = st.tabs(["📊 Semua Artikel", "🔍 Hasil Pencarian"])
    
    with tab1:
        st.subheader("Semua Artikel yang Diambil")
        selected_article_all = display_articles_with_selection(
            st.session_state.df, 
            "semua artikel", 
            "all"
        )
        
        # Simpan selected article di session state
        if selected_article_all is not None:
            st.session_state.selected_article_all = selected_article_all
    
    with tab2:
        st.subheader("Hasil Pencarian")
        if search_query or filter_type != "Semua Artikel":
            selected_article_search = display_articles_with_selection(
                filtered_df, 
                "hasil pencarian", 
                "search"
            )
            
            # Simpan selected article di session state
            if selected_article_search is not None:
                st.session_state.selected_article_search = selected_article_search
        else:
            st.info("🔍 Gunakan filter di sidebar untuk melihat hasil pencarian")
    
    # Tampilkan detail artikel yang terpilih
    st.markdown("---")
    
    # Tentukan artikel mana yang akan ditampilkan (prioritaskan dari tab aktif)
    if tab2._active:
        selected_article = st.session_state.selected_article_search
        tab_source = "Hasil Pencarian"
    else:
        selected_article = st.session_state.selected_article_all
        tab_source = "Semua Artikel"
    
    if selected_article is not None:
        display_article_detail(selected_article)
    else:
        st.info("👆 Pilih artikel dari tabel di atas untuk melihat detail metadata")
    
else:
    st.info("👈 Pilih portal berita dan klik 'Tampilkan Semua Berita' di sidebar untuk memulai")

# Footer
st.divider()
st.caption("Dibuat dengan Streamlit • Data dari berbagai portal berita Indonesia")