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
        
        # Sütun isimlerini standartlaştır
        df.columns = df.columns.str.strip().str.replace('i', 'İ').str.upper()
        
        # Boşluk doldurma
        if 'İTİRAZ NEDENİ' in df.columns:
            df['İTİRAZ NEDENİ'] = df['İTİRAZ NEDENİ'].fillna('Belirtilmemiş')
            
        # Tarih sütununu datetime formatına çevir (Trend analizi için)
        if 'KAYIT TARİHİ' in df.columns:
            df['KAYIT TARİHİ'] = pd.to_datetime(df['KAYIT TARİHİ'], errors='coerce', dayfirst=True)
            
        return df
    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        return None

# --- YARDIMCI FONKSİYONLAR ---
def calculate_metrics(df):
    total_records = len(df)
    tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
    unique_children = df[tc_col].nunique() if tc_col in df.columns else total_records
    return total_records, unique_children

def get_vaccine_dose_stats(df):
    possible_vaccines = [
        'DABT-İPA-HİB-HEP-B', 'HEP B', 'BCG', 'KKK', 
        'HEP A', 'KPA', 'OPA', 'SU ÇİÇEĞİ', 'DABT-İPA', 'TD'
    ]
    existing_vaccines = [col for col in possible_vaccines if col in df.columns]
    melted = df.melt(value_vars=existing_vaccines, var_name='Aşı Türü', value_name='Doz Değeri')
    melted['Doz Değeri'] = pd.to_numeric(melted['Doz Değeri'], errors='coerce')
    melted = melted.dropna(subset=['Doz Değeri'])
    melted = melted[melted['Doz Değeri'] > 0]
    
    melted['Aşı ve Doz'] = melted['Aşı Türü'] + " (" + melted['Doz Değeri'].astype(int).astype(str) + ". Doz)"
    stats = melted['Aşı ve Doz'].value_counts().reset_index()
    stats.columns = ['Aşı ve Doz', 'Frekans']
    
    total_doses = stats['Frekans'].sum()
    stats['Yüzde Oranı (%)'] = (stats['Frekans'] / total_doses * 100).round(2) if total_doses > 0 else 0.0
    return stats.sort_values(by='Frekans', ascending=False), total_doses

def get_reason_stats(df):
    if 'İTİRAZ NEDENİ' not in df.columns:
        return pd.DataFrame()
    reason_counts = df['İTİRAZ NEDENİ'].value_counts().reset_index()
    reason_counts.columns = ['İtiraz Nedeni', 'Frekans']
    return reason_counts

# --- ANA UYGULAMA ---
def main():
    st.title("💉 İlçe Sağlık - Aşı Reddi Yönetici Dashboard'u")
    st.markdown("Aşı reddi verilerinizi demografik, zamansal ve kurumsal boyutlarda analiz edin.")
    
    st.sidebar.header("📁 Veri Yükleme")
    uploaded_file = st.sidebar.file_uploader("Excel veya CSV yükleyin", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is None:
        st.info("👆 Lütfen sol menüden veri setini yükleyin.")
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

    # 1. TEMEL METRİKLER (KPI)
    total_records, unique_children = calculate_metrics(df_filtered)
    vaccine_stats, total_refused_doses = get_vaccine_dose_stats(df_filtered)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam İtiraz/Kayıt", f"{total_records:,}")
    col2.metric("Tekil Çocuk Sayısı", f"{unique_children:,}")
    col3.metric("Reddedilen Toplam Doz", f"{total_refused_doses:,}")
    
    # ASM sayısını bulma (eğer sütun varsa)
    asm_count = df_filtered['ASM ADI'].nunique() if 'ASM ADI' in df_filtered.columns else 0
    col4.metric("Etkilenen ASM Sayısı", f"{asm_count:,}")
    st.divider()

    # --- YENİ: ZAMAN İÇİNDE EĞİLİM VE ASM ANALİZİ ---
    st.subheader("📈 Zaman İçinde Red Eğilimi ve ASM Dağılımı")
    col_trend, col_asm = st.columns(2)
    
    with col_trend:
        if 'KAYIT TARİHİ' in df_filtered.columns:
            # Gün bazında kayıt sayısı
            trend_df = df_filtered.groupby(df_filtered['KAYIT TARİHİ'].dt.date).size().reset_index(name='Kayıt Sayısı')
            if not trend_df.empty:
                fig_trend = px.line(
                    trend_df, x='KAYIT TARİHİ', y='Kayıt Sayısı', 
                    title="Günlere Göre Aşı Reddi Sayıları",
                    markers=True
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Tarih formatı grafiğe uygun değil.")
                
    with col_asm:
        if 'ASM ADI' in df_filtered.columns:
            # En çok red alan ilk 10 ASM
            top_asms = df_filtered['ASM ADI'].value_counts().head(10).reset_index()
            top_asms.columns = ['ASM Adı', 'Vaka Sayısı']
            fig_asm = px.bar(
                top_asms, x='Vaka Sayısı', y='ASM Adı', orientation='h',
                title="En Çok Red Görülen İlk 10 ASM", text='Vaka Sayısı',
                color='Vaka Sayısı', color_continuous_scale='Reds'
            )
            fig_asm.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_asm, use_container_width=True)

    st.divider()

    # --- AŞI DOZ VE NEDEN ANALİZİ (Önceki başarılı grafikler) ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Aşı ve Doz Bazlı Red Sayıları")
        if not vaccine_stats.empty:
            top_15_vaccines = vaccine_stats.head(15)
            fig_vac = px.bar(
                top_15_vaccines, x='Frekans', y='Aşı ve Doz', text='Frekans',
                orientation='h', color='Frekans', color_continuous_scale='Teal',
                title='En Çok Reddedilen 15 Aşı-Doz Kombinasyonu'
            )
            fig_vac.update_layout(yaxis={'categoryorder':'total ascending'}, height=450)
            st.plotly_chart(fig_vac, use_container_width=True)

    with col_right:
        st.subheader("📋 Aşı Red Nedenleri")
        reason_df = get_reason_stats(df_filtered)
        if not reason_df.empty:
            fig_reason = px.pie(
                reason_df, values='Frekans', names='İtiraz Nedeni', hole=0.4,
                title='İtiraz Nedenleri Dağılımı'
            )
            fig_reason.update_traces(textposition='inside', textinfo='percent+label')
            fig_reason.update_layout(height=450)
            st.plotly_chart(fig_reason, use_container_width=True)

    st.divider()

    # --- YENİ: CİNSİYET VE KARAR DAĞILIMI ---
    st.subheader("👥 Demografi ve İlçe Karar Durumu")
    col_gender, col_decision = st.columns(2)
    
    with col_gender:
        cinsiyet_col = 'İTİRAZ KONUSU KİŞİNİN CİNSİYETİ'
        if cinsiyet_col in df_filtered.columns:
            cinsiyet_df = df_filtered[cinsiyet_col].value_counts().reset_index()
            cinsiyet_df.columns = ['Cinsiyet', 'Kişi Sayısı']
            fig_gender = px.pie(
                cinsiyet_df, values='Kişi Sayısı', names='Cinsiyet',
                color='Cinsiyet', color_discrete_map={'Erkek': '#636EFA', 'Kız': '#EF553B', 'Kadın': '#EF553B'},
                title="Cinsiyet Dağılımı"
            )
            st.plotly_chart(fig_gender, use_container_width=True)

    with col_decision:
        karar_col = 'İLÇE - KARAR'
        if karar_col in df_filtered.columns:
            karar_df = df_filtered[karar_col].value_counts().reset_index()
            karar_df.columns = ['Karar', 'Sayı']
            fig_decision = px.bar(
                karar_df, x='Karar', y='Sayı', text='Sayı',
                title="İlçe Sağlık Müdürlüğü Karar Sonuçları",
                color='Karar', color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_decision, use_container_width=True)

if __name__ == "__main__":
    main()
