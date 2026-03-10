import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
import random

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

st.markdown("""
<style>
    .stButton button { border-radius: 20px; transition: 0.3s; }
    .stButton button:hover { background-color: #ff4b4b; color: white; }
    .movie-card img { width: 75%; height: auto; }
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

st.title("🎥 Sinema Profil Analizi")

with st.sidebar:
    st.header("🛠️ Filtreler")
    f_imdb = st.slider("Minimum IMDb", 0.0, 10.0, 5.0)
    f_sure = st.slider("Maksimum Süre (dk)", 60, 240, 180)

    st.divider()
    count = len(st.session_state.secilen_listesi)
    st.metric("Seçilen Film", f"{count} / 10")
    st.progress(min(count/10, 1.0))

    if count >= 10:
        if st.button("🚀 ANALİZİ BAŞLAT", use_container_width=True):
            st.session_state.analiz_modu = True

temp_df = df[(df['IMDb_Rating'] >= f_imdb) & (df['Runtime'] <= f_sure)]

def yenile():
    if st.session_state.secilen_listesi:
        secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        secilen_turler = set(t for g in secilen_df['genres'].dropna() for t in g.split('|'))
        adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)]
      
        adaylar = adaylar[adaylar['genres'].apply(lambda x: bool(secilen_turler.intersection(set(str(x).split('|')))))]
        if len(adaylar) < 15:
            adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)]
    else:
        adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)]
    st.session_state.rastgele_filmler = adaylar.sample(min(len(adaylar), 15)).to_dict('records')

if not st.session_state.rastgele_filmler:
    yenile()

tab1, tab2 = st.tabs(["🎯 Film Seçimi", "📊 Profilim"])

with tab1:
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
        m_secim = st.multiselect("Film Ara ve Ekle:", options=temp_df['title'].tolist())
    with col_refresh:
        if st.button("🔄 Önerileri Yenile", use_container_width=True):
            yenile()
            st.rerun()

    if st.button("Seçilenleri Listeye Ekle"):
        for m in m_secim:
            if m not in st.session_state.secilen_listesi:
                st.session_state.secilen_listesi.append(m)
        yenile()
        st.rerun()

    cols = st.columns(5)
    for i, f in enumerate(st.session_state.rastgele_filmler):
        with cols[i % 5]:
            poster_url = get_single_poster(f['imdbId'])
            st.image(poster_url, width=150)
            st.markdown(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | {f['Runtime']} dk")
            if st.button("Seç", key=f"btn_{f['movieId']}"):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    yenile()
                    st.rerun()

with tab2:
    if len(st.session_state.secilen_listesi) > 0:
        s_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        t_c = pd.Series([t for g in s_df['genres'].dropna() for t in g.split('|')]).value_counts().reset_index()
        t_c.columns = ['Tür', 'Adet']

        st.header("✨ Sinema Kimliğiniz")
        fig = px.pie(t_c, values='Adet', names='Tür', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"Favori türünüz: **{t_c.iloc[0]['Tür']}**. Bu türe ait filmler profilinizin %{int(t_c.iloc[0]['Adet']/t_c['Adet'].sum()*100)}'ini oluşturuyor.")
    else:
        st.warning("Analiz için henüz film seçmediniz.") 
