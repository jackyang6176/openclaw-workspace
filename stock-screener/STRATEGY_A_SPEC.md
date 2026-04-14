# 策略A - 技術動能篩選 規格書

_建立日期：2026-04-14_
_最後更新：2026-04-14_

---

## 一、策略說明

短線技術動能策略，專注於「MA5 向上攻擊、成交量配合放量、KD 超跌」的股票。

---

## 二、进場條件（需同時滿足）

| # | 條件 | 說明 |
|---|------|------|
| 1 | MA5 斜率 > 0 | MA5 在**最近3個交易日**連續上升（向上攻擊）|
| 2 | Gap < 2% | (MA20 - MA5) / MA20 < 2% |
| 3 | Gap 三日縮小 | MA5 逐漸逼近 MA20（差距越來越小）|
| 4 | 成交量連三日放大 | **最近4個交易日**絕對值逐日增加（今日 > 昨日 > 前日 > 大前日）|
| 4b | 日均成交張數 >= 1000 | **過去4天日平均成交量** >= 1000 張（使用 candles volume 計算）|
| 5 | K < 25 且 D < 25 | **最近3個交易日**每天都 K<25 且 D<25（超跌狀態）|

---

## 三、进場時機

- 價格**接近 MA20**（Gap < 2%）時進場
- MA5 向上攻擊中，成交量配合放大
- KD 低於 25 超跌狀態
- 適合埋伏，等待突破

---

## 四、出場規則

| 規則 | 條件 |
|------|------|
| **停損** | 進場價 -5%（剛性執行，不請示）|
| **止盈** | 進場價 +10%（到達後了結）|

---

## 五、風險控制

- 每檔投入：根據帳戶可用餘額計算可買張數（1張=1000股）
- 最大同時持倉：5 檔
- 操作策略：純短線，紀律導向，失敗就停損，不留、不攤、不凹

---

## 六、資料來源與 API

### 1. TWSE（臺灣證券交易所）

| 項目 | 內容 |
|------|------|
| URL | `https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={YYYYMMDD}&type=ALL&response=json` |
| 用途 | 取得股票**清單 + 今日收盤價** |
| 呼叫次數 | **1 次**（一次取得全市場，約1,316檔）|
| Rate Limit | **無** |

### 2. 富邦 Fubon SDK

| # | API | 取得的資料 |
|---|-----|---------|
| API 1 | `sdk.marketdata.rest_client.stock.technical.sma(period=5, from, to)` | MA5 值陣列（取 10 天，回傳8-10筆，取最近3個交易日）|
| API 2 | `sdk.marketdata.rest_client.stock.technical.sma(period=20, from, to)` | MA20 值 |
| API 3 | `sdk.marketdata.rest_client.stock.technical.kdj(from, to)` | K/D 值陣列（取 10 天，回傳8-10筆，取最近3個交易日）|
| API 4 | `sdk.marketdata.rest_client.stock.historical.candles(from, to)` | 成交量（取 10 天，回傳8-10筆，取最近4個交易日計算日均量）|

> ⚠️ 注意：candles 的 `volume` 欄位是**股數**（非張數）。
> 1 張 = 1000 股，所以 1000 張 = 1,000,000 股。
> 日均量計算：sum(最近4天volume) / 4
| Rate Limit | **60 次/分鐘**（每呼叫間隔 ≥ 1 秒）|
| 每檔呼叫 | **4 次**（sma5 + sma20 + kdj + candles）|

#### 資料取法

```python
# 一次取 10 天，取「最近 3-4 個交易日」來判斷
data = api.sma(period=5, from='2026-04-01', to='2026-04-14')

# 取陣列最後3筆 = 最近3個交易日
recent_3 = data[-3:]

# MA5 斜率：三天連續上升
ma5_day1 = recent_3[0]['sma']   # 三天前
ma5_day2 = recent_3[1]['sma']   # 兩天前
ma5_day3 = recent_3[2]['sma']   # 今天
slope_positive = (ma5_day3 > ma5_day2 > ma5_day1)

# KDJ：每天都 K<25 且 D<25
all_kd_below_25 = all(
    kdj['k'] < 25 and kdj['d'] < 25
    for kdj in recent_3_kdj
)

# 成交量：日均張數 >= 1000
# candles volume 是股數，1張=1000股
recent_4_volumes = [candle['volume'] for candle in candles_data[-4:]]
avg_volume_shares = sum(recent_4_volumes) / 4
avg_volume_lots = avg_volume_shares / 1000
volume_sufficient = (avg_volume_lots >= 1000)
```

> ⚠️ 注意：一次取 10 天，再用**陣列最後 3-4 筆**取「最近交易日」，可避免長假問題。

---

## 十一、追蹤清單管理

### 追蹤清單更新規則

| # | 規則 | 說明 |
|---|------|------|
| 1 | **庫存股票** | 自動保留（無論是否符合策略）|
| 2 | **新篩選結果** | 符合策略的股票加入清單 |
| 3 | **上限** | 庫存 + 新篩選結果 **最多 20 檔** |
| 4 | **優先順序** | 庫存股票 > 新篩選結果（按信心度排序）|

### 運作方式（舉例）

| 情況 | 庫存 | 新篩選 | 總數 | 結果 |
|------|------|--------|------|------|
| 正常 | 2 檔 | 5 檔符合 | 7 檔 | 全部保留 |
| 超出 | 2 檔 | 20 檔符合 | 22 檔 | 只取前 18 檔新篩選湊滿 20 |
| 庫存已達 20 | 20 檔 | 10 檔符合 | 30 檔 | 不加入新篩選結果 |

---

## 七、API Rate Limit 速查表

| API 類別 | Rate Limit | 每呼叫間隔 |
|---------|-----------|-----------|
| 日內行情 (intraday) | 300 次/分鐘 | ≥ 0.2 秒 |
| 行情快照 (snapshot) | 300 次/分鐘 | ≥ 0.2 秒 |
| 歷史行情 (historical) | 60 次/分鐘 | ≥ 1 秒 |
| 技術指標 (technical) | 60 次/分鐘 | ≥ 1 秒 |

> ⚠️ 注意：SMA/KDJ/RSI/MACD 屬於「技術指標」，不是「歷史行情」，但兩者 Rate Limit 相同（60 次/分鐘）。

---

## 八、掃描執行方式

| 項目 | 說明 |
|------|------|
| **執行時間** | 每日 **14:30**（收盤後，設定 Cron Job）|
| 股票範圍 | 上市櫃股票 + ETF（~1,316 檔）|
| 每檔 API 呼叫 | **4 次**（sma5 + sma20 + kdj + candles）|
| 每呼叫間隔 | **1 秒**（遵守 Rate Limit）|
| 預計總耗時 | ~88 分鐘（1,316 檔 × 4 次 × 1 秒）|
| **輸出** | 追蹤清單（每日更新，供下一交易日參考）|

---

## 九、嚴格禁止事項

- ❌ 使用 Yahoo Finance
- ❌ 使用 FinMind API
- ❌ 使用 Fugle API（非 SDK 內建）
- ❌ 自行猜測或估算資料，應如實說「資料取得失敗」
- ❌ 違反 Rate Limit 規定

---

## 十二、开发确认清单

- [x] Rate Limit 限制已确认
- [x] Fubon SDK API 已确认（SMA + KDJ + candles）
- [x] 策略逻辑确认（MA5斜率>0 + Gap<2% + Gap三日缩小 + 連三日量增 + KD<25）
- [x] 追蹤清單规则已确认（庫存保留 + 新篩選最多20檔）
- [ ] 规格文件确认（少爺说OK后开工）

---

_規格建立：阿福（Alfred）_
_審核：蝙蝠俠（nooya）_
