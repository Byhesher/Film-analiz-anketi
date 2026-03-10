import streamlit as st
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
