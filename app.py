import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Aşı ve İzlem Reddi Dashboard", layout="wide", page_icon="📊")

@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, low_memory=False)
        else:
            df = pd.read_excel(file)
        
        df.columns = df.columns.str.strip().str.replace('i', 'İ').str.upper()
        
        if 'KAYIT TARİHİ' in df.columns:
            df['KAYIT TARİHİ'] = pd.to_datetime(df['KAYIT TARİHİ'], errors='coerce', dayfirst=True)
            
        if 'İTİRAZ NEDENİ' in df.columns:
            df['İTİRAZ NEDENİ'] = df['İTİRAZ NEDENİ'].fillna('Belirtilmemiş')
            
        return df
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

def main():
    st.title("📊 İlçe Sağlık - Kapsamlı Yönetim ve Analiz Platformu")
    
    # --- YAN MENÜ (SIDEBAR) ---
    st.sidebar.header("📁 Veri Yükleme")
    uploaded_file = st.sidebar.file_uploader("Veri Dosyasını Yükleyin", type=['csv', 'xlsx'])
    
    if uploaded_file is None:
        st.info("👆 Analize başlamak için sol menüden veri setini yükleyin.")
        return
        
    with st.spinner("Veri işleniyor ve analiz ediliyor..."):
        df = load_data(uploaded_file)
        
    if df is None or df.empty:
        return

    st.sidebar.header("🔍 Filtreler")
    if 'İLÇE ADI' in df.columns:
        ilceler = sorted(df['İLÇE ADI'].dropna().unique().tolist())
        secilen_ilceler = st.sidebar.multiselect("İlçe Seçin (Tümü için boş bırakın):", options=ilceler, default=[])
        df_filtered = df[df['İLÇE ADI'].isin(secilen_ilceler)] if secilen_ilceler else df.copy()
    else:
        df_filtered = df.copy()

    st.sidebar.markdown(f"**Gösterilen Kayıt:** {len(df_filtered)}")

    # --- ANA SEKMELERİ OLUŞTURMA ---
    tab_dash, tab_analiz = st.tabs(["📊 Karar Destek Dashboard'u", "🔎 Detaylı Veri Seti Analizi"])

    # =========================================================================
    # TAB 1: MEVCUT DASHBOARD (Grafikler ve Metrikler)
    # =========================================================================
    with tab_dash:
        # İzlem ve Aşı Ayrıştırma (Melt)
        izlem_cols = ['GEBE İZLEM', 'LOHUSA İZLEM', 'BEBEK İZLEM', 'ÇOCUK İZLEM']
        asi_cols = ['DABT-İPA-HİB-HEP-B', 'HEP B', 'BCG', 'KKK', 'HEP A', 'KPA', 'OPA', 'SU ÇİÇEĞİ', 'DABT-İPA', 'TD']
        
        mevcut_izlem_cols = [col for col in izlem_cols if col in df_filtered.columns]
        mevcut_asi_cols = [col for col in asi_cols if col in df_filtered.columns]

        df_izlem = df_filtered.melt(value_vars=mevcut_izlem_cols, var_name='İzlem Türü', value_name='Sıra')
        df_izlem['Sıra'] = pd.to_numeric(df_izlem['Sıra'], errors='coerce')
        df_izlem = df_izlem.dropna(subset=['Sıra'])
        df_izlem = df_izlem[df_izlem['Sıra'] > 0]
        df_izlem['İzlem ve Sıra'] = df_izlem['İzlem Türü'] + " (" + df_izlem['Sıra'].astype(int).astype(str) + ". İzlem)"
        izlem_stats = df_izlem['İzlem ve Sıra'].value_counts().reset_index()
        izlem_stats.columns = ['İzlem ve Sıra', 'Frekans']
        toplam_izlem = izlem_stats['Frekans'].sum()

        df_asi = df_filtered.melt(value_vars=mevcut_asi_cols, var_name='Aşı Türü', value_name='Doz')
        df_asi['Doz'] = pd.to_numeric(df_asi['Doz'], errors='coerce')
        df_asi = df_asi.dropna(subset=['Doz'])
        df_asi = df_asi[df_asi['Doz'] > 0]
        df_asi['Aşı ve Doz'] = df_asi['Aşı Türü'] + " (" + df_asi['Doz'].astype(int).astype(str) + ". Doz)"
        asi_stats = df_asi['Aşı ve Doz'].value_counts().reset_index()
        asi_stats.columns = ['Aşı ve Doz', 'Frekans']
        toplam_asi = asi_stats['Frekans'].sum()

        # Temel Metrikler
        total_records = len(df_filtered)
        tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
        unique_children = df_filtered[tc_col].nunique() if tc_col in df_filtered.columns else total_records
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam İtiraz/Kayıt", f"{total_records:,}")
        m2.metric("Tekil Kişi (Çocuk/Gebe)", f"{unique_children:,}")
        m3.metric("Eksik İzlem Toplamı", f"{toplam_izlem:,}")
        m4.metric("Eksik Aşı Dozu Toplamı", f"{toplam_asi:,}")
        st.divider()

        # Grafikler
        colA, colB = st.columns(2)
        with colA:
            if not asi_stats.empty:
                fig_asi_bar = px.bar(asi_stats.head(15), x='Frekans', y='Aşı ve Doz', orientation='h', title='En Çok Reddedilen 15 Aşı/Doz', color='Frekans', color_continuous_scale='Teal')
                fig_asi_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_asi_bar, use_container_width=True)
            
            if 'ASM ADI' in df_filtered.columns:
                top_asms = df_filtered['ASM ADI'].value_counts().head(10).reset_index()
                top_asms.columns = ['ASM Adı', 'Vaka Sayısı']
                fig_asm = px.bar(top_asms, x='Vaka Sayısı', y='ASM Adı', orientation='h', title="En Çok Red Görülen İlk 10 ASM", color='Vaka Sayısı', color_continuous_scale='Reds')
                fig_asm.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_asm, use_container_width=True)

        with colB:
            if 'İTİRAZ NEDENİ' in df_filtered.columns:
                reason_counts = df_filtered['İTİRAZ NEDENİ'].value_counts().reset_index()
                reason_counts.columns = ['İtiraz Nedeni', 'Frekans']
                fig_reason = px.pie(reason_counts.head(7), values='Frekans', names='İtiraz Nedeni', hole=0.4, title='En Sık Görülen İtiraz Nedenleri')
                st.plotly_chart(fig_reason, use_container_width=True)
                
            if 'İLÇE - KARAR' in df_filtered.columns:
                karar_df = df_filtered['İLÇE - KARAR'].value_counts().reset_index()
                karar_df.columns = ['Karar', 'Sayı']
                fig_decision = px.bar(karar_df, x='Karar', y='Sayı', title="İlçe Karar Sonuçları", color='Karar', color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_decision, use_container_width=True)

    # =========================================================================
    # TAB 2: DETAYLI VERİ SETİ ANALİZİ (YENİ EKLENEN KISIM)
    # =========================================================================
    with tab_analiz:
        st.header("1. Genel Veri Seti Özeti")
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır (Gözlem)", f"{df.shape[0]:,}")
        c2.metric("Toplam Sütun (Değişken)", f"{df.shape[1]:,}")
        c3.metric("Toplam Boş Hücre (Eksik Veri)", f"{df.isnull().sum().sum():,}")
        st.divider()

        st.header("2. Sütun Bazlı Profil Çıkarma")
        st.markdown("Veri setinizdeki her bir sütunun (değişkenin) tipini, boş veri oranını ve benzersiz değer sayısını gösterir.")
        
        # Sütun profil verisi hazırlama
        profil_verisi = []
        for col in df.columns:
            profil_verisi.append({
                "Sütun Adı": col,
                "Veri Tipi": str(df[col].dtype).replace('object', 'Metin/Kategori').replace('float64', 'Ondalıklı Sayı').replace('int64', 'Tam Sayı').replace('datetime64[ns]', 'Tarih'),
                "Boş Hücre": df[col].isnull().sum(),
                "Eksik Oranı (%)": round((df[col].isnull().sum() / len(df)) * 100, 1),
                "Benzersiz Değer": df[col].nunique()
            })
        
        df_profil = pd.DataFrame(profil_verisi)
        st.dataframe(
            df_profil.style.format({'Eksik Oranı (%)': '{:.1f}%'}).background_gradient(subset=['Eksik Oranı (%)'], cmap='Reds'),
            use_container_width=True, 
            hide_index=True
        )

        st.divider()
        st.header("3. Dinamik Sıklık Analizi (Çapraz Sorgu)")
        st.markdown("Aşağıdan analiz etmek istediğiniz bir sütunu seçerek içindeki değerlerin dağılımını görebilirsiniz.")
        
        # Kullanıcıya sadece anlamlı analiz yapılabilecek (kategorik veya az benzersiz değerli) sütunları sun
        analiz_edilebilir_sutunlar = [col for col in df.columns if df[col].nunique() < 200]
        
        secilen_sutun = st.selectbox("Analiz Edilecek Sütunu Seçiniz:", analiz_edilebilir_sutunlar)
        
        if secilen_sutun:
            sutun_dagilimi = df[secilen_sutun].value_counts().reset_index()
            sutun_dagilimi.columns = [secilen_sutun, 'Frekans (Sayı)']
            sutun_dagilimi['Yüzdelik (%)'] = (sutun_dagilimi['Frekans (Sayı)'] / sutun_dagilimi['Frekans (Sayı)'].sum() * 100).round(2)
            
            kol1, kol2 = st.columns([1, 1])
            with kol1:
                st.markdown(f"**{secilen_sutun}** Sütununa Ait Frekans Tablosu")
                st.dataframe(sutun_dagilimi.style.format({'Yüzdelik (%)': '{:.2f}%'}), use_container_width=True, hide_index=True)
            with kol2:
                # Eğer benzersiz değer sayısı 15'ten azsa pasta grafik, çoksa bar grafik çiz
                if len(sutun_dagilimi) <= 15:
                    fig_dinamik = px.pie(sutun_dagilimi, values='Frekans (Sayı)', names=secilen_sutun, hole=0.3, title=f'{secilen_sutun} Dağılımı')
                else:
                    fig_dinamik = px.bar(sutun_dagilimi.head(20), x='Frekans (Sayı)', y=secilen_sutun, orientation='h', title=f'{secilen_sutun} Dağılımı (İlk 20)')
                    fig_dinamik.update_layout(yaxis={'categoryorder':'total ascending'})
                
                st.plotly_chart(fig_dinamik, use_container_width=True)

if __name__ == "__main__":
    main()
