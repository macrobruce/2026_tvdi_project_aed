import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

print("🚑 開始執行 step4：臺北市 18 家急救責任醫院醫療可及性分析...")

# 1. 讀取 step3 產出的 AED KNN 結果
df_aed = pd.read_csv('taipei_aed_knn_results.csv', encoding='utf-8-sig')

# 2. 建立臺北市官方完整 18 家急救責任醫院資料庫
hospitals_data = {
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
}
df_hosp = pd.DataFrame(hospitals_data)

# 3. 執行 KNN 跨資料集連線運算
aed_coords = np.radians(df_aed[['緯度', '經度']].values)
hosp_coords = np.radians(df_hosp[['緯度', '經度']].values)

knn = NearestNeighbors(n_neighbors=1, metric='haversine')
knn.fit(hosp_coords)

distances, indices = knn.kneighbors(aed_coords)

# 4. 寫回數據
earth_radius_m = 6371000
df_aed['至最近醫院距離_公尺'] = distances.flatten() * earth_radius_m
df_aed['最近急救醫院'] = df_hosp['醫院名稱'].iloc[indices.flatten()].values
df_aed['預估送醫車程_分鐘'] = df_aed['至最近醫院距離_公尺'] / 300.0

# 5. 儲存
output_file = 'taipei_aed_full_analysis.csv'
df_aed.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"✅ 成功計算 18 家醫院距離！檔案已更新為：{output_file}")