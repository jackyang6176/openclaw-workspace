#!/usr/bin/env python3
"""
FubonComplete SDK - 富邦證券完整技術分析工具
============================================
直接使用富邦 SDK 技術分析 API（不自己計算）
"""

from fubon_neo.sdk import FubonSDK
from fubon_neo.constant import BSAction, OrderType, PriceType, MarketType, TimeInForce
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Quote:
    lastPrice: float
    changePercent: float
    totalVolume: int
    name: str = ""

@dataclass
class OrderRecord:
    order_no: str
    symbol: str
    price: float
    quantity: int
    status: str

@dataclass
class Position:
    symbol: str
    name: str
    quantity: int
    cost: float
    lastPrice: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_pct: float

class FubonComplete:
    """富邦 SDK 完整工具，使用 SDK 技術分析 API"""

    def __init__(self):
        self.sdk = None
        self.account = None
        self.connected = False
        self._load_config()

    def _load_config(self):
        env_path = os.path.expanduser("~/.env/fubon.env")
        self.config = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        self.config[k] = v.strip()

    def login(self):
        try:
            self.sdk = FubonSDK()
            acc = self.sdk.login(
                self.config["ACCOUNT"],
                self.config["ACCT_PASSWORD"],
                self.config["CERT_PATH"],
                self.config["CERT_PASSWORD"]
            )
            self.sdk.init_realtime()
            self.account = acc.data[0]
            self.connected = True
            return True
        except Exception as e:
            print(f"登入失敗: {e}")
            return False

    def logout(self):
        if self.sdk:
            try:
                self.sdk.logout()
            except:
                pass
        self.connected = False

    # ========================
    # 技術分析 API（SDK原生）
    # ========================

    def get_sma(self, symbol: str, period: int = 20, timeframe: str = "D", from_date: str = None, to_date: str = None) -> Optional[list]:
        """取得均線（SMA）- 直接用 SDK technical.sma"""
        if not self.connected:
            return None
        try:
            tech = self.sdk.marketdata.rest_client.stock.technical
            kwargs = {"symbol": symbol, "period": period, "timeframe": timeframe}
            if from_date and to_date:
                kwargs["from"] = from_date
                kwargs["to"] = to_date
            result = tech.sma(**kwargs)
            if result and "data" in result:
                return result["data"]
        except Exception as e:
            print(f"SMA 錯誤: {e}")
        return None

    def get_ma5(self, symbol: str, timeframe: str = "D") -> Optional[float]:
        """取得 MA5 最新值"""
        data = self.get_sma(symbol, period=5, timeframe=timeframe)
        if data:
            return data[-1].get("sma")
        return None

    def get_ma20(self, symbol: str, timeframe: str = "D") -> Optional[float]:
        """取得 MA20 最新值"""
        data = self.get_sma(symbol, period=20, timeframe=timeframe)
        if data:
            return data[-1].get("sma")
        return None

    def get_rsi(self, symbol: str, period: int = 14, timeframe: str = "D") -> Optional[dict]:
        """取得 RSI"""
        if not self.connected:
            return None
        try:
            tech = self.sdk.marketdata.rest_client.stock.technical
            result = tech.rsi(symbol=symbol, period=period, timeframe=timeframe)
            if result and "data" in result:
                return result["data"][-1]
        except Exception as e:
            print(f"RSI 錯誤: {e}")
        return None

    def get_macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9, timeframe: str = "D") -> Optional[dict]:
        """取得 MACD"""
        if not self.connected:
            return None
        try:
            tech = self.sdk.marketdata.rest_client.stock.technical
            result = tech.macd(symbol=symbol, fast=fast, slow=slow, signal=signal, timeframe=timeframe)
            if result and "data" in result:
                return result["data"][-1]
        except Exception as e:
            print(f"MACD 錯誤: {e}")
        return None

    def get_kdj(self, symbol: str, rPeriod: int = 9, kPeriod: int = 3, dPeriod: int = 3, timeframe: str = "D", from_date: str = None, to_date: str = None) -> Optional[list]:
        """取得 KDJ - 直接用 SDK technical.kdj，回傳陣列"""
        if not self.connected:
            return None
        try:
            tech = self.sdk.marketdata.rest_client.stock.technical
            kwargs = {"symbol": symbol, "rPeriod": rPeriod, "kPeriod": kPeriod, "dPeriod": dPeriod, "timeframe": timeframe}
            if from_date and to_date:
                kwargs["from"] = from_date
                kwargs["to"] = to_date
            result = tech.kdj(**kwargs)
            if result and "data" in result:
                return result["data"]
        except Exception as e:
            print(f"KDJ 錯誤: {e}")
        return None

    def get_candles(self, symbol: str, timeframe: str = "D", from_date: str = None, to_date: str = None, fields: str = "open,high,low,close,volume") -> Optional[list]:
        """取得歷史K線（含成交量）- 直接用 SDK historical.candles"""
        if not self.connected:
            return None
        try:
            hist = self.sdk.marketdata.rest_client.stock.historical
            kwargs = {"symbol": symbol, "timeframe": timeframe, "fields": fields}
            if from_date and to_date:
                kwargs["from"] = from_date
                kwargs["to"] = to_date
            result = hist.candles(**kwargs)
            if result and "data" in result:
                return result["data"]
        except Exception as e:
            print(f"Candles 錯誤: {e}")
        return None

    def get_bb(self, symbol: str, period: int = 20, std: int = 2, timeframe: str = "D") -> Optional[dict]:
        """取得布林帶"""
        if not self.connected:
            return None
        try:
            tech = self.sdk.marketdata.rest_client.stock.technical
            result = tech.bb(symbol=symbol, period=period, std=std, timeframe=timeframe)
            if result and "data" in result:
                return result["data"][-1]
        except Exception as e:
            print(f"BB 錯誤: {e}")
        return None

    # ========================
    # 即時報價
    # ========================

    def get_quote(self, symbol: str) -> Optional[dict]:
        """取得即時報價"""
        if not self.connected:
            return None
        try:
            rest = self.sdk.marketdata.rest_client.stock
            q = rest.intraday.quote(symbol=symbol)
            if q and "data" in q:
                return q["data"]
        except Exception as e:
            print(f"報價錯誤: {e}")
        return None

    # ========================
    # 技術分析報告（整合）
    # ========================

    def get_technical_report(self, symbol: str) -> dict:
        """一次取得所有技術分析數據（使用 SDK API）"""
        ma5_data = self.get_sma(symbol, period=5)
        ma20_data = self.get_sma(symbol, period=20)
        ma5 = ma5_data[-1]["sma"] if ma5_data else None
        ma20 = ma20_data[-1]["sma"] if ma20_data else None
        q = self.get_quote(symbol)
        rsi_data = self.get_rsi(symbol)
        macd_data = self.get_macd(symbol)
        kdj_data = self.get_kdj(symbol)
        bb_data = self.get_bb(symbol)

        price = q.get("lastPrice") if q else None
        chg = q.get("changePercent") if q else None

        return {
            "symbol": symbol,
            "name": q.get("name") if q else "",
            "price": price,
            "changePercent": chg,
            "ma5": ma5,
            "ma20": ma20,
            "ma5_ma20_gap": (ma20 - ma5) / ma20 * 100 if (ma5 and ma20) else None,
            "rsi": rsi_data.get("rsi") if rsi_data else None,
            "macd": macd_data,
            "kdj": kdj_data,
            "bb": bb_data,
            "sma_data_ma5": ma5_data,
            "sma_data_ma20": ma20_data,
        }

    def get_strategy_signal(self, symbol: str) -> dict:
        """
        新策略A信號評估（使用 SDK 原生 API）
        條件：
        1. MA5 < MA20（5日均線在20日均線下方）
        2. 兩線價差連三日縮小
        3. 兩線價差 < 1%
        4. 連三日量增
        """
        report = self.get_technical_report(symbol)
        ma5_data = report.get("sma_data_ma5", [])
        ma20_data = report.get("sma_data_ma20", [])

        if len(ma5_data) < 4 or len(ma20_data) < 4:
            return {"error": "資料不足"}

        # 近4日價差
        gaps = []
        for i in range(-4, 0):
            ma5v = ma5_data[i]["sma"]
            ma20v = ma20_data[i]["sma"]
            if ma20v > 0:
                gaps.append((ma20v - ma5v) / ma20v * 100)

        cond1 = report["ma5"] < report["ma20"]  # MA5 < MA20
        cond2 = len(gaps) >= 3 and gaps[-1] < gaps[-2] < gaps[-3]  # 價差三日縮小
        cond3 = gaps[-1] < 1 if gaps else False  # 價差 < 1%

        # 連三日量增（從報價取）
        # ...

        confidence = (cond1 + cond2 + cond3) / 3 * 100

        return {
            "symbol": symbol,
            "price": report["price"],
            "ma5": report["ma5"],
            "ma20": report["ma20"],
            "ma_gap_pct": report["ma5_ma20_gap"],
            "cond1_ma5_below_ma20": cond1,
            "cond2_gap_narrowing": cond2,
            "cond3_gap_under_1pct": cond3,
            "confidence": confidence,
            "all_ok": cond1 and cond2 and cond3
        }


if __name__ == "__main__":
    fb = FubonComplete()
    if fb.login():
        # 測試技術分析 API
        report = fb.get_technical_report("2440")
        print(f"\n=== 2440 技術分析 ===")
        print(f"價格: {report['price']}")
        print(f"MA5: {report['ma5']}")
        print(f"MA20: {report['ma20']}")
        print(f"兩線差%: {report['ma5_ma20_gap']}")
        print(f"RSI(14): {report['rsi']}")
        print(f"MACD: {report['macd']}")
        print(f"KDJ: {report['kdj']}")
        print(f"BB: {report['bb']}")
        fb.logout()
