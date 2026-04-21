# 盤中監控系統 - WebSocket 版本規格書
## Monitor Worker with WebSocket Specification

**版本：** v2.0  
**更新日期：** 2026-04-21  
**狀態：** 待開發

---

## 1. 目標

將盤中監控系統從 **HTTP API 輪詢** 改為 **WebSocket 訂閱**，實現真正的即時監控。

---

## 2. 技術架構

### 2.1 WebSocket 連線
- **API**: `sdk.marketdata.websocket_client.stock`
- **連線上限**: 每條連線可訂閱 **200 檔**
- ** Rate Limit**: 與 Web API 共用
- **初始化**: `sdk.init_realtime()`

### 2.2 連線配置
| 用途 | 連線數 | 訂閱數量 |
|------|--------|----------|
| 持倉監控 | 1 條 | 最多 5 檔 |
| 觀察名單監控 | 1 條 | 最多 200 檔 |

---

## 3. 盤中監控規則

### 3.1 進場條件（觀察名單股票）
需**同時滿足**以下條件才進場：

| # | 條件 | 說明 |
|---|------|------|
| **1** | MA5 > MA20 | 黃金交叉確認（技術指標查詢）|
| **2** | 現價 > MA5 | 價格站穩在均線之上 |
| **3** | 外盤 > 內盤 × 2 | 大單買入偵測（即時資料）|

### 3.2 庫存股票監控
| 條件 | 動作 |
|------|------|
| 現價 <= 停損價 | **自動停損卖出** |
| 現價 >= 目標價 | **自動獲利了結** |

---

## 4. 資料來源

### 4.1 即時資料（WebSocket 推送）
| 欄位 | 說明 |
|------|------|
| `lastPrice` | 現價 |
| `bidPrice` / `askPrice` | 買/賣價 |
| `bidQty` / `askQty` | 買/賣量 |
| `volume` | 成交量 |
| `insideVolume` | 內盤成交量 |
| `outsideVolume` | 外盤成交量 |

### 4.2 技術指標（HTTP API）
| 指標 | 說明 |
|------|------|
| MA5 | 5 日均線 |
| MA20 | 20 日均線 |

---

## 5. 實作架構

### 5.1 模組結構
```
monitor_websocket.py
├── WebSocketManager      # WebSocket 連線管理
│   ├── connect()          # 建立連線
│   ├── subscribe()         # 訂閱股票
│   ├── unsubscribe()      # 取消訂閱
│   └── add_handler()      # 設定回調
│
├── SignalChecker         # 進場信號檢查
│   ├── check_entry()     # 檢查進場條件
│   ├── check_ma_cross()   # MA5 > MA20 確認
│   └── check_big_order()  # 大單偵測
│
├── PositionMonitor       # 持倉監控
│   ├── check_stop_loss()  # 停損檢查
│   └── check_target()     # 目標檢查
│
└── main()               # 主程式
```

### 5.2 WebSocket 回調函數
```python
def on_tick(data):
    """
    data 包含:
    - symbol: 股票代碼
    - lastPrice: 現價
    - insideVolume: 內盤成交量
    - outsideVolume: 外盤成交量
    """
    # 1. 更新現價
    # 2. 計算內外盤比
    # 3. 檢查進場條件或持倉狀態
```

### 5.3 Rate Limit 處理
- WebSocket 與 HTTP API 共用 Rate Limit
- HTTP API 查詢 MA 時仍需延遲
- 建議：`time.sleep(10)` 在每次技術指標查詢後

---

## 6. 錯誤處理

### 6.1 例外處理（依 LLM 文件）
```python
from fubon_neo.fugle_marketdata.rest.base_rest import FugleAPIError

try:
    # API 呼叫
except FugleAPIError as e:
    print(f"Error: {e}")
    print(f"Status Code: {e.status_code}")  # 429 = Rate Limit
    print(f"Response: {e.response_text}")
```

### 6.2 WebSocket 斷線處理
- 斷線時自動重連
- 最多重試 3 次
- 每次重試等候 60 秒

---

## 7. 輸出檔案

| 檔案 | 說明 |
|------|------|
| `/tmp/trading_status.json` | 持倉與進場信號狀態 |
| `/tmp/trading_websocket.log` | WebSocket 執行日誌 |

---

## 8. Cron Job

維持現有設定：
```
*/5 9-13 * * 1-5 cd /home/admin/.openclaw/workspace/stock-screener && python3 monitor_websocket.py
```

---

## 9. 依賴檔案

| 檔案 | 位置 |
|------|------|
| `fubon_complete.py` | `/home/admin/.openclaw/workspace/fubon_sdk_complete/` |
| `watchlist.json` | `/home/admin/.openclaw/workspace/stock-screener/` |

---

## 10. 備註

- 內外盤比：`outsideVolume / insideVolume > 2` 視為大單買入
- MA 查詢使用 `get_sma()` from `fubon_complete.py`
- WebSocket 推送為逐筆資料，需自行計算內外盤累計值
