import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components
from sklearn.cluster import DBSCAN

# 1. 網頁基本設定
st.set_page_config(page_title="台北市 AED 空間分析儀表板", page_icon="🚑", layout="wide")
st.title("🚑 台北市 12 行政區 AED 空間與醫療可及性分析 (含 18 家急救醫院)")

# 台北市區域代碼對照表
DISTRICT_MAP = {
    63000010: '松山區', 63000020: '信義區', 63000030: '大安區', 63000040: '中山區',
    63000050: '中正區', 63000060: '大同區', 63000070: '萬華區', 63000080: '文山區',
    63000090: '南港區', 63000100: '內湖區', 63000110: '士林區', 63000120: '北投區'
}

# 🏥 臺北市官方 18 家急救責任醫院點位資料庫 (放在 import pandas as pd 之後)
HOSPITALS_DATA = pd.DataFrame({
    '醫院名稱': [
        '國立臺灣大學醫學院附設醫院', '臺北市立聯合醫院（和平院區）', '西園醫院', 
        '臺北市立聯合醫院（中興院區）', '振興醫療財團法人振興醫院', '臺北榮民總醫院', 
        '博仁綜合醫院', '三軍總醫院松山分院', '基督復臨安息日會醫療財團法人臺安醫院', 
        '臺北醫學大學附設醫院', '馬偕紀念醫院（台北院區）', '萬芳醫院', 
        '臺北市立聯合醫院（忠孝院區）', '臺北市立聯合醫院（仁愛院區）', '國泰綜合醫院', 
        '新光醫療財團法人新光醫院', '臺北市立聯合醫院（陽明院區）', '三軍總醫院（內湖總院）'
    ],
    '緯度': [
        25.0413, 25.0354, 25.0271, 25.0500, 25.1167, 25.1208, 
        25.0514, 25.0543, 25.0485, 25.0261, 25.0581, 24.9988, 
        25.0425, 25.0378, 25.0372, 25.0934, 25.1051, 25.0682
    ],
    '經度': [
        121.5195, 121.5053, 121.4986, 121.5093, 121.5245, 121.5202, 
        121.5574, 121.5620, 121.5478, 121.5613, 121.5224, 121.5578, 
        121.5866, 121.5441, 121.5517, 121.5173, 121.5322, 121.5932
    ]
})

# 2. 讀取資料
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('taipei_aed_full_analysis.csv', encoding='utf-8-sig')
    except:
        df = pd.read_csv('taipei_aed_full_analysis.csv', encoding='cp950')
    
    if '區域代碼' in df.columns:
        df['行政區'] = df['區域代碼'].map(DISTRICT_MAP).fillna('其他/未知')
    else:
        df['行政區'] = '全區'
    return df

df = load_data()

# 3. 側邊欄 - 互動式篩選器
st.sidebar.header("📍 區域與醫院篩選")
district_list = ['全台北市'] + list(DISTRICT_MAP.values())
selected_district = st.sidebar.selectbox("選擇分析行政區", district_list)

if selected_district == '全台北市':
    filtered_df = df.copy()
else:
    filtered_df = df[df['行政區'] == selected_district].copy()

available_hospitals = filtered_df['最近急救醫院'].unique()
selected_hospital = st.sidebar.multiselect("🏥 篩選特定急救醫院", options=available_hospitals, default=available_hospitals)

final_df = filtered_df[filtered_df['最近急救醫院'].isin(selected_hospital)].copy()

st.sidebar.markdown("---")
# ----------------- DBSCAN 參數設定區 -----------------
st.sidebar.header("🎯 DBSCAN 空間分群設定")
dbscan_radius = st.sidebar.slider("DBSCAN 搜尋半徑 (公尺)", min_value=10, max_value=200, value=50, step=10)
dbscan_min_samples = st.sidebar.slider("群集最少 AED 台數 (min_samples)", min_value=2, max_value=10, value=3)
# ---------------------------------------------------

# 4. 即時執行 DBSCAN 動態運算
if not final_df.empty and len(final_df) >= dbscan_min_samples:
    coords = np.radians(final_df[['緯度', '經度']].values)
    kms_per_radian = 6371000.0
    eps_rad = dbscan_radius / kms_per_radian
    
    db = DBSCAN(eps=eps_rad, min_samples=dbscan_min_samples, metric='haversine').fit(coords)
    final_df['DBSCAN_Cluster'] = db.labels_
else:
    final_df['DBSCAN_Cluster'] = -1

# 5. 主畫面 - 核心指標 (KPI)
st.subheader(f"📊 核心數據指標 ({selected_district})")
col1, col2, col3, col4 = st.columns(4)

clusters_count = len(set(final_df['DBSCAN_Cluster'])) - (1 if -1 in final_df['DBSCAN_Cluster'].values else 0)
noise_count = list(final_df['DBSCAN_Cluster']).count(-1)

col1.metric("該區 AED 總數", f"{len(final_df)} 處")
col2.metric(f"DBSCAN 熱區群集數 ({dbscan_radius}m)", f"{clusters_count} 個")
col3.metric("獨立孤島/盲區點位", f"{noise_count} 處")
col4.metric("最遠醫療距離", f"{final_df['至最近醫院距離_公尺'].max():.1f} m" if not final_df.empty else "N/A")

st.markdown("---")

# 6. 動態地圖 (含急救醫院獨立標籤)
st.subheader(f"🗺️ AED 空間分群與急救責任醫院地圖 (半徑：{dbscan_radius}m)")

def generate_dbscan_map(data):
    if data.empty:
        return "<p>無點位資料</p>"
    
    center_lat = data['緯度'].mean()
    center_lon = data['經度'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14 if selected_district != '全台北市' else 12)
    
    # 🏥 標示急救責任醫院 (獨立呈現)
    target_hospitals = HOSPITALS_DATA[HOSPITALS_DATA['醫院名稱'].isin(selected_hospital)]
    hospital_group = folium.FeatureGroup(name="急救責任醫院").add_to(m)
    for idx, hosp in target_hospitals.iterrows():
        folium.Marker(
            location=[hosp['緯度'], hosp['經度']],
            popup=f"<b>🏥 急救責任醫院：{hosp['醫院名稱']}</b>",
            tooltip=f"🏥 {hosp['醫院名稱']}",
            icon=folium.Icon(color="darkred", icon="plus-sign", prefix="glyphicon")
        ).add_to(hospital_group)
    
    # ⚡ 標示 AED 點位
    cluster_colors = ['green', 'purple', 'orange', 'darkblue', 'cadetblue', 'darkgreen', 'pink']
    marker_cluster = MarkerCluster(name="AED 點位").add_to(m)
    
    for idx, row in data.iterrows():
        cluster_id = row['DBSCAN_Cluster']
        
        if cluster_id == -1:
            color = 'red'
            status_text = "⚠️ 獨立孤島 / 服務盲區 (Noise)"
            icon_style = "info-sign"
        else:
            color = cluster_colors[cluster_id % len(cluster_colors)]
            status_text = f"🔥 高密度重複熱區 (群集 #{cluster_id + 1})"
            icon_style = "ok-sign"
        
        popup_html = f"""
        <b>{row['場所名稱']}</b><br>
        <b>分群狀態：</b>{status_text}<br>
        <b>地址：</b>{row.get('場所地址', '無')}<br>
        <b>最近急救醫院：</b>{row['最近急救醫院']}<br>
        <b>送醫距離：</b>{row['至最近醫院距離_公尺']:.1f} 公尺
        """
        
        folium.Marker(
            location=[row['緯度'], row['經度']],
            popup=popup_html,
            tooltip=f"{row['場所名稱']} ({status_text})",
            icon=folium.Icon(color=color, icon=icon_style)
        ).add_to(marker_cluster)
        
    folium.LayerControl().add_to(m)
    return m._repr_html_()

components.html(generate_dbscan_map(final_df), height=550, scrolling=False)

st.markdown("---")

# 7. 圖表分析區
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 🎯 DBSCAN 分群結果數量占比")
    if not final_df.empty:
        cluster_summary = final_df['DBSCAN_Cluster'].value_counts().reset_index()
        cluster_summary.columns = ['Cluster_ID', '點位數量']
        cluster_summary['類別'] = cluster_summary['Cluster_ID'].apply(lambda x: '獨立孤島/盲區' if x == -1 else f'熱區群集 #{x+1}')
        fig_pie = px.pie(cluster_summary, names='類別', values='點位數量', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    st.markdown("#### 🏥 區域醫院急救責任負載")
    if not final_df.empty:
        hospital_counts = final_df['最近急救醫院'].value_counts().reset_index()
        hospital_counts.columns = ['最近急救醫院', '點位數量']
        fig_bar = px.bar(hospital_counts, x='最近急救醫院', y='點位數量', color='最近急救醫院')
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# 8. 智慧決議文字建議
st.subheader(f"💡 DBSCAN 空間決策建議 ({selected_district})")

if not final_df.empty:
    st.info(f"""
    **📌 分析設定說明**：以 **{dbscan_radius} 公尺** 為搜尋半徑 ($\text{{eps}}$)，並設定至少 **{dbscan_min_samples} 台** 構成聚落。
    
    1. **🔥 高密度過度涵蓋區**：辨識出 **{clusters_count}** 個熱區群集。此類區域在 {dbscan_radius} 公尺內高度密集，建議可適度挪移部分設備。
    2. **⚠️ 服務涵蓋盲區 (Noise)**：共有 **{noise_count}** 處點位周邊 {dbscan_radius} 公尺內無其他 AED。若此類點位同時距離地圖上的 **深紅色急救醫院 (➕)** 較遠，應列為優先輔導與培訓志工的重點區域。
    """)

# 9. 顯示詳細數據
with st.expander(f"📂 查看 DBSCAN 詳細分群數據表 ({selected_district})"):
    st.dataframe(final_df[['行政區', '場所名稱', 'DBSCAN_Cluster', '最近急救醫院', '至最近醫院距離_公尺']])