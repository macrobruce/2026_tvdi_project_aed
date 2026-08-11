import pandas as pd
import numpy as np
from pyproj import Transformer
from sklearn.neighbors import NearestNeighbors

# 1. 讀取步驟三產生的帶有 AED KNN 距離的成果檔案
df = pd.read_csv('datong_aed_knn_results.csv')

# 2. 建立台北市大同區及周邊主要急救責任醫院名單與坐標 (WGS84 經緯度)
hospitals_data = [
    {'醫院名稱': '馬偕紀念醫院(台北院區)', '緯度': 25.0583, '經度': 121.5222},
    {'醫院名稱': '臺北市立聯合醫院(中興院區)', '緯度': 25.0508, '經度': 121.5097},
    {'醫院名稱': '臺北市立聯合醫院(陽明院區)', '緯度': 25.1053, '經度': 121.5312},
    {'醫院名稱': '新光吳火獅紀念醫院', '緯度': 25.0931, '經度': 121.5206},
    {'醫院名稱': '國立臺灣大學醫學院附設醫院', '緯度': 25.0413, '經度': 121.5186}
]
hosp_df = pd.DataFrame(hospitals_data)

# 3. 座標轉換至 TWD97 平面坐標 (EPSG:3826)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)

# AED 坐標轉換
aed_x, aed_y = transformer.transform(df['經度'].values, df['緯度'].values)
aed_coords = np.column_stack((aed_x, aed_y))

# 醫院坐標轉換
hosp_x, hosp_y = transformer.transform(hosp_df['經度'].values, hosp_df['緯度'].values)
hosp_coords = np.column_stack((hosp_x, hosp_y))

# 4. 建立 KNN 模型 (K=1，尋找距離每台 AED 最近的 1 間急救責任醫院)
knn_hosp = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(hosp_coords)
hosp_distances, hosp_indices = knn_hosp.kneighbors(aed_coords)

# 5. 填入最近醫院名稱與直線距離 (公尺)
df['最近急救醫院'] = hosp_df.iloc[hosp_indices[:, 0]]['醫院名稱'].values
df['至最近醫院距離_公尺'] = np.round(hosp_distances[:, 0], 1)

# 假設救護車平均時速約 30 km/h (相當於每分鐘 500 公尺)，計算預估送醫時間 (分鐘)
df['預估送醫車程_分鐘'] = np.round(df['至最近醫院距離_公尺'] / 500, 1)

# 6. 印出統計摘要
print("=" * 60)
print("🚑 大同區 AED 點位至最近急救責任醫院 (KNN送醫鏈) 分析結果：")
print(f"• 大同區 AED 至最近醫院平均直線距離：{df['至最近醫院距離_公尺'].mean():.1f} 公尺")
print(f"• 最近醫院距離最小值：{df['至最近醫院距離_公尺'].min():.1f} 公尺")
print(f"• 最近醫院距離最大值：{df['至最近醫院距離_公尺'].max():.1f} 公尺")
print("=" * 60)

print("\n🏥 承接大同區急救送醫的主要責任醫院分布統計：")
print(df['最近急救醫院'].value_counts().to_string())

# 7. 儲存終極綜合分析結果
output_final = 'datong_aed_full_analysis.csv'
df.to_csv(output_final, encoding='utf-8-sig', index=False)
print(f"\n💾 包含「AED近鄰距離」與「醫院送醫鏈」的完整資料已儲存為：{output_final}")