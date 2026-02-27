# Errors Log

Error tracking for OpenClaw workspace.

Format: [ERR-YYYYMMDD-XXX] skill_or_command_name

---

## [ERR-20260227-001] sessions_spawn_model_fallback

**Logged**: 2026-02-27T21:46:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
Subagent spawned via cron job used wrong model despite explicit model specification

### Error
```
api: openai-completions
provider: bailian
model: qwen3.5-plus  // Expected: kimi-k2.5
stopReason: error
timestamp: 1772189274498
errorMessage: <400> InternalError.Algo.DataInspectionFailed: Output data may contain inappropriate content.
```

### Context
- Command: `sessions_spawn` with `model: "bailian/kimi-k2.5"`
- Cron job: "doer-test" (International News Report testing)
- Environment: OpenClaw v2026.2.26, Discord channel

### Resolution
- **Resolved**: 2026-02-27T21:56:00+08:00
- **Solution**: Updated all cron jobs to include explicit model in payload
- **Notes**: The issue was that `sessions_spawn.model` doesn't propagate correctly for isolated sessions. Fix is to specify model in the payload itself.

### Metadata
- Reproducible: no (after fix)
- Related Files: cron configs, SYSTEM_STATUS.md
- See Also: LRN-20260227-001

---

## [ERR-20260227-002] yfinance_data_unavailable

**Logged**: 2026-02-27T22:15:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
yfinance 無法獲取 00887.TW (永豐中國科技 50 大) 數據

### Error
```
HTTP Error 404: Quote not found for symbol: 00887.TW
$00887.TW: possibly delisted; no price data found
```

### Context
- 測試時間：2026-02-27 22:14
- 其他 ETF 數據正常：0050.TW, 00655L.TW, 00882.TW
- 00887.TWO 有數據但名稱不符 (SINOPAC SECS INV TR CO LTD SINO)

### Suggested Fix
1. 確認 00887 正確代碼
2. 從 yfinance 可用列表中移除 00887.TW
3. 使用 FinMind 作為主要台灣股市數據源

### Resolution
- **Resolved**: 2026-02-27T22:15:00+08:00
- **Solution**: 更新 config.py，將 00887.TW 標記為 unavailable_symbols
- **Notes**: FinMind 作為主要數據源，yfinance 作為備用

### Metadata
- Reproducible: yes
- Related Files: investment/scripts/config.py
- See Also: LRN-20260227-003

---
