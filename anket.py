import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime
import random

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .stMultiSelect div[data-baseweb="select"] { min-height: 45px; }
    .stButton button { font-size: 0.75rem !important; padding: 0.1rem 0.4rem !important; min-height: 25px; }
    .stMarkdown p { font-size: 0.8rem !important; line-height: 1.2 !important; margin-bottom: 4px !important; }
    div[data-testid="column"] { padding: 0.15rem !important; }
    div[data-testid="stVerticalBlock"] > div > div > div > div { padding: 0.4rem !important; border-radius: 10px; border: 1px solid #333; }
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
        if match:
            return f"{match.group(2)} {match.group(1)} {match.group(3)}"
        return title

    df_m['title'] = df_m['title'].apply(temizle)
    df = df_m.merge(df_l[['movieId', 'imdbId']], on='movieId')
    stats = df_r.groupby('movieId').agg({'rating': ['mean', 'count']}).reset_index()
    stats.columns = ['movieId', 'IMDb_Rating', 'Votes']
    df = df.merge(stats, on='movieId')
    df['IMDb_Rating'] = (df['IMDb_Rating'] * 2).round(1)
    df['Year'] = df['title'].str.extract(r'\((\d{4})\)').fillna(0).astype(int)
    df['Runtime'] = [random.randint(75, 185) for _ in range(len(df))]

    tr_films = []
    api_key = "8265bd1679663a7ea12ac168da84d2e8"

    for page in range(1, 101):
        tr_url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&with_original_language=tr&language=tr-TR&page={page}&sort_by=vote_count.desc"
        try:
            data = requests.get(tr_url).json().get('results', [])
            for m in data:
                tr_films.append({
                    'title': f"{m['title']} ({m['release_date'][:4]})" if m.get('release_date') else m['title'],
                    'genres': 'Drama|Crime|Thriller|Comedy',
                    'IMDb_Rating': m['vote_average'],
                    'Votes': m['vote_count'],
                    'Year': int(m['release_date'][:4]) if m.get('release_date') else 0,
                    'Runtime': random.randint(90, 150)
                })
        except:
            break
    
    df = pd.concat([df, pd.DataFrame(tr_films)], ignore_index=True).drop_duplicates('title')
    return df

df = verileri_yukle()

TUR_HARITASI = {
    "Hepsi": "All",
    "Aksiyon": "Action",
    "Macera": "Adventure",
    "Animasyon": "Animation",
    "Komedi": "Comedy",
    "Suç": "Crime",
    "Dram": "Drama",
    "Korku": "Horror",
    "Gizem": "Mystery",
    "Romantik": "Romance",
    "Bilim Kurgu": "Sci-Fi",
    "Gerilim": "Thriller"
}

if 'secilen_listesi' not in st.session_state:
    st.session_state.secilen_listesi = []

if 'rastgele_filmler' not in st.session_state:
    st.session_state.rastgele_filmler = df.sample(25).to_dict('records')

def onerileri_guncelle(kaynak_df):
    aday = kaynak_df[~kaynak_df['title'].isin(st.session_state.secilen_listesi)]
    if len(aday) >= 25:
        st.session_state.rastgele_filmler = aday.sample(25).to_dict('records')


st.markdown("<h1 style='font-size:90%;'>🎥 Sinema Profil Analizi</h1>", unsafe_allow_html=True)

st.write("### 🎭 Tür Seçimi")
secili_tur_tr = st.pills(
    "Türler",
    options=list(TUR_HARITASI.keys()),
    default="Hepsi",
    selection_mode="single"
)

with st.sidebar:
    st.header("🛠️ Filtreler")

   
    f_imdb = st.slider("Minimum IMDb", 0.0, 10.0, 6.0)

    f_sure = st.slider("Maksimum Süre (dk)", 60, 240, 180)

    temp_df = df.copy()

    if secili_tur_tr != "Hepsi":
        temp_df = temp_df[temp_df['genres'].str.contains(TUR_HARITASI[secili_tur_tr], na=False)]

    temp_df = temp_df[(temp_df['IMDb_Rating'] >= f_imdb) & (temp_df['Runtime'] <= f_sure)]

st.subheader("🔍 Hızlı Arama")

m_secim = st.multiselect("Film ara:", options=temp_df['title'].tolist())

if st.button("Seçilenleri Ekle", key="manual_add", use_container_width=True):
    for m in m_secim:
        if m not in st.session_state.secilen_listesi:
            st.session_state.secilen_listesi.append(m)

    onerileri_guncelle(temp_df)
    st.rerun()

st.divider()

st.subheader("🎲 Önerilenler")

cols = st.columns(5)

for i, f in enumerate(st.session_state.rastgele_filmler):

    with cols[i % 5]:

        with st.container(border=True):

          
            st.markdown(
                f"<p style='font-size:110%; font-weight:600;'>{f['title']}</p>",
                unsafe_allow_html=True
            )

            st.caption(f"⭐ {f['IMDb_Rating']} | ⏳ {f['Runtime']} dk")

            if st.button("Seç ✅", key=f"btn_{i}_{f['title']}", use_container_width=True):

                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])

                    onerileri_guncelle(temp_df)

                    st.rerun()

count = len(st.session_state.secilen_listesi)

st.sidebar.divider()

st.sidebar.metric("Seçilen", f"{count} / 20")

st.sidebar.progress(min(count/20, 1.0))

if count >= 20:

    if st.sidebar.button("🚀 ANALİZİ BAŞLAT", use_container_width=True):

        s_df = df[df['title'].isin(st.session_state.secilen_listesi)]

        t_c = pd.Series(
            [t for g in s_df['genres'].dropna() for t in g.split('|')]
        ).value_counts().reset_index()

        t_c.columns = ['Tür', 'Adet']

        st.header("✨ Sinema Kimliğiniz")

        l, r = st.columns(2)

        l.plotly_chart(
            px.pie(
                t_c.head(6),
                values='Adet',
                names='Tür',
                hole=0.4
            ),
            use_container_width=True
        )

        r.success(f"En Sevdiğiniz Tür: {t_c.iloc[0]['Tür']}")
