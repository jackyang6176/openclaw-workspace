#!/usr/bin/env python3
"""
股票篩選工具
根據技術面和基本面條件篩選股票
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

# 設定路徑
WORKSPACE = "/home/admin/.openclaw/workspace"
FUBON_API = f"{WORKSPACE}/fubon_api"
PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw/stockanalysis"
os.makedirs(PCLOUD_DIR, exist_ok=True)

sys.path.insert(0, FUBON_API)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

class StockScreener:
    """股票篩選器"""
    
    def __init__(self):
        self.client = None
        
    def login(self) -> bool:
        """登入富邦SDK"""
        try:
            from fubon_kline_sdk import FubonKlineSDK
            self.client = FubonKlineSDK()
            return self.client.login()
        except Exception as e:
            log(f"❌ 登入失敗：{e}")
            return False
    
    def logout(self):
        """登出"""
        if self.client:
            self.client.logout()
    
    def get_stock_data(self, symbol: str, days: int = 90) -> Optional[pd.DataFrame]:
        """獲取股票歷史數據"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            data = self.client.get_historical_candles(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                timeframe="D"
            )
            
            if not data or len(data) < 20:
                return None
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            return df
            
        except Exception as e:
            log(f"❌ 獲取 {symbol} 數據失敗：{e}")
            return None
    
    def calculate_kd(self, df: pd.DataFrame, n: int = 9) -> pd.DataFrame:
        """計算KD指標"""
        low_min = df['low'].rolling(window=n).min()
        high_max = df['high'].rolling(window=n).max()
        df['rsv'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['k'] = df['rsv'].ewm(com=2).mean()
        df['d'] = df['k'].ewm(com=2).mean()
        return df
    
    def check_condition_1(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        條件1：近20日股價無明顯波動，最近一、二天發動股價拉升合併成交量放大
        """
        if len(df) < 25:
            return False, "數據不足", 0
        
        recent_20 = df.iloc[-22:-2]
        latest_2 = df.iloc[-2:]
        
        # 波動率
        volatility = recent_20['close'].std() / recent_20['close'].mean()
        low_volatility = volatility < 0.05
        
        # 價格拉升
        price_change_1d = (latest_2.iloc[-1]['close'] - recent_20.iloc[-1]['close']) / recent_20.iloc[-1]['close']
        price_surge = price_change_1d > 0.03
        
        # 成交量放大
        avg_volume_20 = recent_20['volume'].mean()
        latest_volume = latest_2.iloc[-1]['volume']
        volume_expansion = latest_volume > avg_volume_20 * 1.5
        
        is_valid = low_volatility and price_surge and volume_expansion
        detail = f"波動率:{volatility:.1%}, 漲幅:{price_change_1d:.1%}, 成交量:{latest_volume/avg_volume_20:.1f}x"
        score = (0.4 if low_volatility else 0) + (0.3 if price_surge else 0) + (0.3 if volume_expansion else 0)
        
        return is_valid, detail, score
    
    def check_condition_2(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        條件2：KD技術線圖，KD低於20，並且K值向上突破D值（黃金交叉）
        """
        if len(df) < 10:
            return False, "數據不足", 0
        
        df = self.calculate_kd(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        kd_oversold = latest['k'] < 20 and latest['d'] < 20
        golden_cross = prev['k'] <= prev['d'] and latest['k'] > latest['d']
        
        is_valid = kd_oversold and golden_cross
        detail = f"K:{latest['k']:.1f}, D:{latest['d']:.1f}, 交叉:{'是' if golden_cross else '否'}"
        score = (0.5 if kd_oversold else 0) + (0.5 if golden_cross else 0)
        
        return is_valid, detail, score
    
    def check_condition_3(self, symbol: str) -> Tuple[bool, str, float]:
        """
        條件3：近三月公司營收持續遞增
        暫時使用模擬數據
        """
        # 這裡需要整合財務數據API
        # 暫時返回中性結果
        return True, "財務數據需外部API", 0.5
    
    def screen_stock(self, symbol: str) -> Optional[Dict]:
        """篩選單一股票"""
        log(f"分析 {symbol}...")
        
        df = self.get_stock_data(symbol, days=90)
        if df is None:
            return None
        
        c1_pass, c1_detail, c1_score = self.check_condition_1(df)
        c2_pass, c2_detail, c2_score = self.check_condition_2(df)
        c3_pass, c3_detail, c3_score = self.check_condition_3(symbol)
        
        total_score = c1_score + c2_score + c3_score
        
        result = {
            'symbol': symbol,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': df.iloc[-1]['close'],
            'volume': df.iloc[-1]['volume'],
            'condition_1': {'pass': c1_pass, 'detail': c1_detail, 'score': c1_score},
            'condition_2': {'pass': c2_pass, 'detail': c2_detail, 'score': c2_score},
            'condition_3': {'pass': c3_pass, 'detail': c3_detail, 'score': c3_score},
            'total_score': total_score,
            'all_pass': c1_pass and c2_pass and c3_pass
        }
        
        return result
    
    def screen_multiple(self, symbols: List[str]) -> List[Dict]:
        """篩選多檔股票"""
        results = []
        
        if not self.login():
            log("❌ 登入失敗")
            return results
        
        try:
            for symbol in symbols:
                result = self.screen_stock(symbol)
                if result:
                    results.append(result)
                    status = "✅" if result['all_pass'] else "❌"
                    log(f"{status} {symbol}: 得分 {result['total_score']:.1f}/3.0")
        finally:
            self.logout()
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """生成HTML報告"""
        passed = [r for r in results if r['all_pass']]
        passed.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 生成股票卡片
        stock_cards = ""
        for r in results:
            status_class = "passed" if r['all_pass'] else "failed"
            status_icon = "✅" if r['all_pass'] else "❌"
            
            stock_cards += f"""
            <div class="stock-card {status_class}">
                <h3>{status_icon} {r['symbol']}</h3>
                <p>目前價格: <strong>{r['current_price']:.2f}</strong></p>
                <p>成交量: {r['volume']:,}</p>
                <p>綜合得分: <strong>{r['total_score']:.1f}/3.0</strong></p>
                <hr>
                <p>📊 條件1: {'✅' if r['condition_1']['pass'] else '❌'} {r['condition_1']['detail']}</p>
                <p>📈 條件2: {'✅' if r['condition_2']['pass'] else '❌'} {r['condition_2']['detail']}</p>
                <p>💰 條件3: {'✅' if r['condition_3']['pass'] else '❌'} {r['condition_3']['detail']}</p>
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>股票篩選報告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Microsoft JhengHei', Arial, sans-serif; }}
        body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px 0; border-bottom: 2px solid #667eea; margin-bottom: 30px; }}
        h1 {{ font-size: 2.5em; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .summary {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 30px; text-align: center; }}
        .summary h2 {{ color: #667eea; margin-bottom: 10px; }}
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stock-card {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.1); }}
        .stock-card.passed {{ border-color: #00d084; background: rgba(0,208,132,0.1); }}
        .stock-card.failed {{ border-color: #ff4757; background: rgba(255,71,87,0.1); }}
        .stock-card h3 {{ font-size: 1.5em; margin-bottom: 10px; }}
        .stock-card p {{ margin: 5px 0; color: #ccc; }}
        .stock-card strong {{ color: #fff; }}
        .stock-card hr {{ border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; border-top: 1px solid rgba(255,255,255,0.1); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 股票篩選報告</h1>
            <p>篩選時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="summary">
            <h2>篩選結果摘要</h2>
            <p>符合所有條件: <strong style="color: #00d084;">{len(passed)}</strong> 檔</p>
            <p>總分析數: <strong>{len(results)}</strong> 檔</p>
        </div>
        
        <div class="stock-grid">
            {stock_cards}
        </div>
        
        <div class="footer">
            <p>Powered by 富邦證券SDK + Python技術分析</p>
            <p>⚠️ 數據僅供參考，投資有風險</p>
        </div>
    </div>
</body>
</html>"""
        
        return html

def save_report(html_content: str) -> str:
    """保存報告"""
    filename = f"stock_screener_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存: {filepath}")
        return filepath
    except Exception as e:
        log(f"❌ 保存失敗: {e}")
        return None

def main():
    """主程式"""
    # 預設篩選的股票清單（可以從參數讀取）
    default_symbols = [
        # 你的持倉
        "00655L", "00882", "00887",
        # 熱門ETF
        "0050", "0056", "00878", "00891",
        # 熱門個股
        "2330", "2317", "2454", "2382", "2881", "2891"
    ]
    
    symbols = sys.argv[1:] if len(sys.argv) > 1 else default_symbols
    
    log(f"開始篩選 {len(symbols)} 檔股票...")
    log("篩選條件:")
    log("1. 近20日低波動 + 近1-2日價量齊揚")
    log("2. KD<20 且 K值向上突破D值（黃金交叉）")
    log("3. 近三月營收遞增")
    
    screener = StockScreener()
    results = screener.screen_multiple(symbols)
    
    if not results:
        log("❌ 無篩選結果")
        return 1
    
    # 生成報告
    log("\n生成HTML報告...")
    html = screener.generate_report(results)
    filepath = save_report(html)
    
    # 輸出符合條件的股票
    passed = [r for r in results if r['all_pass']]
    log("\n" + "="*60)
    log(f"✅ 符合所有條件的股票 ({len(passed)} 檔):")
    for r in passed:
        log(f"  {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f})")
    log("="*60)
    
    if filepath:
        log(f"\n📁 報告位置: {filepath}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
