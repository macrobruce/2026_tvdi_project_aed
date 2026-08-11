import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components
from sklearn.cluster import DBSCAN

# 1. 網頁基本頁面設定
st.set_page_config(page_title="台北市 AED 空間分析儀表板", page_icon="🚑", layout="wide")
st.title("🚑 台北市 12 行政區 AED 空間「熱區與冷區」決策分析儀表板")

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

# 2. 讀取分析資料
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

# 3. 側邊欄 - 多維度條件篩選器
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
st.sidebar.header("🎯 DBSCAN 空間分群與熱冷區門檻")
dbscan_radius = st.sidebar.slider("熱區搜尋半徑 (公尺)", min_value=10, max_value=200, value=50, step=10)
dbscan_min_samples = st.sidebar.slider("熱區最少 AED 台數 (min_samples)", min_value=2, max_value=10, value=3)

cold_dist_threshold = st.sidebar.slider("❄️ 冷區(醫療孤島)距離門檻 (公尺)", min_value=500, max_value=3000, value=1500, step=100)

# 4. 即時執行 DBSCAN 動態運算
if not final_df.empty and len(final_df) >= dbscan_min_samples:
    coords = np.radians(final_df[['緯度', '經度']].values)
    kms_per_radian = 6371000.0
    eps_rad = dbscan_radius / kms_per_radian
    
    db = DBSCAN(eps=eps_rad, min_samples=dbscan_min_samples, metric='haversine').fit(coords)
    final_df['DBSCAN_Cluster'] = db.labels_
else:
    final_df['DBSCAN_Cluster'] = -1

# 分類熱區與冷區
def classify_zone(row):
    if row['DBSCAN_Cluster'] != -1:
        return '🔥 高密度熱區'
    elif row['至最近醫院距離_公尺'] >= cold_dist_threshold:
        return '❄️ 高風險冷區 (醫療孤島)'
    else:
        return '🔹 一般單點涵蓋'

final_df['區域型態'] = final_df.apply(classify_zone, axis=1)

# 5. 主畫面 - 核心數據指標 (KPI)
st.subheader(f"📊 核心數據指標 ({selected_district})")
col1, col2, col3, col4 = st.columns(4)

hotspots_count = len(final_df[final_df['區域型態'] == '🔥 高密度熱區'])
coldspots_count = len(final_df[final_df['區域型態'] == '❄️ 高風險冷區 (醫療孤島)'])

col1.metric("該區 AED 總數", f"{len(final_df)} 處")
col2.metric("🔥 熱區過度涵蓋點位", f"{hotspots_count} 處")
col3.metric("❄️ 高風險冷區/孤島點位", f"{coldspots_count} 處")
col4.metric("最遠送醫距離", f"{final_df['至最近醫院距離_公尺'].max():.1f} m" if not final_df.empty else "N/A")

st.markdown("---")

# 6. 動態地圖 (含熱區範圍圈、冷區警示標籤與 18 家醫院)
st.subheader(f"🗺️ 空間熱區 (🔥紅色半徑圈) 與冷區 (❄️冰藍深色) 標示地圖")

def generate_hot_cold_map(data):
    if data.empty:
        return "<p>無點位資料</p>"
    
    center_lat = data['緯度'].mean()
    center_lon = data['經度'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14 if selected_district != '全台北市' else 12)
    
    # 🏥 1. 標示 18 家急救責任醫院
    target_hospitals = HOSPITALS_DATA[HOSPITALS_DATA['醫院名稱'].isin(selected_hospital)]
    hospital_group = folium.FeatureGroup(name="🏥 18家急救責任醫院").add_to(m)
    for idx, hosp in target_hospitals.iterrows():
        folium.Marker(
            location=[hosp['緯度'], hosp['經度']],
            popup=f"<b>🏥 急救責任醫院：{hosp['醫院名稱']}</b>",
            tooltip=f"🏥 {hosp['醫院名稱']}",
            icon=folium.Icon(color="darkred", icon="plus-sign", prefix="glyphicon")
        ).add_to(hospital_group)
    
    # 🔥 2. 繪製高密度熱區半徑範圍圈 (Circle)
    hotspot_group = folium.FeatureGroup(name="🔥 熱區重疊涵蓋圈").add_to(m)
    hot_clusters = data[data['DBSCAN_Cluster'] != -1]
    
    for cluster_id in hot_clusters['DBSCAN_Cluster'].unique():
        cluster_pts = hot_clusters[hot_clusters['DBSCAN_Cluster'] == cluster_id]
        c_lat = cluster_pts['緯度'].mean()
        c_lon = cluster_pts['經度'].mean()
        
        folium.Circle(
            location=[c_lat, c_lon],
            radius=dbscan_radius,
            color='crimson',
            fill=True,
            fill_color='red',
            fill_opacity=0.25,
            popup=f"🔥 高密度熱區 #{cluster_id + 1}<br>包含 {len(cluster_pts)} 台 AED"
        ).add_to(hotspot_group)

    # ⚡ 3. 標示各 AED 點位 (依熱/冷區變色)
    marker_cluster = MarkerCluster(name="📍 AED 點位").add_to(m)
    
    for idx, row in data.iterrows():
        z_type = row['區域型態']
        
        if z_type == '🔥 高密度熱區':
            color = 'orange'
            icon_style = "fire"
        elif z_type == '❄️ 高風險冷區 (醫療孤島)':
            color = 'cadetblue'
            icon_style = "exclamation-sign"
        else:
            color = 'blue'
            icon_style = "info-sign"
        
        popup_html = f"""
        <b>{row['場所名稱']}</b><br>
        <b>區域分類：</b>{z_type}<br>
        <b>地址：</b>{row.get('場所地址', '無')}<br>
        <b>最近急救醫院：</b>{row['最近急救醫院']}<br>
        <b>送醫距離：</b>{row['至最近醫院距離_公尺']:.1f} 公尺
        """
        
        folium.Marker(
            location=[row['緯度'], row['經度']],
            popup=popup_html,
            tooltip=f"{row['場所名稱']} ({z_type})",
            icon=folium.Icon(color=color, icon=icon_style)
        ).add_to(marker_cluster)
        
    folium.LayerControl().add_to(m)
    return m._repr_html_()

components.html(generate_hot_cold_map(final_df), height=550, scrolling=False)

st.markdown("---")

# 7. 多維度圖表分析區
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 🎯 空間區域型態占比 (熱區 vs 冷區)")
    if not final_df.empty:
        type_summary = final_df['區域型態'].value_counts().reset_index()
        type_summary.columns = ['區域型態', '點位數量']
        fig_pie = px.pie(type_summary, names='區域型態', values='點位數量', hole=0.4,
                         color='區域型態',
                         color_discrete_map={
                             '🔥 高密度熱區': '#ff4b4b',
                             '❄️ 高風險冷區 (醫療孤島)': '#1c83e1',
                             '🔹 一般單點涵蓋': '#708090'
                         })
        st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    st.markdown("#### 🏥 各急救責任醫院負責之冷熱區比例")
    if not final_df.empty:
        fig_bar = px.histogram(final_df, x='最近急救醫院', color='區域型態',
                               color_discrete_map={
                                   '🔥 高密度熱區': '#ff4b4b',
                                   '❄️ 高風險冷區 (醫療孤島)': '#1c83e1',
                                   '🔹 一般單點涵蓋': '#708090'
                               })
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# 8. 智慧決議與政策建議 (深度數據推理強化版)
st.subheader(f"💡 DBSCAN 空間決策與資源最佳化建議 ({selected_district})")

if not final_df.empty:
    total_aed = len(final_df)
    hotspots_count = len(final_df[final_df['區域型態'] == '🔥 高密度熱區'])
    coldspots_count = len(final_df[final_df['區域型態'] == '❄️ 高風險冷區 (醫療孤島)'])
    normal_count = len(final_df[final_df['區域型態'] == '🔹 一般單點涵蓋'])

    # 計算統計指標
    hotspot_ratio = (hotspots_count / total_aed) * 100 if total_aed > 0 else 0
    coldspot_ratio = (coldspots_count / total_aed) * 100 if total_aed > 0 else 0
    
    avg_dist = final_df['至最近醫院距離_公尺'].mean()
    max_dist = final_df['至最近醫院距離_公尺'].max()
    
    # 找出送醫距離最遠的極端場所 (醫療孤島代表)
    furthest_site = final_df.loc[final_df['至最近醫院距離_公尺'].idxmax()]
    furthest_site_name = furthest_site['場所名稱']
    furthest_site_hosp = furthest_site['最近急救醫院']
    
    # 計算醫院負載分佈 (找出承擔最多的醫院)
    hosp_vc = final_df['最近急救醫院'].value_counts()
    top_hosp_name = hosp_vc.index[0] if not hosp_vc.empty else "無"
    top_hosp_count = hosp_vc.iloc[0] if not hosp_vc.empty else 0
    top_hosp_ratio = (top_hosp_count / total_aed) * 100 if total_aed > 0 else 0

    # 呈現多維度數據指標摘要
    col_a, col_b, col_c = st.columns(3)
    col_a.info(f"**資源重複配置率**：{hotspot_ratio:.1f}% ({hotspots_count}/{total_aed} 處)")
    col_b.warning(f"**醫療冷區涵蓋率**：{coldspot_ratio:.1f}% ({coldspots_count}/{total_aed} 處)")
    col_c.success(f"**平均送醫直線距離**：{avg_dist:.1f} 公尺")

    st.markdown("---")

    # 動態深度分析報告與四階段行動方針
    st.markdown(f"""
    #### 🔍 **空間結構深度診斷分析**

    1. **過度集中與重複涵蓋評估**：
       - 目前 **{selected_district}** 在搜尋半徑 **{dbscan_radius} 公尺** 條件下，共有 **{hotspots_count}** 處 AED 點位（佔全區 **{hotspot_ratio:.1f}%**）處於高度密集聚落中。
       - 這顯示該區部分場域（如捷運站周邊、大型商場或行政中心）存在 **「資源過度重複配置」** 現象，在極短距離內有多台設備重疊涵蓋，效益邊際遞減。

    2. **醫療涵蓋盲區與極端孤島診斷**：
       - 本區共有 **{coldspots_count}** 處 AED（佔全區 **{coldspot_ratio:.1f}%**）被判定為高風險冷區。這些點位周邊缺乏鄰近 AED 支援，且距離急救責任醫院超過 **{cold_dist_threshold} 公尺**。
       - **極端案例警訊**：全區送醫距離最遠的點位為 **「{furthest_site_name}」**，距離最近的急救醫院（**{furthest_site_hosp}**）達 **{max_dist:.1f} 公尺**。若此處發生心肺功能停止（OHCA）事件，救護車抵達車程較長，極度仰賴現場第一時間的 CPR+AED 處置。

    3. **醫療後送負載集中度分析**：
       - 數據顯示，該區有 **{top_hosp_ratio:.1f}%**（共 {top_hosp_count} 處）的 AED 點位在地理上最鄰近 **「{top_hosp_name}」**。
       - 醫療資源後送責任顯著集中於特定院區，建議衛政單位需關注區域急診量能協調與責任區域分流。

    ---

    #### 🎯 **管理單位四階段行動優化策略 (Actionable Policy Roadmap)**

    * **📌 第一階段：資源盤點與優化移設（盤點熱區）**
      建議優先針對上述 **{hotspots_count} 处熱區點位** 進行現場使用率與租約盤點，研擬將重疊率過高、使用率偏低的 AED **遷移移設**至周邊 300~500 公尺內的住宅區、老舊社區或公園盲區。

    * **📌 第二階段：精準增設公眾 AED（補強冷區）**
      將 **「{furthest_site_name}」** 等 **{coldspots_count} 處高風險冷區** 列為優先輔導名單，運用政府補助或獎勵機制，鼓勵周邊私人機構（如大樓管理委員會、超商、加油站）參與公眾 AED 增設案。

    * **📌 第三階段：急救志工與 CPR+AED 培訓（強化韌性）**
      針對距離醫院超過 1.5 公里的冷區站點，推動 **「社區急救防護網」**。優先對該場所管理人員、社區志工及巡守隊進行急救認證培訓，確保在救護車抵達前的「黃金 4~6 分鐘」內能即時施救。

    * **📌 第四階段：動態智慧監控與資訊公開（數位治理）**
      持續結合本動態儀表板進行年度 AED 涵蓋率複查，並將最新 AED 正確座標與開放時間同步發布至「急救資訊 App」，提升民眾緊急狀況下的尋找效率。
    """)

else:
    st.warning("⚠️ 目前選擇的條件下無資料，無法提供系統建議。")

# 9. 展開檢視詳細資料表
with st.expander(f"📂 查看詳細熱冷區分類數據表 ({selected_district})"):
    st.dataframe(final_df[['行政區', '場所名稱', '區域型態', '最近急救醫院', '至最近醫院距離_公尺']])