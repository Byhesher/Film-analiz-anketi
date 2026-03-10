import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime
import random

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

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
                    'Year': int(m['release_date'][:4]) if m.get('release_date') else 0
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
if 'karisik_liste' not in st.session_state:
    l = df['title'].tolist()
    random.shuffle(l)
    st.session_state.karisik_liste = l

def onerileri_guncelle():
    aday = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(300)
    st.session_state.rastgele_filmler = aday.sample(min(20, len(aday))).to_dict('records')

st.title("🎥 Sinema Profil Analizi")

if not st.session_state.kurulum_tamam:
    with st.expander("🎬 Başlangıç: Tür Seçimi", expanded=True):
        s_t = []
        c1, c2 = st.columns(2)
        for i, (tr, en) in enumerate(TUR_HARITASI.items()):
            with (c1 if i % 2 == 0 else c2):
                if st.toggle(tr, key=f"t_{en}"): s_t.append(en)
        if st.button("Devam Et", use_container_width=True):
            if s_t:
                st.session_state.kurulum_tamam = True
                onerileri_guncelle()
                st.rerun()
    st.stop()

st.subheader("🔍 Manuel Film Arama")
manuel_secim = st.multiselect("Film ismini buraya yazarak aratın (Yerli ve yabancı filmler karışıktır):", options=st.session_state.karisik_liste)
if st.button("Seçilenleri Listeye Ekle", use_container_width=True):
    if manuel_secim:
        for m in manuel_secim:
            if m not in st.session_state.secilen_listesi:
                st.session_state.secilen_listesi.append(m)
        onerileri_guncelle()
        st.rerun()

st.divider()

st.subheader("🎲 Önerilen Popüler Filmler")
st.caption("Aşağıdaki kartlardan hızlıca seçim yapabilirsiniz:")

cols = st.columns(5)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 5]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | 📅 {f['Year']}")
            if st.button("Seç ✅", key=f"btn_{i}_{f['title']}", use_container_width=True):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    onerileri_guncelle()
                    st.rerun()

st.sidebar.title("📊 İlerleme")
count = len(st.session_state.secilen_listesi)
st.sidebar.metric("Seçilen", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))
st.sidebar.write("### Son Eklenenler:")
for s in st.session_state.secilen_listesi[-10:]:
    st.sidebar.caption(f"• {s}")

if count >= 20:
    if st.sidebar.button("🚀 Analizi Çalıştır", use_container_width=True):
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
else:
    st.sidebar.info(f"Analiz için {20 - count} film daha seçmelisiniz.")
