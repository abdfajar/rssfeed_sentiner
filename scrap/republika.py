import requests
from bs4 import BeautifulSoup
import re

def scrape_republika_content(url):
    """
    Scraping konten artikel dari Republika.co.id.
    
    Parameters:
        url (str): URL artikel Republika.co.id
    
    Returns:
        str: Teks konten artikel saja (bersih), atau string error jika gagal.
    """
    try:
        # Setup headers agar tidak diblokir
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'id,en;q=0.7',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Cari container utama
        main_content = soup.find('div', class_='main-content__left')
        if not main_content:
            return "Error: Struktur halaman tidak dikenali (tidak ditemukan .main-content__left)"
        
        # Prioritas 1: div.article-content
        article_content = main_content.find('div', class_='article-content')
        if article_content:
            text = article_content.get_text(separator='\n', strip=True)
        else:
            # Fallback: coba selector lain
            selectors = [
                '.article-body', '.content', '.post-content',
                '[itemprop="articleBody"]', '.detail-text'
            ]
            text = ""
            for sel in selectors:
                elem = main_content.select_one(sel)
                if elem:
                    text = elem.get_text(separator='\n', strip=True)
                    break
            if not text:
                # Fallback terakhir: ambil semua teks dari main_content
                text = main_content.get_text(separator='\n', strip=True)
        
        # Bersihkan teks
        text = re.sub(r'\s+', ' ', text)  # Hapus whitespace berlebih
        text = re.sub(r'[^\w\s.,!?;:()\-]', '', text)  # Hapus karakter aneh
        text = text.strip()
        
        if len(text) < 50:
            return "Error: Konten terlalu pendek atau tidak berhasil diekstrak."
        
        return text
        
    except requests.exceptions.RequestException as e:
        return f"Error jaringan: {str(e)}"
    except Exception as e:
        return f"Error tak terduga: {str(e)}"


# --- CONTOH PENGGUNAAN ---
if __name__ == "__main__":
    url = "https://www.republika.co.id/berita/some-article-slug"  # Ganti dengan URL asli
    konten = scrape_republika_content(url)
    print(konten[:1000])  # Tampilkan 1000 karakter pertama