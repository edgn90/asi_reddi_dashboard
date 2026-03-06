import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Aşı Reddi Analiz Dashboard",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VERİ YÜKLEME VE TEMİZLEME (Önbellekli Fonksiyon) ---
@st.cache_data
def load_data(uploaded_file):
    try:
        # Dosya uzantısına göre oku
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, low_memory=False)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Temel veri temizliği: Boşlukları sil ve sütun isimlerini standartlaştır
        df.columns = df.columns.str.strip().str.upper()
        
        # 'İTİRAZ NEDENİ' sütunundaki eksik verileri 'Belirtilmemiş' olarak doldur
        if 'İTİRAZ NEDENİ' in df.columns:
            df['İTİRAZ NEDENİ'] = df['İTİRAZ NEDENİ'].fillna('Belirtilmemiş')
            
        return df
    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        return None

# --- YARDIMCI ANALİZ FONKSİYONLARI ---
def calculate_metrics(df):
    """Temel KPI metriklerini hesaplar."""
    # Toplam kayıt (satır) sayısı
    total_records = len(df)
    
    # TC Kimlik No üzerinden tekil çocuk sayısını bulma (Eğer sütun varsa)
    tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
    if tc_col in df.columns:
        unique_children = df[tc_col].nunique()
    else:
        unique_children = total_records # TC yoksa satır sayısını baz al
        
    # Aşı Reddi olanlar (İtiraz Nedeni boş olmayan veya belirli bir filtreye uyanlar)
    # Bu veri seti özelinde her satır bir itiraz/red kaydı olarak varsayılmıştır.
    total_refusals = total_records
    
    return total_records, unique_children, total_refusals

def get_reason_stats(df):
    """İtiraz/Red nedenlerinin frekans ve yüzde oranlarını hesaplar."""
    if 'İTİRAZ NEDENİ' not in df.columns:
        return pd.DataFrame()
        
    reason_counts = df['İTİRAZ NEDENİ'].value_counts().reset_index()
    reason_counts.columns = ['İtiraz Nedeni', 'Frekans']
    
    # Yüzde hesaplama
    total = reason_counts['Frekans'].sum()
    reason_counts['Yüzde Oranı (%)'] = (reason_counts['Frekans'] / total * 100).round(2)
    
    return reason_counts

# --- ANA UYGULAMA ---
def main():
    st.title("💉 İlçe Sağlık - Aşı Reddi Analiz Dashboard")
    st.markdown("Bu uygulama, yüklediğiniz veriler üzerinden ilçelere ve red nedenlerine göre aşı reddi analizleri sunar.")
    
    # Sidebar - Dosya Yükleme Alanı
    st.sidebar.header("📁 Veri Yükleme")
    uploaded_file = st.sidebar.file_uploader(
        "Lütfen Excel veya CSV dosyanızı yükleyin", 
        type=["csv", "xlsx", "xls"]
    )
    
    if uploaded_file is None:
        st.info("👆 Analize başlamak için sol menüden bir veri seti yükleyin.")
        return
        
    # Veriyi Yükle
    with st.spinner("Veri yükleniyor ve temizleniyor..."):
        df = load_data(uploaded_file)
        
    if df is None or df.empty:
        st.warning("Yüklenen dosya boş veya okunamadı.")
        return

    # Sidebar - Filtreleme Alanı
    st.sidebar.header("🔍 Filtreler")
    
    # İlçe Filtresi
    if 'İLÇE ADI' in df.columns:
        ilceler = sorted(df['İLÇE ADI'].dropna().unique().tolist())
        secilen_ilceler = st.sidebar.multiselect(
            "İlçe Seçin (Tümü için boş bırakın):", 
            options=ilceler, 
            default=[]
        )
        
        # Filtreyi uygula
        if secilen_ilceler:
            df_filtered = df[df['İLÇE ADI'].isin(secilen_ilceler)]
        else:
            df_filtered = df.copy()
    else:
        st.sidebar.warning("Verisetinde 'İLÇE ADI' sütunu bulunamadı.")
        df_filtered = df.copy()

    st.sidebar.divider()
    st.sidebar.markdown(f"**Gösterilen Kayıt:** {len(df_filtered)}")

    # --- 1. METRİKLER (ÖZET KARTLARI) ---
    total_records, unique_children, total_refusals = calculate_metrics(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İşlem (Satır) Sayısı", f"{total_records:,}")
    col2.metric("Tekil Çocuk Sayısı", f"{unique_children:,}")
    col3.metric("Toplam Aşı Reddi", f"{total_refusals:,}")
    
    st.divider()

    # --- 2. GRAFİKLER ---
    # Eğer İtiraz Nedeni sütunu varsa grafikleri çiz
    if 'İTİRAZ NEDENİ' in df_filtered.columns:
        st.subheader("📊 Aşı Reddi Nedenleri Analizi")
        reason_stats_df = get_reason_stats(df_filtered)
        
        tab1, tab2, tab3 = st.tabs(["Çubuk Grafik (Bar Chart)", "Pasta Grafik (Pie Chart)", "Özet Tablo"])
        
        with tab1:
            fig_bar = px.bar(
                reason_stats_df, 
                x='Frekans', 
                y='İtiraz Nedeni', 
                orientation='h',
                title="Red Nedenlerine Göre Dağılım",
                text='Frekans',
                color='Frekans',
                color_continuous_scale='Reds'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with tab2:
            fig_pie = px.pie(
                reason_stats_df, 
                values='Frekans', 
                names='İtiraz Nedeni',
                title="Red Nedenleri Yüzdelik Dağılımı",
                hole=0.4 # Donut chart görünümü için
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with tab3:
            st.markdown("##### Frekans ve Yüzde Oranları Tablosu")
            st.dataframe(
                reason_stats_df.style.format({'Yüzde Oranı (%)': '{:.2f}%'}),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("Verisetinde analiz için 'İTİRAZ NEDENİ' sütunu bulunamadı.")

    st.divider()

    # --- 3. İLÇE BAZLI DAĞILIM ---
    if 'İLÇE ADI' in df_filtered.columns:
        st.subheader("📍 İlçelere Göre Çocuk (İtiraz) Sayısı Dağılımı")
        
        ilce_dagilimi = df_filtered['İLÇE ADI'].value_counts().reset_index()
        ilce_dagilimi.columns = ['İlçe Adı', 'Kişi Sayısı']
        
        fig_ilce = px.bar(
            ilce_dagilimi,
            x='İlçe Adı',
            y='Kişi Sayısı',
            text='Kişi Sayısı',
            title="İlçelere Göre Reddedilen Aşı Sayıları",
            color='Kişi Sayısı',
            color_continuous_scale='Blues'
        )
        fig_ilce.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_ilce, use_container_width=True)
        
    # --- 4. HAM VERİ GÖSTERİMİ (Opsiyonel) ---
    with st.expander("Ham Veriyi Görüntüle"):
        st.dataframe(df_filtered.head(100), use_container_width=True)

if __name__ == "__main__":
    main()
