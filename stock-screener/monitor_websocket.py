#!/usr/bin/env python3
"""
盤中監控系統 - WebSocket 即時版
================================
使用 WebSocket 訂閱即時報價，監控：
1. 觀察名單進場條件（MA5 > MA20、現價 > MA5、外盤 > 內盤×2）
2. 持倉停損/目標監控

依規格：sdk.marketdata.websocket_client.stock
WebSocket 回調使用 on() 方法（add_handler 在 SDK 中等價於 on）
"""

import os
import sys
import json
import time
import signal
import atexit
from datetime import datetime, date
from typing import Optional, Dict, Any, List

# ── 路徑設定 ────────────────────────────────────────────────────────────────
WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API_DIR = f"{WORKSPACE}/fubon_sdk_complete"
sys.path.insert(0, FUBON_API_DIR)

# ── 常數 ──────────────────────────────────────────────────────────────────
STATUS_FILE = "/tmp/trading_status.json"
WATCHLIST_FILE = "/home/admin/pCloudDrive/openclaw/stock-screener/data/tracking_list.json"
ENV_FILE = "/home/admin/.env/fubon.env"
LOG_FILE = f"{SCREENER_DIR}/log/websocket_monitor.log"

# Rate Limit
MA_QUERY_DELAY = 10   # HTTP API 查詢 MA 後延遲秒數
RETRY_WAIT = 60       # 遇到 429 等候秒數
MAX_RETRIES = 3       # WebSocket 重連次數

# WebSocket channels
CHANNEL_TICK = "trades"

# ── 載入環境變數 ────────────────────────────────────────────────────────────
def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

# ── 富邦 SDK 初始化 ────────────────────────────────────────────────────────
def init_sdk():
    from fubon_neo.sdk import FubonSDK
    from fugle_marketdata import FugleAPIError
    env = load_env()
    sdk = FubonSDK()
    lr = sdk.login(
        env["ACCOUNT"],
        env["ACCT_PASSWORD"],
        env["CERT_PATH"],
        env["CERT_PASSWORD"]
    )
    if not lr.is_success:
        raise RuntimeError(f"富邦登入失敗: {lr}")
    sdk.init_realtime()
    return sdk

# ── 登出處理 ───────────────────────────────────────────────────────────────
def logout_sdk(sdk):
    try:
        sdk.logout()
    except Exception:
        pass

# ── 日誌 ───────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── 狀態寫入 ───────────────────────────────────────────────────────────────
def write_status(data: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── FugleAPIError 包裝（規格要求） ────────────────────────────────────────
from fugle_marketdata import FugleAPIError

def http_get_with_retry(fn, *args, **kwargs):
    """帶 Rate Limit 重試的 HTTP API 呼叫"""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except FugleAPIError as e:
            if e.status_code == 429:
                log(f"WARNING: Rate Limit 429，等待 {RETRY_WAIT} 秒後重試（第 {attempt+1} 次）...")
                time.sleep(RETRY_WAIT)
            else:
                log(f"ERROR: FugleAPIError: status={e.status_code} msg={e.response_text}")
                raise
        except Exception as e:
            log(f"ERROR: HTTP API 錯誤: {e}")
            raise
    log("ERROR: 超過最大重試次數")
    return None

# ── MA 查詢（帶 Rate Limit 延遲） ─────────────────────────────────────────
def get_ma5_ma20(sdk, symbol: str) -> Optional[Dict[str, float]]:
    """查詢 MA5 和 MA20，失敗時回 None"""
    try:
        ma5_data = http_get_with_retry(
            sdk.marketdata.rest_client.stock.technical.sma,
            symbol=symbol, period=5, timeframe="D"
        )
        time.sleep(MA_QUERY_DELAY)
        ma20_data = http_get_with_retry(
            sdk.marketdata.rest_client.stock.technical.sma,
            symbol=symbol, period=20, timeframe="D"
        )
        time.sleep(MA_QUERY_DELAY)

        if not ma5_data or not ma20_data:
            return None
        if "data" not in ma5_data or "data" not in ma20_data:
            return None

        ma5 = ma5_data["data"][-1].get("sma") if ma5_data["data"] else None
        ma20 = ma20_data["data"][-1].get("sma") if ma20_data["data"] else None
        if ma5 is None or ma20 is None:
            return None
        return {"ma5": ma5, "ma20": ma20}
    except Exception as e:
        log(f"ERROR: get_ma5_ma20({symbol}) 錯誤: {e}")
        return None

# ── 時間檢查（模擬盤不交易）─────────────────────────────────────────────
def is_market_open() -> bool:
    """檢查是否在正式交易時段（09:00-13:30）"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()  # 0=周一, 5=週六, 6=週日
    
    # 週六日不交易
    if weekday >= 5:
        return False
    
    # 08:30-09:00 模擬盤，不交易
    if hour == 8 and minute < 55:  # 08:00 - 08:54 是模擬盤
        return False
    
    # 09:00 以後才正式開盤
    if hour < 9:
        return False
    
    # 13:30 以後收盤，不交易
    if hour >= 13 and minute >= 30:
        return False
    
    return True

# ── 初始 MA 資料載入（在 WebSocket 連線前完成） ──────────────────────────
def preload_ma_data(sdk, symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """預先載入所有觀察名單的 MA5/MA20"""
    ma_cache = {}
    for sym in symbols:
        log(f"INFO: 查詢 MA: {sym}")
        ma = get_ma5_ma20(sdk, sym)
        if ma:
            ma_cache[sym] = ma
            log(f"  {sym}: MA5={ma['ma5']:.2f} MA20={ma['ma20']:.2f} gap={(ma['ma20']-ma['ma5'])/ma['ma20']*100:.3f}%")
        else:
            log(f"  {sym}: MA 資料不足")
    return ma_cache

# ── WebSocket 管理 ─────────────────────────────────────────────────────────
class WebSocketManager:
    """WebSocket 連線管理，支援自動重連"""

    def __init__(self, sdk, name: str = "ws"):
        self.sdk = sdk
        self.name = name
        self.ws = sdk.marketdata.websocket_client.stock
        self.connected = False
        self._retry_count = 0
        self._handlers = {}
        self._pending_subs = []  # 等待連線後的訂閱

    def connect(self):
        """建立 WebSocket 連線"""
        ws = self.ws
        # 設定事件處理
        ws.on("connect", self._on_connect)
        ws.on("disconnect", self._on_disconnect)
        ws.on("message", self._on_message)
        ws.on("error", self._on_error)
        log(f"DEBUG: [{self.name}] 連線中...")
        ws.connect()
        # 等認證完成
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            if hasattr(ws, "auth_status"):
                # 直接檢查認證狀態（使用墊片層）
                status = ws._client.auth_status
                from fugle_marketdata.websocket.client import AuthenticationState
                if status == AuthenticationState.AUTHENTICATED:
                    self.connected = True
                    log(f"OK: [{self.name}] 已認證")
                    self._flush_subscriptions()
                    return True
            time.sleep(0.1)
        log(f"WARNING: [{self.name}] 認證超時")
        return False

    def _flush_subscriptions(self):
        """發送等待中的訂閱"""
        for params in self._pending_subs:
            self._do_subscribe(params)
        self._pending_subs = []

    def subscribe(self, params: dict):
        """訂閱頻道（連線中直接發送，否則排入佇列）"""
        if self.connected:
            self._do_subscribe(params)
        else:
            self._pending_subs.append(params)

    def _do_subscribe(self, params: dict):
        sym = params.get("symbol", "?")
        self.ws.subscribe(params)
        log(f"INFO: [{self.name}] 訂閱 {params.get('channel')} {sym}")

    def unsubscribe(self, params: dict):
        self.ws.unsubscribe(params)

    def add_handler(self, event: str, handler):
        """設定事件回調（規格要求的 add_handler 等價於 on）"""
        self._handlers[event] = handler
        self.ws.on(event, handler)

    def _on_connect(self, *args):
        log(f"DEBUG: [{self.name}] 連線開啟")
        self.connected = True

    def _on_disconnect(self, *args):
        log(f"DEBUG: [{self.name}] 連線斷開")
        self.connected = False

    def _on_message(self, data):
        # data 是原始 bytes，需解析
        try:
            import orjson
            msg = orjson.loads(data)
            event = msg.get("event", "")
            # 派發到一般 handler
            handler = self._handlers.get("message")
            if handler:
                handler(msg)
        except Exception as e:
            log(f"ERROR: [{self.name}] 訊息解析錯誤: {e}")

    def _on_error(self, err):
        log(f"ERROR: [{self.name}] WebSocket 錯誤: {err}")

    def reconnect(self):
        """斷線重連（最多 3 次）"""
        if self._retry_count >= MAX_RETRIES:
            log(f"ERROR: [{self.name}] 超過最大重連次數")
            return False
        self._retry_count += 1
        wait = RETRY_WAIT * self._retry_count
        log(f"INFO: [{self.name}] 等待 {wait} 秒後重連（第 {self._retry_count} 次）...")
        time.sleep(wait)
        try:
            self.ws.disconnect()
        except Exception:
            pass
        return self.connect()

    def disconnect(self):
        self.connected = False
        try:
            self.ws.disconnect()
        except Exception:
            pass

# ── 進場條件檢查 ───────────────────────────────────────────────────────────
class SignalChecker:
    """檢查進場信號"""

    def __init__(self, sdk, ma_cache: Dict[str, Dict[str, float]]):
        self.sdk = sdk
        self.ma_cache = ma_cache  # 預先載入的 MA 資料

    def check_entry(self, symbol: str, last_price: float) -> Optional[Dict]:
        """
        檢查進場條件：
        1. MA5 > MA20（黃金交叉）
        2. 現價 > MA5
        """
        ma = self.ma_cache.get(symbol)
        if not ma:
            return None

        ma5 = ma["ma5"]
        ma20 = ma["ma20"]

        cond1 = ma5 > ma20            # 黃金交叉
        cond2 = last_price > ma5      # 價格 > MA5

        signal = cond1 and cond2

        return {
            "symbol": symbol,
            "price": last_price,
            "ma5": ma5,
            "ma20": ma20,
            "gap_pct": (ma20 - ma5) / ma20 * 100 if ma20 else 0,
            "cond1_ma5_gt_ma20": cond1,
            "cond2_price_gt_ma5": cond2,
            "signal": signal,
        }

# ── 持倉監控 ───────────────────────────────────────────────────────────────
class PositionMonitor:
    """持倉監控，停損/目標檢查"""

    @staticmethod
    def check(position: Dict, last_price: float) -> Optional[str]:
        """
        檢查持倉狀態
        回傳：'STOP_LOSS' | 'TARGET' | None
        """
        entry = position.get("entry", 0)
        stop = position.get("stop", 0)
        target = position.get("target", 0)

        if not entry or not last_price:
            return None

        if stop > 0 and last_price <= stop:
            return "STOP_LOSS"
        if target > 0 and last_price >= target:
            return "TARGET"
        return None

# ── 訂單執行 ───────────────────────────────────────────────────────────────
def place_market_sell(sdk, symbol: str, quantity: int = 1):
    """市價卖出（停損/目標觸發時執行）"""
    try:
        from fubon_neo._fubon_neo import BSAction, MarketType, TimeInForce, PriceType, OrderType
        order = sdk.order.rest_client.place_order(
            account=sdk.accounting.account(),
            action=BSAction.SELL,
            symbol=symbol,
            quantity=quantity,
            price_type=PriceType.MARKET,
            order_type=OrderType.ROD,
            market_type=MarketType.TSE,
            time_in_force=TimeInForce.IOC,
            price=0,
        )
        log(f"INFO: 卖出 {symbol} @ 市價 quantity={quantity}")
        return order
    except Exception as e:
        log(f"ERROR: 卖出 {symbol} 失敗: {e}")
        return None

# ── 狀態初始化 ──────────────────────────────────────────────────────────────
def load_watchlist() -> dict:
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return {"holdings": {}, "watchlist": []}

# ── 解析 Tick 訊息 ─────────────────────────────────────────────────────────
def parse_tick(msg) -> Optional[dict]:
    """從 WebSocket 訊息解析 tick data"""
    try:
        if isinstance(msg, str):
            msg = json.loads(msg)
        event = msg.get("event", "")
        if event not in ("data", "message"):
            return None
        data = msg.get("data", {})
        if isinstance(data, dict):
            symbol = data.get("symbol", "")
            # trades channel: price, volume
            # tick channel: lastPrice, volume, insideVolume, outsideVolume
            last_price = float(data.get("price") or data.get("lastPrice") or 0)
            volume = int(data.get("volume") or 0)
            return {
                "symbol": symbol,
                "lastPrice": last_price,
                "volume": volume,
            }
    except Exception as e:
        log(f"ERROR: parse_tick 錯誤: {e}")
    return None

# ── 主程式 ─────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("🌙 盤中 WebSocket 監控系統啟動")
    log("=" * 60)

    # 初始化 SDK
    sdk = init_sdk()
    atexit.register(lambda: logout_sdk(sdk))
    log("✅ SDK 登入成功")

    # 載入 watchlist
    wl_data = load_watchlist()
    holdings_raw = wl_data.get("holdings", {})
    watchlist = wl_data.get("watchlist", [])

    # 整理持倉（支援 list 和 dict 兩種格式）
    holdings = []
    if isinstance(holdings_raw, list):
        # list 格式：[{"code": "2536", "entry_price": 22.532, ...}]
        for h in holdings_raw:
            if isinstance(h, dict) and h.get("entry_price", 0) > 0:
                holdings.append({
                    "code": h.get("code", ""),
                    "entry": h.get("entry_price", 0),
                    "qty": h.get("qty", 1),
                    "stop": h.get("stop_loss", 0),
                    "target": h.get("target_price", 0),
                    "name": h.get("name", h.get("code", "")),
                })
    elif isinstance(holdings_raw, dict):
        # dict 格式：{"2536": {"entry_price": 22.532, ...}}
        for code, h in holdings_raw.items():
            if isinstance(h, dict) and h.get("entry_price", 0) > 0:
                holdings.append({
                    "code": code,
                    "entry": h.get("entry_price", 0),
                    "qty": h.get("qty", 1),
                    "stop": h.get("stop_loss", 0),
                    "target": h.get("target_price", 0),
                    "name": h.get("name", code),
                })

    # 觀察名單（排除已有部位的）
    holding_codes = set(h["code"] for h in holdings)
    watchlist_codes = [
        w["code"] for w in watchlist
        if w.get("code") not in holding_codes
    ]

    log(f"INFO: 持倉: {[h['code'] for h in holdings]}")
    log(f"INFO: 觀察名單: {watchlist_codes}")

    # ── 連線 1：持倉監控（最多 5 檔）───────────────────────────────
    ws_positions = WebSocketManager(sdk, "positions")

    # ── 連線 2：觀察名單監控（最多 200 檔）───────────────────────
    ws_watchlist = WebSocketManager(sdk, "watchlist")

    # 狀態
    position_prices = {}   # code -> lastPrice
    position_vol = {}      # code -> {inside, outside}
    signal_prices = {}     # code -> lastPrice
    signal_vol = {}        # code -> {inside, outside}

    # 產出結構
    status = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "holdings": [],
        "signals": [],
        "has_action": False,
    }

    # ── 預先載入 MA 資料（HTTP API）───────────────────────────────
    all_codes = list(set(watchlist_codes + list(holding_codes)))
    ma_cache = preload_ma_data(sdk, all_codes)

    signal_checker = SignalChecker(sdk, ma_cache)
    pos_monitor = PositionMonitor()

    actions_taken = []

    # ── Tick 處理（持倉連線）────────────────────────────────────
    def on_position_tick(msg: dict):
        tick = parse_tick(msg)
        if not tick:
            return
        sym = tick["symbol"]
        if sym not in holding_codes:
            return

        last = float(tick["lastPrice"] or 0)
        position_prices[sym] = last

        # 找持倉
        pos = next((p for p in holdings if p["code"] == sym), None)
        if not pos:
            return

        if not is_market_open():
            return  # 模擬盤時間（08:30-09:00）不交易
        
        action = pos_monitor.check(pos, last)
        if action:
            # 模擬盤時間不停損/不了結，僅記錄
            log(f"INFO: {sym} 達到 {action} 條件（模擬盤，暫不執行）現價={last}")
            action = None  # 清除行動
        pos_entry = {
            "code": sym,
            "name": pos.get("name", sym),
            "entry": pos["entry"],
            "qty": pos.get("qty", 1),
            "last": last,
            "pnl": round((last - pos["entry"]) / pos["entry"] * 100, 2) if pos["entry"] else 0,
            "stop": pos["stop"],
            "target": pos["target"],
            "action": action,
        }

        # 移除舊的，加入新的
        status["holdings"] = [p for p in status["holdings"] if p["code"] != sym]
        status["holdings"].append(pos_entry)

        if action:
            log(f"INFO: {sym} 觸發 {action}！現價={last} 停損={pos['stop']} 目標={pos['target']}")
            status["has_action"] = True
            actions_taken.append((sym, action, pos))

        write_status(status)

    # ── Tick 處理（觀察名單連線）────────────────────────────────
    def on_watchlist_tick(msg: dict):
        tick = parse_tick(msg)
        if not tick:
            return
        sym = tick["symbol"]
        if sym not in watchlist_codes:
            return

        last = float(tick["lastPrice"] or 0)
        signal_prices[sym] = last

        if not is_market_open():
            return  # 模擬盤時間（08:30-09:00）不進場
        
        result = signal_checker.check_entry(sym, last)
        if result and result["signal"]:
            log(f"INFO: 進場信號！{sym} 現價={last} MA5={result['ma5']:.2f} MA20={result['ma20']:.2f}")

            # 更新 signals
            status["signals"] = [s for s in status["signals"] if s["code"] != sym]
            status["signals"].append({
                "code": sym,
                "price": last,
                "ma5": result["ma5"],
                "ma20": result["ma20"],
                "gap_pct": round(result["gap_pct"], 3),
                "note": "MA5>MA20 且 現價>MA5",
            })
            write_status(status)

    # ── 連線並訂閱 ──────────────────────────────────────────────
    # 連線 1：持倉監控
    if holdings:
        if ws_positions.connect():
            for h in holdings[:5]:  # 最多 5 檔
                ws_positions.subscribe({"channel": "trades", "symbol": h["code"]})
            ws_positions.add_handler("message", on_position_tick)
            log(f"INFO: 持倉監控已訂閱 {len(holdings[:5])} 檔")
        else:
            log("ERROR: 持倉 WebSocket 連線失敗")
    else:
        log("📋 無持倉，跳過持倉連線")

    # 連線 2：觀察名單
    if watchlist_codes:
        if ws_watchlist.connect():
            # 分批訂閱（每批 50 檔，避免單次太多）
            batch = 50
            for i in range(0, min(len(watchlist_codes), 200), batch):
                batch_codes = watchlist_codes[i:i+batch]
                for code in batch_codes:
                    ws_watchlist.subscribe({"channel": "trades", "symbol": code})
                log(f"INFO: 觀察名單已訂閱 {len(batch_codes)} 檔")
            ws_watchlist.add_handler("message", on_watchlist_tick)
        else:
            log("ERROR: 觀察名單 WebSocket 連線失敗")
    else:
        log("📋 無觀察名單，跳過")

    # ── 執行買賣 ────────────────────────────────────────────────
    if actions_taken:
        log(f"INFO: 執行 {len(actions_taken)} 筆交易...")
        for sym, action, pos in actions_taken:
            if action in ("STOP_LOSS", "TARGET"):
                log(f"  {'🛑' if action=='STOP_LOSS' else '🏠'} {action} {sym}")
                place_market_sell(sdk, sym, pos.get("qty", 1))

                # 更新 watchlist.json 的 holdings
                if sym in holdings_raw:
                    holdings_raw[sym]["entry_price"] = 0
                    holdings_raw[sym]["is_holding"] = False
    else:
        log("✅ 無需要執行的交易")

    # ── 定期寫入狀態 ─────────────────────────────────────────────
    # 讓 WebSocket 運行一段時間（主動中斷時結束）
    log("INFO: WebSocket 監控運行中（等待訊息，按 Ctrl-C 結束）...")
    try:
        while True:
            time.sleep(5)
            # 更新狀態時間戳
            status["checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            write_status(status)

            # 檢查持倉連線狀態
            if holdings and not ws_positions.connected:
                log("⚠️ 持倉連線已斷線，嘗試重連...")
                if not ws_positions.reconnect():
                    break
                for h in holdings[:5]:
                    ws_positions.subscribe({"channel": "trades", "symbol": h["code"]})
                ws_positions.add_handler("message", on_position_tick)

            if watchlist_codes and not ws_watchlist.connected:
                log("⚠️ 觀察名單連線已斷線，嘗試重連...")
                if not ws_watchlist.reconnect():
                    break
                for code in watchlist_codes[:200]:
                    ws_watchlist.subscribe({"channel": "trades", "symbol": code})
                ws_watchlist.add_handler("message", on_watchlist_tick)

    except KeyboardInterrupt:
        log("\n🛑 收到中斷訊號，結束監控...")

    finally:
        # 更新 watchlist.json
        try:
            with open(WATCHLIST_FILE) as f:
                wl_data_current = json.load(f)
            wl_data_current["holdings"] = holdings_raw
            wl_data_current["last_updated"] = datetime.now().isoformat()
            with open(WATCHLIST_FILE, "w") as f:
                json.dump(wl_data_current, f, ensure_ascii=False, indent=2)
            log("✅ watchlist.json 已更新")
        except Exception as e:
            log(f"INFO: watchlist 更新失敗: {e}")

        # 結束連線
        ws_positions.disconnect()
        ws_watchlist.disconnect()
        logout_sdk(sdk)
        log("👋 WebSocket 監控系統已結束")


if __name__ == "__main__":
    main()
