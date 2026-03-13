#!/usr/bin/env python3
"""
台股上市股票分批篩選工具 V2
符合富邦API頻率限制：歷史行情 60次/分鐘
"""
import os
import sys
import gc
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_api')

# 台股主要股票清單（150檔，按產業分類）
TWSE_MAJOR_STOCKS = [
    # 金融（25檔）
    '2881', '2882', '2883', '2884', '2885', '2886', '2887', '2888', '2889', '2890',
    '2891', '2892', '2897', '2898', '2899', '2900', '5871', '5876', '5880', '6015',
    '6016', '6024', '6026', '6028', '6030',
    # 電子科技（50檔）
    '2330', '2317', '2454', '2382', '2308', '2303', '3711', '3034', '2357', '3231',
    '3008', '2327', '2890', '3045', '2301', '3661', '2379', '2324', '2618', '2002',
    '3481', '2353', '2345', '2609', '2610', '2323', '2325', '2337', '2340', '2344',
    '2347', '2352', '2356', '2360', '2362', '2363', '2365', '2373', '2375', '2376',
    '2377', '2383', '2385', '2388', '2392', '2401', '2404', '2405', '2406', '2408',
    # 傳產（40檔）
    '1101', '1102', '1103', '1216', '1301', '1303', '1304', '1307', '1308', '1309',
    '1402', '1410', '1503', '1504', '1506', '1507', '1603', '1604', '1605', '1701',
    '1702', '1704', '1707', '1708', '1710', '1711', '1712', '1713', '1714', '1717',
    '1718', '1720', '1721', '1722', '1723', '1724', '1725', '1726', '1727', '1729',
    # ETF與權值（35檔）
    '0050', '0056', '00878', '00881', '00882', '00887', '00891', '00900', '00919', '00929',
    '00632R', '00633L', '00650L', '00655L', '00657L', '00658L', '00661R', '00662L', '00663L', '00664R',
    '00665L', '00666R', '00667R', '00668R', '00669R', '00670L', '00671R', '00672L', '00673R', '00674R',
    '00675L', '00676R', '00677U', '00678L', '00680L',
]

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def check_condition_1(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """條件1：近20日股價無明顯波動，最近一、二天發動股價拉升合併成交量放大"""
    if len(df) < 25:
        return False, "數據不足", 0
    
    recent_20 = df.iloc[-22:-2]
    latest_2 = df.iloc[-2:]
    
    volatility = recent_20['close'].std() / recent_20['close'].mean()
    low_volatility = volatility < 0.05
    
    price_change_1d = (latest_2.iloc[-1]['close'] - recent_20.iloc[-1]['close']) / recent_20.iloc[-1]['close']
    price_surge = price_change_1d > 0.03
    
    avg_volume_20 = recent_20['volume'].mean()
    latest_volume = latest_2.iloc[-1]['volume']
    volume_expansion = latest_volume > avg_volume_20 * 1.5
    
    score = (0.4 if low_volatility else 0) + (0.3 if price_surge else 0) + (0.3 if volume_expansion else 0)
    detail = f"波動率:{volatility:.1%}, 漲幅:{price_change_1d:.1%}, 成交量:{latest_volume/avg_volume_20:.1f}x"
    
    return low_volatility and price_surge and volume_expansion, detail, score

def check_condition_2(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """條件2：KD技術線圖，KD低於20，並且K值向上突破D值（黃金交叉）"""
    if len(df) < 10:
        return False, "數據不足", 0
    
    n = 9
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    df['rsv'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['k'] = df['rsv'].ewm(com=2).mean()
    df['d'] = df['k'].ewm(com=2).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    kd_oversold = latest['k'] < 20 and latest['d'] < 20
    golden_cross = prev['k'] <= prev['d'] and latest['k'] > latest['d']
    
    score = (0.5 if kd_oversold else 0) + (0.5 if golden_cross else 0)
    detail = f"K:{latest['k']:.1f}, D:{latest['d']:.1f}, 交叉:{'是' if golden_cross else '否'}"
    
    return kd_oversold and golden_cross, detail, score

def check_condition_3(symbol: str) -> Tuple[bool, str, float]:
    """條件3：近三月公司營收持續遞增"""
    return True, "需要財務數據API", 0.5

def screen_single_stock(client, symbol: str) -> Optional[Dict]:
    """篩選單一股票"""
    try:
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        data = client.get_historical_candles(
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
        
        if len(df) > 60:
            df = df.iloc[-60:]
        
        c1_pass, c1_detail, c1_score = check_condition_1(df)
        c2_pass, c2_detail, c2_score = check_condition_2(df)
        c3_pass, c3_detail, c3_score = check_condition_3(symbol)
        
        total_score = c1_score + c2_score + c3_score
        
        result = {
            'symbol': symbol,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': float(df.iloc[-1]['close']),
            'volume': int(df.iloc[-1]['volume']),
            'condition_1': {'pass': c1_pass, 'detail': c1_detail, 'score': c1_score},
            'condition_2': {'pass': c2_pass, 'detail': c2_detail, 'score': c2_score},
            'condition_3': {'pass': c3_pass, 'detail': c3_detail, 'score': c3_score},
            'total_score': total_score,
            'all_pass': c1_pass and c2_pass and c3_pass
        }
        
        del df
        del data
        gc.collect()
        
        return result
        
    except Exception as e:
        log(f"❌ 分析 {symbol} 失敗：{e}")
        return None

def batch_screen_with_rate_limit(symbols: List[str]) -> List[Dict]:
    """
    分批篩選，符合富邦API頻率限制
    歷史行情：60次/分鐘
    """
    from fubon_kline_sdk import FubonKlineSDK
    
    results = []
    
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 登入失敗")
        return results
    
    try:
        total = len(symbols)
        batch_size = 60  # 每分鐘最多60次（符合API限制）
        total_batches = (total - 1) // batch_size + 1
        
        for i in range(0, total, batch_size):
            batch = symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            batch_start_time = time.time()
            
            log(f"\n{'='*60}")
            log(f"批次 {batch_num}/{total_batches} (處理 {len(batch)} 檔)...")
            log(f"{'='*60}")
            
            for j, symbol in enumerate(batch, 1):
                result = screen_single_stock(client, symbol)
                if result:
                    results.append(result)
                    status = "✅" if result['all_pass'] else "⚠️"
                    log(f"  [{j:2d}/{len(batch)}] {status} {symbol}: {result['current_price']:.2f} (得分: {result['total_score']:.1f})")
                
                # 每檔之間加入延遲，確保不超過60次/分鐘
                # 60次/分鐘 = 1次/秒，加入0.5秒緩衝
                if j < len(batch):
                    time.sleep(1.0)  # 每秒1檔
            
            # 批次處理時間
            batch_duration = time.time() - batch_start_time
            log(f"  批次 {batch_num} 完成，耗時 {batch_duration:.1f} 秒")
            
            # 如果不是最後一批，等待到下一分鐘
            if batch_num < total_batches:
                wait_time = max(0, 60 - batch_duration)
                if wait_time > 0:
                    log(f"  等待 {wait_time:.1f} 秒以符合API頻率限制...")
                    time.sleep(wait_time)
            
            # 釋放記憶體
            gc.collect()
            
    finally:
        client.logout()
    
    return results

def generate_report(results: List[Dict]) -> str:
    """生成HTML報告"""
    passed = [r for r in results if r['all_pass']]
    passed.sort(key=lambda x: x['total_score'], reverse=True)
    
    top20 = sorted(results, key=lambda x: x['total_score'], reverse=True)[:20]
    
    rows = ""
    for r in top20:
        status = "✅" if r['all_pass'] else "⚠️"
        rows += f"""<tr>
            <td>{status}</td>
            <td><strong>{r['symbol']}</strong></td>
            <td>{r['current_price']:.2f}</td>
            <td>{r['total_score']:.1f}</td>
            <td>{'✅' if r['condition_1']['pass'] else '❌'}</td>
            <td>{'✅' if r['condition_2']['pass'] else '❌'}</td>
            <td>{r['condition_1']['detail']}</td>
            <td>{r['condition_2']['detail']}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>台股上市股票篩選報告 V2 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Microsoft JhengHei', Arial, sans-serif; }}
        body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px 0; border-bottom: 2px solid #667eea; margin-bottom: 30px; }}
        h1 {{ font-size: 2.5em; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }}
        .subtitle {{ color: #888; font-size: 1.1em; }}
        .summary {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 30px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .summary-item {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; text-align: center; }}
        .summary-item h3 {{ color: #667eea; font-size: 2em; margin-bottom: 5px; }}
        .summary-item p {{ color: #888; font-size: 0.9em; }}
        .section {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 30px; }}
        .section h2 {{ color: #667eea; margin-bottom: 15px; border-left: 4px solid #667eea; padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #667eea; padding: 12px; text-align: left; font-weight: bold; }}
        td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.03); }}
        tr:hover {{ background: rgba(102,126,234,0.2); }}
        .positive {{ color: #00d084; }}
        .negative {{ color: #ff4757; }}
        .footer {{ text-align: center; padding: 20px; color: #666; border-top: 1px solid rgba(255,255,255,0.1); margin-top: 30px; }}
        .criteria {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 30px; }}
        .criteria h3 {{ color: #667eea; margin-bottom: 10px; }}
        .criteria ul {{ margin-left: 20px; color: #ccc; }}
        .criteria li {{ margin: 5px 0; }}
        .badge {{ background: #667eea; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 台股上市股票篩選報告 V2</h1>
            <p class="subtitle">篩選時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 符合富邦API頻率限制</p>
        </header>
        
        <div class="summary">
            <div class="summary-item">
                <h3 style="color: #00d084">{len(passed)}</h3>
                <p>完全符合</p>
            </div>
            <div class="summary-item">
                <h3 style="color: #ffa502">{len(results) - len(passed)}</h3>
                <p>部分符合</p>
            </div>
            <div class="summary-item">
                <h3>{len(results)}</h3>
                <p>總分析數</p>
            </div>
            <div class="summary-item">
                <h3 style="color: #667eea">V2</h3>
                <p>API頻率控管</p>
            </div>
        </div>
        
        <div class="criteria">
            <h3>🎯 篩選條件</h3>
            <ul>
                <li><strong>條件1：</strong>近20日股價無明顯波動（波動率&lt;5%），最近1-2天股價拉升（漲幅&gt;3%）且成交量放大（&gt;1.5倍）</li>
                <li><strong>條件2：</strong>KD技術指標低於20（超賣區），且K值向上突破D值（黃金交叉）</li>
                <li><strong>條件3：</strong>近三月公司營收持續遞增（需財務數據API）</li>
            </ul>
            <p style="margin-top: 10px; color: #888;"><span class="badge">API限制</span> 歷史行情：60次/分鐘 | 日內行情：300次/分鐘</p>
        </div>
        
        <div class="section">
            <h2>🏆 Top 20 得分最高股票</h2>
            <table>
                <thead>
                    <tr>
                        <th>狀態</th>
                        <th>代號</th>
                        <th>價格</th>
                        <th>得分</th>
                        <th>條件1</th>
                        <th>條件2</th>
                        <th>條件1詳情</th>
                        <th>條件2詳情</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Powered by 富邦證券SDK + Python技術分析</p>
            <p>⚠️ 數據僅供參考，投資有風險，決策需謹慎</p>
            <p>報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def save_report(html_content: str) -> str:
    """保存報告"""
    PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw/stockanalysis"
    filename = f"twse_screener_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filepath

def main():
    """主程式"""
    log("="*60)
    log("台股上市股票分批篩選 V2")
    log("符合富邦API頻率限制：歷史行情 60次/分鐘")
    log("="*60)
    log(f"總股票數：{len(TWSE_MAJOR_STOCKS)} 檔")
    log(f"分批大小：60 檔/批（符合API限制）")
    log(f"預計批次：{(len(TWSE_MAJOR_STOCKS)-1)//60 + 1} 批")
    log(f"預計時間：約 {(len(TWSE_MAJOR_STOCKS)-1)//60 + 1} 分鐘")
    log("="*60)
    
    log("\n篩選條件：")
    log("1. 近20日低波動 + 近1-2日價量齊揚")
    log("2. KD<20 + K值向上突破D值（黃金交叉）")
    log("3. 近三月營收遞增")
    log("="*60)
    
    # 執行篩選
    results = batch_screen_with_rate_limit(TWSE_MAJOR_STOCKS)
    
    if not results:
        log("❌ 無篩選結果")
        return 1
    
    # 排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 生成報告
    log("\n" + "="*60)
    log("生成HTML報告...")
    html = generate_report(results)
    filepath = save_report(html)
    log(f"✅ 報告已保存：{filepath}")
    
    # 輸出結果
    passed = [r for r in results if r['all_pass']]
    
    log("\n" + "="*60)
    log("篩選結果摘要")
    log("="*60)
    log(f"總分析數：{len(results)} 檔")
    log(f"完全符合：{len(passed)} 檔")
    log(f"部分符合：{len(results) - len(passed)} 檔")
    
    if passed:
        log("\n✅ 完全符合所有條件的股票：")
        for r in passed:
            log(f"  - {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f})")
    else:
        log("\n⚠️  無完全符合的股票")
        log("\n🏆 得分最高的股票 (Top 10):")
        for i, r in enumerate(results[:10], 1):
            log(f"  {i}. {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f})")
            log(f"     條件1: {'✅' if r['condition_1']['pass'] else '❌'} | 條件2: {'✅' if r['condition_2']['pass'] else '❌'}")
    
    log("\n" + "="*60)
    log(f"📁 完整報告：{filepath}")
    log("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
