# 每小時國際重大訊息監控系統

## 狀態
- **系統架構**：✅ 已建立
- **網頁模板**：✅ 已創建  
- **自動化腳本**：✅ 已準備
- **Brave Search API**：⚠️ 需要 API key 設置

## 功能
- 每小時自動搜尋國際重大新聞
- 生成結構化 HTML 報告
- 自動發布到 pCloud 目錄
- 透過 Discord 發送通知

## 設置步驟
1. 運行 `openclaw configure --section web` 設置 Brave Search API key
2. 系統將自動啟用每小時新聞監控
3. 報告將發布到：`/home/admin/pCloudDrive/openclaw/public/news/`

## 報告格式
- 標題：國際重大訊息 - [日期時間]
- 內容：分類整理的重大新聞（政治、經濟、科技、災害等）
- 來源：可信的新聞網站和官方消息
- 更新頻率：每小時一次