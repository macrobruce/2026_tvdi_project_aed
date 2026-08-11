import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

print("🚑 開始執行 step4：台北市全區 AED 醫療可及性分析 (距離急救醫院)...")

# 1. 讀取 step3 產出的 AED KNN 結果
df_aed = pd.read_csv('taipei_aed_knn_results.csv', encoding='utf-8-sig')

# 2. 建立台北市主要急救責任醫院資料庫 (核心醫療網)
hospitals_data = {
    '醫院名稱': [
        '臺大醫院', '馬偕紀念醫院(台北院區)', '臺北榮民總醫院', '三軍總醫院(內湖)',
        '臺北長庚醫院', '新光醫院', '臺北市立聯合醫院(中興院區)', '萬芳醫院', 
        '臺北醫學大學附設醫院', '國泰綜合醫院', '臺北市立聯合醫院(仁愛院區)', '臺北市立聯合醫院(和平院區)'
    ],
    '緯度': [
        25.040, 25.058, 25.120, 25.068, 25.054, 25.093, 25.050, 24.998, 
        25.026, 25.037, 25.037, 25.035
    ],
    '經度': [
        121.516, 121.522, 121.520, 121.593, 121.549, 121.517, 121.509, 121.557, 
        121.561, 121.552, 121.544, 121.505
    ]
}
df_hosp = pd.DataFrame(hospitals_data)

# 3. 準備跨資料集 KNN 運算
aed_coords = np.radians(df_aed[['緯度', '經度']].values)
hosp_coords = np.radians(df_hosp[['緯度', '經度']].values)

# 這次 n_neighbors=1，因為是跨資料集尋找最近的一家醫院
knn = NearestNeighbors(n_neighbors=1, metric='haversine')
knn.fit(hosp_coords) # 將醫院設為目標模型

# 尋找每個 AED 最近的醫院
distances, indices = knn.kneighbors(aed_coords)

# 4. 資料合併與轉換
earth_radius_m = 6371000
df_aed['至最近醫院距離_公尺'] = distances.flatten() * earth_radius_m
df_aed['最近急救醫院'] = df_hosp['醫院名稱'].iloc[indices.flatten()].values

# 估算救護車送醫車程 (考量市區紅綠燈與車流，以平均時速約 18km/h = 300公尺/分鐘 估算)
df_aed['預估送醫車程_分鐘'] = df_aed['至最近醫院距離_公尺'] / 300.0

# 5. 儲存最終整合分析檔案
output_file = 'taipei_aed_full_analysis.csv'
df_aed.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"✅ step4 完成！AED 與醫院連線計算完畢。")
print(f"📁 終極分析檔已儲存為：{output_file}")