import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components

# 1. 網頁基本設定
st.set_page_config(page_title="台北市 AED 空間分析儀表板", page_icon="🚑", layout="wide")
st.title("🚑 台北市 12 行政區 AED 空間與醫療可及性分析")

# 台北市區域代碼對照表 (對應您原始資料的區域代碼)
DISTRICT_MAP = {
    63000010: '松山區', 63000020: '信義區', 63000030: '大安區', 63000040: '中山區',
    63000050: '中正區', 63000060: '大同區', 63000070: '萬華區', 63000080: '文山區',
    63000090: '南港區', 63000100: '內湖區', 63000110: '士林區', 63000120: '北投區'
}

# 2. 讀取全台北市資料
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('taipei_aed_full_analysis.csv', encoding='utf-8-sig')
    except:
        df = pd.read_csv('taipei_aed_full_analysis.csv', encoding='cp950')
    
    # 建立行政區欄位
    if '區域代碼' in df.columns:
        df['行政區'] = df['區域代碼'].map(DISTRICT_MAP).fillna('其他/未知')
    else:
        df['行政區'] = '全區' # 備用機制
    return df

df = load_data()

# 3. 側邊欄 - 跨維度動態篩選器
st.sidebar.header("🔍 區域與條件篩選")

# 行政區下拉選單
district_list = ['全台北市'] + list(DISTRICT_MAP.values())
selected_district = st.sidebar.selectbox("📍 選擇分析行政區", district_list)

max_overlap_dist = st.sidebar.slider("📏 篩選高度重疊距離 (公尺)", min_value=0, max_value=100, value=30, step=5)

# 根據所選行政區進行資料過濾
if selected_district == '全台北市':
    filtered_df = df
else:
    filtered_df = df[df['行政區'] == selected_district]

# 動態產生可選醫院清單 (僅顯示該區有負責的醫院)
available_hospitals = filtered_df['最近急救醫院'].unique()
selected_hospital = st.sidebar.multiselect("🏥 篩選特定急救醫院", options=available_hospitals, default=available_hospitals)

# 最終過濾結果
final_df = filtered_df[filtered_df['最近急救醫院'].isin(selected_hospital)]

# 4. 主畫面 - 核心指標 (KPI)
st.subheader(f"📊 核心數據指標 ({selected_district})")
col1, col2, col3, col4 = st.columns(4)
col1.metric("該區 AED 總數", f"{len(final_df)} 處")
col2.metric("高度重疊點位數", f"{len(final_df[final_df['第1近AED距離_公尺'] <= max_overlap_dist])} 處")
col3.metric("平均送醫直線距離", f"{final_df['至最近醫院距離_公尺'].mean():.1f} m" if not final_df.empty else "N/A")
col4.metric("最遠醫療孤島距離", f"{final_df['至最近醫院距離_公尺'].max():.1f} m" if not final_df.empty else "N/A")

st.markdown("---")

# 5. 動態互動式地圖 (由 Streamlit 即時渲染)
st.subheader(f"🗺️ AED 空間分佈地圖 ({selected_district})")

def generate_dynamic_map(data):
    if data.empty:
        return "<p>無點位資料</p>"
    
    # 取該區座標平均值作為地圖中心
    center_lat = data['緯度'].mean()
    center_lon = data['經度'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14 if selected_district != '全台北市' else 12)
    
    # 由於全台北市點位眾多，使用 MarkerCluster 提升網頁效能
    marker_cluster = MarkerCluster().add_to(m)
    
    for idx, row in data.iterrows():
        folium.Marker(
            location=[row['緯度'], row['經度']],
            popup=f"<b>{row['場所名稱']}</b><br>地址: {row.get('場所地址', '無')}<br>最近醫院: {row['最近急救醫院']}<br>送醫距離: {row['至最近醫院距離_公尺']:.1f} m",
            tooltip=row['場所名稱'],
            icon=folium.Icon(color="red" if row['第1近AED距離_公尺'] <= max_overlap_dist else "blue", icon="info-sign")
        ).add_to(marker_cluster)
        
    return m._repr_html_()

# 將 Folium 轉換為 HTML 並嵌入
components.html(generate_dynamic_map(final_df), height=550, scrolling=False)

st.markdown("---")

# 6. 多維度視覺化圖表
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 🏥 區域醫院 AED 負載佔比")
    if not final_df.empty:
        hospital_counts = final_df['最近急救醫院'].value_counts().reset_index()
        hospital_counts.columns = ['最近急救醫院', '點位數量']
        fig_pie = px.pie(hospital_counts, names='最近急救醫院', values='點位數量', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    st.markdown("#### 📏 送醫距離分佈狀況")
    if not final_df.empty:
        fig_hist = px.histogram(final_df, x='至最近醫院距離_公尺', nbins=30, marginal="box", color_discrete_sequence=['indianred'])
        st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("---")

# 7. 具體建議與改善方針 (Insights & Actions) 動態文字生成
st.subheader(f"💡 系統綜合評估與具體建議 ({selected_district})")

if not final_df.empty:
    overlap_count = len(final_df[final_df['第1近AED距離_公尺'] <= max_overlap_dist])
    max_dist = final_df['至最近醫院距離_公尺'].max()
    avg_dist = final_df['至最近醫院距離_公尺'].mean()

    st.success(f"""
    **🎯 資源重分配建議**：
    目前 **{selected_district}** 共有 **{overlap_count}** 處 AED 點位彼此間的距離小於 {max_overlap_dist} 公尺，屬於「資源高度重疊區」。建議管理單位可盤點這些點位，將部分閒置或使用率低的 AED 遷移至周邊無 AED 涵蓋的盲區。

    **🚑 醫療後送防護網**：
    數據顯示，該區 AED 點位距離急救責任醫院最遠達 **{max_dist:.1f} 公尺**（平均送醫直線距離為 {avg_dist:.1f} 公尺）。針對距離醫院超過 1.5 公里的醫療孤島站點，建議優先加強該區域社區志工的 CPR+AED 培訓，以爭取黃金搶救時間。
    """)
else:
    st.warning("⚠️ 目前選擇的條件下無資料，無法提供系統建議。")

st.markdown("---")

# 8. 顯示詳細原始數據
with st.expander(f"📂 展開查看詳細分析數據表 ({selected_district})"):
    st.dataframe(final_df[['行政區', '場所名稱', '場所地址', '第1近AED距離_公尺', '最近急救醫院', '至最近醫院距離_公尺', '預估送醫車程_分鐘']])