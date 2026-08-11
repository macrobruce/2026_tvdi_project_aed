import pandas as pd
import numpy as np
from pyproj import Transformer
from sklearn.neighbors import NearestNeighbors

# 1. 讀取剛才產生的 112 筆大同區 AED 資料
df = pd.read_csv('datong_aed.csv')

# 2. 將經緯度 (WGS84) 轉為台灣平面坐標 TWD97 (EPSG:3826)，這樣計算出來的距離才是正確的「公尺」
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
x_coords, y_coords = transformer.transform(df['經度'].values, df['緯度'].values)

# 組合平面 X, Y 座標陣列
coords = np.column_stack((x_coords, y_coords))

# 3. 建立 KNN 模型 (K=4 代表：包含點自己本身，以及最近的第 1、2、3 個鄰居)
knn = NearestNeighbors(n_neighbors=4, algorithm='kd_tree').fit(coords)
distances, indices = knn.kneighbors(coords)

# 4. 將距離運算結果填入 DataFrame (第 0 欄是自己到自己 = 0 公尺，取第 1、2、3 欄)
df['第1近AED距離_公尺'] = np.round(distances[:, 1], 1)
df['第2近AED距離_公尺'] = np.round(distances[:, 2], 1)
df['第3近AED距離_公尺'] = np.round(distances[:, 3], 1)

# 5. 印出大同區 AED 密集度統計結果
total_count = len(df)
count_30m = (df['第1近AED距離_公尺'] <= 30).sum()
count_50m = (df['第1近AED距離_公尺'] <= 50).sum()

print("=" * 50)
print("📊 大同區 AED 空間近鄰 (KNN) 分析結果：")
print(f"• 大同區分析地點總數：{total_count} 處")
print(f"• 距離 30 公尺以內就有另一台 AED：{count_30m} 處 (約 {count_30m/total_count*100:.1f}%)")
print(f"• 距離 50 公尺以內就有另一台 AED：{count_50m} 處 (約 {count_50m/total_count*100:.1f}%)")
print("=" * 50)

print("\n📍 大同區最密集的 5 個地點與近鄰距離範例：")
sample_display = df.sort_values(by='第1近AED距離_公尺')[
    ['場所名稱', '第1近AED距離_公尺', '第2近AED距離_公尺', '第3近AED距離_公尺']
].head(5)
print(sample_display.to_string(index=False))

# 6. 儲存帶有 KNN 距離欄位的完整結果檔
output_file = 'datong_aed_knn_results.csv'
df.to_csv(output_file, encoding='utf-8-sig', index=False)
print(f"\n💾 完整 KNN 分析成果已儲存為：{output_file}")