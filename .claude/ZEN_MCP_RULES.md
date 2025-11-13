# Zen MCP Usage Rules & Guidelines

**Purpose**: Offload high-token tasks to free models (Gemini Pro, Ollama) while maintaining Claude Code quality and avoiding cost increases.

**Status**: Active (v1.0)
**Last Updated**: 2025-11-04

---

## Core Principles

### 1. **Cost Optimization Strategy - Three-Tier Model Selection**

**TIER 1: Ollama Models (FREE, Experimental Validation)** ⭐ Try First
- **`gpt-oss:120b-cloud`** (PRIMARY) - 120B params, cloud-hosted, zero cost
- **`deepseek-v3.1:671b-cloud`** - 671B params, complex reasoning
- **`minimax-m2:cloud`** - Experimental cloud model
- **Local models** (mistral, phi3.5, etc.) - Quick drafts, offline work
- **Use For**: Non-critical analysis, exploration, quality validation
- **Quality Gate**: Score ≥ 18/25 to use, fallback to Tier 2 if lower

**TIER 2: Gemini Models (FREE, Proven Quality)** ⭐ Refinement & High-Stakes
- **`gemini-2.5-pro`** (1M context) - Analysis, reviews, planning, debugging
- **`gemini-2.5-flash`** (1M context) - Quick checks, simple analysis
- **Use For**: Quality refinement, high-stakes analysis, Ollama fallback
- **Quality Gate**: Gemini is proven reliable, use when quality matters

**TIER 3: Paid Models (COST $$, Avoid)** ❌
- All OpenAI models (`gpt-5-pro`, `gpt-5`, `o3-pro`, etc.) - Cost per token
- OpenRouter models - Cost per token
- **Exception**: Only use if Tiers 1-2 demonstrably fail quality checks

**Claude Code (Sonnet 4.5) Role**:
- Orchestration and task routing
- Final code generation and editing
- Critical decision-making
- Quality validation of Tier 1/2 outputs
- Integration and assembly work
- Direct user interaction

### 2. **Quality Maintenance Strategy - Ollama-First Workflow**

**The Progressive Validation Pattern**:
```
1. Try Ollama (gpt-oss:120b-cloud) for non-critical tasks
2. Claude validates output (5-point quality checklist: correctness, completeness,
   specificity, context-awareness, actionability)
3. Score output:
   - 20-25/25 (4-5 avg): ✅ Use as-is
   - 15-19/25 (3-4 avg): ⚠️ Refine with Gemini
   - < 15/25 (< 3 avg): ❌ Discard, use Gemini or Claude
4. Log quality score for continuous improvement
5. Claude implements based on validated findings
```

**When to Skip Ollama**:
- High-stakes tasks (production code, security, customer-facing)
- Time-sensitive tasks (Ollama validation adds 1-2 min)
- Tasks where Ollama historically scores < 15/25

**Quality Checklist** (Score 1-5 each):
1. **Correctness**: Factually accurate?
2. **Completeness**: All aspects addressed?
3. **Specificity**: Concrete vs vague?
4. **Context Awareness**: Understands project context?
5. **Actionability**: Can Claude implement directly?

### 3. **Token Efficiency Strategy**
- Offload high-token reads (documentation, large file analysis)
- Offload exploratory work (debugging, tracing, architecture analysis)
- Keep low-token high-value work with Claude (actual code edits)
- Use Ollama for experimentation and quality validation (adds data, zero cost)

---

## Decision Tree: When to Use Which Tool

### 🔍 Code Analysis & Understanding

**Ollama-First Pattern** (Recommended):
- **Primary**: `mcp__zen__analyze` with `gpt-oss:120b-cloud`
- **Fallback**: `mcp__zen__analyze` with `gemini-2.5-pro`
- **When**: Understanding codebase architecture, patterns, dependencies
- **Why**: Validate Ollama quality, zero cost, fallback to Gemini if needed
- **Workflow**: Ollama analyzes → Claude validates (score quality) → Use if ≥18/25, else refine with Gemini

**Traditional Pattern** (High-Stakes):
- **Use**: `mcp__zen__analyze` with `gemini-2.5-pro`
- **When**: Production-critical analysis, time-sensitive
- **Workflow**: Gemini analyzes → returns summary → Claude uses insights

**Example (Ollama-First)**:
```
Task: "Understand how authentication works in this codebase"

1. Try Ollama first:
   → mcp__zen__analyze with gpt-oss:120b-cloud, analysis_type="architecture"

2. Claude validates quality:
   → Correctness: 5, Completeness: 4, Specificity: 4, Context: 4, Actionable: 4
   → Total: 21/25 ✅ (High quality)

3. Claude uses findings to explain to user

Alternative: If score < 18/25:
   → mcp__zen__analyze with gemini-2.5-pro (refine)
   → Claude uses refined findings
```

**Example (High-Stakes)**:
```
Task: "Analyze authentication for security audit before production deploy"
→ Skip Ollama (high-stakes)
→ mcp__zen__analyze with gemini-2.5-pro, analysis_type="security"
→ Claude Code reviews findings
```

### 🐛 Debugging & Root Cause Analysis
**Use**: `mcp__zen__debug` with `gemini-2.5-pro`
- **When**: Investigating bugs, mysterious errors, performance issues
- **Why**: Deep reasoning + large context for tracing issues
- **Workflow**: Gemini traces issue → Claude implements fix

**Example**:
```
Task: "Why is this function crashing intermittently?"
→ mcp__zen__debug with gemini-2.5-pro
→ Gemini provides root cause analysis
→ Claude Code implements the fix
```

### 📋 Planning & Decomposition
**Use**: `mcp__zen__planner` with `gemini-2.5-pro`
- **When**: Breaking down complex features, refactors, migrations
- **Why**: Free model can handle planning, Claude executes
- **Workflow**: Gemini creates plan → Claude implements step-by-step

**Example**:
```
Task: "Migrate from REST to GraphQL"
→ mcp__zen__planner with gemini-2.5-pro
→ Get phased migration plan
→ Claude Code executes each phase
```

### 👀 Code Review
**Use**: `mcp__zen__codereview` with `gemini-2.5-pro`
- **When**: Pre-commit reviews, PR reviews, quality checks
- **Why**: Comprehensive review without token cost
- **Workflow**: Gemini reviews → Claude addresses issues

**Example**:
```
Before committing major changes:
→ mcp__zen__codereview with gemini-2.5-pro, review_type="full"
→ Review findings
→ Claude Code fixes identified issues
```

### 🔐 Security Audits
**Use**: `mcp__zen__secaudit` with `gemini-2.5-pro`
- **When**: Security reviews, OWASP checks, vulnerability scans
- **Why**: Thorough analysis on free tier
- **Workflow**: Gemini audits → Claude fixes vulnerabilities

**Example**:
```
Task: "Check for security vulnerabilities"
→ mcp__zen__secaudit with gemini-2.5-pro, audit_focus="owasp"
→ Claude Code implements security fixes
```

### 🧪 Test Generation
**Use**: `mcp__zen__testgen` with `gemini-2.5-pro`
- **When**: Need comprehensive test coverage
- **Why**: Gemini identifies edge cases, Claude writes tests
- **Workflow**: Gemini plans tests → Claude implements

**Example**:
```
Task: "Write tests for authentication module"
→ mcp__zen__testgen with gemini-2.5-pro
→ Get test plan with edge cases
→ Claude Code writes actual test code
```

### 🔄 Refactoring Analysis
**Use**: `mcp__zen__refactor` with `gemini-2.5-pro`
- **When**: Identifying code smells, refactoring opportunities
- **Why**: Analysis is high-token, implementation is focused
- **Workflow**: Gemini identifies opportunities → Claude refactors

**Example**:
```
Task: "Find refactoring opportunities in legacy code"
→ mcp__zen__refactor with gemini-2.5-pro, refactor_type="codesmells"
→ Review opportunities
→ Claude Code performs refactoring
```

### 💬 Brainstorming & Second Opinions
**Use**: `mcp__zen__chat` with `gemini-2.5-pro`
- **When**: Exploring approaches, getting validation, discussing tradeoffs
- **Why**: Free conversational model for exploration
- **Workflow**: Discuss with Gemini → Claude implements chosen approach

**Example**:
```
Task: "Should I use Redis or Memcached for caching?"
→ mcp__zen__chat with gemini-2.5-pro
→ Get pros/cons analysis
→ Claude Code implements chosen solution
```

### 🤔 Multi-Model Consensus (Use Sparingly)
**Use**: `mcp__zen__consensus` with FREE models only
- **When**: Critical architectural decisions requiring multiple perspectives
- **Why**: High value, but uses multiple model calls
- **Workflow**: Multiple Gemini perspectives → Claude implements

**Cost Warning**: Uses multiple models, so configure carefully:
```json
{
  "models": [
    {"model": "gemini-2.5-pro", "stance": "for"},
    {"model": "gemini-2.5-flash", "stance": "against"},
    {"model": "gemini-2.5-pro", "stance": "neutral"}
  ]
}
```
**Do NOT use paid models in consensus unless absolutely critical.**

### 📚 API Documentation Lookup
**Use**: `mcp__zen__apilookup`
- **When**: Need current docs for rapidly-changing APIs/frameworks
- **Why**: Prevents outdated information from training data
- **Always use**: This prevents hallucinations about API changes

**Example**:
```
Task: "How do I use the latest React 19 features?"
→ mcp__zen__apilookup prompt="React 19 new features and API changes"
```

### 🔬 Deep Reasoning (Use with Caution)
**Use**: `mcp__zen__thinkdeep` with `gemini-2.5-pro`
- **When**: Complex problems requiring extended reasoning
- **Cost Note**: Uses thinking mode (more tokens), but still free on Gemini
- **Workflow**: Deep analysis → Claude implements

**Example**:
```
Task: "Design optimal caching strategy for distributed system"
→ mcp__zen__thinkdeep with gemini-2.5-pro, thinking_mode="high"
```

---

## Tools to AVOID (High Cost, Low Value)

### ❌ Don't Use These Unless Absolutely Necessary

**1. Paid Models for Any Tool**
- `gpt-5-pro`, `gpt-5`, `o3-pro` - Cost per token
- Only exception: Free model failed quality check AND task is critical

**2. `mcp__zen__consensus` with Paid Models**
- Default to all Gemini models
- Never include OpenAI models unless user explicitly requests

**3. `mcp__zen__clink` (CLI-to-CLI Bridge)**
- Complex and may spawn multiple instances
- Use direct Zen tools instead
- Exception: If you need to isolate a specialized workflow

**4. Local Ollama via Custom API (Until Properly Configured)**
- Currently not configured in .mcp.json
- Would need: `CUSTOM_API_URL=http://localhost:11434`
- Note: Ollama is mentioned but not set up as a custom provider yet

---

## Quality Validation Patterns

### Pattern 1: Analysis → Implementation
```
1. Use Zen tool with gemini-2.5-pro for analysis/planning
2. Claude Code reviews findings
3. If findings are high quality → Claude implements
4. If findings are poor → Claude does it directly
```

### Pattern 2: Multi-Pass Review
```
1. Claude Code writes initial implementation
2. mcp__zen__codereview with gemini-2.5-pro
3. Claude Code addresses review comments
4. mcp__zen__precommit with gemini-2.5-pro (final check)
5. Claude Code commits if validation passes
```

### Pattern 3: Iterative Debugging
```
1. mcp__zen__debug with gemini-2.5-pro (hypothesis generation)
2. Claude Code tests hypothesis
3. If confirmed → Claude implements fix
4. If not → repeat with new hypothesis from Gemini
```

### Pattern 4: Collaborative Planning
```
1. mcp__zen__planner with gemini-2.5-pro (decomposition)
2. Claude Code reviews plan, identifies gaps
3. mcp__zen__chat with gemini-2.5-pro (discuss gaps)
4. Claude Code executes refined plan
```

---

## Configuration Best Practices

### Model Selection Guidelines

**Automatic Selection (Recommended)**:
- Let Zen MCP auto-select based on DEFAULT_MODEL setting
- Configure DEFAULT_MODEL=gemini-2.5-pro for free tier

**Explicit Selection (When Needed)**:
```python
# High-token analysis → Gemini Pro
mcp__zen__analyze(model="gemini-2.5-pro", ...)

# Quick checks → Gemini Flash
mcp__zen__codereview(model="gemini-2.5-flash", review_type="quick")

# Critical decisions requiring thinking → Gemini Pro
mcp__zen__thinkdeep(model="gemini-2.5-pro", thinking_mode="max")
```

### Thinking Mode Settings

**For Gemini Models (Free)**:
- `thinking_mode="minimal"` - Quick analysis (default for most tools)
- `thinking_mode="medium"` - Moderate complexity
- `thinking_mode="high"` - Complex problems
- `thinking_mode="max"` - Critical decisions requiring deep reasoning

**Note**: Thinking mode increases token usage but is still free on Gemini

### Temperature Settings

- `temperature=0` - Deterministic (code generation, refactoring)
- `temperature=0.3` - Slightly creative (test generation)
- `temperature=0.7` - Creative (brainstorming, exploration)
- `temperature=1` - Maximum creativity (rare use cases)

---

## Token Optimization Strategies

### 1. **Offload High-Token Reads**
**Instead of**: Claude reading 50 files to understand architecture
**Do**: `mcp__zen__analyze` with gemini-2.5-pro → summary → Claude uses

**Token Savings**: ~100k tokens per architectural analysis

### 2. **Offload Exploratory Debugging**
**Instead of**: Claude tracing through codebase to find bug
**Do**: `mcp__zen__debug` with gemini-2.5-pro → root cause → Claude fixes

**Token Savings**: ~50k tokens per complex bug

### 3. **Offload Pre-Commit Reviews**
**Instead of**: Claude reviewing all changes
**Do**: `mcp__zen__precommit` with gemini-2.5-pro → issues → Claude fixes

**Token Savings**: ~20k tokens per review

### 4. **Batch Analysis Tasks**
**Instead of**: Multiple small analysis requests
**Do**: Single comprehensive analysis with continuation_id

**Token Savings**: Reuse context across multiple related queries

### 5. **Use continuation_id for Multi-Turn Workflows**
**All Zen tools support continuation_id** for context preservation
```python
# First call
result1 = mcp__zen__debug(
    prompt="Investigate memory leak",
    model="gemini-2.5-pro",
    ...
)

# Follow-up (reuses context, no re-reading)
result2 = mcp__zen__debug(
    continuation_id=result1.continuation_id,
    prompt="Test hypothesis about buffer overflow",
    model="gemini-2.5-pro",
    ...
)
```

**Token Savings**: ~70% on follow-up queries

---

## Cost Monitoring

### RED FLAGS (Stop and Review)
- Any tool call using `gpt-5-pro`, `gpt-5`, `o3-pro` without explicit user request
- Multiple `mcp__zen__consensus` calls in single session
- Using paid models for tasks that Gemini can handle

### GREEN LIGHTS (Optimal Usage)
- Majority of tool calls use `gemini-2.5-pro` or `gemini-2.5-flash`
- Claude Code handles final code generation
- Multi-pass workflows (Gemini analyzes → Claude implements)

### TRACKING
Monitor tool usage in session logs:
```python
from src.core.activity_logger import log_tool_usage

# Automatically logged when using Zen tools
# Review .claude/logs/session_current.jsonl for patterns
```

---

## Example Workflows

### Workflow 1: Feature Implementation
```
User: "Add user authentication with JWT"

1. mcp__zen__planner with gemini-2.5-pro
   → Get implementation plan (5 phases)

2. For each phase:
   a. mcp__zen__chat with gemini-2.5-pro
      → Discuss implementation details
   b. Claude Code writes code
   c. mcp__zen__codereview with gemini-2.5-pro
      → Review for issues
   d. Claude Code fixes issues

3. mcp__zen__secaudit with gemini-2.5-pro
   → Security review of auth implementation

4. mcp__zen__testgen with gemini-2.5-pro
   → Identify test cases

5. Claude Code writes tests

6. mcp__zen__precommit with gemini-2.5-pro
   → Final validation

7. Claude Code commits

Token Cost: ~95% on Gemini (free), ~5% on Claude (orchestration)
```

### Workflow 2: Bug Investigation
```
User: "API is returning 500 errors intermittently"

1. mcp__zen__debug with gemini-2.5-pro
   → Systematic investigation
   → Root cause: Race condition in database connection pool

2. mcp__zen__chat with gemini-2.5-pro
   → Discuss fix approaches (connection pooling vs. locking)
   → Recommendation: Implement connection pooling with proper limits

3. Claude Code implements fix

4. mcp__zen__codereview with gemini-2.5-pro
   → Review fix for edge cases

5. Claude Code addresses review comments

6. mcp__zen__testgen with gemini-2.5-pro
   → Plan concurrency tests

7. Claude Code writes tests

Token Cost: ~90% on Gemini (free), ~10% on Claude (implementation)
```

### Workflow 3: Refactoring Legacy Code
```
User: "Refactor authentication module - it's a mess"

1. mcp__zen__analyze with gemini-2.5-pro
   → Understand current architecture
   → Identify dependencies

2. mcp__zen__refactor with gemini-2.5-pro, refactor_type="codesmells"
   → Identify specific issues (long methods, tight coupling, etc.)

3. mcp__zen__planner with gemini-2.5-pro
   → Create phased refactoring plan

4. For each phase:
   a. Claude Code performs refactoring
   b. mcp__zen__codereview with gemini-2.5-pro
   c. Claude Code runs tests, fixes issues

5. mcp__zen__precommit with gemini-2.5-pro
   → Final validation

6. Claude Code commits

Token Cost: ~85% on Gemini (free), ~15% on Claude (refactoring)
```

---

## Integration with SubAgent Tracking System

### Logging Zen Tool Usage
```python
from src.core.activity_logger import log_tool_usage, log_decision

# Log decision to use Zen tool
log_decision(
    question="Which approach for code analysis?",
    options=["Claude direct analysis", "Zen analyze with Gemini"],
    selected="Zen analyze with Gemini",
    rationale="100k+ tokens to analyze, Gemini is free"
)

# Log tool usage
log_tool_usage(
    agent="zen-mcp",
    tool="analyze",
    details={
        "model": "gemini-2.5-pro",
        "analysis_type": "architecture",
        "token_estimate": "~150k tokens"
    }
)
```

### Creating Snapshots Before Expensive Operations
```python
from src.core.snapshot_manager import take_snapshot

# Before large analysis or multi-step workflow
snapshot_id = take_snapshot(
    trigger="before_zen_workflow",
    context={
        "workflow": "Feature implementation with Gemini analysis",
        "expected_steps": 7
    }
)
```

---

## Troubleshooting

### Issue: Gemini Output Quality Lower Than Expected
**Solution**:
1. Increase thinking_mode: `thinking_mode="high"` or `"max"`
2. Be more specific in prompts
3. Use multi-pass: Gemini drafts → Claude refines
4. Fallback: Let Claude handle it directly

### Issue: Context Not Preserved Between Tool Calls
**Solution**:
- Always pass `continuation_id` from previous call
- Check that continuation_id is not None/empty
- Use same model across continuation chain

### Issue: Accidentally Using Paid Models
**Solution**:
1. Review model parameter in tool calls
2. Set DEFAULT_MODEL environment variable to "gemini-2.5-pro"
3. Monitor logs for unexpected model usage
4. Add assertion: Never use model starting with "gpt-" or "o3-" without user request

### Issue: Ollama Not Working
**Current Status**: Ollama mentioned in config but not set up as custom provider
**To Fix**:
```json
// Add to .mcp.json if you want to use Ollama
{
  "zen": {
    "env": {
      "CUSTOM_API_URL": "http://localhost:11434",
      // ... other env vars
    }
  }
}
```
**Note**: Ollama models would need to be specified as custom models

---

## Quick Reference Cheat Sheet

| Task Type | Zen Tool | Model | Why |
|-----------|----------|-------|-----|
| Code analysis | `analyze` | `gemini-2.5-pro` | 1M context, free |
| Debugging | `debug` | `gemini-2.5-pro` | Deep reasoning, free |
| Planning | `planner` | `gemini-2.5-pro` | Complex decomposition, free |
| Code review | `codereview` | `gemini-2.5-pro` | Comprehensive, free |
| Security audit | `secaudit` | `gemini-2.5-pro` | Thorough analysis, free |
| Test generation | `testgen` | `gemini-2.5-pro` | Edge case discovery, free |
| Refactoring | `refactor` | `gemini-2.5-pro` | Pattern identification, free |
| Brainstorming | `chat` | `gemini-2.5-pro` | Exploration, free |
| API docs | `apilookup` | N/A | Current info |
| Quick checks | `codereview` | `gemini-2.5-flash` | Fast, free |
| Multi-perspective | `consensus` | All Gemini | Critical decisions only |

---

## Ollama-Specific Documentation

**For comprehensive Ollama rules and quality validation, see**:
- **`.claude/OLLAMA_INTEGRATION_RULES.md`** - Complete Ollama usage guide
  - Available models (cloud and local)
  - Quality validation checklist (5-point scoring)
  - Progressive rollout plan (validation → adoption → full integration)
  - Use case definitions for `gpt-oss:120b-cloud`
  - Quality tracking and analytics
  - Emergency procedures and fallback patterns

**Quick Ollama Reference**:
- **Try first**: `gpt-oss:120b-cloud` (120B, cloud, free)
- **Complex tasks**: `deepseek-v3.1:671b-cloud` (671B, cloud, free)
- **Quick drafts**: `mistral:latest`, `phi3.5:3.8b` (local, fast)
- **Quality gate**: Score ≥ 18/25 to use, refine with Gemini if lower
- **Skip Ollama for**: High-stakes, time-sensitive, historically poor quality

---

## Version History

**v1.1 (2025-11-04)**:
- Added three-tier model selection (Ollama → Gemini → Paid)
- Ollama integration with quality validation workflow
- Progressive validation pattern with 5-point quality checklist
- Updated examples to show Ollama-first pattern

**v1.0 (2025-11-04)**:
- Initial rules document
- Cost optimization strategy
- Quality validation patterns
- Example workflows
- Integration with SubAgent Tracking System

---

## Notes for Future Updates

1. **Ollama Quality Metrics**: Track gpt-oss:120b-cloud performance across task types
2. **Performance Metrics**: Compare Ollama vs Gemini speed and quality
3. **Quality Benchmarks**: Establish baseline scores for each model/task combination
4. **Cost Tracking**: Monitor usage patterns and quality scores
5. **Model Evolution**: Update as new Ollama or Gemini models are released
6. **Progressive Rollout**: Move from validation phase → selective adoption → full integration

---

## Summary: The Golden Rules (Updated for Three-Tier Strategy)

1. **Try Ollama first** (`gpt-oss:120b-cloud`) for non-critical analysis tasks
2. **Validate rigorously** with 5-point quality checklist (score ≥ 18/25 to use)
3. **Fallback intelligently** to Gemini if quality is insufficient
4. **Never use paid models** (GPT-5, O3) unless both Ollama and Gemini fail
5. **Claude Code is the implementer** - always writes the final code
6. **Use continuation_id** to preserve context and save tokens
7. **Monitor and improve** through activity logs and quality tracking
8. **Think progressive**: Ollama tries → Claude validates → Gemini refines (if needed) → Claude implements
9. **Skip Ollama for high-stakes** - production code, security, time-sensitive tasks
10. **Token efficiency**: Offload high-token reads, keep low-token writes with Claude

**Expected Benefits**:
- **Token savings**: Still 85-95% on free tier (same as before)
- **Quality validation**: More experimental validation at zero cost
- **Continuous improvement**: Quality scores drive model selection refinement
- **Flexibility**: Three tiers provide fallback options for any scenario

**Three-Tier Summary**:
- **Tier 1 (Ollama)**: Try first for exploration and validation (60-70% of tasks if quality good)
- **Tier 2 (Gemini)**: Refinement, high-stakes, and fallback (20-30% of tasks)
- **Tier 3 (Paid)**: Emergency only, never use unless explicitly required (0% target)
