import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

# 1. 讀取台北市 AED 資料
df = pd.read_csv('taipei_aed.csv', encoding='utf-8-sig').dropna(subset=['緯度', '經度'])

# 2. 將經緯度轉為弧度 (radians)
coords = np.radians(df[['緯度', '經度']].values)

# 3. 設定 DBSCAN 參數
# 地球平均半徑 6,371,000 公尺
kms_per_radian = 6371000.0

# 設定搜尋半徑 eps = 50 公尺，最小點數 min_samples = 3 台
epsilon_meters = 50.0
eps_rad = epsilon_meters / kms_per_radian

db = DBSCAN(eps=eps_rad, min_samples=3, metric='haversine').fit(coords)

# 4. 將分群結果寫回資料表 (-1 代表離群點/孤島，0, 1, 2... 代表不同的高密度熱區群集)
df['DBSCAN_Cluster'] = db.labels_

# 5. 印出統計摘要
n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
n_noise = list(db.labels_).count(-1)

print(f"✅ DBSCAN 分析完成！在半徑 {epsilon_meters} 公尺條件下：")
print(f"📊 共辨識出 {n_clusters} 個 AED 高密度重複熱區群集")
print(f"⚠️ 共發現 {n_noise} 處獨立涵蓋的盲區/孤島點位 (Noise)")

df.to_csv('taipei_aed_dbscan_results.csv', index=False, encoding='utf-8-sig')