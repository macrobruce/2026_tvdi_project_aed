import pandas as pd

# 讀取原始檔案
df = pd.read_csv('115年6月.csv', encoding='cp950')

print("🔍 1. 前 10 筆地址長怎樣：")
print(df['場所地址'].head(10))

print("\n🔍 2. 「區域代碼」欄位前 10 名的內容與數量：")
print(df['區域代碼'].value_counts().head(10))