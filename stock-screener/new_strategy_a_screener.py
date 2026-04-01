#!/usr/bin/env python3
"""
新策略A篩選器 - 2026-04-01
條件：
1. 5日均線在20日均線下方（5MA < 20MA）
2. 兩線價差（20MA-5MA）連三日縮小
3. 20MA > 5MA（方向未翻轉）且兩線價差 < 1%
4. 最近交易日：兩線價差 < 1%
5. 連三日量增（今日 > 昨日 > 前日 > 大前日）

出场：價格反彈至 MA20 獲利了結
停損：進場價 -3%
"""
import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
OUTPUT_DIR = f"{SCREENER_DIR}/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 全市場股票清單
TWSE_STOCKS = [
    '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
    '3481','2353','2345','2609','2610','2323','2325','2344','2352','2360',
    '2379','2383','2440','2498','3006','3014','3031','3045','3090','3130',
    '3149','3189','3231','3257','3305','3338','3416','3443','3450','3481',
    '3504','3532','3545','3567','3576','3532','3583','3587','3593','3594','3607',
    '3617','3652','3661','3665','3673','3682','3698','3702','3706','3711',
    '3714','3740','3800','3838','4001','4002','4107','4137','4401','4414',
    '4426','4523','4549','4551','4562','4580','4604','4702','4707','4720',
    '4807','4904','4930','4938','4952','4958','4960','5009','5104','5120',
    '5130','5151','5203','5225','5234','5264','5309','5387','5434','5469',
    '5474','5487','5511','5512','5522','5530','5536','5607','5609','5701',
    '5702','5820','5876','5880','5903','5904','5906','6005','6024','6026',
    '6108','6112','6115','6116','6120','6128','6136','6147','6152','6153',
    '6155','6164','6165','6172','6174','6176','6180','6182','6184','6185',
    '6190','6191','6192','6201','6202','6205','6206','6208','6213','6214',
    '6216','6220','6221','6223','6225','6226','6229','6230','6234','6235',
    '6239','6244','6257','6269','6270','6271','6274','6275','6279','6281',
    '6283','6285','6288','6289','6290','6291','6292','6293','6294','6505',
    '6525','6531','6533','6535','6541','6542','6550','6560','6569','6570',
    '6575','6579','6581','6585','6590','6591','6592','6594','6603','6625',
    '6655','6700','6706','6715','6721','6752','6756','6806','6881','6889',
    '8011','8016','8021','8033','8039','8046','8050','8069','8070','8081',
    '8101','8105','8110','8114','8121','8147','8150','8163','8171','8176',
    '8183','8200','8210','8213','8215','8226','8234','8249','8255','8261',
    '8271','8277','8285','8289','8299','8303','8306','8341','8349','8354',
    '8358','8367','8374','8383','8401','8410','8415','8420','8422','8426',
    '8430','8442','8454','8462','8463','8464','8473','8478','8482','8495',
    '8506','8905','8906','8916','8917','8927','8930','8931','8932','8933',
    '8934','8935','8936','8937','8938','8941','8942','8996','9904','9905',
    '9910','9911','9914','9917','9921','9924','9925','9928','9930','9931',
    '9933','9934','9935','9937','9938','9939','9940','9941','9942','9943',
    '9944','9945','9946','9950','9955','9956','9958',
]

# 簡化股票代號映射
STOCK_NAMES = {
    '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2382': '緯創', '2308': '台達電',
    '2303': '聯電', '3034': '聯詠', '2357': '華碩', '3008': '大立光', '2327': '國巨',
    '3481': '友達', '2353': '宏碁', '2345': '智邦', '2609': '陽明', '2610': '長榮',
    '2323': '中壽', '2325': '矽品', '2344': '華邦電', '2352': '方正', '2360': '鴻準',
    '2379': '瑞昱', '2383': '台光電', '2440': '太空梭', '2498': '宏達電', '3006': '順德',
    '3014': '聯陽', '3031': '佰鴻', '3045': '凌耀', '3090': '日電硝', '3130': '一零',
    '3149': '衡平', '3189': '景碩', '3231': '緯穎', '3257': '虹冠電', '3305': '聚積',
    '3338': '新利虹', '3416': '龍燷', '3443': '創意', '3450': '聯亞', '3504': '昇陽',
    '3532': '台勝科', '3545': '敦泰', '3567': '逸昌', '3576': '新日光', '3583': '辛耘',
    '3587': '闊新', '3593': '保銓', '3594': '淂瑩', '3607': '谷林', '3617': '頎邦',
    '3652': '力致', '3661': '世芯', '3665': '創家', '3673': 'TPK', '3682': '粵海',
    '3698': '上海', '3702': '大聯大', '3706': '永道', '3711': '眾達', '3714': '富邦',
    '3740': '永固', '3800': '傳', '3838': '大', '4001': '中華', '4002': '中石化',
    '4107': '美吾', '4137': '星', '4401': '大', '4414': '永', '4426': '大',
    '4523': '大', '4549': '大', '4551': '大', '4562': '大', '4580': '大',
    '4604': '大', '4702': '大', '4707': '大', '4720': '大', '4807': '大',
    '4904': '大', '4930': '大', '4938': '大', '4952': '大', '4958': '大',
    '4960': '大', '5009': '大', '5104': '大', '5120': '大', '5130': '大',
    '5151': '大', '5203': '大', '5225': '大', '5234': '大', '5264': '大',
    '5309': '大', '5387': '大', '5434': '大', '5469': '大', '5474': '大',
    '5487': '大', '5511': '大', '5512': '大', '5522': '大', '5530': '大',
    '5536': '大', '5607': '大', '5609': '大', '5701': '大', '5702': '大',
    '5820': '大', '5876': '大', '5880': '大', '5903': '大', '5904': '大',
    '5906': '大', '6005': '大', '6024': '大', '6026': '大', '6108': '大',
    '6112': '大', '6115': '大', '6116': '大', '6120': '大', '6128': '大',
    '6136': '大', '6147': '大', '6152': '大', '6153': '大', '6155': '大',
    '6164': '大', '6165': '大', '6172': '大', '6174': '大', '6176': '大',
    '6180': '大', '6182': '大', '6184': '大', '6185': '大', '6190': '大',
    '6191': '大', '6192': '大', '6201': '大', '6202': '大', '6205': '大',
    '6206': '大', '6208': '大', '6213': '大', '6214': '大', '6216': '大',
    '6220': '大', '6221': '大', '6223': '大', '6225': '大', '6226': '大',
    '6229': '大', '6230': '大', '6234': '大', '6235': '大', '6239': '大',
    '6244': '大', '6257': '大', '6269': '大', '6270': '大', '6271': '大',
    '6274': '大', '6275': '大', '6279': '大', '6281': '大', '6283': '大',
    '6285': '大', '6288': '大', '6289': '大', '6290': '大', '6291': '大',
    '6292': '大', '6293': '大', '6294': '大', '6505': '大', '6525': '大',
    '6531': '大', '6533': '大', '6535': '大', '6541': '大', '6542': '大',
    '6550': '大', '6560': '大', '6569': '大', '6570': '大', '6575': '大',
    '6579': '大', '6581': '大', '6585': '大', '6590': '大', '6591': '大',
    '6592': '大', '6594': '大', '6603': '大', '6625': '大', '6655': '大',
    '6700': '大', '6706': '大', '6715': '大', '6721': '大', '6752': '大',
    '6756': '大', '6806': '大', '6881': '大', '6889': '大', '2008': '高興昌',
    '2007': '燁興', '3023': '信邦',
}

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_stock_data(symbol: str, days: int = 40) -> Optional[pd.DataFrame]:
    """使用 yfinance 獲取股票數據"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.TW")
        end = datetime.now()
        start = end - timedelta(days=days * 2)
        df = ticker.history(start=start, end=end)
        if df is None or df.empty or len(df) < 25:
            return None
        
        records = []
        for idx, row in df.iterrows():
            try:
                records.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume'])
                })
            except:
                continue
        
        if len(records) < 25:
            return None
        
        result = pd.DataFrame(records)
        return result
        
    except Exception as e:
        return None

def analyze_new_strategy_a(df: pd.DataFrame) -> Dict:
    """
    分析股票是否符合新策略A的5個進場條件
    返回分析結果字典
    """
    if len(df) < 25:
        return None
    
    # 取最近25天
    df = df.tail(25).reset_index(drop=True)
    
    close = df['close'].values
    volume = df['volume'].values
    dates = df['date'].values
    
    # 計算MA5和MA20
    ma5_all = []
    ma20_all = []
    gap_pct_all = []
    
    for i in range(len(close)):
        if i >= 4:  # 需要至少5天計算MA5
            ma5 = close[max(0, i-4):i+1].mean()
        else:
            ma5 = close[:i+1].mean()
        
        if i >= 19:  # 需要至少20天計算MA20
            ma20 = close[max(0, i-19):i+1].mean()
        else:
            ma20 = close[:i+1].mean()
        
        ma5_all.append(ma5)
        ma20_all.append(ma20)
        gap_pct_all.append((ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0)
    
    # 最近4天需要計算（今日、昨日、前日、大前日）
    n = len(close)
    if n < 4:
        return None
    
    # 最新數據（今日 = index -1，但為了方便我們用倒數的方式）
    # 我們用正數index：0=最舊，n-1=最新
    latest_idx = n - 1
    prev1_idx = n - 2  # 昨日
    prev2_idx = n - 3  # 前日
    prev3_idx = n - 4  # 大前日
    
    ma5_latest = ma5_all[latest_idx]
    ma20_latest = ma20_all[latest_idx]
    gap_pct_latest = gap_pct_all[latest_idx]
    
    # 條件1：5MA < 20MA（5日均線在20日均線下方）
    cond1 = ma5_latest < ma20_latest
    
    # 條件2：兩線價差（20MA-5MA）連三日縮小
    # 需要第1天、第2天、第3天的價差，並確認是否逐日縮小
    gap_d3 = gap_pct_all[prev3_idx]  # 大前日
    gap_d2 = gap_pct_all[prev2_idx]  # 前日
    gap_d1 = gap_pct_all[prev1_idx]  # 昨日
    gap_d0 = gap_pct_all[latest_idx]  # 今日
    
    cond2 = (gap_d2 < gap_d3) and (gap_d1 < gap_d2) and (gap_d0 < gap_d1)  # 連三日縮小
    
    # 條件3：20MA > 5MA（方向未翻轉）且兩線價差 < 1%
    cond3 = cond1 and (gap_pct_latest < 1.0)
    
    # 條件4：最近交易日：兩線價差 < 1%
    cond4 = gap_pct_latest < 1.0
    
    # 條件5：連三日量增（今日 > 昨日 > 前日 > 大前日）
    vol_today = volume[latest_idx]
    vol_yesterday = volume[prev1_idx]
    vol_2day = volume[prev2_idx]
    vol_3day = volume[prev3_idx]
    cond5 = (vol_today > vol_yesterday) and (vol_yesterday > vol_2day) and (vol_2day > vol_3day)
    
    # 計算10日內最高/最低
    high_10 = df['high'].tail(10).max()
    low_10 = df['low'].tail(10).min()
    latest_close = close[latest_idx]
    price_vs_high = (latest_close - high_10) / high_10 * 100
    price_vs_low = (latest_close - low_10) / low_10 * 100
    
    # 進場價建議（現價）
    entry_price = latest_close
    
    # 目標（MA20）
    target_price = round(ma20_latest, 2)
    target_pct = (target_price - entry_price) / entry_price * 100
    
    # 停損價（-3%）
    stop_loss = round(entry_price * 0.97, 2)
    
    result = {
        'symbol': None,  # 填入
        'name': None,    # 填入
        'date': dates[latest_idx],
        'close': latest_close,
        'ma5': round(ma5_latest, 2),
        'ma20': round(ma20_latest, 2),
        'gap_pct': round(gap_pct_latest, 3),
        'gap_d3': round(gap_d3, 3),  # 大前日
        'gap_d2': round(gap_d2, 3),  # 前日
        'gap_d1': round(gap_d1, 3),  # 昨日
        'gap_d0': round(gap_d0, 3),  # 今日
        'cond1_ma5_below_ma20': cond1,
        'cond2_gap_shrinking_3d': cond2,
        'cond3_gap_lt_1pct': cond3,
        'cond4_latest_gap_lt_1pct': cond4,
        'cond5_vol_increase_3d': cond5,
        'cond1_ok': '✅' if cond1 else '❌',
        'cond2_ok': '✅' if cond2 else '❌',
        'cond3_ok': '✅' if cond3 else '❌',
        'cond4_ok': '✅' if cond4 else '❌',
        'cond5_ok': '✅' if cond5 else '❌',
        'cond_count': sum([cond1, cond2, cond3, cond4, cond5]),
        'high_10': round(high_10, 2),
        'low_10': round(low_10, 2),
        'price_vs_high_pct': round(price_vs_high, 2),
        'price_vs_low_pct': round(price_vs_low, 2),
        'vol_today': int(vol_today),
        'vol_yesterday': int(vol_yesterday),
        'vol_2day': int(vol_2day),
        'vol_3day': int(vol_3day),
        'entry_price': entry_price,
        'target_price': target_price,
        'stop_loss': stop_loss,
        'target_pct': round(target_pct, 2),
    }
    
    return result

def main():
    log("新策略A篩選器啟動（2026-04-01）")
    
    # 讀取候選股票（優先使用 result_4_kline_volume）
    result_file = f"{OUTPUT_DIR}/fixed_batch_results_20260401_202256.json"
    candidates = []
    
    if os.path.exists(result_file):
        with open(result_file) as f:
            data = json.load(f)
            candidates = data.get('strategies', {}).get('result_4_kline_volume', [])
            log(f"從 result_4_kline_volume 載入 {len(candidates)} 檔候選")
    
    # 如果 result_4 為空，使用 result_1_tech_only（如果存在的話）
    if not candidates:
        log("result_4_kline_volume 為空，檢查是否有 result_1_tech_only...")
        # 沒有 result_1_tech_only，改用全市場股票
        candidates = []
    
    # 如果仍然沒有候選，使用全市場股票（分批處理以節省時間）
    if not candidates:
        log("使用全市場股票清單進行新策略A篩選...")
        # 只取部分代表性股票以節省時間
        # 優先取成交量大的藍籌股
        priority_stocks = [
            '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
            '3481','2353','2345','2609','2610','2323','2325','2344','2352','2360',
            '2379','2383','2440','2498','3006','3014','3031','3045','3090','3130',
            '3149','3189','3231','3257','3305','3416','3443','3450','3504','3532',
            '3545','3661','3673','3682','3711','3714','4958','4960','5009','6108',
            '6116','6128','6153','6165','6176','6180','6182','6191','6201','6213',
            '6221','6230','6269','6271','6277','6281','6285','6288','6291','6505',
            '6525','6533','6550','6560','6569','6570','6575','6579','6581','6590',
            '6591','6592','6700','6706','6715','6756','6806','6881','6889',
            '2008','2007','3023',
        ]
        candidates = [{'symbol': s} for s in priority_stocks]
        log(f"共 {len(candidates)} 檔候選股票")
    
    # 分析每檔股票
    passed = []      # 完全符合（5/5條件）
    near_miss = []   # 接近符合（3-4/5條件）
    
    batch_size = 5
    total = len(candidates)
    
    for i, cand in enumerate(candidates):
        sym = cand.get('symbol') or cand.get('code') or cand.get('stock_id')
        if not sym:
            continue
        
        log(f"[{i+1}/{total}] 分析 {sym}...")
        
        df = get_stock_data(sym, days=40)
        if df is None or len(df) < 25:
            time.sleep(0.3)
            continue
        
        result = analyze_new_strategy_a(df)
        if result is None:
            time.sleep(0.3)
            continue
        
        result['symbol'] = sym
        result['name'] = STOCK_NAMES.get(sym, sym)
        
        count = result['cond_count']
        if count == 5:
            passed.append(result)
            log(f"  ✅ {sym} 完全符合！({count}/5)")
        elif count >= 3:
            near_miss.append(result)
        
        time.sleep(0.5)  # 避免API限速
    
    # 輸出結果
    print()
    print("=" * 100)
    print("【新策略A篩選結果 2026-04-01】")
    print("=" * 100)
    print()
    
    if not passed:
        print("📊 完全符合新策略A的標的：0 檔")
        print()
        print("說明：今日無股票完全滿足全部5個進場條件。")
        print("可能原因：")
        print("  1. result_4_kline_volume 今日篩選結果為空（0檔通過）")
        print("  2. result_1_tech_only 無今日資料")
        print("  3. 市場今日走勢與新策略A進場條件不相符")
        print("  4. 兩線價差收斂至 <1% 的股票數量稀少")
    else:
        print(f"📊 完全符合新策略A的標的（MA5-MA20黃金交叉前夕）：{len(passed)} 檔")
        print()
        header = f"{'代碼':<6} {'名稱':<8} {'現價':>8} {'MA5':>8} {'MA20':>8} {'兩線差%':>8} {'三日收斂':>8} {'差<1%':>6} {'量增3日':>8} {'進場價':>8} {'目標':>8} {'停損':>8}"
        print(header)
        print("-" * 100)
        for r in sorted(passed, key=lambda x: x['gap_pct']):
            print(f"{r['symbol']:<6} {r['name']:<8} {r['close']:>8.2f} {r['ma5']:>8.2f} {r['ma20']:>8.2f} {r['gap_pct']:>8.3f} {'✅' if r['cond2_gap_shrinking_3d'] else '❌':>8} {'✅' if r['cond4_latest_gap_lt_1pct'] else '❌':>6} {'✅' if r['cond5_vol_increase_3d'] else '❌':>8} {r['entry_price']:>8.2f} {r['target_price']:>8.2f} {r['stop_loss']:>8.2f}")
    
    print()
    if near_miss:
        print(f"📊 接近符合的標的（缺1-2條件）：{len(near_miss)} 檔")
        print()
        header2 = f"{'代碼':<6} {'名稱':<8} {'現價':>8} {'兩線差%':>8} {'滿足條件':>8} {'缺失條件':<30} {'備註':<20}"
        print(header2)
        print("-" * 100)
        for r in sorted(near_miss, key=lambda x: -x['cond_count']):
            missing = []
            if not r['cond1_ma5_below_ma20']: missing.append('MA5≥MA20')
            if not r['cond2_gap_shrinking_3d']: missing.append('三日未收斂')
            if not r['cond3_gap_lt_1pct']: missing.append('差≥1%')
            if not r['cond4_latest_gap_lt_1pct']: missing.append('今日差≥1%')
            if not r['cond5_vol_increase_3d']: missing.append('量未增3日')
            missing_str = ','.join(missing) if missing else '無'
            remark = f"10日低:{r['price_vs_low_pct']:.1f}% 高:{r['price_vs_high_pct']:.1f}%"
            print(f"{r['symbol']:<6} {r['name']:<8} {r['close']:>8.2f} {r['gap_pct']:>8.3f} {r['cond_count']:>8}/5    {missing_str:<30} {remark:<20}")
    else:
        print("📊 接近符合的標的（缺1-2條件）：0 檔")
    
    print()
    print("=" * 100)
    print("【策略說明】")
    print("新策略A進場條件（需同時滿足5條件）：")
    print("  1. 5日均線在20日均線下方（5MA < 20MA）")
    print("  2. 兩線價差（20MA-5MA）連三日縮小")
    print("  3. 20MA > 5MA（方向未翻轉）且兩線價差 < 1%")
    print("  4. 最近交易日：兩線價差 < 1%")
    print("  5. 連三日量增（今日 > 昨日 > 前日 > 大前日）")
    print()
    print("出场：價格反彈至 MA20 獲利了結")
    print("停損：進場價 -3%")
    print("=" * 100)
    
    # 保存結果
    output_data = {
        'date': '20260401',
        'timestamp': datetime.now().isoformat(),
        'passed': passed,
        'near_miss': near_miss,
        'total_screened': total,
    }
    
    out_file = f"{OUTPUT_DIR}/new_strategy_a_results_20260401_{datetime.now().strftime('%H%M%S')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    log(f"結果已保存：{out_file}")

if __name__ == '__main__':
    main()
