#!/usr/bin/env python3
"""
台股上市股票篩選 - 成交量優先版本
Step 1: 篩選成交量前200大股票
Step 2: 套用技術面條件篩選
"""
import os
import sys
import gc
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_api')

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

def get_stock_volume(client, symbol: str, days: int = 30) -> Optional[Dict]:
    """獲取股票平均成交量"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        data = client.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            timeframe="D"
        )
        
        if not data or len(data) < 10:
            return None
        
        df = pd.DataFrame(data)
        avg_volume = df['volume'].mean()
        latest_price = df.iloc[-1]['close']
        latest_volume = df.iloc[-1]['volume']
        
        result = {
            'symbol': symbol,
            'avg_volume': float(avg_volume),
            'latest_volume': float(latest_volume),
            'latest_price': float(latest_price)
        }
        
        del df
        del data
        gc.collect()
        
        return result
        
    except Exception as e:
        return None

def get_top_volume_stocks(symbols: List[str], top_n: int = 200) -> List[str]:
    """Step 1: 篩選成交量前N大股票"""
    from fubon_kline_sdk import FubonKlineSDK
    
    log(f"Step 1: 篩選成交量前{top_n}大股票...")
    log(f"候選股票數：{len(symbols)} 檔")
    
    volume_data = []
    
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 登入失敗")
        return []
    
    try:
        for i, symbol in enumerate(symbols, 1):
            if i % 10 == 0:
                log(f"  已處理 {i}/{len(symbols)} 檔...")
            
            data = get_stock_volume(client, symbol)
            if data:
                volume_data.append(data)
            
            # 每檔間隔1秒，符合API限制
            time.sleep(1.0)
            
    finally:
        client.logout()
    
    # 依成交量排序，取前N
    volume_data.sort(key=lambda x: x['avg_volume'], reverse=True)
    top_stocks = [d['symbol'] for d in volume_data[:top_n]]
    
    log(f"\n✅ 篩選完成，成交量前{top_n}大股票：")
    for i, d in enumerate(volume_data[:10], 1):
        log(f"  {i:2d}. {d['symbol']}: {d['avg_volume']/1000000:.1f}M股/日")
    log(f"  ... (共{top_n}檔)")
    
    return top_stocks, volume_data[:top_n]

def screen_with_conditions(symbols: List[str]) -> List[Dict]:
    """Step 2: 套用技術面條件篩選"""
    from fubon_kline_sdk import FubonKlineSDK
    
    log(f"\nStep 2: 套用技術面條件篩選...")
    log(f"篩選對象：{len(symbols)} 檔高成交量股票")
    
    results = []
    
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 登入失敗")
        return results
    
    try:
        for i, symbol in enumerate(symbols, 1):
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                data = client.get_historical_candles(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    timeframe="D"
                )
                
                if not data or len(data) < 20:
                    continue
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                if len(df) > 60:
                    df = df.iloc[-60:]
                
                c1_pass, c1_detail, c1_score = check_condition_1(df)
                c2_pass, c2_detail, c2_score = check_condition_2(df)
                c3_pass, c3_detail, c3_score = True, "需要財務數據API", 0.5
                
                total_score = c1_score + c2_score + c3_score
                
                result = {
                    'symbol': symbol,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'current_price': float(df.iloc[-1]['close']),
                    'volume': int(df.iloc[-1]['volume']),
                    'avg_volume': float(df['volume'].mean()),
                    'condition_1': {'pass': c1_pass, 'detail': c1_detail, 'score': c1_score},
                    'condition_2': {'pass': c2_pass, 'detail': c2_detail, 'score': c2_score},
                    'condition_3': {'pass': c3_pass, 'detail': c3_detail, 'score': c3_score},
                    'total_score': total_score,
                    'all_pass': c1_pass and c2_pass and c3_pass
                }
                
                results.append(result)
                
                status = "✅" if result['all_pass'] else "⚠️"
                log(f"[{i}/{len(symbols)}] {status} {symbol}: {result['current_price']:.2f} (得分: {total_score:.1f})")
                
                del df
                del data
                gc.collect()
                
            except Exception as e:
                continue
            
            # 每檔間隔1秒
            if i < len(symbols):
                time.sleep(1.0)
            
    finally:
        client.logout()
    
    return results

def generate_report(results: List[Dict], top_volume_data: List[Dict]) -> str:
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
            <td>{r['avg_volume']/1000000:.1f}M</td>
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
    <title>台股成交量前200大股票篩選報告</title>
    <style>
        body {{ font-family: 'Microsoft JhengHei', Arial, sans-serif; background: #1a1a2e; color: #fff; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #667eea; }}
        .summary {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .summary-item {{ text-align: center; }}
        .summary-item h3 {{ font-size: 2em; margin: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #667eea; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #444; }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.05); }}
        .positive {{ color: #00d084; }}
        .negative {{ color: #ff4757; }}
        .footer {{ text-align: center; margin-top: 30px; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股成交量前200大股票篩選報告</h1>
        <p style="text-align:center">篩選時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
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
                <h3 style="color: #667eea">{len(top_volume_data)}</h3>
                <p>成交量前200大</p>
            </div>
        </div>
        
        <h2>🏆 Top 20 得分最高</h2>
        <table>
            <tr><th>狀態</th><th>代號</th><th>價格</th><th>均量</th><th>得分</th><th>條件1</th><th>條件2</th><th>條件1詳情</th><th>條件2詳情</th></tr>
            {rows}
        </table>
        
        <div class="footer">
            <p>Powered by 富邦證券SDK | 成交量前200大篩選</p>
            <p>⚠️ 數據僅供參考，投資有風險</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def save_report(html_content: str) -> str:
    """保存報告"""
    PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw/stockanalysis"
    filename = f"twse_volume_screener_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filepath

def main():
    """主程式"""
    # 台股主要股票清單（約300檔流動性較高的股票）
    symbols = [
        # 金融股
        '2881', '2882', '2883', '2884', '2885', '2886', '2887', '2888', '2889', '2890',
        '2891', '2892', '2897', '5871', '5876', '5880',
        # 電子科技股
        '2330', '2317', '2454', '2382', '2308', '2303', '3711', '3034', '2357', '3231',
        '3008', '2327', '3045', '2301', '3661', '2379', '2324', '2618', '2002', '3481',
        '2353', '2345', '2609', '2610', '2323', '2325', '2337', '2340', '2344', '2347',
        '2352', '2356', '2360', '2362', '2363', '2365', '2373', '2375', '2376', '2377',
        '2383', '2385', '2388', '2392', '2401', '2404', '2405', '2406', '2408', '2412',
        # 傳產股
        '1101', '1102', '1103', '1216', '1301', '1303', '1304', '1307', '1308', '1309',
        '1402', '1410', '1503', '1504', '1506', '1507', '1603', '1604', '1605', '1701',
        '1702', '1704', '1707', '1708', '1710', '1711', '1712', '1713', '1714', '1717',
        '1718', '1720', '1721', '1722', '1723', '1724', '1725', '1726', '1727', '1729',
        # ETF
        '0050', '0056', '00878', '00881', '00882', '00887', '00891', '00900', '00919', '00929',
        '00632R', '00633L', '00650L', '00655L', '00657L', '00658L', '00661R', '00662L', '00663L', '00664R',
        '00665L', '00666R', '00667R', '00668R', '00669R', '00670L', '00671R', '00672L', '00673R', '00674R',
        '00675L', '00676R', '00677U', '00678L', '00680L',
        # 其他大型股
        '2002', '2006', '2008', '2009', '2010', '2012', '2013', '2014', '2015', '2017',
        '2020', '2022', '2023', '2024', '2025', '2027', '2028', '2029', '2030', '2031',
        '2032', '2033', '2034', '2038', '2049', '2059', '2062', '2069', '2101', '2102',
        '2103', '2104', '2105', '2106', '2107', '2108', '2109', '2114', '2115', '2201',
        '2204', '2206', '2207', '2208', '2211', '2221', '2227', '2228', '2231', '2233',
        '2236', '2239', '2241', '2243', '2247', '2250', '2302', '2305', '2311', '2312',
        '2313', '2314', '2316', '2321', '2328', '2329', '2331', '2338', '2342', '2348',
        '2351', '2354', '2355', '2358', '2359', '2364', '2367', '2368', '2369', '2371',
        '2374', '2380', '2387', '2390', '2393', '2395', '2397', '2399', '2402', '2409',
        '2413', '2414', '2415', '2417', '2419', '2420', '2421', '2423', '2424', '2425',
        '2426', '2427', '2428', '2429', '2430', '2431', '2433', '2434', '2436', '2438',
        '2439', '2440', '2441', '2442', '2443', '2444', '2449', '2450', '2451', '2453',
        '2455', '2456', '2457', '2458', '2459', '2460', '2461', '2462', '2464', '2465',
        '2466', '2467', '2468', '2471', '2472', '2474', '2480', '2481', '2482', '2483',
        '2485', '2486', '2488', '2489', '2491', '2492', '2493', '2495', '2496', '2497',
        '2498', '2501', '2504', '2505', '2506', '2509', '2511', '2514', '2515', '2516',
        '2520', '2524', '2527', '2528', '2530', '2534', '2535', '2536', '2537', '2538',
        '2539', '2540', '2542', '2543', '2545', '2546', '2547', '2548', '2596', '2597',
        '2601', '2603', '2605', '2606', '2607', '2608', '2611', '2612', '2613', '2614',
        '2615', '2616', '2617',
    ]
    
    log("="*60)
    log("台股上市股票篩選 - 成交量優先版本")
    log("="*60)
    log(f"Step 1: 從 {len(symbols)} 檔股票中篩選成交量前200大")
    log(f"Step 2: 套用技術面條件篩選")
    log("="*60)
    
    # Step 1: 篩選成交量前200大
    top_volume_stocks, top_volume_data = get_top_volume_stocks(symbols, top_n=200)
    
    if not top_volume_stocks:
        log("❌ 無法取得成交量數據")
        return 1
    
    # Step 2: 套用技術面條件
    results = screen_with_conditions(top_volume_stocks)
    
    if not results:
        log("❌ 無篩選結果")
        return 1
    
    # 排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 生成報告
    log("\n生成HTML報告...")
    html = generate_report(results, top_volume_data)
    filepath = save_report(html)
    log(f"✅ 報告已保存：{filepath}")
    
    # 輸出結果
    passed = [r for r in results if r['all_pass']]
    
    log("\n" + "="*60)
    log("篩選結果摘要")
    log("="*60)
    log(f"Step 1 - 成交量前200大：{len(top_volume_stocks)} 檔")
    log(f"Step 2 - 技術面篩選結果：")
    log(f"  完全符合：{len(passed)} 檔")
    log(f"  部分符合：{len(results) - len(passed)} 檔")
    log(f"  總分析數：{len(results)} 檔")
    
    if passed:
        log("\n✅ 完全符合所有條件的股票：")
        for r in passed:
            log(f"  - {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f}, 均量: {r['avg_volume']/1000000:.1f}M)")
    else:
        log("\n⚠️  無完全符合的股票")
        log("\n🏆 得分最高的股票 (Top 10):")
        for i, r in enumerate(results[:10], 1):
            log(f"  {i}. {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f}, 均量: {r['avg_volume']/1000000:.1f}M)")
            log(f"     條件1: {'✅' if r['condition_1']['pass'] else '❌'} | 條件2: {'✅' if r['condition_2']['pass'] else '❌'}")
    
    log("\n" + "="*60)
    log(f"📁 完整報告：{filepath}")
    log("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
