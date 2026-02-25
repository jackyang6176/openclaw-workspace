# pCloud 儲存配置

## 主要目錄映射
- 投資報告: `/home/admin/pCloudDrive/openclaw/web/investment/`
- 旅遊網頁: `/home/admin/pCloudDrive/openclaw/web/travel/`
- 一般網頁: `/home/admin/pCloudDrive/openclaw/web/`
- 備份檔案: `/home/admin/pCloudDrive/openclaw/backup/`

## 工作流程
1. 所有對外檔案直接生成到 pCloud 目錄
2. 不再使用本地 /var/www 或其他實體硬碟位置
3. 網域名稱 aiothome.top 指向 pCloud 內容
4. 本地只保留工作過程中的臨時檔案

## 網址映射
- http://aiothome.top/investment/ → pCloud investment/
- http://aiothome.top/travel/ → pCloud travel/
- http://aiothome.top/ → pCloud web/

## 注意事項
- pCloud 同步可能有延遲，重要操作需確認同步完成
- 本地工作空間仍用於處理和計算
- 最終輸出直接寫入 pCloud 目錄