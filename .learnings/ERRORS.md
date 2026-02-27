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

## [ERR-20260227-004] unreliable_data_sources_removed

**Logged**: 2026-02-27T22:26:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: infra

### Summary
yfinance 和 FinMind 數據源不可靠，已移除並等待 Fubon API

### Error
```
yfinance:
  - HTTP 404: Quote not found for symbol: 00887.TW
  - 實際情況：00887 正常交易中 (收盤價 13.29, 2026-02-26)

FinMind:
  - HTTP 400: Your level is register. Please update your user level.
  - 需要升級贊助會員才能使用
```

### Context
- 驗證時間：2026-02-27 22:14-22:20
- 用戶提供 00887 實際交易截圖證明數據源錯誤
- 投資分析依賴準確數據，錯誤數據可能導致錯誤決策

### Impact
- ❌ yfinance: 00887 數據不可用（但實際仍在交易）
- ❌ FinMind: 權限不足，所有台股數據無法獲取
- ⚠️ 投資報告可能使用中斷或錯誤數據

### Resolution
- **Resolved**: 2026-02-27T22:26:00+08:00
- **Solution**: 
  1. 完全移除 yfinance 和 FinMind 配置
  2. 設置 Fubon API 為主要數據源（待開通）
  3. 等待 Fubon 證券帳號審批（預計 2026-02-28）
- **Notes**: 寧可暫停報告生成，也不使用不可靠數據

### Metadata
- Reproducible: yes
- Related Files: investment/scripts/config.py
- See Also: LRN-20260227-004
- Fubon API: v2.2.8, Python SDK 已安裝

---
