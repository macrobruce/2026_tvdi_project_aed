import pandas as pd

# 告訴 Python 我們的檔案名稱是什麼
file_name = '115年6月.csv'

try:
    # 使用涵蓋更廣的中文字元集 cp950 來讀取檔案
    df = pd.read_csv(file_name, encoding='cp950')
    
    print("✅ 太棒了！成功讀取資料！\n")
    
    # 印出資料的總筆數 (列數) 與欄位數
    print(f"📊 這份資料總共有 {df.shape[0]} 筆 AED 地點，包含 {df.shape[1]} 個欄位。")
    
    # 印出所有的欄位名稱，讓我們知道手邊有哪些資料可以用
    print("📝 欄位名稱如下：")
    print(df.columns.tolist())
    
except Exception as e:
    print("❌ 讀取失敗，錯誤訊息：", e)