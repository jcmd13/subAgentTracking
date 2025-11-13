# Ollama Integration Rules

**Purpose**: Use Ollama models (especially `gpt-oss:120b-cloud`) frequently for validation and quality testing while ensuring they don't hinder progress.

**Status**: Active (v1.0)
**Last Updated**: 2025-11-04

---

## Available Ollama Models

### Cloud Models (Remote, Zero Local Resources)
- **`gpt-oss:120b-cloud`** ⭐ PRIMARY - 120B parameters, cloud-hosted
- **`deepseek-v3.1:671b-cloud`** - 671B parameters, massive context/reasoning
- **`minimax-m2:cloud`** - Cloud model, experimental

### Local Models (On-Device, Fast)
- **`mistral:latest`** (4.4 GB) - General purpose, good balance
- **`phi3.5:3.8b`** (2.2 GB) - Microsoft, good reasoning
- **`gemma3:4b`** (3.3 GB) - Google, code-focused
- **`llama3.2:latest`** (2.0 GB) - Meta, general purpose
- **`gemma2:2b`** (1.6 GB) - Lightweight, fast
- **`llama3.2:1b`** (1.3 GB) - Ultra-light
- **`qwen2.5:1.5b`** (986 MB) - Ultra-light, Alibaba

---

## Core Strategy: Progressive Quality Validation

### The Ollama-First Approach

**Goal**: Use Ollama models frequently to validate their quality without blocking progress.

**Workflow**:
```
1. Try Ollama model (gpt-oss:120b-cloud preferred)
2. Validate output quality (5-point checklist)
3. If quality >= 4/5 → Use output
4. If quality 2-3/5 → Refine with Gemini
5. If quality < 2/5 → Fallback to Gemini/Claude
6. Log quality score for model improvement
```

---

## Model Selection Decision Tree

```
                    TASK ARRIVES
                         |
                         |
         ┌───────────────┴───────────────┐
         |                               |
         v                               v
    HIGH-STAKES?                    EXPERIMENTAL?
    (prod code,                     (exploration,
     final impl)                     drafts, ideas)
         |                               |
         v                               v
    Skip Ollama                    Try Ollama First!
    → Gemini/Claude                      |
                                         v
                              ┌──────────┴──────────┐
                              |                     |
                              v                     v
                        Need MASSIVE            Normal task
                        context/reasoning?       (most cases)
                              |                     |
                              v                     v
                    deepseek-v3.1:671b-cloud  gpt-oss:120b-cloud
                              |                     |
                              └──────────┬──────────┘
                                         |
                                         v
                                  Validate Quality
                                         |
                          ┌──────────────┼──────────────┐
                          |              |              |
                          v              v              v
                      Score 4-5      Score 2-3      Score 0-1
                          |              |              |
                          v              v              v
                      ✅ Use it    Refine w/Gemini  Fallback
                                                    Gemini/Claude
```

---

## Quality Validation Checklist

**Before accepting Ollama output, score each criterion (1 = poor, 5 = excellent)**:

1. **Correctness** (1-5): Is the analysis/solution factually accurate?
2. **Completeness** (1-5): Are all aspects addressed? Any gaps?
3. **Specificity** (1-5): Concrete recommendations vs vague suggestions?
4. **Context Awareness** (1-5): Understands project context and constraints?
5. **Actionability** (1-5): Can Claude implement this directly?

**Scoring**:
- **20-25 points (4-5 avg)**: ✅ Excellent, use as-is
- **15-19 points (3-4 avg)**: ⚠️ Good but refine with Gemini
- **10-14 points (2-3 avg)**: ⚠️ Needs significant refinement
- **< 10 points (< 2 avg)**: ❌ Discard, use Gemini/Claude

**Quality Tracking**:
```python
from src.core.activity_logger import log_tool_usage

log_tool_usage(
    agent="ollama",
    tool="gpt-oss:120b-cloud",
    details={
        "task": "Code review of auth module",
        "quality_score": "21/25",
        "breakdown": {
            "correctness": 5,
            "completeness": 4,
            "specificity": 4,
            "context_awareness": 4,
            "actionability": 4
        },
        "outcome": "Used as-is",
        "fallback_needed": False
    }
)
```

---

## When to Use Each Ollama Model

### PRIMARY: `gpt-oss:120b-cloud` (Default Choice)

**Use For**:
- Code analysis and architecture understanding
- Bug investigation and debugging
- Code reviews (quality, patterns, smells)
- Planning and task decomposition
- Refactoring analysis
- Test planning
- Documentation generation
- General brainstorming

**Strengths**:
- 120B parameters = strong reasoning
- Cloud-hosted = no local resource usage
- Fast enough for most tasks
- Good balance of quality and speed

**Validation Priority**: ⭐ HIGH - Want to use this often

**Quality Target**: 18+/25 (3.6+ average) to validate as production-ready

### ADVANCED: `deepseek-v3.1:671b-cloud` (Complex Tasks)

**Use For**:
- Extremely complex architectural decisions
- Large codebase analysis (100k+ LOC)
- Deep reasoning about system design
- Security audits requiring thorough analysis
- Performance optimization requiring deep understanding
- Multi-step reasoning across many files

**Strengths**:
- 671B parameters = exceptional reasoning
- Massive context window
- Cloud-hosted = no local resources

**When NOT to Use**:
- Simple tasks (overkill, slower)
- Quick checks (use gpt-oss:120b-cloud)
- Time-sensitive tasks (can be slower)

**Validation Priority**: MEDIUM - Use for specific complex cases

**Quality Target**: 20+/25 (4+ average) expected for complex tasks

### EXPERIMENTAL: `minimax-m2:cloud`

**Use For**:
- Testing alternative approaches
- Experimental analysis
- Backup when other cloud models are slow

**Validation Priority**: LOW - Experimental only

**Quality Target**: 15+/25 (3+ average) to consider usable

### LOCAL MODELS (Quick Drafts & Experiments)

**Use For**:
- Quick sanity checks
- Generating initial drafts (to be refined)
- Rapid prototyping ideas
- Learning/experimenting with prompts
- Offline work

**Recommended Local Model Tier List**:
1. **`mistral:latest`** (4.4 GB) - Best all-around local model
2. **`phi3.5:3.8b`** (2.2 GB) - Good reasoning, Microsoft quality
3. **`gemma3:4b`** (3.3 GB) - Code-focused tasks
4. **`llama3.2:latest`** (2.0 GB) - General purpose
5. **`gemma2:2b`** (1.6 GB) - Quick checks only
6. **`llama3.2:1b`** (1.3 GB) - Ultra-quick, limited capability
7. **`qwen2.5:1.5b`** (986 MB) - Lightweight experiments

**Validation Priority**: LOW - Drafts only, always refine

**Quality Target**: 12+/25 (2.4+ average) for drafts

---

## Integration with Zen MCP Tools

### Using Ollama with Zen Tools

**Syntax**:
```python
# For gpt-oss:120b-cloud (via Ollama)
mcp__zen__analyze(
    model="gpt-oss:120b-cloud",
    analysis_type="architecture",
    ...
)

# For deepseek (via Ollama)
mcp__zen__debug(
    model="deepseek-v3.1:671b-cloud",
    ...
)

# For local models (via Ollama)
mcp__zen__chat(
    model="mistral:latest",
    ...
)
```

**Note**: When CUSTOM_API_URL is set, Zen MCP will route these to Ollama instead of cloud APIs.

---

## Workflow Patterns

### Pattern 1: Ollama-First Analysis (Recommended)

```
User: "Analyze the authentication system"

1. mcp__zen__analyze with gpt-oss:120b-cloud
   → Get analysis from Ollama

2. Claude validates quality (score 1-5 each criterion)
   → Score: 22/25 (4.4 avg) ✅

3. Quality passes → Claude uses findings to explain to user

Token Cost: $0 (Ollama free) + minimal Claude for validation
Quality: Validated before use
```

### Pattern 2: Ollama Draft + Gemini Refine (Mid-Quality)

```
User: "Find refactoring opportunities in legacy code"

1. mcp__zen__refactor with gpt-oss:120b-cloud
   → Get initial analysis from Ollama

2. Claude validates quality
   → Score: 17/25 (3.4 avg) ⚠️ Needs refinement

3. mcp__zen__refactor with gemini-2.5-pro
   → Refine with Gemini, pass Ollama findings as context

4. Claude uses refined findings

Token Cost: $0 (both free) + minimal Claude
Quality: Double-validated
```

### Pattern 3: Complex Task with DeepSeek

```
User: "Design distributed caching strategy for microservices"

1. mcp__zen__thinkdeep with deepseek-v3.1:671b-cloud
   → Deep reasoning on complex architectural decision

2. Claude validates quality
   → Score: 23/25 (4.6 avg) ✅

3. mcp__zen__consensus with multiple perspectives:
   - deepseek-v3.1:671b-cloud (stance: "for")
   - gemini-2.5-pro (stance: "against")
   - gpt-oss:120b-cloud (stance: "neutral")

4. Claude synthesizes and implements

Token Cost: Minimal (all free models)
Quality: Multi-model validation
```

### Pattern 4: High-Stakes Fallback (Production Code)

```
User: "Review this critical payment processing code"

1. Skip Ollama for high-stakes
   → Go directly to gemini-2.5-pro

2. mcp__zen__codereview with gemini-2.5-pro
   → Comprehensive review

3. mcp__zen__secaudit with gemini-2.5-pro
   → Security-specific review

4. Claude implements fixes

5. Final validation:
   - Optional: mcp__zen__precommit with gpt-oss:120b-cloud
   - Score quality, fallback to Gemini if score < 4/5

Token Cost: Mostly free (Gemini)
Quality: High-stakes = validated models only
```

---

## Use Case Definitions for `gpt-oss:120b-cloud`

### HIGH-FREQUENCY Use Cases (Use Often)

**1. Code Analysis & Understanding**
- Analyzing module architecture
- Understanding code flow
- Identifying dependencies
- Mapping data structures

**Quality Target**: 18+/25
**Fallback**: Gemini if < 18/25

**2. Bug Investigation (Non-Critical)**
- Investigating non-production bugs
- Understanding error patterns
- Tracing execution paths
- Identifying potential causes

**Quality Target**: 17+/25
**Fallback**: Gemini if critical or < 17/25

**3. Code Review (Initial Pass)**
- First-pass code review
- Pattern identification
- Code smell detection
- Style consistency checks

**Quality Target**: 18+/25
**Fallback**: Gemini for final review

**4. Planning & Decomposition**
- Breaking down features
- Creating task lists
- Estimating complexity
- Identifying dependencies

**Quality Target**: 17+/25
**Fallback**: Gemini if complex or < 17/25

**5. Refactoring Analysis**
- Identifying refactoring opportunities
- Suggesting improvements
- Analyzing technical debt
- Proposing modernization

**Quality Target**: 17+/25
**Fallback**: Gemini for implementation plan

**6. Test Planning**
- Identifying test cases
- Edge case discovery
- Coverage analysis
- Test strategy

**Quality Target**: 18+/25
**Fallback**: Gemini if complex domain

**7. Documentation Review**
- Reviewing existing docs
- Identifying gaps
- Suggesting improvements
- Checking accuracy

**Quality Target**: 16+/25
**Fallback**: Gemini for final docs

**8. Brainstorming & Exploration**
- Exploring approaches
- Discussing tradeoffs
- Generating ideas
- Validating assumptions

**Quality Target**: 15+/25 (exploratory)
**Fallback**: Gemini for final decisions

### MEDIUM-FREQUENCY Use Cases (Selective)

**9. Security Review (Initial)**
- First-pass security analysis
- Common vulnerability checks
- Authentication/authorization review
- Input validation review

**Quality Target**: 19+/25
**Fallback**: Gemini for production security

**10. Performance Analysis**
- Identifying bottlenecks
- Suggesting optimizations
- Analyzing complexity
- Resource usage patterns

**Quality Target**: 18+/25
**Fallback**: Gemini for production perf

### LOW-FREQUENCY Use Cases (Experimental)

**11. Complex Reasoning**
- Multi-step architectural decisions
- System design from scratch
- Migration strategies

**Quality Target**: 20+/25
**Fallback**: Use deepseek-v3.1:671b-cloud or Gemini

### NEVER Use Cases (Always Fallback)

**❌ Don't Use gpt-oss:120b-cloud For**:
- Production code generation (Claude does this)
- Critical security audits (Gemini)
- Final pre-commit validation (Gemini)
- Customer-facing documentation (Gemini or Claude)
- High-stakes decisions without validation (Gemini)

---

## Progressive Rollout Plan

### Phase 1: Validation (Current Phase)

**Goal**: Establish quality baselines

**Tasks**:
- Use gpt-oss:120b-cloud for 10+ analysis tasks
- Score quality for each task (1-5 per criterion)
- Track scores in activity logger
- Calculate average quality score
- Identify strengths and weaknesses

**Success Criteria**:
- Average score ≥ 18/25 (3.6+ avg) across 10+ tasks
- No critical failures (score < 10/25)
- Faster than Gemini for most tasks

### Phase 2: Selective Adoption (Next Phase)

**Goal**: Use for validated use cases

**Tasks**:
- Use gpt-oss:120b-cloud as default for high-scoring use cases
- Continue quality tracking
- Expand to medium-frequency use cases
- Compare speed vs Gemini

**Success Criteria**:
- 50%+ of analysis tasks use gpt-oss:120b-cloud
- Maintained quality (avg ≥ 18/25)
- Reduced Gemini token usage

### Phase 3: Full Integration (Future)

**Goal**: Ollama-first for all non-critical tasks

**Tasks**:
- Default to gpt-oss:120b-cloud for all analysis
- Use deepseek-v3.1:671b-cloud for complex tasks
- Use local models for quick drafts
- Gemini only for high-stakes or quality failures

**Success Criteria**:
- 80%+ of analysis tasks use Ollama
- Quality maintained or improved
- Significant speed improvements

---

## Quality Tracking & Improvement

### Logging Template

```python
from src.core.activity_logger import log_tool_usage

def log_ollama_usage(model, task_type, quality_score_breakdown, outcome):
    """Log Ollama model usage with quality tracking."""

    total_score = sum(quality_score_breakdown.values())
    avg_score = total_score / len(quality_score_breakdown)

    log_tool_usage(
        agent="ollama",
        tool=model,
        details={
            "task_type": task_type,
            "quality_score": f"{total_score}/25",
            "average": f"{avg_score:.2f}",
            "breakdown": quality_score_breakdown,
            "outcome": outcome,  # "used_as_is", "refined_with_gemini", "discarded"
            "timestamp": datetime.now().isoformat()
        }
    )

# Example usage
log_ollama_usage(
    model="gpt-oss:120b-cloud",
    task_type="code_analysis",
    quality_score_breakdown={
        "correctness": 5,
        "completeness": 4,
        "specificity": 4,
        "context_awareness": 5,
        "actionability": 4
    },
    outcome="used_as_is"
)
```

### Analytics Queries

```python
from src.core.analytics_db import query_tool_effectiveness

# Get average quality score for gpt-oss:120b-cloud
results = query_tool_effectiveness(
    tool="gpt-oss:120b-cloud",
    metrics=["quality_score", "outcome", "task_type"]
)

# Analyze by task type
for task_type in ["code_analysis", "debugging", "code_review"]:
    avg_quality = results[results.task_type == task_type]["quality_score"].mean()
    success_rate = (results[results.task_type == task_type]["outcome"] == "used_as_is").sum()
    print(f"{task_type}: Avg Quality = {avg_quality:.2f}, Success = {success_rate}")
```

---

## Cost Analysis

### Model Costs

| Model | Cost | Speed | Quality (Est) | Use Case |
|-------|------|-------|---------------|----------|
| `gpt-oss:120b-cloud` | $0 | Fast | High | Primary analysis |
| `deepseek-v3.1:671b-cloud` | $0 | Medium | Very High | Complex reasoning |
| `minimax-m2:cloud` | $0 | Fast | Unknown | Experimental |
| Local models | $0 | Very Fast | Medium | Quick drafts |
| `gemini-2.5-pro` | $0 | Fast | Very High | Validation/refinement |
| `gemini-2.5-flash` | $0 | Very Fast | High | Quick checks |
| `gpt-5-pro` | $$$ | Fast | Very High | AVOID |
| Claude Code (you) | $$ | N/A | Very High | Final implementation |

### Token Savings Strategy

**Before Ollama Integration**:
- Gemini: 90% of tokens (free)
- Claude: 10% of tokens (implementation)

**After Ollama Integration**:
- Ollama: 60-70% of tokens (free, experimental validation)
- Gemini: 20-30% of tokens (free, refinement/validation)
- Claude: 10% of tokens (implementation)

**Net Effect**:
- Still $0 for analysis (all free models)
- More experimentation and validation
- Better quality through multi-model checks
- Faster iteration (Ollama is local/fast)

---

## Emergency Procedures

### If Ollama is Down/Slow

1. Check Ollama status: `ollama list`
2. Fallback to Gemini immediately
3. Log downtime in activity logger
4. Continue with Gemini until Ollama recovers

### If Quality Consistently Poor (< 15/25 avg)

1. Stop using that model for that task type
2. Analyze what went wrong (prompt issues? model limitation?)
3. Try different model (deepseek or Gemini)
4. Update rules to avoid that combination

### If Ollama Blocks Progress

**Never let Ollama validation delay critical work**:
- Time limit: 2 minutes for Ollama validation
- If exceeds 2 min → Skip to Gemini
- If blocking deployment → Skip Ollama entirely

---

## Summary: The Ollama-First Philosophy

**Core Principle**: Try Ollama first, validate quality, fallback intelligently.

**The Decision Flow**:
```
1. Is task high-stakes?
   → YES: Skip to Gemini/Claude
   → NO: Continue

2. Try gpt-oss:120b-cloud (or deepseek for complex)

3. Validate quality (5-point checklist)
   → Score ≥ 18/25: Use as-is ✅
   → Score 15-17/25: Refine with Gemini ⚠️
   → Score < 15/25: Discard, use Gemini ❌

4. Log quality for continuous improvement

5. Claude implements based on validated findings
```

**Expected Outcome**:
- **60-70% tasks**: Ollama provides good quality → Use as-is
- **20-30% tasks**: Ollama provides draft → Gemini refines
- **10% tasks**: Ollama quality poor → Gemini handles
- **Result**: More validation, same $0 cost, better quality through multi-model checking

---

## Quick Reference

| Scenario | Model | Quality Target | Fallback |
|----------|-------|----------------|----------|
| Default analysis | gpt-oss:120b-cloud | 18+/25 | Gemini |
| Complex reasoning | deepseek-v3.1:671b-cloud | 20+/25 | Gemini |
| Quick draft | mistral:latest | 12+/25 | Refine |
| High-stakes | N/A | N/A | Skip to Gemini |
| Production code | N/A | N/A | Claude |

**Golden Rule**: Use Ollama frequently, validate rigorously, fallback intelligently, never block progress.
