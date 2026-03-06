import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="İzlem ve Aşı Reddi Analizi", layout="wide", page_icon="📊")

@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, low_memory=False)
        else:
            df = pd.read_excel(file)
        
        df.columns = df.columns.str.strip().str.replace('i', 'İ').str.upper()
        return df
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

def main():
    st.title("📊 İzlem ve Aşı Reddi Analiz Raporu")
    
    uploaded_file = st.sidebar.file_uploader("Veri Dosyasını Yükleyin (CSV/Excel)", type=['csv', 'xlsx'])
    
    if uploaded_file is None:
        st.info("Lütfen analize başlamak için sol menüden veri dosyanızı yükleyin.")
        return
        
    df = load_data(uploaded_file)
    if df is None or df.empty:
        return

    # Sütun Tanımları
    izlem_cols = ['GEBE İZLEM', 'LOHUSA İZLEM', 'BEBEK İZLEM', 'ÇOCUK İZLEM']
    asi_cols = ['DABT-İPA-HİB-HEP-B', 'HEP B', 'BCG', 'KKK', 'HEP A', 'KPA', 'OPA', 'SU ÇİÇEĞİ', 'DABT-İPA', 'TD']
    
    mevcut_izlem_cols = [col for col in izlem_cols if col in df.columns]
    mevcut_asi_cols = [col for col in asi_cols if col in df.columns]

    # --- VERİ İŞLEME: İZLEM ---
    df_izlem = df.melt(value_vars=mevcut_izlem_cols, var_name='İzlem Türü', value_name='Sıra')
    df_izlem['Sıra'] = pd.to_numeric(df_izlem['Sıra'], errors='coerce')
    df_izlem = df_izlem.dropna(subset=['Sıra'])
    df_izlem = df_izlem[df_izlem['Sıra'] > 0]
    df_izlem['İzlem ve Sıra'] = df_izlem['İzlem Türü'] + " (" + df_izlem['Sıra'].astype(int).astype(str) + ". İzlem)"
    
    izlem_stats = df_izlem['İzlem ve Sıra'].value_counts().reset_index()
    izlem_stats.columns = ['İzlem ve Sıra', 'Frekans']
    toplam_izlem = izlem_stats['Frekans'].sum()
    izlem_stats['Oran (%)'] = (izlem_stats['Frekans'] / toplam_izlem * 100).round(2) if toplam_izlem > 0 else 0

    # --- VERİ İŞLEME: AŞI ---
    df_asi = df.melt(value_vars=mevcut_asi_cols, var_name='Aşı Türü', value_name='Doz')
    df_asi['Doz'] = pd.to_numeric(df_asi['Doz'], errors='coerce')
    df_asi = df_asi.dropna(subset=['Doz'])
    df_asi = df_asi[df_asi['Doz'] > 0]
    df_asi['Aşı ve Doz'] = df_asi['Aşı Türü'] + " (" + df_asi['Doz'].astype(int).astype(str) + ". Doz)"
    
    asi_stats = df_asi['Aşı ve Doz'].value_counts().reset_index()
    asi_stats.columns = ['Aşı ve Doz', 'Frekans']
    toplam_asi = asi_stats['Frekans'].sum()
    asi_stats['Oran (%)'] = (asi_stats['Frekans'] / toplam_asi * 100).round(2) if toplam_asi > 0 else 0

    # --- 1. ÖZET DEĞERLENDİRME RAPORU ---
    st.header("📝 Özet Değerlendirme Raporu")
    
    en_sik_izlem = izlem_stats.iloc[0] if not izlem_stats.empty else None
    en_sik_asi = asi_stats.iloc[0] if not asi_stats.empty else None
    
    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Toplam Yapılmayan İzlem", f"{toplam_izlem:,}")
    col_r2.metric("Toplam Yapılmayan Aşı Dozu", f"{toplam_asi:,}")
    col_r3.metric("Toplam Vaka (İzlem + Aşı)", f"{(toplam_izlem + toplam_asi):,}")
    
    st.info(f"""
    **Genel Toplam Oranlar ve Kritik Bulgular:**
    * İncelenen veri setinde toplam **{toplam_izlem:,}** adet izlem ve **{toplam_asi:,}** adet aşı dozu eksikliği/reddi tespit edilmiştir. Aynı hastadaki çoklu eksiklikler ayrı ayrı vaka olarak değerlendirilmiştir.
    * **En Sık Yapılmayan İzlem:** {f"**{en_sik_izlem['İzlem ve Sıra']}** ({en_sik_izlem['Frekans']} vaka, %{en_sik_izlem['Oran (%)']})" if en_sik_izlem is not None else "Veri Yok"}
    * **En Sık Yapılmayan Aşı ve Doz:** {f"**{en_sik_asi['Aşı ve Doz']}** ({en_sik_asi['Frekans']} vaka, %{en_sik_asi['Oran (%)']})" if en_sik_asi is not None else "Veri Yok"}
    """)
    st.divider()

    # --- 2. İZLEM ANALİZLERİ ---
    st.header("🔍 İzlem Türlerine Göre Analiz")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.dataframe(izlem_stats.style.format({'Oran (%)': '{:.2f}%'}), use_container_width=True, hide_index=True)
        
    with col2:
        if not izlem_stats.empty:
            fig_izlem_pie = px.pie(
                df_izlem, names='İzlem Türü', 
                title='İzlem Türlerinin Genel Dağılımı',
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_izlem_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_izlem_pie, use_container_width=True)

    if not izlem_stats.empty:
        fig_izlem_bar = px.bar(
            izlem_stats.head(10), x='Frekans', y='İzlem ve Sıra', orientation='h',
            text='Frekans', title='En Sık Yapılmayan İlk 10 İzlem Türü ve Sırası',
            color='Frekans', color_continuous_scale='Viridis'
        )
        fig_izlem_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_izlem_bar, use_container_width=True)

    st.divider()

    # --- 3. AŞI ANALİZLERİ ---
    st.header("💉 Aşılara Göre Doz Bazlı Analiz")
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.dataframe(asi_stats.style.format({'Oran (%)': '{:.2f}%'}), use_container_width=True, hide_index=True)
        
    with col4:
        if not asi_stats.empty:
            fig_asi_pie = px.pie(
                df_asi, names='Aşı Türü', 
                title='Aşı Türlerinin Genel Dağılımı (Doz Bağımsız)',
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_asi_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_asi_pie, use_container_width=True)

    if not asi_stats.empty:
        fig_asi_bar = px.bar(
            asi_stats.head(20), x='Frekans', y='Aşı ve Doz', orientation='h',
            text='Frekans', title='En Sık Yapılmayan 20 Aşı ve Doz Kombinasyonu',
            color='Frekans', color_continuous_scale='Magma'
        )
        fig_asi_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig_asi_bar, use_container_width=True)

if __name__ == "__main__":
    main()
