# Zen MCP Decision Tree

Visual guide for deciding when and how to use Zen MCP tools.

---

## Primary Decision Tree (Ollama-First Strategy)

```
                            NEW TASK ARRIVES
                                   |
                                   |
                    ┌──────────────┴──────────────┐
                    |                             |
             Is it CODE WRITING?           Is it ANALYSIS/REVIEW?
                    |                             |
                    |                             |
                   YES                           YES
                    |                             |
                    v                             v
            ┌───────────────┐           ┌──────────────────┐
            │ CLAUDE CODE   │           │  Is it HIGH-     │
            │  writes code  │           │  STAKES?         │
            │   directly    │           │ (prod/security)  │
            └───────────────┘           └────────┬─────────┘
                                                 |
                                 ┌───────────────┴───────────────┐
                                 |                               |
                                YES                             NO
                                 |                               |
                                 v                               v
                        ┌─────────────────┐           ┌──────────────────┐
                        │  Skip Ollama    │           │  Try OLLAMA      │
                        │  → Gemini       │           │  gpt-oss:120b-   │
                        │  + Claude       │           │  cloud first     │
                        └─────────────────┘           └────────┬─────────┘
                                                               |
                                                               v
                                                      ┌─────────────────┐
                                                      │  Claude         │
                                                      │  validates      │
                                                      │  quality (score)│
                                                      └────────┬────────┘
                                                               |
                                                 ┌─────────────┼─────────────┐
                                                 |             |             |
                                                 v             v             v
                                            Score 20-25   Score 15-19   Score < 15
                                            (4-5 avg)     (3-4 avg)     (< 3 avg)
                                                 |             |             |
                                                 v             v             v
                                            ✅ Use it    Refine with    Use Gemini
                                            as-is        Gemini         or Claude
                                                 |             |             |
                                                 └─────────────┼─────────────┘
                                                               |
                                                               v
                                                      ┌─────────────────┐
                                                      │  Claude         │
                                                      │  implements     │
                                                      └─────────────────┘
```

---

## Task Type Decision Tree

```
                              TASK TYPE?
                                  |
         ┌────────────────────────┼────────────────────────┐
         |                        |                        |
         v                        v                        v
    UNDERSTAND              DEBUG/TRACE              PLAN/DESIGN
         |                        |                        |
         v                        v                        v
  mcp__zen__analyze      mcp__zen__debug          mcp__zen__planner
  + gemini-2.5-pro      + gemini-2.5-pro         + gemini-2.5-pro
         |                        |                        |
         └────────────────────────┼────────────────────────┘
                                  |
                                  v
                          Claude implements
                                  |
                                  v
                    ┌─────────────┴─────────────┐
                    |                           |
                    v                           v
            Need review?                   Ready to commit?
                    |                           |
                    v                           v
          mcp__zen__codereview          mcp__zen__precommit
          + gemini-2.5-pro             + gemini-2.5-pro
                    |                           |
                    v                           v
            Claude fixes issues          Claude commits
```

---

## Model Selection Decision Tree (Three-Tier Strategy)

```
                        WHICH MODEL TO USE?
                                |
                                |
                    ┌───────────┴───────────┐
                    |                       |
              Analysis/Review          Implementation
                    |                       |
                    v                       v
            ┌───────────────┐       ┌──────────────┐
            │ Is HIGH-      │       │ CLAUDE CODE  │
            │ STAKES?       │       │    always    │
            └───┬───────────┘       └──────────────┘
                |
        ┌───────┴────────┐
        |                |
       YES              NO
        |                |
        v                v
  Skip to TIER 2    Try TIER 1 (Ollama)
  (Gemini)                |
        |                 v
        |         ┌───────────────┐
        |         │ Complex task? │
        |         │ (massive      │
        |         │  context?)    │
        |         └───┬───────────┘
        |             |
        |     ┌───────┴────────┐
        |     |                |
        |    YES              NO
        |     |                |
        |     v                v
        | deepseek-v3.1:   gpt-oss:120b-
        | 671b-cloud       cloud
        |     |                |
        |     └────────┬───────┘
        |              |
        |              v
        |      ┌───────────────┐
        |      │ Validate      │
        |      │ quality       │
        |      │ (score /25)   │
        |      └───┬───────────┘
        |          |
        |  ┌───────┴────────┐
        |  |                |
        | Score ≥ 18    Score < 18
        |  |                |
        |  v                v
        | Use it      TIER 2 (Gemini)
        |  |                |
        └──┴────────┬───────┘
                    |
                    v
           ┌────────────────┐
           │ Is it quick?   │
           └───┬────────────┘
               |
       ┌───────┴────────┐
       |                |
      YES              NO
       |                |
       v                v
 gemini-2.5-flash  gemini-2.5-pro
       |                |
       └────────┬───────┘
                |
                v
        ┌───────────────┐
        │  NEVER use    │
        │  TIER 3       │
        │  (paid models)│
        └───────────────┘
             UNLESS
                |
                v
   ┌─────────────────────────┐
   │ User explicitly         │
   │ requests it OR          │
   │ Both Ollama AND Gemini  │
   │ failed quality check    │
   └─────────────────────────┘
```

---

## Quality Check Decision Tree (Ollama + Gemini)

```
                    MODEL OUTPUT RECEIVED
                            |
                            v
                ┌───────────────────────┐
                │ Which model was used? │
                └───────┬───────────────┘
                        |
          ┌─────────────┴─────────────┐
          |                           |
          v                           v
      OLLAMA                       GEMINI
  (needs validation)            (proven reliable)
          |                           |
          v                           v
  ┌──────────────────┐       ┌────────────────┐
  │ Claude scores    │       │ Claude reviews │
  │ quality (1-5     │       │ for critical   │
  │ per criterion)   │       │ issues only    │
  └────────┬─────────┘       └────────┬───────┘
           |                          |
           v                          v
    ┌──────────────┐           Any critical
    │ Total score? │           issues?
    └────┬─────────┘                  |
         |                    ┌───────┴────────┐
  ┌──────┼──────┐             |                |
  |      |      |            YES              NO
  v      v      v             |                |
20-25  15-19  < 15            v                v
  |      |      |      Claude refines    ✅ Use output
  v      v      v             |
✅Use  Refine  Discard         └────────┬───────┘
      with                             |
     Gemini                            v
        |      │              Claude implements
        |      └──────────┐
        |                 |
        v                 v
   ✅ Use refined    Use Gemini/
      output        Claude instead
```

---

## Workflow Pattern Decision Tree

```
                          COMPLEXITY LEVEL?
                                |
          ┌─────────────────────┼─────────────────────┐
          |                     |                     |
          v                     v                     v
       SIMPLE                MEDIUM               COMPLEX
     (1-2 steps)           (3-5 steps)          (6+ steps)
          |                     |                     |
          v                     v                     v
    ┌──────────┐         ┌──────────────┐      ┌──────────────┐
    │ Direct   │         │ Two-Pass     │      │ Multi-Pass   │
    │ Pattern  │         │ Pattern      │      │ Pattern      │
    └────┬─────┘         └──────┬───────┘      └──────┬───────┘
         |                      |                      |
         v                      v                      v
    Claude only          1. Gemini analyzes     1. Gemini plans
                        2. Claude implements    2. Gemini reviews plan
                                |               3. Claude implements
                                v               4. Gemini reviews code
                        mcp__zen__codereview    5. Claude fixes
                                |               6. Gemini pre-commit
                                v               7. Claude commits
                        Claude fixes/commits
```

---

## Cost Optimization Decision Tree (Three-Tier)

```
                      BEFORE MAKING TOOL CALL
                                |
                                v
                    ┌───────────────────────┐
                    │ What model am I       │
                    │ about to use?         │
                    └───────┬───────────────┘
                            |
              ┌─────────────┼─────────────┐
              |             |             |
              v             v             v
         Ollama       Gemini model    OpenAI model
      (gpt-oss-*,    (gemini-*)      (gpt-*, o3-*, o4-*)
      deepseek-*,
      local models)
              |             |             |
              v             v             v
      ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐
      │ ✅ PROCEED   │ │ ✅ PROCEED   │ │ ⚠️  STOP & CHECK   │
      │ (TIER 1)     │ │ (TIER 2)     │ │   (TIER 3)         │
      │ + VALIDATE   │ │ (Proven)     │ └────────┬───────────┘
      └──────────────┘ └──────────────┘          |
                                         |
                            ┌────────────┴────────────┐
                            |                         |
                            v                         v
                    User explicitly             Doing it anyway?
                    requested it?                     |
                            |                         v
                            |                ┌────────────────┐
                            v                │ Can Gemini do  │
                       ┌────────┐            │ this instead?  │
                       │ ✅ OK  │            └────┬───────────┘
                       └────────┘                 |
                                        ┌─────────┴─────────┐
                                        |                   |
                                       YES                 NO
                                        |                   |
                                        v                   v
                                ┌──────────────┐    ┌──────────────┐
                                │ ❌ USE GEMINI│    │ Document why │
                                │    INSTEAD   │    │ paid model   │
                                └──────────────┘    │ was necessary│
                                                    └──────────────┘
```

---

## Integration Decision Tree

```
              SHOULD I LOG THIS TO ACTIVITY LOGGER?
                            |
              ┌─────────────┴─────────────┐
              |                           |
              v                           v
      Using Zen tool?              Cost > $0.01?
              |                           |
             YES                         YES
              |                           |
              └─────────┬─────────────────┘
                        |
                        v
                ┌───────────────┐
                │ ✅ LOG IT     │
                └───────┬───────┘
                        |
                        v
            log_tool_usage(
                agent="zen-mcp",
                tool="analyze",
                details={
                    "model": "gemini-2.5-pro",
                    "tokens_estimated": "150k",
                    "cost": "$0.00"
                }
            )
```

---

## Emergency Fallback Tree (Three-Tier)

```
                    SOMETHING WENT WRONG
                            |
              ┌─────────────┴─────────────┐
              |                           |
              v                           v
      Ollama quality poor          Tool call failed
      (score < 15/25)                     |
              |                           |
              v                           |
    Try TIER 2 (Gemini)                   |
              |                           |
              v                           |
      ┌──────────────────┐                |
      │ Gemini output OK?│                |
      └────┬─────────────┘                |
           |                              |
    ┌──────┴──────┐                       |
    |             |                       |
   YES           NO                       |
    |             |                       |
    v             v                       |
✅ Use      All tiers                     |
 Gemini     failed                        |
            |                             |
            └─────────────┬───────────────┘
                          |
                          v
                  ┌───────────────┐
                  │ FALLBACK:     │
                  │ Claude Code   │
                  │ handles       │
                  │ directly      │
                  └───────┬───────┘
                          |
                          v
                  ┌───────────────┐
                  │ Document what │
                  │ went wrong &  │
                  │ log quality   │
                  │ scores        │
                  └───────────────┘
```

---

## Summary Flow (Ollama-First Strategy)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Task → High-stakes? → YES → Gemini + Claude                        │
│              ↓                                                       │
│             NO                                                       │
│              ↓                                                       │
│         Try Ollama (gpt-oss:120b-cloud)                              │
│              ↓                                                       │
│         Claude validates quality (score /25)                         │
│              ↓                                                       │
│    ┌─────────┼─────────┐                                            │
│   ≥18      15-17      <15                                           │
│    ↓         ↓         ↓                                            │
│  Use it   Gemini    Gemini/Claude                                   │
│              ↓                                                       │
│         Claude implements                                            │
│              ↓                                                       │
│         Ollama/Gemini review (quality gate)                          │
│              ↓                                                       │
│         Claude fixes                                                 │
│              ↓                                                       │
│         Gemini pre-commit (high-stakes check)                        │
│              ↓                                                       │
│         Claude commits                                               │
│                                                                      │
│  Cost: ~60-70% Ollama + ~20-30% Gemini + ~10% Claude (all free!)    │
│  Quality: Validated at each step, multi-model checking              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Quick Checks

### ✅ BEST: Ollama-First Pattern
```
User wants to understand auth flow (50k tokens to read)
  ↓
mcp__zen__analyze + gpt-oss:120b-cloud (Ollama, free)
  ↓
Claude validates quality (score: 21/25 ✅)
  ↓
Claude explains to user using Ollama findings (1k tokens)

Total: 1k Claude tokens + quality validation data!
```

### ✅ Good: Ollama-Refine Pattern
```
User wants to understand auth flow (50k tokens to read)
  ↓
mcp__zen__analyze + gpt-oss:120b-cloud (Ollama, free)
  ↓
Claude validates quality (score: 16/25 ⚠️ - needs refinement)
  ↓
mcp__zen__analyze + gemini-2.5-pro (refine findings)
  ↓
Claude explains using refined findings (2k tokens)

Total: 2k Claude tokens + multi-model validation!
```

### ✅ Good: High-Stakes Pattern (Skip Ollama)
```
User wants security audit before production deploy
  ↓
Skip Ollama (high-stakes)
  ↓
mcp__zen__secaudit + gemini-2.5-pro (proven reliable)
  ↓
Claude reviews findings (2k tokens)
  ↓
Claude implements fixes

Total: Implementation tokens only, proven quality
```

### ❌ Bad: Skipping Free Tiers
```
User wants to understand auth flow (50k tokens to read)
  ↓
mcp__zen__analyze + gpt-5-pro (PAID!)
  ↓
Wasted money when Ollama + Gemini are both free!
```

### ❌ Bad: No Quality Validation
```
User wants new feature analysis
  ↓
mcp__zen__analyze + gpt-oss:120b-cloud (Ollama)
  ↓
Claude uses output directly (NO VALIDATION!)
  ↓
Potential quality issues missed

Missing: Quality scoring step!
```

---

## Remember

**The Golden Rule (Three-Tier Edition)**:

1. **Try Ollama first** (`gpt-oss:120b-cloud`) unless high-stakes
2. **Validate rigorously** - Score quality out of 25
3. **Fallback smartly** - Gemini if < 18/25
4. **Never use paid** - Only if both Ollama AND Gemini fail

**Ollama-First Mantra**: "Try free validation, fall back to free refinement, avoid paid entirely."
