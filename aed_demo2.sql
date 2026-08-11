USE AED_DB;
GO

-- 🔍 示範一：查詢 30 公尺內高度重疊點位 (重疊率 35.7%)
SELECT 
    場所名稱, 
    場所地址, 
    ROUND(第1近AED距離_公尺, 1) AS 鄰近AED距離_m, 
    最近急救醫院, 
    ROUND(至最近醫院距離_公尺, 1) AS 送醫距離_m
FROM dbo.datong_aed_full_analysis
WHERE 第1近AED距離_公尺 <= 30.0
ORDER BY 第1近AED距離_公尺 ASC;


-- 📊 示範二：統計急救責任醫院承接比率 (醫院後送分工)
SELECT 
    最近急救醫院,
    COUNT(*) AS 承接AED點位數,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dbo.datong_aed_full_analysis), 1) AS [承接百分比_%],
    ROUND(AVG(至最近醫院距離_公尺), 1) AS 平均送醫距離_m
FROM dbo.datong_aed_full_analysis
GROUP BY 最近急救醫院
ORDER BY 承接AED點位數 DESC;


-- 🚑 示範三：查詢送醫車程 2 分鐘以內的高可及性急救點位
SELECT 
    場所名稱, 
    最近急救醫院, 
    ROUND(至最近醫院距離_公尺, 1) AS 送醫距離_m, 
    ROUND(預估送醫車程_分鐘, 1) AS 預估車程_分
FROM dbo.datong_aed_full_analysis
WHERE 預估送醫車程_分鐘 <= 2.0
ORDER BY 預估送醫車程_分鐘 ASC;