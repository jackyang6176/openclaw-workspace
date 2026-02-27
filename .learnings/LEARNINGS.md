# Learnings Log

Self-improvement learnings for OpenClaw workspace.

Format: [LRN-YYYYMMDD-XXX] category

---

## [LRN-20260227-001] best_practice

**Logged**: 2026-02-27T21:46:00+08:00
**Priority**: high
**Status**: promoted
**Area**: config

### Summary
Cron jobs must explicitly specify model in payload to avoid default model fallback

### Details
When creating cron jobs with `sessionTarget: "isolated"`, the `sessions_spawn.model` parameter may not be correctly passed to subagents. This causes the job to use a default model (qwen3.5-plus) instead of the specified model (kimi-k2.5), leading to content filter errors.

### Suggested Action
Always include explicit model specification in cron job payload:
```json
{
  "payload": {
    "kind": "agentTurn",
    "message": "...",
    "model": "bailian/kimi-k2.5",  // Must specify here
    "timeoutSeconds": 300
  }
}
```

### Metadata
- Source: error
- Related Files: MEMORY.md, SYSTEM_STATUS.md
- Tags: cron, model, subagent
- Promoted To: AGENTS.md

---
