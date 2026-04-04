#!/usr/bin/env python3
"""
全市場策略A掃描器 - 收盤後版本
每天 14:00 執行，掃描全市場 1591 檔
"""
import sys, json, time, os
sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_sdk_complete')
from fubon_complete import FubonComplete

STATE_FILE  = "/tmp/scan_state.json"
OUTPUT_FILE = "/tmp/strategy_a_daily.json"
BATCH       = 5          # 每批幾檔
DELAY       = 5          # 秒（安全延遲）
GAP_LIMIT   = 2.0        # %（MA20-MA5 gap < 2%）
REPORT_AT   = 50        # 每幾檔報告一次

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"all_symbols": None, "done": [], "results": []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False)

def analyze(sym, fc):
    try:
        sma5 = fc.get_sma(sym, 5)
        sma20 = fc.get_sma(sym, 20)
        if not sma5 or not sma20:
            return None
        if len(sma5) < 5 or len(sma20) < 20:
            return None
        m5 = sma5[-1]['sma']
        m20 = sma20[-1]['sma']
        gap = (m20 - m5) / m20 * 100

        gaps = []
        for offset in range(-4, 1):
            idx = len(sma20) + offset
            if 0 <= idx < len(sma5):
                m5d = sma5[idx]['sma']
                m20d = sma20[idx]['sma']
                if m20d > 0:
                    gaps.append((m20d - m5d) / m20d * 100)

        cond1 = m5 < m20
        cond2 = len(gaps) >= 3 and gaps[-1] < gaps[-2] < gaps[-3]
        cond3 = 0 < abs(gap) < GAP_LIMIT
        ok = cond1 and cond2 and cond3
        conf = (int(cond1) + int(cond2) + int(cond3)) / 3 * 100
        return {
            'code': sym, 'ma5': round(m5, 2), 'ma20': round(m20, 2),
            'gap': round(gap, 3), 'gap_seq': [round(g, 2) for g in gaps[-4:]],
            'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
            'confidence': round(conf, 1), 'ok': ok
        }
    except:
        return None

def main():
    from datetime import date
    today = date.today()
    print(f"[{today}] === 全市場策略A掃描啟動 ===")

    fc = FubonComplete()
    fc._load_config()
    fc.login()

    state = load_state()
    done = set(state.get('done', []))
    results = state.get('results', [])
    all_symbols = state.get('all_symbols')

    # 取股票代碼（只取一次）
    if not all_symbols:
        print("抓取股票代碼清單...")
        intraday = fc.sdk.marketdata.rest_client.stock.intraday
        tickers = intraday.tickers(exchange='TWSE', type='EQUITY')
        all_symbols = [t['symbol'] for t in tickers['data']]
        state['all_symbols'] = all_symbols
        state['done'] = []
        state['results'] = []
        save_state(state)
        done = set()
        results = []
        print(f"共 {len(all_symbols)} 檔")

    all_symbols = state['all_symbols']
    remaining = [s for s in all_symbols if s not in done]

    print(f"待處理: {len(remaining)} 檔 ({len(all_symbols)-len(remaining)}/{len(all_symbols)}已完成)")

    batch = remaining[:BATCH]
    new_passed = []
    for sym in batch:
        r = analyze(sym, fc)
        if r:
            results.append(r)
            if r['ok']:
                new_passed.append(r)
        done.add(sym)
        done_count = len(done)
        status = '✅' if r and r['ok'] else '⚠️' if r else '❌'
        print(f"  {status} {sym}: gap={r['gap'] if r else 'N/A'}% ({done_count}/{len(all_symbols)})")
        if done_count % REPORT_AT == 0:
            print(f"  ...已處理 {done_count}/{len(all_symbols)}")
        time.sleep(DELAY)

    state['done'] = list(done)
    state['results'] = results
    save_state(state)

    passed = [x for x in results if x['ok']]
    near = [x for x in results if not x['ok'] and x['confidence'] > 0]

    print(f"\n[{today}] 進度 {len(done)}/{len(all_symbols)} | 符合3/3: {len(passed)}檔")

    if passed:
        for p in passed:
            gs = '->'.join(str(g) for g in p['gap_seq'])
            print(f"  ✅ {p['code']}: MA5={p['ma5']} MA20={p['ma20']} gap={p['gap']}% [{gs}]")
        # 輸出最終報告
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                'date': str(today),
                'total': len(all_symbols),
                'scanned': len(done),
                'passed': passed,
                'near': sorted(near, key=lambda x: -x['confidence'])[:20]
            }, f, ensure_ascii=False, indent=2)
        print(f"報告已存: {OUTPUT_FILE}")
    else:
        print("  今日無符合標的")

    if len(done) >= len(all_symbols):
        print("掃描完成！狀態已重置")
        os.remove(STATE_FILE)

    fc.logout()

if __name__ == "__main__":
    main()
