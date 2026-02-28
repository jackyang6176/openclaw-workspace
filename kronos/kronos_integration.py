#!/usr/bin/env python3
"""
Kronos 技術分析整合模塊
整合 Kronos AI 預測模型到投資分析系統

Usage:
    python kronos_integration.py --symbol 00655L --pred_len 120
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加 Kronos 模型路徑
sys.path.insert(0, '/tmp/Kronos')

try:
    from model import Kronos, KronosTokenizer, KronosPredictor
    KRONOS_AVAILABLE = True
except ImportError:
    KRONOS_AVAILABLE = False
    print("⚠️  Kronos 模型未安裝，使用模擬模式")


class KronosIntegration:
    """Kronos 技術分析整合類"""
    
    def __init__(self, model_name="NeoQuasar/Kronos-small"):
        """
        初始化 Kronos 模型
        
        Args:
            model_name: Hugging Face 模型名稱
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.predictor = None
        
        if KRONOS_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """加載預訓練模型"""
        print(f"📥 加載 Kronos 模型：{self.model_name}")
        try:
            # 加載 tokenizer
            self.tokenizer = KronosTokenizer.from_pretrained(
                "NeoQuasar/Kronos-Tokenizer-base"
            )
            # 加載模型
            self.model = Kronos.from_pretrained(self.model_name)
            # 初始化預測器
            self.predictor = KronosPredictor(
                self.model,
                self.tokenizer,
                max_context=512
            )
            print("✅ 模型加載成功")
        except Exception as e:
            print(f"❌ 模型加載失敗：{e}")
            print("⚠️  切換到模擬模式")
            self.predictor = None
    
    def predict_price(self, historical_df, pred_len=120):
        """
        預測未來價格走勢
        
        Args:
            historical_df: 歷史 K 線數據 (需包含 open, high, low, close, volume)
            pred_len: 預測長度 (默认 120 個時間單位)
        
        Returns:
            pred_df: 預測結果 DataFrame
        """
        if self.predictor is None:
            return self._mock_prediction(historical_df, pred_len)
        
        try:
            lookback = min(400, len(historical_df))
            
            # 準備輸入數據
            required_cols = ['open', 'high', 'low', 'close']
            optional_cols = ['volume', 'amount']
            
            available_cols = [col for col in required_cols + optional_cols 
                            if col in historical_df.columns]
            
            x_df = historical_df.iloc[-lookback:][available_cols].copy()
            
            # 時間戳處理
            if 'timestamps' in historical_df.columns:
                x_timestamp = historical_df.iloc[-lookback:]['timestamps'].reset_index(drop=True)
            else:
                # 假設 5 分鐘 K 線
                base_time = datetime.now() - timedelta(minutes=5*lookback)
                x_timestamp = pd.Series(pd.date_range(
                    start=base_time,
                    periods=lookback,
                    freq='5min'
                ))
            
            # 預測時間戳
            last_time = x_timestamp.iloc[-1] if hasattr(x_timestamp, 'iloc') else x_timestamp[-1]
            y_timestamp = pd.date_range(
                start=last_time + pd.Timedelta(minutes=5),
                periods=pred_len,
                freq='5min'
            )
            
            # 生成預測
            print(f"🔮 生成預測 (lookback={lookback}, pred_len={pred_len})...")
            pred_df = self.predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=1.0,
                top_p=0.9,
                sample_count=1,
                verbose=False
            )
            
            print("✅ 預測完成")
            return pred_df
            
        except Exception as e:
            print(f"❌ 預測失敗：{e}")
            return self._mock_prediction(historical_df, pred_len)
    
    def _mock_prediction(self, historical_df, pred_len):
        """
        模擬預測 (當模型不可用時)
        
        使用簡單的趨勢外推
        """
        print("⚠️  使用模擬預測模式")
        
        last_row = historical_df.iloc[-1]
        
        # 計算近期趨勢
        lookback = min(20, len(historical_df))
        recent_data = historical_df.iloc[-lookback:]
        
        # 簡單線性回歸
        x = np.arange(lookback)
        y = recent_data['close'].values
        
        slope = (y[-1] - y[0]) / lookback if lookback > 1 else 0
        
        # 生成預測
        pred_data = []
        for i in range(pred_len):
            future_time = last_row.name + timedelta(minutes=5*(i+1))
            pred_close = y[-1] + slope * (i + 1)
            
            # 添加一些隨機性
            noise = np.random.normal(0, abs(slope) * 0.1)
            pred_close += noise
            
            pred_open = pred_close * (1 + np.random.uniform(-0.001, 0.001))
            pred_high = max(pred_open, pred_close) * (1 + abs(np.random.normal(0, 0.002)))
            pred_low = min(pred_open, pred_close) * (1 - abs(np.random.normal(0, 0.002)))
            pred_volume = last_row.get('volume', 1000000) * (1 + np.random.normal(0, 0.1))
            
            pred_data.append({
                'timestamps': future_time,
                'open': pred_open,
                'high': pred_high,
                'low': pred_low,
                'close': pred_close,
                'volume': max(0, pred_volume)
            })
        
        return pd.DataFrame(pred_data)
    
    def generate_signals(self, historical_df, pred_df):
        """
        根據預測生成交易信號
        
        Args:
            historical_df: 歷史數據
            pred_df: 預測數據
        
        Returns:
            signal: 'BUY', 'SELL', or 'HOLD'
            confidence: 置信度 (0-100%)
            target_price: 目標價
            stop_loss: 停損價
        """
        last_close = historical_df['close'].iloc[-1]
        
        # 短期預測 (前 12 個時間單位，約 1 小時)
        short_term_pred = pred_df['close'].iloc[:12].mean()
        
        # 中期預測 (前 48 個時間單位，約 4 小時)
        mid_term_pred = pred_df['close'].iloc[:48].mean()
        
        # 計算預期漲跌幅
        short_term_change = (short_term_pred - last_close) / last_close
        mid_term_change = (mid_term_pred - last_close) / last_close
        
        # 綜合判斷
        avg_change = (short_term_change * 0.6 + mid_term_change * 0.4)
        
        # 置信度計算
        volatility = historical_df['close'].iloc[-20:].std() / last_close
        confidence = min(abs(avg_change) / volatility * 100, 95) if volatility > 0 else 50
        
        # 生成信號
        if avg_change > 0.01:  # 預測上漲 > 1%
            signal = 'BUY'
            target_price = last_close * (1 + avg_change * 1.5)
            stop_loss = last_close * 0.98
        elif avg_change < -0.01:  # 預測下跌 > 1%
            signal = 'SELL'
            target_price = last_close * (1 + avg_change * 1.5)
            stop_loss = last_close * 1.02
        else:
            signal = 'HOLD'
            target_price = last_close
            stop_loss = last_close * 0.99
        
        return {
            'signal': signal,
            'confidence': confidence,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'short_term_change': short_term_change * 100,
            'mid_term_change': mid_term_change * 100
        }
    
    def analyze(self, symbol, historical_df, pred_len=120):
        """
        完整分析流程
        
        Args:
            symbol: 股票代碼
            historical_df: 歷史 K 線數據
            pred_len: 預測長度
        
        Returns:
            analysis_result: 完整分析結果
        """
        print(f"\n{'='*60}")
        print(f"📊 Kronos 技術分析：{symbol}")
        print(f"{'='*60}\n")
        
        # 生成預測
        pred_df = self.predict_price(historical_df, pred_len)
        
        # 生成信號
        signals = self.generate_signals(historical_df, pred_df)
        
        # 整合結果
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'last_close': historical_df['close'].iloc[-1],
            'prediction': {
                'short_term': pred_df['close'].iloc[:12].mean(),
                'mid_term': pred_df['close'].iloc[:48].mean(),
                'full_period': pred_df['close'].mean()
            },
            'signals': signals,
            'model': self.model_name,
            'pred_len': pred_len
        }
        
        # 打印結果
        self._print_analysis(result)
        
        return result
    
    def _print_analysis(self, result):
        """打印分析結果"""
        print(f"代碼：{result['symbol']}")
        print(f"時間：{result['timestamp']}")
        print(f"最後收盤價：${result['last_close']:.2f}")
        print()
        
        print("📈 預測價格:")
        print(f"  短期 (1 小時):  ${result['prediction']['short_term']:.2f}")
        print(f"  中期 (4 小時):  ${result['prediction']['mid_term']:.2f}")
        print(f"  平均：${result['prediction']['full_period']:.2f}")
        print()
        
        signals = result['signals']
        print("🎯 交易信號:")
        print(f"  信號：{signals['signal']}")
        print(f"  置信度：{signals['confidence']:.1f}%")
        print(f"  目標價：${signals['target_price']:.2f}")
        print(f"  停損價：${signals['stop_loss']:.2f}")
        print()
        
        print("📊 預期漲跌:")
        print(f"  短期：{signals['short_term_change']:+.2f}%")
        print(f"  中期：{signals['mid_term_change']:+.2f}%")
        print(f"{'='*60}\n")


def load_mock_data(symbol="00655L", days=30):
    """
    加載模擬數據 (實際使用時替換為 Fubon API 數據)
    
    Args:
        symbol: 股票代碼
        days: 天數
    
    Returns:
        historical_df: 歷史 K 線數據
    """
    print(f"📥 加載 {symbol} 歷史數據 ({days}天)...")
    
    # 生成模擬 5 分鐘 K 線
    minutes_per_day = 240  # 台股 5 分鐘 K 線約 240 根/天
    total_bars = days * minutes_per_day
    
    # 模擬價格走勢
    base_price = 32.0  # 00655L 近似價格
    dates = pd.date_range(
        end=datetime.now(),
        periods=total_bars,
        freq='5min'
    )
    
    # 生成隨機游走
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.005, total_bars)
    close_prices = base_price * np.cumprod(1 + returns)
    
    # 生成 OHLCV
    data = []
    for i, (date, close) in enumerate(zip(dates, close_prices)):
        open_price = close * (1 + np.random.uniform(-0.002, 0.002))
        high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.003)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.003)))
        volume = int(np.random.uniform(50000, 500000))
        
        data.append({
            'timestamps': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamps', inplace=True)
    
    print(f"✅ 數據加載完成：{len(df)} 根 K 線")
    return df


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='Kronos 技術分析整合')
    parser.add_argument('--symbol', type=str, default='00655L', help='股票代碼')
    parser.add_argument('--pred_len', type=int, default=120, help='預測長度 (時間單位)')
    parser.add_argument('--days', type=int, default=30, help='歷史數據天數')
    parser.add_argument('--model', type=str, default='NeoQuasar/Kronos-small', help='模型名稱')
    
    args = parser.parse_args()
    
    # 初始化 Kronos
    kronos = KronosIntegration(model_name=args.model)
    
    # 加載歷史數據 (實際使用時從 Fubon API 獲取)
    historical_df = load_mock_data(symbol=args.symbol, days=args.days)
    
    # 執行分析
    result = kronos.analyze(
        symbol=args.symbol,
        historical_df=historical_df,
        pred_len=args.pred_len
    )
    
    # 保存結果
    output_file = f'/home/admin/.openclaw/workspace/kronos/kronos_analysis_{args.symbol}_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    result_df = pd.DataFrame([result])
    result_df.to_json(output_file, orient='records', indent=2)
    print(f"📁 結果已保存：{output_file}")
    
    return result


if __name__ == "__main__":
    main()
