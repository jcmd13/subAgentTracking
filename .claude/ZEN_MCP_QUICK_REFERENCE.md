# Zen MCP Quick Reference Card

**TL;DR**: Try Ollama first, validate quality, fallback to Gemini, Claude codes.

---

## The 5-Second Decision

**Is this HIGH-STAKES?** (prod, security) → Skip to Gemini + Claude
**Is this reading/analyzing code?** → Try Ollama (`gpt-oss:120b-cloud`), validate quality
**Quality score ≥ 18/25?** → Use it! Otherwise, refine with Gemini
**Is this writing/editing code?** → Claude Code directly
**Is this using OpenAI models?** → STOP, use Ollama or Gemini instead (both free)

---

## Task → Tool → Model Mapping (Three-Tier Strategy)

```
Understanding codebase     → mcp__zen__analyze + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Finding bugs              → mcp__zen__debug + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Breaking down features    → mcp__zen__planner + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Reviewing code           → mcp__zen__codereview + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Security checks          → mcp__zen__secaudit + gemini-2.5-pro (skip Ollama, high-stakes)
Finding refactor targets → mcp__zen__refactor + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Planning tests           → mcp__zen__testgen + gpt-oss:120b-cloud (validate) → gemini-2.5-pro (fallback)
Discussing approaches    → mcp__zen__chat + gpt-oss:120b-cloud (explore) → gemini-2.5-pro (decide)
Getting current API docs → mcp__zen__apilookup (no model selection needed)
Complex reasoning        → mcp__zen__thinkdeep + deepseek-v3.1:671b-cloud (massive context)
Critical decisions       → mcp__zen__consensus + gpt-oss:120b-cloud, gemini-2.5-pro, deepseek-v3.1:671b-cloud
Quick checks/drafts      → Any tool + mistral:latest or phi3.5:3.8b (local, fast)
```

**Model Selection Priority**:
1. Try `gpt-oss:120b-cloud` (Ollama) → Validate quality
2. If quality < 18/25 → Use `gemini-2.5-pro`
3. Never use paid models unless both fail

---

## The Standard Workflow (Ollama-First)

```
1. Ollama analyzes/plans (via Zen tool with gpt-oss:120b-cloud)
2. Claude validates quality (5-point checklist, score out of 25)
   - If score ≥ 18/25: Use Ollama findings ✅
   - If score < 18/25: Refine with Gemini ⚠️
3. Claude implements code (based on validated findings)
4. Ollama reviews (via codereview tool with gpt-oss:120b-cloud)
   - If score ≥ 18/25: Use review ✅
   - If score < 18/25: Use Gemini instead ⚠️
5. Claude fixes issues
6. Gemini validates (via precommit tool - high-stakes check)
7. Claude commits
```

**Token split** (if Ollama quality is good):
- ~60-70% Ollama (free, validation)
- ~20-30% Gemini (free, refinement/high-stakes)
- ~10% Claude (implementation)

---

## DO ✅

- Try `gpt-oss:120b-cloud` (Ollama) first for non-critical tasks
- Validate ALL Ollama output with 5-point quality checklist
- Use `gemini-2.5-pro` for refinement/fallback or high-stakes
- Use `gemini-2.5-flash` for quick checks
- Use `deepseek-v3.1:671b-cloud` for complex reasoning
- Let Claude Code write all final code
- Pass `continuation_id` to reuse context
- Log quality scores for continuous improvement
- Monitor for accidental paid model usage

## DON'T ❌

- Use Ollama for HIGH-STAKES (production, security) without validation
- Use `gpt-5-pro`, `gpt-5`, `o3-pro` (they cost money!)
- Use OpenRouter models (unless explicitly requested)
- Accept Ollama output with score < 18/25 without refinement
- Let any model write final code (only Claude)
- Skip quality validation of Ollama output
- Use consensus unless decision is critical
- Forget to pass continuation_id in multi-turn workflows
- Let Ollama validation block progress (2 min time limit)

---

## Model Cost Reminder (Three-Tier Strategy)

**TIER 1 - FREE (Try First)**:
- `gpt-oss:120b-cloud` - Ollama cloud model, 120B params, zero cost, VALIDATE QUALITY
- `deepseek-v3.1:671b-cloud` - Ollama cloud model, 671B params, complex reasoning
- `mistral:latest`, `phi3.5:3.8b` - Ollama local models, quick drafts

**TIER 2 - FREE (Refinement/Fallback)**:
- `gemini-2.5-pro` - Best for analysis, proven reliable
- `gemini-2.5-flash` - Best for speed

**TIER 3 - PAID (Avoid)**:
- `gpt-5-pro`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- `o3-pro`, `o3`, `o3-mini`, `o4-mini`
- Anything via OpenRouter
- **Only use if**: Both Ollama AND Gemini fail quality check AND task is critical

---

## Quality Checklist (For Ollama Output)

**Score each criterion 1-5**:
- [ ] **Correctness** (1-5): Is the analysis/solution factually accurate?
- [ ] **Completeness** (1-5): Are all aspects addressed? Any gaps?
- [ ] **Specificity** (1-5): Concrete recommendations vs vague suggestions?
- [ ] **Context Awareness** (1-5): Understands project context and constraints?
- [ ] **Actionability** (1-5): Can Claude implement this directly?

**Scoring**:
- **20-25/25** (4-5 avg): ✅ Excellent, use as-is
- **18-19/25** (3.6-3.8 avg): ✅ Good, use with minor validation
- **15-17/25** (3-3.4 avg): ⚠️ Refine with Gemini
- **< 15/25** (< 3 avg): ❌ Discard, use Gemini or Claude

**For Gemini Output** (proven reliable):
- If any critical issue → Claude refines
- Otherwise trust the output

---

## Token Savings Examples

| Task | Claude Only | With Gemini | Savings |
|------|-------------|-------------|---------|
| Analyze architecture | ~150k tokens | ~8k tokens | 95% |
| Debug complex bug | ~100k tokens | ~10k tokens | 90% |
| Pre-commit review | ~50k tokens | ~5k tokens | 90% |
| Plan feature | ~80k tokens | ~6k tokens | 93% |

**Why it works**: Gemini reads (free), Claude writes (focused)

---

## Common Patterns

### Pattern: Feature Implementation
```
planner(gemini) → chat(gemini) → Claude writes → codereview(gemini) → Claude fixes → precommit(gemini) → Claude commits
```

### Pattern: Bug Fix
```
debug(gemini) → chat(gemini) → Claude fixes → codereview(gemini) → Claude commits
```

### Pattern: Refactoring
```
analyze(gemini) → refactor(gemini) → planner(gemini) → Claude refactors → codereview(gemini) → Claude commits
```

---

## Emergency Fallback

**If Gemini output is poor**:
1. Try increasing `thinking_mode` to "high" or "max"
2. Be more specific in prompt
3. Use multi-pass: Gemini draft → Claude refines
4. **Last resort**: Claude does it directly

**If accidentally used paid model**:
1. Check if output justified the cost
2. Note for future: How to avoid with Gemini
3. Update rules if needed

---

## Integration with Activity Logger

```python
# Log when offloading to Zen
from src.core.activity_logger import log_decision, log_tool_usage

log_decision(
    question="Claude direct or Gemini analysis?",
    options=["Claude direct", "Zen + Gemini"],
    selected="Zen + Gemini",
    rationale="100k+ tokens, Gemini is free"
)

log_tool_usage(
    agent="zen-mcp",
    tool="analyze",
    details={"model": "gemini-2.5-pro", "task": "architecture analysis"}
)
```

---

## One-Line Summary

**Ollama tries (free) → Claude validates (quality gate) → Gemini refines if needed (free) → Claude implements (focused) → Ollama/Gemini reviews (free) → Claude commits (final)**

Cost: ~$0 for analysis (all free models) + Claude's implementation cost = Massive savings + Quality validation
