import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime

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

def onerileri_guncelle():
    aday = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(200)
    st.session_state.rastgele_filmler = aday.sample(min(12, len(aday))).to_dict('records')

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

a_h = df.sort_values(['Votes', 'IMDb_Rating'], ascending=False)['title'].tolist()
secilen_yeni = st.multiselect(
    "🔍 Film Ara ve Seç:", 
    options=a_h, 
    default=st.session_state.secilen_listesi
)

if secilen_yeni != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilen_yeni

st.divider()

col1, col2 = st.columns([3, 1])
col1.subheader("🎲 Hızlı Seçim Önerileri")
if col2.button("🔄 Listeyi Yenile"):
    onerileri_guncelle()
    st.rerun()

cols = st.columns(4)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | 📅 {f['Year']}")
            if st.button("Ekle +", key=f"btn_{i}_{f['title']}", use_container_width=True):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    st.rerun()

st.sidebar.title("📊 İlerleme")
count = len(st.session_state.secilen_listesi)
st.sidebar.metric("Seçilen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    if st.sidebar.button("🚀 Analizi Başlat", use_container_width=True):
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
                    st.write(f"🔹 {row['title']} (⭐{row['IMDb_Rating']})")import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime

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

def onerileri_guncelle():
    aday = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(200)
    st.session_state.rastgele_filmler = aday.sample(min(12, len(aday))).to_dict('records')

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

a_h = df.sort_values(['Votes', 'IMDb_Rating'], ascending=False)['title'].tolist()
secilen_yeni = st.multiselect(
    "🔍 Film Ara ve Seç:", 
    options=a_h, 
    default=st.session_state.secilen_listesi
)

if secilen_yeni != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilen_yeni

st.divider()

col1, col2 = st.columns([3, 1])
col1.subheader("🎲 Hızlı Seçim Önerileri")
if col2.button("🔄 Listeyi Yenile"):
    onerileri_guncelle()
    st.rerun()

cols = st.columns(4)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | 📅 {f['Year']}")
            if st.button("Ekle +", key=f"btn_{i}_{f['title']}", use_container_width=True):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    st.rerun()

st.sidebar.title("📊 İlerleme")
count = len(st.session_state.secilen_listesi)
st.sidebar.metric("Seçilen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    if st.sidebar.button("🚀 Analizi Başlat", use_container_width=True):
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
                    st.write(f"🔹 {row['title']} (⭐{row['IMDb_Rating']})")import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px
from datetime import datetime

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
if 'ana_türler' not in st.session_state: st.session_state.ana_türler = []

def onerileri_guncelle():
    sec_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    if not sec_df.empty:
        m_t = [t for g in sec_df['genres'].dropna() for t in g.split('|')]
        f_t = '|'.join(pd.Series(m_t).value_counts().index[:3].tolist())
    else:
        f_t = '|'.join(st.session_state.ana_türler)
        
    aday = df[df['genres'].str.contains(f_t, na=False) & (~df['title'].isin(st.session_state.secilen_listesi))]
    y_f = (aday['Year'] >= (g_yil - 3)) & (aday['Votes'] >= 5) 
    e_f = (aday['Year'] < (g_yil - 3)) & (aday['Votes'] >= 10)
    aday = aday[(y_f | e_f) & (aday['IMDb_Rating'] >= 4.0)]
    
    if len(aday) < 12:
        aday = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(100)
    st.session_state.rastgele_filmler = aday.sample(min(12, len(aday))).to_dict('records')

st.title("🎥 Sinema Profil Analizi")

if not st.session_state.kurulum_tamam:
    with st.expander("🎬 Başlangıç: Favori Türlerinizi Seçin", expanded=True):
        s_t = []
        c1, c2 = st.columns(2)
        for i, (tr, en) in enumerate(TUR_HARITASI.items()):
            with (c1 if i % 2 == 0 else c2):
                if st.toggle(tr, key=f"t_{en}"): s_t.append(en)
        if st.button("Uygulamaya Git", use_container_width=True):
            if s_t:
                st.session_state.ana_türler, st.session_state.kurulum_tamam = s_t, True
                onerileri_guncelle()
                st.rerun()
            else:
                st.error("Lütfen en az bir tür seçin!")
    st.stop()

a_h = df.sort_values(['Votes', 'IMDb_Rating'], ascending=False)['title'].tolist()
secilen = st.multiselect("🔍 Film Ara (Yerli filmler Türkçe isimleriyle eklenmiştir):", options=a_h, default=st.session_state.secilen_listesi)

if secilen != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilen
    onerileri_guncelle()
    st.rerun()

st.divider()
col1, col2 = st.columns([3, 1])
col1.subheader("🎲 Senin İçin Seçtiklerimiz")
if col2.button("🔄 Önerileri Yenile"):
    onerileri_guncelle()
    st.rerun()

cols = st.columns(4)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | 📅 {f['Year']}")
            if st.button("Seç ✅", key=f"s_{i}_{f['title']}", use_container_width=True):
                if f['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(f['title'])
                    onerileri_guncelle()
                    st.rerun()

st.sidebar.title("📊 Profil İlerlemesi")
count = len(st.session_state.secilen_listesi)
st.sidebar.metric("Eklenen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    if st.sidebar.button("🚀 Profilimi Analiz Et", use_container_width=True):
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


