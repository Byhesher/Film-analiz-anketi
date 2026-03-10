import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime
import random

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
    .stButton button { font-size: 0.75rem !important; padding: 0.1rem 0.4rem !important; min-height: 25px; }
    .stMarkdown p { font-size: 0.8rem !important; line-height: 1.2 !important; margin-bottom: 4px !important; }
    [data-testid="stVerticalBlock"] > div > div > div > div { padding: 0.4rem !important; border-radius: 8px; }
    div[data-testid="column"] { padding: 0.2rem !important; }
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
    
    df['Runtime'] = [random.randint(70, 210) for _ in range(len(df))]

    tr_films = []
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    for page in range(1, 151):
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
                    'Runtime': random.randint(85, 160)
                })
        except: break
        if len(tr_films) >= 2500: break

    df = pd.concat([df, pd.DataFrame(tr_films)], ignore_index=True).drop_duplicates('title')
    return df

df = verileri_yukle()
g_yil = datetime.now().year

TUR_HARITASI = {
    "Aksiyon": "Action", "Macera": "Adventure", "Animasyon": "Animation",
    "Komedi": "Comedy", "Suç": "Crime", "Belgesel": "Documentary",
    "Dram": "Drama", "Aile": "Family", "Fantastik": "Fantasy",
    "Korku": "Horror", "Müzikal": "Musical", "Gizem": "Mystery",
    "Romantik": "Romance", "Bilim Kurgu": "Sci-Fi", "Gerilim": "Thriller",
    "Savaş": "War", "Batı": "Western"
}

if 'kurulum_tamam' not in st.session_state: st.session_state.kurulum_tamam = False
if 'secilen_listesi' not in st.session_state: st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state: st.session_state.rastgele_filmler = []
if 'ana_filtreli_df' not in st.session_state: st.session_state.ana_filtreli_df = df
if 'secili_turler' not in st.session_state: st.session_state.secili_turler = []

def onerileri_guncelle(kaynak_df):
    aday = kaynak_df[~kaynak_df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(500)
    st.session_state.rastgele_filmler = aday.sample(min(25, len(aday))).to_dict('records')

st.sidebar.title("🛠️ Kontrol Paneli")

with st.sidebar.form("filtre_formu"):
    f_turler = st.multiselect("Tür Tercihi", options=list(TUR_HARITASI.keys()), default=st.session_state.secili_turler)
    f_imdb = st.checkbox("Sadece Yüksek Puanlı (7.0+)", value=False)
    f_sure = st.slider("Film Süresi (Dakika)", 60, 240, (80, 180))
    apply_btn = st.form_submit_button("Filtreleri Uygula", use_container_width=True)

if apply_btn:
    temp_df = df.copy()
    if f_turler:
        en_turler = [TUR_HARITASI[t] for t in f_turler]
        temp_df = temp_df[temp_df['genres'].str.contains('|'.join(en_turler), na=False)]
        st.session_state.secili_turler = f_turler
    if f_imdb:
        temp_df = temp_df[temp_df['IMDb_Rating'] >= 7.0]
    temp_df = temp_df[(temp_df['Runtime'] >= f_sure[0]) & (temp_df['Runtime'] <= f_sure[1])]
    
    st.session_state.ana_filtreli_df = temp_df
    onerileri_guncelle(temp_df)
    st.session_state.kurulum_tamam = True

st.title("🎥 Sinema Profil Analizi")

if not st.session_state.kurulum_tamam:
    st.info("Başlamak için sol taraftaki filtreleri belirleyip 'Uygula' butonuna basın.")
    st.stop()

st.subheader("🔍 Hızlı Arama")
siralama = st.selectbox("Arama Listesi Sıralaması:", ["Karışık", "A-Z", "IMDb Puanı", "Yıl"])

l_df = st.session_state.ana_filtreli_df
if siralama == "A-Z": l_df = l_df.sort_values('title')
elif siralama == "IMDb Puanı": l_df = l_df.sort_values('IMDb_Rating', ascending=False)
elif siralama == "Yıl": l_df = l_df.sort_values('Year', ascending=False)

m_secim = st.multiselect("Filtrelerinize uygun filmler:", options=l_df['title'].tolist())

if st.button("Seçilenleri Ekle", key="btn_manual_add", use_container_width=True):
    for m in m_secim:
        if m not in st.session_state.secilen_listesi:
            st.session_state.secilen_listesi.append(m)
    onerileri_guncelle(st.session_state.ana_filtreli_df)
    st.rerun()

st.divider()

st.subheader("🎲 Keşfet (Size Özel 25 Öneri)")
cols = st.columns(5)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 5]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | ⏳ {f['Runtime']} dk")
            if st.button("Seç ✅", key=f"btn_{i}_{f['title']}", use_container_width=True):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    onerileri_guncelle(st.session_state.ana_filtreli_df)
                    st.rerun()

count = len(st.session_state.secilen_listesi)
st.sidebar.divider()
st.sidebar.metric("Toplam Seçilen", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    if st.sidebar.button("🚀 ANALİZİ BAŞLAT", key="btn_analyze", use_container_width=True):
        s_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        t_c = pd.Series([t for g in s_df['genres'].dropna() for t in g.split('|')]).value_counts().reset_index()
        t_c.columns = ['Tür', 'Adet']
        st.header("✨ Sinema Kimliğiniz")
        l, r = st.columns(2)
        l.plotly_chart(px.pie(t_c.head(6), values='Adet', names='Tür', hole=0.4), use_container_width=True)
        r.success(f"En Sevdiğiniz Tür: {t_c.iloc[0]['Tür']}")
        st.divider()
        st.subheader("🍿 Bunları da Sevebilirsiniz")
        t_cols = st.columns(3)
        for i, tur in enumerate(t_c.head(3)['Tür'].tolist()):
            with t_cols[i]:
                st.markdown(f"#### 🎭 {tur}")
                t_a = df[df['genres'].str.contains(tur, na=False) & (~df['title'].isin(st.session_state.secilen_listesi))]
                res = t_a[((t_a['Year'] >= g_yil-3) & (t_a['Votes'] >= 5)) | ((t_a['Year'] < g_yil-3) & (t_a['Votes'] >= 10))]
                for _, row in res[res['IMDb_Rating'] >= 4.0].sort_values(['IMDb_Rating', 'Votes'], ascending=False).head(3).iterrows():
                    st.write(f"🔹 {row['title']} (⭐{row['IMDb_Rating']})")
