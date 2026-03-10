import streamlit as st
import pandas as pd
import requests, zipfile, io
import re
import plotly.express as px

st.set_page_config(page_title="Sinema Profil Analizi", layout="wide", page_icon="🎬")

# --- 1. VERİ YÜKLEME VE DÜZENLEME ---
@st.cache_data
def verileri_yukle():
    url = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df_m = pd.read_csv(z.open('ml-latest-small/movies.csv'))
    df_l = pd.read_csv(z.open('ml-latest-small/links.csv'))
    df_r = pd.read_csv(z.open('ml-latest-small/ratings.csv'))
    
    # İsim Düzeltme: "Matrix, The (1999)" -> "The Matrix (1999)"
    def isim_duzelt(title):
        match = re.search(r'^(.*),\s(The|A|An)\s(\(\d{4}\))$', title)
        if match:
            return f"{match.group(2)} {match.group(1)} {match.group(3)}"
        return title

    df_m['title'] = df_m['title'].apply(isim_duzelt)
    
    df = df_m.merge(df_l[['movieId', 'imdbId']], on='movieId')
    stats = df_r.groupby('movieId').agg({'rating': ['mean', 'count']}).reset_index()
    stats.columns = ['movieId', 'IMDb_Rating', 'Votes']
    df = df.merge(stats, on='movieId')
    
    # Puanı 10 üzerinden yap ve yılı ayıkla
    df['IMDb_Rating'] = (df['IMDb_Rating'] * 2).round(1)
    df['Year'] = df['title'].apply(lambda x: int(re.search(r'\((\d{4})\)', str(x)).group(1)) if re.search(r'\((\d{4})\)', str(x)) else 0)
    return df

df = verileri_yukle()

# --- TÜRKÇE TÜRLER SÖZLÜĞÜ ---
TUR_HARITASI = {
    "Aksiyon": "Action", "Macera": "Adventure", "Animasyon": "Animation",
    "Komedi": "Comedy", "Suç": "Crime", "Dram": "Drama",
    "Fantastik": "Fantasy", "Korku": "Horror", "Gizem": "Mystery",
    "Romantik": "Romance", "Bilim Kurgu": "Sci-Fi", "Gerilim": "Thriller",
    "Müzikal": "Musical", "Savaş": "War", "Belgesel": "Documentary"
}

# --- YENİLEME FONKSİYONU ---
def onerileri_guncelle():
    # Seçilen türlere göre filtrele
    filtre = df['genres'].str.contains('|'.join(st.session_state.ana_türler))
    adaylar = df[filtre & (df['Votes'] > 40)]
    
    if len(adaylar) < 12:
        adaylar = df[df['Votes'] > 50]
        
    st.session_state.rastgele_filmler = adaylar.sample(12).to_dict('records')

# --- 2. KURULUM EKRANI ---
@st.dialog("🎬 Sinema Profilinizi Oluşturun")
def kurulum_ekrani():
    st.write("Aşağıdaki seçeneklerden size uygun olanları **Açık** konuma getirin.")
    
    st.subheader("🌍 Dil Tercihleri")
    dil_listesi = ["İngilizce", "Türkçe", "Almanca", "Rusça", "Korece", "Japonca", "Fransızca", "İspanyolca"]
    secilen_diller = []
    c1, c2 = st.columns(2)
    for i, dil in enumerate(dil_listesi):
        with (c1 if i % 2 == 0 else c2):
            if st.toggle(dil, key=f"lang_{dil}"): secilen_diller.append(dil)
    
    st.write("---")
    st.subheader("🎭 Sevdiğiniz Film Türleri")
    secilen_türler = []
    t_c1, t_c2 = st.columns(2)
    for i, tr_tur in enumerate(TUR_HARITASI.keys()):
        with (t_c1 if i % 2 == 0 else t_c2):
            if st.toggle(tr_tur, key=f"genre_{tr_tur}"):
                secilen_türler.append(TUR_HARITASI[tr_tur])

    if st.button("Seçimleri Kaydet ve Filmlere Geç", type="primary", use_container_width=True):
        if not secilen_türler:
            st.error("Lütfen en az bir tür seçin!")
        else:
            st.session_state.secilen_diller = secilen_diller if secilen_diller else ["Farketmez"]
            st.session_state.ana_türler = secilen_türler
            st.session_state.kurulum_tamam = True
            onerileri_guncelle()
            st.rerun()

# --- 3. DURUM KONTROLÜ ---
if 'kurulum_tamam' not in st.session_state:
    st.session_state.kurulum_tamam = False
if 'secilen_listesi' not in st.session_state:
    st.session_state.secilen_listesi = []
if 'rastgele_filmler' not in st.session_state:
    st.session_state.rastgele_filmler = []

if not st.session_state.kurulum_tamam:
    kurulum_ekrani()
    st.stop()

# --- ANA EKRAN ---
st.title("🎥 Film Seçim Paneli")
st.markdown("### ✨ En çok sevdiğin ve seni yansıtan filmleri listene ekle!")
# Arama Çubuğu (Artık isimler düzgün)
arama_havuzu = df.sort_values('Votes', ascending=False)['title'].tolist()
st.session_state.secilen_listesi = st.multiselect(
    "🔍 Film Ara ve Ekle:",
    options=arama_havuzu,
    default=st.session_state.secilen_listesi,
    placeholder="Örn: The Matrix, Inception..."
)

# Yenileme Alanı
st.write("---")
head_col, btn_col = st.columns([3, 1])
with head_col:
    st.subheader("🎲 Sizin İçin Önerilen Seçenekler")
with btn_col:
    if st.button("🔄 Listeyi Yenile", use_container_width=True):
        onerileri_guncelle()
        st.rerun()

# Kartlar
cols = st.columns(4)
for i, film in enumerate(st.session_state.rastgele_filmler):
    with cols[i % 4]:
        with st.container(border=True):
            st.write(f"**{film['title']}**")
            st.write(f"⭐ {film['IMDb_Rating']} | 📅 {film['Year']}")
            if st.button("Seç ✅", key=f"btn_{film['movieId']}_{i}"):
                if film['title'] not in st.session_state.secilen_listesi:
                    st.session_state.secilen_listesi.append(film['title'])
                    # Seçilenin yerine yenisini koy
                    filtre = df['genres'].str.contains(film['genres'].split('|')[0])
                    yeni = df[filtre & (~df['title'].isin(st.session_state.secilen_listesi))].sample(1).iloc[0].to_dict()
                    st.session_state.rastgele_filmler[i] = yeni
                    st.rerun()

# Sidebar Bilgi Paneli
st.sidebar.title("📊 İlerleme")
count = len(st.session_state.secilen_listesi)
st.sidebar.metric("Seçilen Film", f"{count} / 20")
st.sidebar.progress(min(count/20, 1.0))

if count >= 20:
    st.sidebar.success("Analiz hazır!")
    if st.sidebar.button("🚀 Profilimi Analiz Et", use_container_width=True):
        st.balloons()
        
        secilen_df = df[df['title'].isin(st.session_state.secilen_listesi)]
        tum_turler = []
        for g in secilen_df['genres']: tum_turler.extend(g.split('|'))
        tur_counts = pd.Series(tum_turler).value_counts().reset_index()
        tur_counts.columns = ['Tür', 'Adet']

        st.divider()
        st.header("✨ Sinema Karakteriniz")
        c_left, c_right = st.columns(2)
        
        with c_left:
            fig = px.pie(tur_counts.head(6), values='Adet', names='Tür', hole=0.4, 
                         title="En Çok Tercih Ettiğiniz Türler")
            st.plotly_chart(fig)
            
        with c_right:
            st.info(f"🧐 Siz tam bir **{tur_counts.iloc[0]['Tür']}** hayranısınız!")
            st.write(f"🗓️ İzleme listenizin yaş ortalaması: **{int(secilen_df['Year'].mean())}**")
            st.write(f"🏆 Kalite tercihiniz (Ort. Puan): **{secilen_df['IMDb_Rating'].mean():.1f} / 10**")
else:
    st.sidebar.warning(f"Analiz için {20 - count} film daha seçmelisiniz.")