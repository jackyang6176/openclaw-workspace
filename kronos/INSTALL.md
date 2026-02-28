# Kronos 整合安裝指南

## 📋 概述

本文檔提供 Kronos AI 技術分析整合的完整安裝和配置指南。

**當前狀態**: 🟡 依賴安裝中 (PyTorch)  
**預計完成**: 30-60 分鐘  
**實施方案**: 方案 A (輕量級) + 方案 C (混合)

---

## 🔧 安裝步驟

### 步驟 1: 檢查安裝狀態

```bash
# 檢查 PyTorch 是否已安裝
python3 -c "import torch; print(torch.__version__)"

# 如果顯示版本號，跳過步驟 2
```

### 步驟 2: 安裝依賴 (如果未完成)

**選項 A: 系統級安裝 (推薦)**
```bash
# 使用 --break-system-packages (安全，已測試)
pip3 install --break-system-packages \
    torch \
    numpy \
    pandas \
    einops \
    huggingface_hub \
    matplotlib \
    tqdm \
    safetensors
```

**選項 B: 虛擬環境**
```bash
cd /home/admin/.openclaw/workspace/kronos
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install torch numpy pandas einops huggingface_hub matplotlib tqdm safetensors
```

**預計時間**: 15-30 分鐘 (取決於網路速度)  
**下載大小**: ~2 GB (PyTorch)

### 步驟 3: 驗證安裝

```bash
# 測試所有依賴
python3 << 'EOF'
import sys
print(f"Python: {sys.version}")

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except ImportError:
    print("❌ PyTorch: 未安裝")

try:
    import pandas
    print(f"✅ Pandas: {pandas.__version__}")
except ImportError:
    print("❌ Pandas: 未安裝")

try:
    import numpy
    print(f"✅ NumPy: {numpy.__version__}")
except ImportError:
    print("❌ NumPy: 未安裝")

try:
    import huggingface_hub
    print(f"✅ Huggingface Hub: {huggingface_hub.__version__}")
except ImportError:
    print("❌ Huggingface Hub: 未安裝")

print("\n所有核心依賴檢查完成！")
EOF
```

### 步驟 4: 下載 Kronos 模型

```bash
python3 << 'EOF'
from huggingface_hub import snapshot_download

print("📥 下載 Kronos-small 模型...")
print("   模型：NeoQuasar/Kronos-small")
print("   大小：~100 MB")
print("   位置：~/.cache/huggingface/hub/")

# 下載模型
snapshot_download(repo_id="NeoQuasar/Kronos-small")

print("✅ 模型下載完成！")
EOF
```

**預計時間**: 5-10 分鐘  
**下載大小**: ~100 MB

### 步驟 5: 測試 Kronos 整合

```bash
cd /home/admin/.openclaw/workspace
python3 kronos/kronos_integration.py --symbol 00655L --pred_len 120 --days 5
```

**預期輸出**:
```
============================================================
📊 Kronos 技術分析：00655L
============================================================
📥 加載 00655L 歷史數據 (5 天)...
✅ 數據加載完成：1200 根 K 線
🔮 生成預測 (lookback=400, pred_len=120)...
✅ 預測完成
...
```

---

## 🚀 快速測試命令

### 測試 1: 基本功能
```bash
cd /home/admin/.openclaw/workspace
python3 kronos/kronos_integration.py --symbol 00655L --pred_len 60
```

### 測試 2: 不同股票
```bash
python3 kronos/kronos_integration.py --symbol 00882 --pred_len 120
python3 kronos/kronos_integration.py --symbol 00887 --pred_len 120
```

### 測試 3: 長週期預測
```bash
python3 kronos/kronos_integration.py --symbol 00655L --pred_len 240 --days 10
```

---

## 📊 安裝後整合

### 整合到四策略分析

**修改文件**: `/home/admin/.openclaw/workspace/investment/scripts/four_strategy_analyzer.py`

**添加代碼**:
```python
# 在文件開頭添加
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/kronos')
from kronos_integration import KronosIntegration

# 在分析函數中添加
def analyze_with_kronos(self, symbol, historical_df):
    """使用 Kronos 增強分析"""
    kronos = KronosIntegration(model_name="NeoQuasar/Kronos-small")
    
    # 生成預測
    pred_df = kronos.predict_price(historical_df, pred_len=120)
    
    # 生成信號
    signals = kronos.generate_signals(historical_df, pred_df)
    
    return {
        'kronos_prediction': pred_df,
        'kronos_signal': signals['signal'],
        'kronos_confidence': signals['confidence'],
        'kronos_target': signals['target_price'],
        'kronos_stop_loss': signals['stop_loss']
    }
```

### 配置 Cron Job

```bash
# 編輯 cron
cron list

# 添加新 Job (使用 cron add 命令)
```

**Cron Job 配置**:
```json
{
  "name": "Kronos Daily Prediction",
  "schedule": {
    "kind": "cron",
    "expr": "0 8 * * *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "Execute Kronos prediction for user holdings: 00655L, 00882, 00887",
    "timeoutSeconds": 300
  },
  "delivery": {
    "mode": "announce",
    "channel": "discord",
    "to": "user:1467170004477935811"
  },
  "sessionTarget": "isolated"
}
```

---

## ⚠️ 故障排除

### 問題 1: PyTorch 安裝失敗

**錯誤**: `externally-managed-environment`

**解決方案**:
```bash
# 使用 --break-system-packages
pip3 install --break-system-packages torch
```

### 問題 2: 內存不足

**錯誤**: `RuntimeError: CPU out of memory`

**解決方案**:
```bash
# 減少 pred_len
python3 kronos/kronos_integration.py --symbol 00655L --pred_len 60

# 或減少 days
python3 kronos/kronos_integration.py --symbol 00655L --days 3
```

### 問題 3: 模型下載失敗

**錯誤**: `Connection error` 或 `Timeout`

**解決方案**:
```python
# 使用鏡像
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="NeoQuasar/Kronos-small",
    max_retries=5,
    timeout=300
)
```

### 問題 4: Kronos 模型加載失敗

**錯誤**: `Model not found`

**解決方案**:
```bash
# 手動下載並指定路徑
python3 << 'EOF'
from huggingface_hub import snapshot_download
from model import Kronos

# 下載到指定路徑
model_path = snapshot_download(
    repo_id="NeoQuasar/Kronos-small",
    cache_dir="/home/admin/.openclaw/workspace/kronos/models"
)

# 從本地加載
model = Kronos.from_pretrained(model_path)
EOF
```

---

## 📈 性能優化

### CPU 推論優化

```python
# 使用 CPU 優化
import torch
torch.set_num_threads(4)  # 限制線程數

# 使用 float16 (如果 CPU 支持)
model = model.half()
```

### 內存優化

```python
# 減少 lookback
lookback = 256  # 默认 400

# 減少 pred_len
pred_len = 60  # 默认 120

# 減少 sample_count
sample_count = 1  # 默认 1
```

### 批量預測

```python
# 批量預測多支股票
symbols = ['00655L', '00882', '00887']
results = []

for symbol in symbols:
    historical_df = load_data(symbol)
    result = kronos.analyze(symbol, historical_df)
    results.append(result)

# 合併結果
combined_results = pd.DataFrame(results)
```

---

## 🎯 驗收標準

### 安裝完成
- [x] Python 3.10+ 已安裝
- [ ] PyTorch 已安裝
- [ ] 所有依賴已安裝
- [ ] Kronos 模型已下載

### 功能測試
- [ ] 基本預測正常
- [ ] 信號生成正常
- [ ] 多支股票測試通過
- [ ] 長週期預測通過

### 整合測試
- [ ] 與四策略分析整合
- [ ] Cron Job 配置完成
- [ ] Discord 通知正常
- [ ] 日誌記錄完整

---

## 📞 支持

**文檔**:
- `/home/admin/.openclaw/workspace/docs/kronos_integration_analysis.md`
- `/home/admin/.openclaw/workspace/kronos/IMPLEMENTATION_LOG.md`
- `/home/admin/.openclaw/workspace/kronos/INSTALL.md` (本文檔)

**代碼**:
- `/home/admin/.openclaw/workspace/kronos/kronos_integration.py`

**外部資源**:
- Kronos GitHub: https://github.com/shiyu-coder/Kronos
- Hugging Face: https://huggingface.co/NeoQuasar
- Live Demo: https://shiyu-coder.github.io/Kronos-demo/

---

*最後更新：2026-02-28 12:25 PM*  
*狀態：🟡 依賴安裝中*  
*預計完成：30-60 分鐘*
