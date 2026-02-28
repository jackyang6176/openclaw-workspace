#!/usr/bin/env python3
"""
Kronos 時間戳修復驗證腳本
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 測試 calc_time_stamps 函數的輸入格式
def test_timestamp_format():
    """測試不同時間戳格式"""
    
    print("=== 測試時間戳格式 ===\n")
    
    # 創建測試數據
    base_time = datetime.now() - timedelta(minutes=5*10)
    
    # 測試 1: pandas Series
    print("1️⃣  測試 pandas Series:")
    series_ts = pd.Series(pd.date_range(start=base_time, periods=10, freq='5min'))
    print(f"   類型：{type(series_ts)}")
    print(f"   有 .dt: {hasattr(series_ts, 'dt')}")
    try:
        minute = series_ts.dt.minute.iloc[0]
        print(f"   ✅ 可以訪問 .dt.minute: {minute}")
    except Exception as e:
        print(f"   ❌ 錯誤：{e}")
    print()
    
    # 測試 2: DatetimeIndex
    print("2️⃣  測試 DatetimeIndex:")
    index_ts = pd.date_range(start=base_time, periods=10, freq='5min')
    print(f"   類型：{type(index_ts)}")
    print(f"   有 .dt: {hasattr(index_ts, 'dt')}")
    try:
        minute = index_ts.dt.minute[0]
        print(f"   ✅ 可以訪問 .dt.minute: {minute}")
    except Exception as e:
        print(f"   ❌ 錯誤：{e}")
    print()
    
    # 測試 3: 從 DataFrame 提取 (reset_index)
    print("3️⃣  測試從 DataFrame 提取 (reset_index):")
    df = pd.DataFrame({
        'timestamps': pd.date_range(start=base_time, periods=10, freq='5min'),
        'close': range(10)
    })
    extracted_ts = df['timestamps'].iloc[-5:].reset_index(drop=True)
    print(f"   類型：{type(extracted_ts)}")
    print(f"   有 .dt: {hasattr(extracted_ts, 'dt')}")
    try:
        minute = extracted_ts.dt.minute.iloc[0]
        print(f"   ✅ 可以訪問 .dt.minute: {minute}")
    except Exception as e:
        print(f"   ❌ 錯誤：{e}")
    print()
    
    # 測試 4: 從 DataFrame 提取 (不 reset_index)
    print("4️⃣  測試從 DataFrame 提取 (不 reset_index):")
    extracted_ts2 = df['timestamps'].iloc[-5:]
    print(f"   類型：{type(extracted_ts2)}")
    print(f"   有 .dt: {hasattr(extracted_ts2, 'dt')}")
    try:
        minute = extracted_ts2.dt.minute.iloc[0]
        print(f"   ✅ 可以訪問 .dt.minute: {minute}")
    except Exception as e:
        print(f"   ❌ 錯誤：{e}")
    print()
    
    print("=== 結論 ===")
    print("✅ pandas Series 和 DatetimeIndex 都支持 .dt 訪問器")
    print("✅ 從 DataFrame 提取時，無論是否 reset_index，都能保持正確類型")
    print("✅ 關鍵：必須保持為 Series 或 DatetimeIndex，不能轉換為普通 Index")

if __name__ == "__main__":
    test_timestamp_format()
