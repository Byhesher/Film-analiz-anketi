import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
import random

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

st.markdown("""
<style>
    .stImage img { margin-bottom: -10px !important; cursor: pointer; }
    .css-1n76uvr {gap: 4px !important;} 
    .poster-container {position:relative; display:inline-block; margin-bottom: 10px;}
    .poster-label {position:absolute; bottom:0; left:0; background:rgba(255,0,0,0.6); color:white; font-weight:bold; padding:2px 6px; border-radius:4px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def verileri_yukle():
    url = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df_m = pd.read_csv(z.open('ml-latest-small/movies.csv'))
    df_l = pd.read_csv(z.open('ml-latest-small/links.csv'))
    df_r = pd.read_csv(z.open('ml-latest-small/ratings.csv'))

    def temizle(title):
        match = re.search(r'^(.*),\s(The|A|An)\s(\(\d{4}\))$', title)
        if match: return f"{match.group(2)} {match.group(1)} {match.group(3)}"
        return title

    df_m['title'] = df_m['title'].apply(temizle)
    df = df_m.merge(df_l[['movieId', 'imdbId']], on='movieId')
    stats = df_r.groupby('movieId').agg({'rating': ['mean', 'count']}).reset_index()
    stats.columns = ['movieId', 'IMDb_Rating', 'Votes']
    df = df.merge(stats, on='movieId')
    df['IMDb_Rating'] = (df['IMDb_Rating'] * 2).round(1)
    df['Year'] = df['title'].str.extract(r'\((\d{4})\)').fillna(0).astype(int)
    df['Runtime'] = [random.randint(80, 160) for _ in range(len(df))]
    return df

def get_single_poster(imdb_id):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        url = f"https://api.themoviedb.org/3/find/tt{str(imdb_id).zfill(7)}?api_key={api_key}&external_source=imdb_id"
        res = requests.get(url).json().get("movie_results", [])
        if res and res[0].get("poster_path"):
            return "https://image.tmdb.org/t/p/w500" + res[0]["poster_path"]
    except: pass
    return "https://via.placeholder.com/300x450?text=Film+Afisi"

df = verileri_yukle()
if 'secilen_listesi' not in st.session_state: st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state: st.session_state.rastgele_filmler = []
if 'analiz_modu' not in st.session_state: st.session_state.analiz_modu = False

st.title("🎥 Sinema Profil Analizi")


count = len(st.session_state.secilen_listesi)
st.markdown(f"<div style='font-size:20px; font-weight:bold'>🎬 Seçilen Film: {count} / 20</div>", unsafe_allow_html=True)


if st.button("🧹 Clear Seçilenleri", use_container_width=True):
    st.session_state.secilen_listesi = []
    st.session_state.rastgele_filmler = []
    st.session_state.analiz_modu = False

temp_df = df.copy()

def yenile():
    adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)]
    st.session_state.rastgele_filmler = adaylar.sample(min(len(adaylar), 20)).to_dict('records')

if not st.session_state.rastgele_filmler:
    yenile()

def afise_tikla(film_adi):
    if film_adi not in st.session_state.secilen_listesi:
        st.session_state.secilen_listesi.append(film_adi)
        yenile()

if st.session_state.analiz_modu:
 
    secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    secilen_tur = pd.Series([t for g in secilen_df['genres'].dropna() for t in g.split('|')]).value_counts().idxmax()
    imdb_avg = secilen_df['IMDb_Rating'].mean()
    runtime_avg = secilen_df['Runtime'].mean()
    adaylar = df[~df['title'].isin(st.session_state.secilen_listesi)].copy()

    def benzerlik(film):
        turler = set(str(film['genres']).split('|'))
        tur_skor = len(set(secilen_df['genres'].dropna().str.cat(sep='|').split('|')).intersection(turler)) / max(len(set(secilen_df['genres'].dropna().str.cat(sep='|').split('|'))),1)
        imdb_skor = 1 - abs(film['IMDb_Rating'] - imdb_avg) / 10
        sure_skor = 1 - abs(film['Runtime'] - runtime_avg) / 160
        return 100 * (0.6 * tur_skor + 0.3 * imdb_skor + 0.1 * sure_skor)

    adaylar['Benzerlik'] = adaylar.apply(benzerlik, axis=1)
    adaylar = adaylar.sort_values('Benzerlik', ascending=False).head(20)

    def tavsiye(skor):
        if skor >= 84: return f"🔥 Kesinlikle izlemelisiniz (%{skor:.0f})"
        elif skor >= 70: return f"⭐ Kesinlikle izlemelisiniz (%{skor:.0f})"
        elif skor >= 50: return f"⭐ İzlemelisiniz (%{skor:.0f})"
        else: return f"🔹 Bakmaya değer (%{skor:.0f})"

    adaylar['Tavsiye Durumu'] = adaylar['Benzerlik'].apply(tavsiye)
    adaylar['Link'] = "https://www.imdb.com/title/tt" + adaylar['imdbId'].astype(str).str.zfill(7)

    st.header("🎯 Size Özel Film Önerileri")
    st.markdown(f'<div style="font-size:18px; font-weight:bold; background:rgba(255,0,0,0.6); color:white; padding:4px; border-radius:6px; width:fit-content;">Favori Tür: {secilen_tur}</div>', unsafe_allow_html=True)

    cols = st.columns(5, gap="small")
    for i, f in enumerate(adaylar.to_dict('records')):
        with cols[i%5]:
            poster_url = get_single_poster(f['imdbId'])
            if st.button(f"{f['title']}", key=f"poster_btn_{f['movieId']}", on_click=afise_tikla, args=(f['title'],)):
                pass
            st.markdown(f'<div class="poster-container"><img src="{poster_url}" width="160"></div>', unsafe_allow_html=True)
            st.caption(f"⭐ {f['IMDb_Rating']} | {f['Tavsiye Durumu']}")

    st.header("📊 Sinema Kimliğiniz")
    t_c = pd.Series([t for g in secilen_df['genres'].dropna() for t in g.split('|')]).value_counts().reset_index()
    t_c.columns = ['Tür', 'Adet']
    fig = px.pie(t_c, values='Adet', names='Tür', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

else:
    tab1, tab2 = st.tabs(["🎯 Film Seçimi", "📊 Profilim"])
    with tab1:
        film_listesi = temp_df['title'].astype(str).tolist()
        m_secim = st.multiselect("Film Ara ve Ekle:", options=film_listesi, default=[], key="m_secim")
        for f in m_secim:
            if f not in st.session_state.secilen_listesi:
                st.session_state.secilen_listesi.append(f)
                yenile()
        if st.button("🔄 Önerileri Yenile", use_container_width=True):
            yenile()
       
        cols = st.columns(5, gap="small")
        for i, f in enumerate(st.session_state.rastgele_filmler):
            with cols[i % 5]:
                poster_url = get_single_poster(f['imdbId'])
                st.markdown(f'<div class="poster-container"><img src="{poster_url}" width="160"></div>', unsafe_allow_html=True)
                if st.button(f"{f['title']}", key=f"poster_btn_{f['movieId']}", on_click=afise_tikla, args=(f['title'],)):
                    pass
                st.caption(f"⭐ {f['IMDb_Rating']} | {f['Runtime']} dk")

        
        if count >= 20:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<center>", unsafe_allow_html=True)
            if st.button("🚀 ANALİZİ BAŞLAT", use_container_width=False):
                st.session_state.analiz_modu = True
            st.markdown("</center>", unsafe_allow_html=True)
