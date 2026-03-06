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
        
        # Sütun isimlerini standartlaştır
        df.columns = df.columns.str.strip().str.replace('i', 'İ').str.upper()
        
        # Zaman analizi için tarih formatını ayarla
        if 'KAYIT TARİHİ' in df.columns:
            df['KAYIT TARİHİ'] = pd.to_datetime(df['KAYIT TARİHİ'], errors='coerce', dayfirst=True)
            
        if 'İTİRAZ NEDENİ' in df.columns:
            df['İTİRAZ NEDENİ'] = df['İTİRAZ NEDENİ'].fillna('Belirtilmemiş')
            
        return df
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

def main():
    st.title("📊 İlçe Sağlık - Kapsamlı Aşı ve İzlem Reddi Dashboard'u")
    
    # --- YAN MENÜ (SIDEBAR) ---
    st.sidebar.header("📁 Veri Yükleme")
    uploaded_file = st.sidebar.file_uploader("Veri Dosyasını Yükleyin", type=['csv', 'xlsx'])
    
    if uploaded_file is None:
        st.info("👆 Analize başlamak için sol menüden veri setini yükleyin.")
        return
        
    with st.spinner("Veri işleniyor..."):
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

    # --- VERİ İŞLEME: İZLEM VE AŞI ---
    izlem_cols = ['GEBE İZLEM', 'LOHUSA İZLEM', 'BEBEK İZLEM', 'ÇOCUK İZLEM']
    asi_cols = ['DABT-İPA-HİB-HEP-B', 'HEP B', 'BCG', 'KKK', 'HEP A', 'KPA', 'OPA', 'SU ÇİÇEĞİ', 'DABT-İPA', 'TD']
    
    mevcut_izlem_cols = [col for col in izlem_cols if col in df_filtered.columns]
    mevcut_asi_cols = [col for col in asi_cols if col in df_filtered.columns]

    # İzlem Ayrıştırma (Melt)
    df_izlem = df_filtered.melt(value_vars=mevcut_izlem_cols, var_name='İzlem Türü', value_name='Sıra')
    df_izlem['Sıra'] = pd.to_numeric(df_izlem['Sıra'], errors='coerce')
    df_izlem = df_izlem.dropna(subset=['Sıra'])
    df_izlem = df_izlem[df_izlem['Sıra'] > 0]
    df_izlem['İzlem ve Sıra'] = df_izlem['İzlem Türü'] + " (" + df_izlem['Sıra'].astype(int).astype(str) + ". İzlem)"
    
    izlem_stats = df_izlem['İzlem ve Sıra'].value_counts().reset_index()
    izlem_stats.columns = ['İzlem ve Sıra', 'Frekans']
    toplam_izlem = izlem_stats['Frekans'].sum()

    # Aşı Ayrıştırma (Melt)
    df_asi = df_filtered.melt(value_vars=mevcut_asi_cols, var_name='Aşı Türü', value_name='Doz')
    df_asi['Doz'] = pd.to_numeric(df_asi['Doz'], errors='coerce')
    df_asi = df_asi.dropna(subset=['Doz'])
    df_asi = df_asi[df_asi['Doz'] > 0]
    df_asi['Aşı ve Doz'] = df_asi['Aşı Türü'] + " (" + df_asi['Doz'].astype(int).astype(str) + ". Doz)"
    
    asi_stats = df_asi['Aşı ve Doz'].value_counts().reset_index()
    asi_stats.columns = ['Aşı ve Doz', 'Frekans']
    toplam_asi = asi_stats['Frekans'].sum()

    # --- 1. TEMEL METRİKLER ---
    total_records = len(df_filtered)
    tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
    unique_children = df_filtered[tc_col].nunique() if tc_col in df_filtered.columns else total_records
    asm_count = df_filtered['ASM ADI'].nunique() if 'ASM ADI' in df_filtered.columns else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Toplam İtiraz/Kayıt", f"{total_records:,}")
    m2.metric("Tekil Çocuk", f"{unique_children:,}")
    m3.metric("Eksik İzlem", f"{toplam_izlem:,}")
    m4.metric("Eksik Aşı Dozu", f"{toplam_asi:,}")
    m5.metric("Etkilenen ASM", f"{asm_count:,}")
    st.divider()

    # --- 2. GENEL DURUM RAPORU VE TEYİT VERİLERİ ---
    st.subheader("📋 Genel Durum Raporu")
    en_sik_izlem = izlem_stats.iloc[0] if not izlem_stats.empty else None
    en_sik_asi = asi_stats.iloc[0] if not asi_stats.empty else None
    
    st.info(f'''
    * Toplamda **{toplam_izlem:,}** adet izlem ve **{toplam_asi:,}** adet aşı dozu eksikliği saptanmıştır.
    * **En Sık Yapılmayan İzlem:** {en_sik_izlem['İzlem ve Sıra'] if en_sik_izlem is not None else "Yok"} ({en_sik_izlem['Frekans'] if en_sik_izlem is not None else 0} vaka)
    * **En Sık Yapılmayan Aşı:** {en_sik_asi['Aşı ve Doz'] if en_sik_asi is not None else "Yok"} ({en_sik_asi['Frekans'] if en_sik_asi is not None else 0} vaka)
    ''')
    
    # ASM Onam ve İlçe Teyit İstatistikleri
    if 'ASM ONAM' in df_filtered.columns or 'İLÇE SAĞLIK TEYİT' in df_filtered.columns:
        c_onam, c_teyit = st.columns(2)
        with c_onam:
            if 'ASM ONAM' in df_filtered.columns:
                st.markdown("**🔹 ASM Onam Durumu**")
                onam_counts = df_filtered['ASM ONAM'].value_counts()
                total_onam = onam_counts.sum()
                # Olası isimlendirmeleri yakalıyoruz
                imzali_red = onam_counts.get('İmzalı Red', onam_counts.get('İmzalı Red Formu', 0))
                imtina_red = onam_counts.get('İmzadan İmtina Red', onam_counts.get('İmzadan İmtina Red Formu', 0))
                
                imzali_oran = (imzali_red / total_onam * 100) if total_onam > 0 else 0
                imtina_oran = (imtina_red / total_onam * 100) if total_onam > 0 else 0
                
                st.write(f"- İmzalı Red: **{imzali_red}** *(%{imzali_oran:.1f})*")
                st.write(f"- İmzadan İmtina Red: **{imtina_red}** *(%{imtina_oran:.1f})*")

        with c_teyit:
            if 'İLÇE SAĞLIK TEYİT' in df_filtered.columns:
                st.markdown("**🔹 İlçe Sağlık Teyit Durumu**")
                teyit_counts = df_filtered['İLÇE SAĞLIK TEYİT'].value_counts()
                total_teyit = teyit_counts.sum()
                telefon = teyit_counts.get('Telefon', teyit_counts.get('Telefonla Teyit', 0))
                ev_ziyareti = teyit_counts.get('Ev Ziyareti', 0)
                
                tel_oran = (telefon / total_teyit * 100) if total_teyit > 0 else 0
                ev_oran = (ev_ziyareti / total_teyit * 100) if total_teyit > 0 else 0
                
                st.write(f"- Telefon ile Teyit: **{telefon}** *(%{tel_oran:.1f})*")
                st.write(f"- Ev Ziyareti: **{ev_ziyareti}** *(%{ev_oran:.1f})*")
    st.divider()

    # --- 3. ZAMAN VE ASM EĞİLİMİ (Eski Sürümden) ---
    st.subheader("📈 Zaman İçinde Red Eğilimi ve ASM Dağılımı")
    col_trend, col_asm = st.columns(2)
    with col_trend:
        if 'KAYIT TARİHİ' in df_filtered.columns:
            trend_df = df_filtered.groupby(df_filtered['KAYIT TARİHİ'].dt.date).size().reset_index(name='Kayıt Sayısı')
            if not trend_df.empty:
                fig_trend = px.line(trend_df, x='KAYIT TARİHİ', y='Kayıt Sayısı', markers=True, title="Günlere Göre Sayılar")
                st.plotly_chart(fig_trend, use_container_width=True)
                
    with col_asm:
        if 'ASM ADI' in df_filtered.columns:
            top_asms = df_filtered['ASM ADI'].value_counts().head(10).reset_index()
            top_asms.columns = ['ASM Adı', 'Vaka Sayısı']
            fig_asm = px.bar(top_asms, x='Vaka Sayısı', y='ASM Adı', orientation='h', title="En Çok Red Görülen İlk 10 ASM", color='Vaka Sayısı', color_continuous_scale='Reds')
            fig_asm.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_asm, use_container_width=True)

    st.divider()

    # --- 4. İZLEM VE AŞI DETAYLARI (Yeni Sürümden) ---
    st.subheader("🔍 İzlem ve Aşı Doz Analizleri")
    t1, t2 = st.tabs(["Aşı Doz Analizi", "İzlem Analizi"])
    
    with t1:
        colA, colB = st.columns(2)
        with colA:
            if not asi_stats.empty:
                fig_asi_bar = px.bar(asi_stats.head(15), x='Frekans', y='Aşı ve Doz', orientation='h', title='En Sık Yapılmayan 15 Aşı/Doz', color='Frekans', color_continuous_scale='Teal')
                fig_asi_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
                st.plotly_chart(fig_asi_bar, use_container_width=True)
        with colB:
            if not df_asi.empty:
                fig_asi_pie = px.pie(df_asi, names='Aşı Türü', title='Aşı Türlerinin Genel Dağılımı (Doz Bağımsız)', hole=0.4)
                st.plotly_chart(fig_asi_pie, use_container_width=True)
                
    with t2:
        colC, colD = st.columns(2)
        with colC:
            if not izlem_stats.empty:
                fig_izlem_bar = px.bar(izlem_stats.head(10), x='Frekans', y='İzlem ve Sıra', orientation='h', title='En Sık Yapılmayan İzlemler', color='Frekans', color_continuous_scale='Viridis')
                fig_izlem_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
                st.plotly_chart(fig_izlem_bar, use_container_width=True)
        with colD:
            if not df_izlem.empty:
                fig_izlem_pie = px.pie(df_izlem, names='İzlem Türü', title='İzlem Türlerinin Dağılımı', hole=0.4)
                st.plotly_chart(fig_izlem_pie, use_container_width=True)

    st.divider()

    # --- 5. DEMOGRAFİ, NEDENLER VE KARAR DURUMU (Eski Sürümden) ---
    st.subheader("👥 Demografi, Nedenler ve İlçe Kararları")
    col_gender, col_reason, col_decision = st.columns(3)
    
    with col_gender:
        if 'İTİRAZ KONUSU KİŞİNİN CİNSİYETİ' in df_filtered.columns:
            cinsiyet_df = df_filtered['İTİRAZ KONUSU KİŞİNİN CİNSİYETİ'].value_counts().reset_index()
            cinsiyet_df.columns = ['Cinsiyet', 'Kişi Sayısı']
            fig_gender = px.pie(cinsiyet_df, values='Kişi Sayısı', names='Cinsiyet', title="Cinsiyet Dağılımı", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_gender, use_container_width=True)

    with col_reason:
        if 'İTİRAZ NEDENİ' in df_filtered.columns:
            reason_counts = df_filtered['İTİRAZ NEDENİ'].value_counts().reset_index()
            reason_counts.columns = ['İtiraz Nedeni', 'Frekans']
            fig_reason = px.pie(reason_counts, values='Frekans', names='İtiraz Nedeni', hole=0.4, title='İtiraz Nedenleri')
            fig_reason.update_traces(textposition='inside', textinfo='percent')
            st.plotly_chart(fig_reason, use_container_width=True)

    with col_decision:
        if 'İLÇE - KARAR' in df_filtered.columns:
            karar_df = df_filtered['İLÇE - KARAR'].value_counts().reset_index()
            karar_df.columns = ['Karar', 'Sayı']
            
            color_map = {'Başarılı': 'blue'} # Özel durum haritalaması
            
            fig_decision = px.bar(karar_df, x='Karar', y='Sayı', title="İlçe Karar Sonuçları", color='Karar', color_discrete_map=color_map)
            st.plotly_chart(fig_decision, use_container_width=True)

if __name__ == "__main__":
    main()
