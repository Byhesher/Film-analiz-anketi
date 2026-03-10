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
    .image-button {padding:0; border:none; background:none; width:100%; height:100%; position:absolute; top:0; left:0; cursor:pointer;}
    .poster-container {position:relative; display:inline-block;}
    .poster-label {position:absolute; top:0; left:0; background:rgba(255,0,0,0.6); color:white; font-weight:bold; padding:2px 6px; border-radius:4px;}
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

with st.sidebar:
    st.header("🛠️ Filtreler")
    f_imdb = st.slider("Minimum IMDb", 0.0, 10.0, 5.0)
    f_sure = st.slider("Maksimum Süre (dk)", 60, 240, 180)
    st.divider()
    count = len(st.session_state.secilen_listesi)
    st.metric("Seçilen Film", f"{count} / 20")
    st.progress(min(count/20, 1.0))
    if count >= 20:
        if st.button("🚀 ANALİZİ BAŞLAT", use_container_width=True):
            st.session_state.analiz_modu = True

temp_df = df[(df['IMDb_Rating'] >= f_imdb) & (df['Runtime'] <= f_sure)]

def yenile():
    if not st.session_state.secilen_listesi:
        adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)]
        st.session_state.rastgele_filmler = adaylar.sample(min(len(adaylar), 20)).to_dict('records')
        return
    secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    turler = [t for g in secilen_df['genres'].dropna() for t in g.split('|')]
    tur_df = pd.Series(turler).value_counts(normalize=True).reset_index()
    tur_df.columns = ['Tür', 'Ağırlık']
    adaylar = temp_df[~temp_df['title'].isin(st.session_state.secilen_listesi)].copy()
    secilen_filmsayisi = min(20, len(adaylar))
    secilen_filmler = []
    for _, row in tur_df.iterrows():
        tur = row['Tür']
        agirlik = row['Ağırlık']
        n_sec = max(1, round(secilen_filmsayisi * agirlik))
        tur_aday = adaylar[adaylar['genres'].str.contains(tur, na=False)]
        tur_aday = tur_aday[~tur_aday['title'].isin([f['title'] for f in secilen_filmler])]
        if len(tur_aday) > 0:
            secilen_filmler.extend(tur_aday.sample(min(n_sec, len(tur_aday))).to_dict('records'))
    kalan = secilen_filmsayisi - len(secilen_filmler)
    if kalan > 0:
        geri_kalan = adaylar[~adaylar['title'].isin([f['title'] for f in secilen_filmler])]
        if len(geri_kalan) > 0:
            secilen_filmler.extend(geri_kalan.sample(min(kalan, len(geri_kalan))).to_dict('records'))
    st.session_state.rastgele_filmler = secilen_filmler

if not st.session_state.rastgele_filmler:
    yenile()

if st.session_state.analiz_modu:
    secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    secilen_turler = set(t for g in secilen_df['genres'].dropna() for t in g.split('|'))
    imdb_avg = secilen_df['IMDb_Rating'].mean()
    runtime_avg = secilen_df['Runtime'].mean()
    adaylar = df[~df['title'].isin(st.session_state.secilen_listesi)].copy()

    def benzerlik(film):
        turler = set(str(film['genres']).split('|'))
        tur_skor = len(secilen_turler.intersection(turler)) / max(len(secilen_turler),1)
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
    secilen_tur = pd.Series([t for g in secilen_df['genres'].dropna() for t in g.split('|')]).value_counts().idxmax()
    st.markdown(f'<div style="font-size:18px; font-weight:bold; background:rgba(255,0,0,0.6); color:white; padding:4px; border-radius:6px; width:fit-content;">Favori Tür: {secilen_tur}</div>', unsafe_allow_html=True)

    cols = st.columns(5, gap="small")
    for i, f in enumerate(adaylar.to_dict('records')):
        with cols[i%5]:
            poster_url = get_single_poster(f['imdbId'])
            if st.button(" ", key=f"btn_{f['movieId']}", help=f"Seç: {f['title']}"):
                st.session_state.secilen_listesi.append(f['title'])
            st.markdown(f'<div class="poster-container"><img src="{poster_url}" width="200"></div>', unsafe_allow_html=True)
            st.markdown(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | {f['Tavsiye Durumu']}")

    st.header("📊 Sinema Kimliğiniz")
    t_c = pd.Series([t for g in secilen_df['genres'].dropna() for t in g.split('|')]).value_counts().reset_index()
    t_c.columns = ['Tür', 'Adet']
    fig = px.pie(t_c, values='Adet', names='Tür', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig, use_container_width=True)

else:
    tab1, tab2 = st.tabs(["🎯 Film Seçimi", "📊 Profilim"])
    with tab1:
        def ekle_film(film_adi):
            if film_adi not in st.session_state.secilen_listesi:
                st.session_state.secilen_listesi.append(film_adi)
                yenile()

        m_secim = st.multiselect(
            "Film Ara ve Ekle:",
            options=temp_df['title'].tolist(),
            default=[],
            key="m_secim"
        )
        for f in m_secim:
            ekle_film(f)

        if st.button("🔄 Önerileri Yenile", use_container_width=True):
            yenile()

        cols = st.columns(5, gap="small")
        for i, f in enumerate(st.session_state.rastgele_filmler):
            with cols[i % 5]:
                poster_url = get_single_poster(f['imdbId'])
                if st.button(" ", key=f"poster_btn_{f['movieId']}", help=f"Seç: {f['title']}"):
                    ekle_film(f['title'])
                st.markdown(f'<div class="poster-container"><img src="{poster_url}" width="200"></div>', unsafe_allow_html=True)
                st.markdown(f"**{f['title']}**")
                st.caption(f"⭐ {f['IMDb_Rating']} | {f['Runtime']} dk")
