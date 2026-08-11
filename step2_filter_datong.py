import pandas as pd

# 1. 讀取原始資料
file_name = '115年6月.csv'
try:
    df = pd.read_csv('115年6月.csv', encoding='utf-8-sig')
except UnicodeDecodeError:
    df = pd.read_csv('115年6月.csv', encoding='cp950')

# 2. 將「區域代碼」轉為字串格式，並篩選大同區 (代碼為 63000060 或地址含大同區)
df['區域代碼'] = df['區域代碼'].astype(str)

# 雙重鎖定：區域代碼為 63000060，或者地址裡有大同區
datong_df = df[(df['區域代碼'] == '63000060') | (df['場所地址'].str.contains('大同區', na=False))]

# 3. 印出正確篩選結果
print(f"🎯 成功鎖定大同區！總共有 {datong_df.shape[0]} 筆 AED 設置點！")

# 4. 存成全新且乾淨的 CSV 檔案 (utf-8-sig 編碼)
output_name = 'datong_aed.csv'
datong_df.to_csv(output_name, encoding='utf-8-sig', index=False)

print(f"💾 檔案已儲存為：{output_name}")