import streamlit as st
import pandas as pd
import plotly.express as px

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Aşı Reddi Analiz Dashboard",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERİ YÜKLEME VE TEMİZLEME ---
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, low_memory=False)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Sütun isimlerini büyük harfe çevir ve boşlukları temizle
        df.columns = df.columns.str.strip().str.replace('i', 'İ').str.upper()
        
        if 'İTİRAZ NEDENİ' in df.columns:
            df['İTİRAZ NEDENİ'] = df['İTİRAZ NEDENİ'].fillna('Belirtilmemiş')
            
        return df
    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        return None

# --- YARDIMCI ANALİZ FONKSİYONLARI ---
def calculate_metrics(df):
    total_records = len(df)
    tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
    unique_children = df[tc_col].nunique() if tc_col in df.columns else total_records
    return total_records, unique_children

def get_reason_stats(df):
    if 'İTİRAZ NEDENİ' not in df.columns:
        return pd.DataFrame()
    reason_counts = df['İTİRAZ NEDENİ'].value_counts().reset_index()
    reason_counts.columns = ['İtiraz Nedeni', 'Frekans']
    total = reason_counts['Frekans'].sum()
    reason_counts['Yüzde Oranı (%)'] = (reason_counts['Frekans'] / total * 100).round(2)
    return reason_counts

def get_vaccine_dose_stats(df):
    # Olası tüm aşı sütun isimleri
    possible_vaccines = [
        'DABT-İPA-HİB-HEP-B', 'HEP B', 'BCG', 'KKK', 
        'HEP A', 'KPA', 'OPA', 'SU ÇİÇEĞİ', 'DABT-İPA', 'TD'
    ]
    
    # Sadece verisetinde gerçekten var olan aşı sütunlarını al
    existing_vaccines = [col for col in possible_vaccines if col in df.columns]
    
    # Veriyi 'Aşı Türü' ve 'Doz' bazında satırlara erit (melt)
    melted = df.melt(value_vars=existing_vaccines, var_name='Aşı Türü', value_name='Doz Değeri')
    
    # Boş hücreleri ve hatalı verileri at
    melted['Doz Değeri'] = pd.to_numeric(melted['Doz Değeri'], errors='coerce')
    melted = melted.dropna(subset=['Doz Değeri'])
    
    # Doz değeri 0'dan büyük olanları (geçerli doz rakamlarını) filtrele
    melted = melted[melted['Doz Değeri'] > 0]
    
    # "KKK (7. Doz)" formatında birleştirilmiş yeni sütun yarat
    melted['Aşı ve Doz'] = melted['Aşı Türü'] + " (" + melted['Doz Değeri'].astype(int).astype(str) + ". Doz)"
    
    # Frekansları say
    stats = melted['Aşı ve Doz'].value_counts().reset_index()
    stats.columns = ['Aşı ve Doz', 'Frekans']
    
    # Yüzde hesapla
    total_doses = stats['Frekans'].sum()
    if total_doses > 0:
        stats['Yüzde Oranı (%)'] = (stats['Frekans'] / total_doses * 100).round(2)
    else:
        stats['Yüzde Oranı (%)'] = 0.0
        
    # En çok reddedilenden en aza sırala
    stats = stats.sort_values(by='Frekans', ascending=False)
    
    return stats, total_doses

# --- ANA UYGULAMA ---
def main():
    st.title("💉 İlçe Sağlık - Aşı Reddi Analiz Dashboard")
    st.markdown("Yüklediğiniz veriler üzerinden ilçelere, red nedenlerine ve spesifik aşı dozlarına göre dağılımları inceleyebilirsiniz.")
    
    # Sidebar
    st.sidebar.header("📁 Veri Yükleme")
    uploaded_file = st.sidebar.file_uploader("Excel veya CSV yükleyin", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is None:
        st.info("👆 Analize başlamak için sol menüden veri setini yükleyin.")
        return
        
    with st.spinner("Veri işleniyor..."):
        df = load_data(uploaded_file)
        
    if df is None or df.empty:
        return

    # Filtreler
    st.sidebar.header("🔍 Filtreler")
    if 'İLÇE ADI' in df.columns:
        ilceler = sorted(df['İLÇE ADI'].dropna().unique().tolist())
        secilen_ilceler = st.sidebar.multiselect("İlçe Seçin (Tümü için boş bırakın):", options=ilceler, default=[])
        df_filtered = df[df['İLÇE ADI'].isin(secilen_ilceler)] if secilen_ilceler else df.copy()
    else:
        df_filtered = df.copy()

    st.sidebar.markdown(f"**Gösterilen Kayıt:** {len(df_filtered)}")

    # 1. Metrikler
    total_records, unique_children = calculate_metrics(df_filtered)
    vaccine_stats, total_refused_doses = get_vaccine_dose_stats(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İtiraz/Kayıt Sayısı", f"{total_records:,}")
    col2.metric("Tekil Çocuk Sayısı", f"{unique_children:,}")
    col3.metric("Toplam Reddedilen Doz", f"{total_refused_doses:,}")
    st.divider()

    # 2. GRAFİKLER BÖLÜMÜ
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Aşı ve Doz Bazlı Red Sayıları")
        if not vaccine_stats.empty:
            tab1, tab2 = st.tabs(["Çubuk Grafik", "Özet Tablo"])
            with tab1:
                # Çok fazla doz kombinasyonu olabileceği için yatay (horizontal) grafik daha okunabilir olur
                # İlk 15'i göstermek grafiğin çok uzun olmasını engeller
                top_15_vaccines = vaccine_stats.head(15)
                fig_vac = px.bar(
                    top_15_vaccines, 
                    x='Frekans', 
                    y='Aşı ve Doz',
                    text='Frekans',
                    orientation='h',
                    color='Frekans',
                    color_continuous_scale='Teal',
                    title='En Çok Reddedilen 15 Aşı-Doz Kombinasyonu'
                )
                fig_vac.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
                st.plotly_chart(fig_vac, use_container_width=True)
                
            with tab2:
                st.markdown("##### Tüm Aşı ve Doz Detayları")
                st.dataframe(
                    vaccine_stats.style.format({'Yüzde Oranı (%)': '{:.2f}%'}),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("Seçili veride aşı türü dağılımı bulunamadı.")

    with col_right:
        st.subheader("📋 Aşı Red Nedenleri")
        reason_df = get_reason_stats(df_filtered)
        
        if not reason_df.empty:
            tab3, tab4 = st.tabs(["Pasta Grafik", "Özet Tablo"])
            with tab3:
                fig_reason = px.pie(
                    reason_df, 
                    values='Frekans', 
                    names='İtiraz Nedeni',
                    hole=0.4
                )
                fig_reason.update_traces(textposition='inside', textinfo='percent+label')
                fig_reason.update_layout(height=500)
                st.plotly_chart(fig_reason, use_container_width=True)
            with tab4:
                 st.markdown("##### Red Nedeni Dağılımı")
                 st.dataframe(
                     reason_df.style.format({'Yüzde Oranı (%)': '{:.2f}%'}),
                     use_container_width=True,
                     hide_index=True
                 )
        else:
            st.info("Seçili veride itiraz nedeni bulunamadı.")

    st.divider()

    # 3. İLÇE DAĞILIMI
    if 'İLÇE ADI' in df_filtered.columns:
        st.subheader("📍 İlçelere Göre Red Dağılımı")
        ilce_df = df_filtered['İLÇE ADI'].value_counts().reset_index()
        ilce_df.columns = ['İlçe Adı', 'Kişi Sayısı']
        
        fig_ilce = px.bar(
            ilce_df, x='İlçe Adı', y='Kişi Sayısı', text='Kişi Sayısı',
            color='Kişi Sayısı', color_continuous_scale='Blues'
        )
        fig_ilce.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_ilce, use_container_width=True)

if __name__ == "__main__":
    main()
