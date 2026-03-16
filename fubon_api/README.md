# 富邦 Neo API 整合專案

## 📋 專案狀態

| 項目 | 狀態 | 說明 |
|------|------|------|
| SDK 安裝 | ✅ 完成 | v2.2.8 |
| 環境配置 | ✅ 完成 | 目錄結構建立 |
| 認證配置 | ⏸️ 等待 | 等待用戶填寫 credentials.json |
| 連線測試 | ⏸️ 等待 | 等待認證配置完成 |
| 數據獲取 | ⏸️ 等待 | 等待連線測試成功 |

## 📁 目錄結構

```
fubon_api/
├── config/
│   ├── credentials.json.example    # 配置範本
│   └── credentials.json            # 真實配置（需手動建立，不上傳 Git）
├── tests/
│   └── test_connection.py          # 連線測試腳本
├── logs/                           # 日誌目錄
└── README.md                       # 本文件
```

## 🚀 快速開始

### 1. 安裝 SDK（已完成）

```bash
pip install /tmp/fubon_neo-2.2.8-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

### 2. 配置認證

```bash
cd /home/admin/.openclaw/workspace/fubon_api/config
cp credentials.json.example credentials.json
# 編輯 credentials.json，填入真實認證資訊
```

### 3. 測試連線

```bash
cd /home/admin/.openclaw/workspace/fubon_api/tests
python3 test_connection.py
```

### 4. 獲取持倉數據

連線成功後，可以開始獲取持倉數據。

## 🔐 認證方式

### 方式 1：網頁憑證匯出（推薦）

1. 登入富邦證券電子平台
2. 申請網頁版憑證
3. 匯出憑證檔案
4. 在 `credentials.json` 中填入憑證路徑和密碼

### 方式 2：API Key（v2.2.7+）

1. 登入富邦證券電子平台
2. 申請 API Key
3. 在 `credentials.json` 中填入 API Key

## 📊 支援的功能

| 功能 | API | 狀態 |
|------|-----|------|
| 即時行情 | `/intraday/quote/{symbol}` | ✅ 支援 |
| 歷史行情 | `/historical/candles/{symbol}` | ✅ 支援 |
| 持倉查詢 | `sdk.account.get_balance()` | ✅ 支援 |
| 下單交易 | `sdk.stock.place_order()` | ✅ 支援 |
| 條件單 | `TPSLOrder` | ✅ 支援 |

## 🔒 安全注意事項

1. **切勿上傳** `credentials.json` 至版本控制
2. **加密儲存** 認證資訊
3. **定期更新** API Key 或憑證
4. **限制權限** 檔案權限設為 600

```bash
chmod 600 /home/admin/.openclaw/workspace/fubon_api/config/credentials.json
```

## 📝 待辦事項

- [ ] 填寫 `credentials.json`
- [ ] 執行 `test_connection.py` 驗證連線
- [ ] 獲取持倉數據（00655L、00882、00887）
- [ ] 整合 VERIFIER 驗證機制
- [ ] 生成投資分析報告

## 📞 參考資源

- [富邦 Neo API 官方文件](https://www.fbs.com.tw/TradeAPI/)
- [LLM 友善完整文件](https://www.fbs.com.tw/TradeAPI/llms-full.txt)
- [安裝與版本相容性](https://www.fbs.com.tw/TradeAPI/docs/install-compatibility.md)
- [快速開始指南](https://www.fbs.com.tw/TradeAPI/docs/trading/quickstart.md)

---

**最後更新**：2026-02-26  
**狀態**：環境準備完成，等待認證配置
