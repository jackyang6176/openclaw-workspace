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
- **Resolved**: 2026-02-27T21:30:00+08:00
- **Solution**: Updated all cron jobs to include explicit model in payload
- **Notes**: The issue was that `sessions_spawn.model` doesn't propagate correctly for isolated sessions. Fix is to specify model in the payload itself.

### Metadata
- Reproducible: no (after fix)
- Related Files: cron configs, SYSTEM_STATUS.md
- See Also: LRN-20260227-001

---
