import pandas as pd
import folium
from folium import plugins

# 1. 讀取包含完整 KNN 分析的 CSV 資料
df = pd.read_csv('datong_aed_full_analysis.csv')

# 2. 以大同區中心點 (約緯度 25.063, 經度 121.513) 建立 Folium 地圖物件
map_datong = folium.Map(
    location=[25.063, 121.513],
    zoom_start=14,
    tiles='OpenStreetMap'
)

# 3. 標註急救責任醫院 (綠色十字 Icon)
hospitals = [
    {'名稱': '馬偕紀念醫院(台北院區)', 'lat': 25.0583, 'lon': 121.5222},
    {'名稱': '臺北市立聯合醫院(中興院區)', 'lat': 25.0508, 'lon': 121.5097},
    {'名稱': '臺北市立聯合醫院(陽明院區)', 'lat': 25.1053, 'lon': 121.5312},
    {'名稱': '新光吳火獅紀念醫院', 'lat': 25.0931, 'lon': 121.5206},
    {'名稱': '國立臺灣大學醫學院附設醫院', 'lat': 25.0413, 'lon': 121.5186}
]

for hosp in hospitals:
    folium.Marker(
        location=[hosp['lat'], hosp['lon']],
        popup=f"<b>🏥 急救責任醫院：{hosp['名稱']}</b>",
        tooltip=hosp['名稱'],
        icon=folium.Icon(color='green', icon='plus', prefix='fa')
    ).add_to(map_datong)

# 4. 逐一加入大同區 112 個 AED 標點
for idx, row in df.iterrows():
    loc_name = row['場所名稱']
    address = row['場所地址']
    dist_aed = row['第1近AED距離_公尺']
    hosp_name = row['最近急救醫院']
    dist_hosp = row['至最近醫院距離_公尺']
    lat = row['緯度']
    lon = row['經度']
    
    # 建立彈出視窗內容
    popup_text = f"""
    <div style="font-family: Arial, sans-serif; width: 220px;">
        <h4 style="margin: 0 0 5px 0; color: #333;">{loc_name}</h4>
        <p style="margin: 2px 0; font-size: 12px; color: #666;"><b>地址:</b> {address}</p>
        <hr style="margin: 5px 0;">
        <p style="margin: 2px 0; font-size: 12px;"><b>最近 AED 距離:</b> <span style="color: red; font-weight: bold;">{dist_aed} m</span></p>
        <p style="margin: 2px 0; font-size: 12px;"><b>最近急救醫院:</b> {hosp_name}</p>
        <p style="margin: 2px 0; font-size: 12px;"><b>送醫距離:</b> {dist_hosp} m</p>
    </div>
    """
    
    # 判斷是否為「過度密集重疊點」(距離 30m 內)
    if dist_aed <= 30.0:
        # 紅色標點（警告）
        marker_color = 'red'
        icon_name = 'exclamation-triangle'
    else:
        # 藍色標點（正常）
        marker_color = 'blue'
        icon_name = 'heartbeat'
        
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=f"{loc_name} (鄰近AED: {dist_aed}m)",
        icon=folium.Icon(color=marker_color, icon=icon_name, prefix='fa')
    ).add_to(map_datong)

# 5. 儲存地圖為可獨立開啟的 HTML 檔案
output_map = 'datong_aed_interactive_map.html'
map_datong.save(output_map)

print(f"🎉 成功生成互動式地圖！檔案已儲存為：{output_map}")
print("💡 請在檔案總管雙擊點開這個 .html 檔，即可在 Chrome/Edge 瀏覽器中查看地圖！")