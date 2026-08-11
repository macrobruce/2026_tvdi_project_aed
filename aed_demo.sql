USE AED_DB;
GO

-- 🔍 查詢大同區 30 公尺內高度重疊的 AED 點位
SELECT 
    場所名稱, 
    場所地址, 
    第1近AED距離_公尺, 
    最近急救醫院, 
    至最近醫院距離_公尺
FROM dbo.datong_aed_full_analysis
WHERE 第1近AED距離_公尺 <= 30.0
ORDER BY 第1近AED距離_公尺 ASC;