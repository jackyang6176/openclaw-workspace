# 擬人化瀏覽器自動化框架

## 核心原則
1. **模擬真實用戶行為**：隨機延遲、自然滾動、人類般的點擊模式
2. **避免反爬蟲檢測**：不使用 API 直接呼叫，而是透過瀏覽器正常瀏覽
3. **多樣化資料來源**：直接從網站前端獲取資料，不依賴後端 API
4. **容錯與重試機制**：處理網路波動、頁面載入失敗等情況

## 支援的資料來源
- 新聞網站（BBC, Reuters, AP News, CNN, Al Jazeera）
- 天氣網站（wttr.in, AccuWeather, Weather.com）
- 財經網站（Yahoo Finance, Google Finance, Bloomberg）
- 社交媒體（Twitter, Reddit - 公開內容）

## 技術實現
- 使用 OpenClaw browser control with human-like behavior
- 隨機等待時間 (0.5-3秒)
- 自然滾動模式
- 智能元素定位（多種選擇器備用）
- 截圖驗證（確保內容正確載入）