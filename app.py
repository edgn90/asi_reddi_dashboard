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
    tab_dash, tab_analiz = st.tabs(["📊 Karar Destek Dashboard'u", "🔎 Detaylı Değişken Analizi"])

    # =========================================================================
    # TAB 1: MEVCUT DASHBOARD (Grafikler ve Metrikler)
    # =========================================================================
    with tab_dash:
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

        total_records = len(df_filtered)
        tc_col = 'İTİRAZ KONUSU KİŞİNİN TC KİMLİK NO'
        unique_children = df_filtered[tc_col].nunique() if tc_col in df_filtered.columns else total_records
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam İtiraz/Kayıt", f"{total_records:,}")
        m2.metric("Tekil Kişi (Çocuk/Gebe)", f"{unique_children:,}")
        m3.metric("Eksik İzlem Toplamı", f"{toplam_izlem:,}")
        m4.metric("Eksik Aşı Dozu Toplamı", f"{toplam_asi:,}")
        st.divider()

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
    # TAB 2: DETAYLI DEĞİŞKEN ANALİZİ (YENİ VE İSTENEN FORMAT)
    # =========================================================================
    with tab_analiz:
        st.header("🔎 Sütun (Değişken) Bazlı Tekil Analiz Raporu")
        st.markdown("Aşağıda, yüklediğiniz verideki her bir sütunun yapısı, eksik verileri ve dağılımları tek tek analiz edilmiştir.")
        st.divider()

        toplam_gozlem = len(df)

        for col in df.columns:
            st.subheader(f"📌 DEĞİŞKEN: {col}")
            
            # 1. Genel Bilgi Tablosu
            bos_hucre = df[col].isnull().sum()
            bos_orani = (bos_hucre / toplam_gozlem) * 100
            benzersiz = df[col].nunique()
            
            genel_df = pd.DataFrame({
                "Özellik": ["Sütun Adı", "Toplam Gözlem Sayısı", "Boş Hücre Sayısı", "Boş Hücre Oranı (%)", "Benzersiz Değer Sayısı"],
                "Bilgi": [col, f"{toplam_gozlem:,}", f"{bos_hucre:,}", f"%{bos_orani:.2f}", f"{benzersiz:,}"]
            })
            
            st.table(genel_df)

            # Sütunun sayısal mı kategorik mi olduğunu anlama
            is_numeric = False
            
            # TC No, Telefon No, Birim Kodu gibi veriler sayısal olsa da istatistiksel olarak kategoriktir.
            # Bu yüzden bu kelimeleri içeren sütunları sayısal saymıyoruz.
            kategorik_kelimeler = ["TC", "NO", "KOD", "TARİH"]
            is_categorical_forced = any(k in col for k in kategorik_kelimeler)

            if not is_categorical_forced:
                if pd.api.types.is_numeric_dtype(df[col]):
                    is_numeric = True
                else:
                    # Aşı dozları (1, 2) gibi metin formatında ama aslında sayısal olanları tespit etme
                    temp_num = pd.to_numeric(df[col], errors='coerce')
                    # Eğer dolu verilerin tamamı sayıya dönüşebiliyorsa bunu sayısal kabul et
                    if temp_num.notnull().sum() > 0 and temp_num.notnull().sum() == df[col].notnull().sum():
                        is_numeric = True
                        num_series = temp_num

            # 2. Tip bazlı alt tablo
            if is_numeric:
                # Sayısal İstatistik Tablosu
                s = num_series if not pd.api.types.is_numeric_dtype(df[col]) else df[col]
                
                stat_df = pd.DataFrame({
                    "İstatistik": ["Ortalama", "Medyan", "Minimum", "Maksimum", "Std. Sapma"],
                    "Değer": [
                        round(s.mean(), 2) if pd.notnull(s.mean()) else "-",
                        round(s.median(), 2) if pd.notnull(s.median()) else "-",
                        round(s.min(), 2) if pd.notnull(s.min()) else "-",
                        round(s.max(), 2) if pd.notnull(s.max()) else "-",
                        round(s.std(), 2) if pd.notnull(s.std()) else "-"
                    ]
                })
                st.table(stat_df)
                
            else:
                # Kategorik (Frekans) Tablosu
                if benzersiz > 0:
                    val_counts = df[col].value_counts().reset_index()
                    val_counts.columns = ['Değer', 'Frekans']
                    val_counts['Yüzde'] = (val_counts['Frekans'] / val_counts['Frekans'].sum() * 100).apply(lambda x: f"%{x:.2f}")
                    
                    # Çok fazla benzersiz değer varsa sayfayı dondurmamak için ilk 20'yi göster
                    if len(val_counts) > 20:
                        st.info(f"💡 Bu değişkende çok fazla benzersiz değer ({benzersiz:,}) olduğu için sadece en sık görülen ilk 20 değer listelenmiştir.")
                        st.table(val_counts.head(20).astype(str))
                    else:
                        st.table(val_counts.astype(str))
                else:
                    st.info("Bu sütunda veri bulunmamaktadır (Tüm hücreler boş).")
            
            st.markdown("---") # Sütunlar arasına çizgi çek

if __name__ == "__main__":
    main()
