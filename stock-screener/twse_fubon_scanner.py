#!/usr/bin/env python3
"""
TWSE + Fubon API 混合策略A掃描器
================================
【這個是正確版本】
- TWSE: 取得股票清單 + 今日收盤價（無 rate limit）
- Fubon API: 直接取得 MA5、MA20（SMA技術分析 API）

【Rate Limit 規定】
- 歷史行情: 60 次/分鐘（即每檔間隔 1 秒）
- 遇到 429 錯誤需等候 1 分鐘後重試
"""
import sys
import json
import time
import os
from datetime import datetime, date

# ====== 設定 ======
WORKSPACE = "/home/admin/.openclaw/workspace"
STATE_FILE = f"{WORKSPACE}/tmp/scan_state_twse_fubon.json"
OUTPUT_FILE = f"{WORKSPACE}/tmp/strategy_a_daily.json"
DELAY = 1    # 每檔間隔秒數（歷史行情 rate limit: 60/min）
GAP_LIMIT = 2.0
RETRIES = 3

# ====== TWSE 下載（僅取清單+今日收盤價）======
def get_twse_today():
    """從 TWSE 取得今日收盤資料（股票清單+價格）"""
    import urllib.request
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=ALL&response=json"
    
    print(f"下載 TWSE 資料: {date_str}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode('utf-8'))
    
    tables = raw.get('tables', [])
    if not tables:
        print("TWSE: 無表格資料")
        return {}
    
    # 找「每日收盤行情(全部)」表格
    target_table = None
    for t in tables:
        title = t.get('title', '')
        if '收盤行情' in title and '全部' in title:
            target_table = t
            break
    
    if not target_table:
        print("TWSE: 找不到收盤行情表格")
        return {}
    
    result = {}
    skipped = 0
    for row in target_table.get('data', []):
        if len(row) < 9:
            continue
        code = row[0].strip()
        name = row[1].strip() if len(row) > 1 else code
        
        # 過濾：只留上市櫃股票 + ETF
        if not is_stock_or_etf(code):
            skipped += 1
            continue
        
        try:
            close = float(row[8].replace(',', ''))
            vol = int(row[2].replace(',', '')) if row[2] else 0
            result[code] = {'name': name, 'close': close, 'volume': vol}
        except (ValueError, IndexError):
            continue
    
    print(f"TWSE: 取得 {len(result)} 檔（已過濾 {skipped} 檔）")
    return result


def is_stock_or_etf(code):
    """過濾上市櫃股票 + ETF"""
    if code.startswith('00') or code.startswith('02'):
        return True
    if len(code) >= 4 and len(code) <= 6 and code.isdigit():
        first = int(code[0])
        if first in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            return True
    return False


# ====== Fubon SDK ======
sys.path.insert(0, f"{WORKSPACE}/fubon_sdk_complete")
from fubon_complete import FubonComplete


def get_fubon_sma_with_retry(fc, code, period=20):
    """從 Fubon SDK 取得 SMA（含重試機制）"""
    for attempt in range(RETRIES):
        try:
            sma = fc.get_sma(code, period)
            # 每呼叫一次 API，間隔 1 秒（歷史行情 rate limit: 60/min）
            time.sleep(DELAY)
            if sma and len(sma) >= period:
                return sma
            return None
        except Exception as e:
            err_str = str(e).lower()
            if '429' in err_str or 'rate' in err_str or 'timeout' in err_str:
                wait = 60  # Rate limit 需等候 1 分鐘
                print(f"  ⚠️ {code} rate limit，等待 {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ {code} SMA 錯誤: {e}")
                return None
    print(f"  ❌ {code} 多次失敗")
    return None


# ====== 策略分析 ======
def analyze_strategy_a(code, twse_data, fc):
    """
    策略A分析（使用 Fubon SDK 直接取 MA5、MA20）
    條件1: MA5 < MA20
    條件2: gap 三日縮小
    條件3: gap < 2%
    """
    today_data = twse_data.get(code)
    if not today_data:
        return None
    
    close = today_data.get('close')
    if not close or close <= 0:
        return None
    
    # 從 Fubon SDK 直接取得 MA5 和 MA20
    sma5 = get_fubon_sma_with_retry(fc, code, 5)
    sma20 = get_fubon_sma_with_retry(fc, code, 20)
    
    if not sma5 or not sma20:
        return None
    if len(sma5) < 5 or len(sma20) < 20:
        return None
    
    # 取最新值
    m5 = sma5[-1]['sma']
    m20 = sma20[-1]['sma']
    gap = (m20 - m5) / m20 * 100 if m20 > 0 else None
    
    # 計算三日 gap 序列
    gaps = []
    for offset in range(-4, 1):
        idx = len(sma20) + offset
        if 0 <= idx < len(sma5):
            m5d = sma5[idx]['sma']
            m20d = sma20[idx]['sma']
            if m20d > 0:
                gaps.append((m20d - m5d) / m20d * 100)
    
    cond1 = m5 < m20
    cond2 = len(gaps) >= 4 and gaps[-1] < gaps[-2] < gaps[-3] < gaps[-4] if len(gaps) >= 4 else False
    cond3 = gap is not None and gap > 0 and abs(gap) < GAP_LIMIT
    
    ok = cond1 and cond2 and cond3
    conf = (int(cond1) + int(cond2) + int(cond3)) / 3 * 100
    
    return {
        'code': code,
        'name': today_data.get('name', code),
        'close': close,
        'ma5': round(m5, 2),
        'ma20': round(m20, 2),
        'gap': round(gap, 3) if gap else None,
        'gap_seq': [round(g, 2) for g in gaps[-4:]] if gaps else [],
        'cond1': cond1,
        'cond2': cond2,
        'cond3': cond3,
        'confidence': round(conf, 1),
        'ok': ok
    }


# ====== 主要掃描流程 ======
def main():
    now = datetime.now()
    print(f"\n[{'='*60}]")
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] TWSE+Fubon 策略A掃描啟動")
    print(f"[{'='*60}]\n")
    
    # Step 1: 下載 TWSE 今日資料
    twse_data = get_twse_today()
    if not twse_data:
        print("❌ 無法取得 TWSE 資料，掃描終止")
        return
    
    # Step 2: 登入 Fubon SDK
    fc = FubonComplete()
    fc._load_config()
    fc.login()
    print()
    
    # Step 3: 分析
    results = []
    codes = list(twse_data.keys())
    total = len(codes)
    
    print(f"總共 {total} 檔待掃描")
    print(f"每檔間隔 {DELAY} 秒，預計耗時 {total * DELAY / 60:.0f} 分鐘\n")
    
    for i, code in enumerate(codes):
        r = analyze_strategy_a(code, twse_data, fc)
        if r:
            results.append(r)
        
        # 進度報告
        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"  進度: {i+1}/{total} ({(i+1)*100//total}%)")
    
    # 分類結果
    passed = [x for x in results if x['ok']]
    near = sorted([x for x in results if not x['ok'] and x['confidence'] > 0], 
                  key=lambda x: -x['confidence'])[:20]
    
    print(f"\n{'='*60}")
    print(f"掃描完成！")
    print(f"總掃描: {len(results)}/{total} 檔")
    print(f"符合3/3條件: {len(passed)} 檔")
    print(f"{'='*60}\n")
    
    if passed:
        print(f"【完全符合 3/3 條件】({len(passed)}檔)")
        for p in sorted(passed, key=lambda x: -x['confidence']):
            gs = '→'.join(str(g) for g in p.get('gap_seq', []))
            print(f"  ✅ {p['code']} {p.get('name','')}: "
                  f"收={p['close']} MA5={p['ma5']} MA20={p['ma20']} "
                  f"gap={p['gap']}% [{gs}]")
    
    # 儲存結果
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({
            'date': str(date.today()),
            'total': total,
            'scanned': len(results),
            'passed': passed,
            'near': near
        }, f, ensure_ascii=False, indent=2)
    print(f"\n報告已存: {OUTPUT_FILE}")
    
    fc.logout()


if __name__ == "__main__":
    main()
