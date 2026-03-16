#!/usr/bin/env python3
import akshare as ak
import sys
import json
import argparse
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions

def parse_args():
    parser = argparse.ArgumentParser(description='獲取股票數據')
    parser.add_argument('tickers', nargs='+', help='股票代碼列表')
    parser.add_argument('--market', default='cn', choices=['cn', 'hk'], help='市場類型（cn=A股, hk=港股）')
    return parser.parse_args()

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=3, max=15), retry=retry_if_exception_type(requests.exceptions.ConnectionError))
def fetch_data(ticker, market):
    data = {}
    # 獲取即時行情
    if market == 'cn':
        quote = ak.stock_zh_a_spot_em()[ak.stock_zh_a_spot_em()['代碼'] == ticker].iloc[0]
    elif market == 'hk':
        quote = ak.stock_hk_spot_em()[ak.stock_hk_spot_em()['代碼'] == ticker].iloc[0]
    # 獲取技術指標
    kline = ak.stock_zh_a_daily(symbol=ticker, adjust='qfq').tail(60)
    macd = ak.stock_macd(symbol=ticker).tail(30)
    rsi = ak.stock_rsi(symbol=ticker).tail(30)
    atr = ak.stock_atr(symbol=ticker).tail(30)
    # 組裝數據
    data = {
        'quote': quote.to_dict(),
        'kline': kline.to_dict(),
        'macd': macd.to_dict(),
        'rsi': rsi.to_dict(),
        'atr': atr.to_dict()
    }
    return data

def main():
    args = parse_args()
    result = {}
    for ticker in args.tickers:
        try:
            result[ticker] = fetch_data(ticker, args.market)
        except Exception as e:
            result[ticker] = {'error': str(e)}
    with open('analysis_data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': '成功', 'data_path': 'analysis_data.json'}))

if __name__ == '__main__':
    main()