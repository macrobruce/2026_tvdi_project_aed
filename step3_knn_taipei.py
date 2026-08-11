import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

print("🚀 開始執行 step3：台北市全區 AED 空間重疊分析 (KNN)...")

# 1. 讀取台北市 AED 資料
df = pd.read_csv('taipei_aed.csv', encoding='utf-8-sig')

# 確保排除沒有經緯度的無效資料
df = df.dropna(subset=['緯度', '經度']).copy()

# 2. 準備 KNN 模型 (使用 Haversine 計算球面真實距離)
# 必須先將經緯度轉換為弧度 (radians)
coords = np.radians(df[['緯度', '經度']].values)

# 設定 n_neighbors=2 (因為最近的點會是自己，所以要找第二近的)
knn = NearestNeighbors(n_neighbors=2, metric='haversine')
knn.fit(coords)

# 計算距離與索引
distances, indices = knn.kneighbors(coords)

# 3. 將弧度距離轉換為「公尺」 (地球平均半徑約 6,371 公里)
earth_radius_m = 6371000
df['第1近AED距離_公尺'] = distances[:, 1] * earth_radius_m

# 4. 儲存 KNN 分析結果
output_file = 'taipei_aed_knn_results.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"✅ step3 完成！所有 AED 點位的重疊距離已計算完畢。")
print(f"📁 檔案已儲存為：{output_file}")