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
    for page in range(1, 101):
        tr_url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&with_original_language=tr&page={page}&sort_by=vote_count.desc"
        try:
            data = requests.get(tr_url).json().get('results', [])
            for m in data:
                tr_films.append({
                    'title': f"{m['title']} ({m['release_date'][:4]})" if m.get('release_date') else m['title'],
                    'genres': 'Drama|Comedy',
                    'IMDb_Rating': m['vote_average'],
                    'Votes': m['vote_count'],
                    'Year': int(m['release_date'][:4]) if m.get('release_date') else 0
                })
        except: break
        if len(tr_films) >= 2000: break

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

def onerileri_guncelle():
    sec_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    if not sec_df.empty:
        m_t = [t for g in sec_df['genres'].dropna() for t in g.split('|')]
        f_t = '|'.join(pd.Series(m_t).value_counts().index[:3].tolist())
    else:
        f_t = '|'.join(st.session_state.ana_türler)
        
    aday = df[df['genres'].str.contains(f_t, na=False) & (~df['title'].isin(st.session_state.secilen_listesi))]
    y_f = (aday['Year'] >= (g_yil - 3)) & (aday['Votes'] >= 10) 
    e_f = (aday['Year'] < (g_yil - 3)) & (aday['Votes'] >= 20)
    aday = aday[(y_f | e_f) & (aday['IMDb_Rating'] >= 5.0)]
    
    if len(aday) < 12:
        aday = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(100)
    st.session_state.rastgele_filmler = aday.sample(min(12, len(aday))).to_dict('records')

@st.dialog("🎬 Kurulum")
def kurulum_ekrani():
    s_t = []
    c1, c2 = st.columns(2)
    for i, (tr, en) in enumerate(TUR_HARITASI.items()):
        with (c1 if i % 2 == 0 else c2):
            if st.toggle(tr, key=f"t_{en}"): s_t.append(en)
    if st.button("Uygulamaya Git", use_container_width=True):
        if s_t:
            st.session_state.ana_türler, st.session_state.kurulum_tamam = s_t, True
            onerileri_guncelle(); st.rerun()

if 'kurulum_tamam' not in st.session_state: st.session_state.kurulum_tamam = False
if 'secilen_listesi' not in st.session_state: st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state: st.session_state.rastgele_filmler = []

if not st.session_state.kurulum_tamam:
    kurulum_ekrani(); st.stop()

st.title("🎥 Sinema Profil Analizi")
a_h = df.sort_values(['Votes', 'IMDb_Rating'], ascending=False)['title'].tolist()
secilen = st.multiselect("🔍 Film Ara:", options=a_h, default=st.session_state.secilen_listesi)

if secilen != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilen
    onerileri_guncelle(); st.rerun()

st.divider()
col1, col2 = st.columns([3, 1])
col1.subheader("🎲 Öneriler")
if col2.button("🔄 Yenile"):
    onerileri_guncelle(); st.rerun()

cols = st.columns(4)
for i, f in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{f['title']}**")
            st.caption(f"⭐ {f['IMDb_Rating']} | 📅 {f['Year']}")
            if st.button("Seç ✅", key=f"s_{i}_{f['title']}", use_container_width=True):
                st.session_state.secilen_listesi.append(f['title'])
                onerileri_guncelle(); st.rerun()

st.sidebar.title("📊 İlerleme")
cnt = len(st.session_state.secilen_listesi)
st.sidebar.metric("Film Sayısı", f"{cnt} / 20")
st.sidebar.progress(min(cnt/20, 1.0))

if cnt >= 20:
    if st.sidebar.button("🚀 Analiz Et", use_container_width=True):
        s_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        t_c = pd.Series([t for g in s_df['genres'].dropna() for t in g.split('|')]).value_counts().reset_index()
        t_c.columns = ['Tür', 'Adet']
        st.header("✨ Sinema Kimliğiniz")
        l, r = st.columns(2)
        l.plotly_chart(px.pie(t_c.head(6), values='Adet', names='Tür', hole=0.4), use_container_width=True)
        r.success(f"Baskın Tür: {t_c.iloc[0]['Tür']}")
        st.divider()
        st.subheader("🍿 Özel Öneriler")
        t_cols = st.columns(3)
        for i, tur in enumerate(t_c.head(3)['Tür'].tolist()):
            with t_cols[i]:
                st.markdown(f"#### 🎭 {tur}")
                t_a = df[df['genres'].str.contains(tur, na=False) & (~df['title'].isin(st.session_state.secilen_listesi))]
                res = t_a[((t_a['Year'] >= g_yil-3) & (t_a['Votes'] >= 10)) | ((t_a['Year'] < g_yil-3) & (t_a['Votes'] >= 20))]
                for _, row in res[res['IMDb_Rating'] >= 5.0].sort_values(['IMDb_Rating', 'Votes'], ascending=False).head(3).iterrows():
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
    return df

df = verileri_yukle()
guncel_yil = datetime.now().year

TUR_HARITASI = {
    "Aksiyon": "Action", "Macera": "Adventure", "Animasyon": "Animation",
    "Komedi": "Comedy", "Suç": "Crime", "Dram": "Drama",
    "Fantastik": "Fantasy", "Korku": "Horror", "Gizem": "Mystery",
    "Romantik": "Romance", "Bilim Kurgu": "Sci-Fi", "Gerilim": "Thriller",
    "Müzikal": "Musical", "Savaş": "War", "Belgesel": "Documentary"
}

def onerileri_guncelle():
    secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
    if not secilen_df.empty:
        mevcut_turler = [t for g in secilen_df['genres'] for t in g.split('|')]
        en_cok_tur = pd.Series(mevcut_turler).value_counts().index[:3].tolist()
        filtre_turu = '|'.join(en_cok_tur)
    else:
        filtre_turu = '|'.join(st.session_state.ana_türler)
        
    adaylar = df[df['genres'].str.contains(filtre_turu) & (~df['title'].isin(st.session_state.secilen_listesi))]
    
    yeni_filtre = (adaylar['Year'] >= (guncel_yil - 3)) & (adaylar['Votes'] >= 50) 
    eski_filtre = (adaylar['Year'] < (guncel_yil - 3)) & (adaylar['Votes'] >= 100)
    adaylar = adaylar[(yeni_filtre | eski_filtre) & (adaylar['IMDb_Rating'] >= 6.0)]
    
    if len(adaylar) < 12:
        adaylar = df[~df['title'].isin(st.session_state.secilen_listesi)].sort_values('Votes', ascending=False).head(100)
    
    st.session_state.rastgele_filmler = adaylar.sample(min(12, len(adaylar))).to_dict('records')

@st.dialog("🎬 Profilini Oluştur")
def kurulum_ekrani():
    st.write("Başlangıç için sevdiğin türleri seç:")
    secilen_türler = []
    t_c1, t_c2 = st.columns(2)
    for i, (tr, en) in enumerate(TUR_HARITASI.items()):
        with (t_c1 if i % 2 == 0 else t_c2):
            if st.toggle(tr, key=f"g_{en}"): secilen_türler.append(en)

    if st.button("Kaydet ve Başla", type="primary", use_container_width=True):
        if not secilen_türler:
            st.error("En az bir tür seçmelisin!")
        else:
            st.session_state.ana_türler = secilen_türler
            st.session_state.kurulum_tamam = True
            onerileri_guncelle()
            st.rerun()

if 'kurulum_tamam' not in st.session_state: st.session_state.kurulum_tamam = False
if 'secilen_listesi' not in st.session_state: st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state: st.session_state.rastgele_filmler = []

if not st.session_state.kurulum_tamam:
    kurulum_ekrani()
    st.stop()

st.title("🎥 Film Seçim Paneli")

arama_havuzu = df.sort_values('Votes', ascending=False)['title'].tolist()
secilenler = st.multiselect(
    "🔍 Film Ara ve Listene Ekle:", 
    options=arama_havuzu, 
    default=st.session_state.secilen_listesi,
    key="ana_arama_cubugu"
)

if secilenler != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilenler
    onerileri_guncelle()
    st.rerun()

st.divider()
c1, c2 = st.columns([3, 1])
c1.subheader("🎲 Senin İçin Seçtiklerimiz")
if c2.button("🔄 Önerileri Yenile", use_container_width=True):
    onerileri_guncelle()
    st.rerun()

cols = st.columns(4)
for i, film in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{film['title']}**")
            st.caption(f"⭐ {film['IMDb_Rating']} | 📅 {film['Year']}")
            if film['title'] in st.session_state.secilen_listesi:
                onerileri_guncelle()
                st.rerun()
            else:
                if st.button("Seç ✅", key=f"f_{film['movieId']}_{i}", use_container_width=True):
                    st.session_state.secilen_listesi.append(film['title'])
                    onerileri_guncelle()
                    st.rerun()

count = len(st.session_state.secilen_listesi)
st.sidebar.title("📊 İlerleme")
st.sidebar.metric("Seçilen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    st.sidebar.success("Analiz hazır!")
    if st.sidebar.button("🚀 Profilimi Analiz Et", use_container_width=True):
        st.balloons()
        secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        tum_turler = [t for g in secilen_df['genres'] for t in g.split('|')]
        tur_counts = pd.Series(tum_turler).value_counts().reset_index()
        tur_counts.columns = ['Tür', 'Adet']

        st.header("✨ Sinema Karakteriniz")
        cl, cr = st.columns(2)
        with cl:
            st.plotly_chart(px.pie(tur_counts.head(6), values='Adet', names='Tür', hole=0.4), use_container_width=True)
        with cr:
            st.info(f"🧐 Listenize göre en çok **{tur_counts.iloc[0]['Tür']}** filmlerini tercih ediyorsunuz!")
            st.write(f"🏆 Puan ortalaması: **{secilen_df['IMDb_Rating'].mean():.1f}**")

        st.divider()
        st.subheader("🍿 10 Puanlık Seçimlerinize En Yakın Öneriler")
        
        en_cok_3_tur = tur_counts.head(3)['Tür'].tolist()
        t_cols = st.columns(3)
        
        for i, tur in enumerate(en_cok_3_tur):
            with t_cols[i]:
                st.markdown(f"#### 🎭 {tur}")
                tavsiye_adaylari = df[df['genres'].str.contains(tur) & (~df['title'].isin(st.session_state.secilen_listesi))]
                
                f1 = (tavsiye_adaylari['Year'] >= (guncel_yil - 3)) & (tavsiye_adaylari['Votes'] >= 50)
                f2 = (tavsiye_adaylari['Year'] < (guncel_yil - 3)) & (tavsiye_adaylari['Votes'] >= 100)
                
                final_tavsiye = tavsiye_adaylari[(f1 | f2) & (tavsiye_adaylari['IMDb_Rating'] >= 6.0)]
                final_tavsiye = final_tavsiye.sort_values(['IMDb_Rating', 'Votes'], ascending=False).head(3)
                
                for _, row in final_tavsiye.iterrows():
                    st.write(f"🔹 {row['title']} (⭐{row['IMDb_Rating']})")
else:
    st.sidebar.warning(f"Analiz için {20 - count} film daha lazım.")import streamlit as st
import pandas as pd
import requests, zipfile, io, re
import plotly.express as px

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
    return df

df = verileri_yukle()

TUR_HARITASI = {
    "Aksiyon": "Action", "Macera": "Adventure", "Animasyon": "Animation",
    "Komedi": "Comedy", "Suç": "Crime", "Dram": "Drama",
    "Fantastik": "Fantasy", "Korku": "Horror", "Gizem": "Mystery",
    "Romantik": "Romance", "Bilim Kurgu": "Sci-Fi", "Gerilim": "Thriller",
    "Müzikal": "Musical", "Savaş": "War", "Belgesel": "Documentary"
}

def onerileri_guncelle():
    filtre = df['genres'].str.contains('|'.join(st.session_state.ana_türler))
    adaylar = df[filtre & (df['Votes'] > 40)]
    if len(adaylar) < 12: adaylar = df[df['Votes'] > 50]
    st.session_state.rastgele_filmler = adaylar.sample(12).to_dict('records')

@st.dialog("🎬 Profilini Oluştur")
def kurulum_ekrani():
    st.write("Film zevkini belirlemek için türleri seç:")
    secilen_türler = []
    t_c1, t_c2 = st.columns(2)
    for i, (tr, en) in enumerate(TUR_HARITASI.items()):
        with (t_c1 if i % 2 == 0 else t_c2):
            if st.toggle(tr, key=f"g_{en}"): secilen_türler.append(en)

    if st.button("Kaydet ve Başla", type="primary", use_container_width=True):
        if not secilen_türler:
            st.error("En az bir tür seçmelisin!")
        else:
            st.session_state.ana_türler = secilen_türler
            st.session_state.kurulum_tamam = True
            onerileri_guncelle()
            st.rerun()

if 'kurulum_tamam' not in st.session_state: st.session_state.kurulum_tamam = False
if 'secilen_listesi' not in st.session_state: st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state: st.session_state.rastgele_filmler = []

if not st.session_state.kurulum_tamam:
    kurulum_ekrani()
    st.stop()

st.title("🎥 Film Seçim Paneli")
st.markdown("### ✨ Favori filmlerini listene ekle!")

arama_havuzu = df.sort_values('Votes', ascending=False)['title'].tolist()

secilenler = st.multiselect(
    "🔍 Film Ara ve Listene Ekle:", 
    options=arama_havuzu, 
    default=st.session_state.secilen_listesi,
    key="ana_arama_cubugu",
    placeholder="Film ismi yazın..."
)

if secilenler != st.session_state.secilen_listesi:
    st.session_state.secilen_listesi = secilenler
    st.rerun()

st.divider()
c1, c2 = st.columns([3, 1])
c1.subheader("🎲 Önerilen Seçenekler")
if c2.button("🔄 Listeyi Yenile", use_container_width=True):
    onerileri_guncelle()
    st.rerun()

cols = st.columns(4)
for i, film in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{film['title']}**")
            st.caption(f"⭐ {film['IMDb_Rating']} | 📅 {film['Year']}")
            if film['title'] in st.session_state.secilen_listesi:
                st.button("Eklendi ✅", key=f"f_{film['movieId']}", disabled=True, use_container_width=True)
            else:
                if st.button("Seç ✅", key=f"f_{film['movieId']}", use_container_width=True):
                    st.session_state.secilen_listesi.append(film['title'])
                    ana_tur = film['genres'].split('|')[0]
                    yeni = df[df['genres'].str.contains(ana_tur) & (~df['title'].isin(st.session_state.secilen_listesi))].sample(1).iloc[0].to_dict()
                    st.session_state.rastgele_filmler[i] = yeni
                    st.rerun()

count = len(st.session_state.secilen_listesi)
st.sidebar.title("📊 İlerleme")
st.sidebar.metric("Seçilen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    st.sidebar.success("Analiz hazır!")
    if st.sidebar.button("🚀 Profilimi Analiz Et", use_container_width=True):
        st.balloons()
        secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        tum_turler = [t for g in secilen_df['genres'] for t in g.split('|')]
        tur_counts = pd.Series(tum_turler).value_counts().reset_index()
        tur_counts.columns = ['Tür', 'Adet']

        st.header("✨ Sinema Karakteriniz")
        cl, cr = st.columns(2)
        with cl:
            st.plotly_chart(px.pie(tur_counts.head(6), values='Adet', names='Tür', hole=0.4), use_container_width=True)
        with cr:
            st.info(f"🧐 Siz tam bir **{tur_counts.iloc[0]['Tür']}** hayranısınız!")
            st.write(f"🗓️ Yaş ortalaması: **{int(secilen_df['Year'].mean())}**")
            st.write(f"🏆 Puan ortalaması: **{secilen_df['IMDb_Rating'].mean():.1f}**")
else:
    st.sidebar.warning(f"Analiz için {20 - count} film daha lazım.")


