import pandas as pd

print("開始讀取原始資料...")

# 1. 讀取全台原始資料 (相容不同編碼)
try:
    df = pd.read_csv('115年6月.csv', encoding='utf-8-sig')
except UnicodeDecodeError:
    df = pd.read_csv('115年6月.csv', encoding='cp950')

# 2. 篩選全台北市 (台北市的區域代碼都是 63000 開頭)
# 先將區域代碼轉為字串，確保不會因為空值報錯
df['區域代碼'] = df['區域代碼'].fillna(0).astype(int).astype(str)
taipei_df = df[df['區域代碼'].str.startswith('63000')]

# 3. 儲存為台北市專用的 CSV
output_file = 'taipei_aed.csv'
taipei_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"✅ 成功篩選全台北市資料！共找到 {len(taipei_df)} 筆 AED 點位。")
print(f"📁 檔案已儲存為：{output_file}")