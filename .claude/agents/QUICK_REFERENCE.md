# Subagent Quick Reference

## Quick Agent Selector

**Need to...** | **Use Agent** | **Example Task**
---|---|---
Extract component from monolith | `refactor-agent` | Extract Whisper → `src/transcription/whisper.py`
Create new plugin | `plugin-builder` | Build OpenAIPlugin with LLMProviderProtocol
Write tests | `test-engineer` | Add unit tests for audio buffer
Optimize performance | `performance-agent` | Add latency tracking to pipeline
Build UI component | `ui-builder` | Create PerformanceCard with charts
Add logging/config | `config-architect` | Implement structured JSON logging
Implement audio feature | `audio-specialist` | Add noise reduction plugin
Update documentation | `doc-writer` | Document plugin architecture
Add security/validation | `security-auditor` | Implement API key storage

---

## Common Task Templates

### Extract Component
```
Use refactor-agent to extract [COMPONENT] from optimized_stt_server_v3.py
into src/[CATEGORY]/[FILE].py following the [PROTOCOL] interface.
Maintain backward compatibility via feature flags.
```

### Create Plugin
```
Use plugin-builder to create [NAME]Plugin implementing [PROTOCOL].
Include: plugin manifest, config schema, lifecycle hooks, and unit tests.
Target latency: <[TIME]ms.
```

### Add Performance Tracking
```
Use performance-agent to add latency tracking for [STAGE].
Measure duration, log with structured logging, and enforce [TIME]ms budget.
Verify no regression against baseline.
```

### Write Tests
```
Use test-engineer to write [TYPE] tests for [COMPONENT] in [FILE].
Include: edge cases, error handling, mocking, and aim for 80%+ coverage.
```

### Build UI Card
```
Use ui-builder to create [NAME]Card displaying [DATA].
Include: real-time updates via WebSocket, responsive layout,
keyboard shortcuts, and 60fps rendering target.
```

---

## Latency Budgets (Reference)

| Component | Budget | Agent |
|-----------|--------|-------|
| Audio preprocessing | <50ms | audio-specialist |
| Transcription | <500ms | performance-agent |
| Question detection | <100ms | performance-agent |
| LLM generation | <3s | performance-agent |
| **End-to-end (p95)** | **<4s** | performance-agent |
| UI rendering | <100ms | ui-builder |
| Plugin swap | <1s | plugin-builder |

---

## File Locations (Reference)

**Category** | **Location** | **Agent**
---|---|---
Core infrastructure | `src/core/` | config-architect
Plugins | `src/plugins/` | plugin-builder
Audio processing | `src/audio/` | audio-specialist
Transcription | `src/transcription/` | refactor-agent
LLM components | `src/llm/` | refactor-agent
Server/WebSocket | `src/server/` | refactor-agent
UI components | `src/ui/components/` | ui-builder
Tests | `tests/` | test-engineer
Documentation | `docs/` | doc-writer

---

## Agent Chaining Examples

### Workflow 1: Extract + Test + Document
```
1. refactor-agent: Extract component
2. test-engineer: Write tests (80%+ coverage)
3. doc-writer: Document API
4. performance-agent: Verify no regression
```

### Workflow 2: Plugin Development
```
1. plugin-builder: Create plugin structure
2. test-engineer: Write plugin tests
3. doc-writer: Add to PLUGIN_GALLERY.md
4. security-auditor: Validate inputs
```

### Workflow 3: Performance Optimization
```
1. performance-agent: Profile and identify bottleneck
2. refactor-agent: Optimize critical path
3. test-engineer: Add regression test
4. performance-agent: Verify improvement
```

### Workflow 4: UI Feature
```
1. ui-builder: Create card component
2. test-engineer: Write UI tests
3. performance-agent: Verify 60fps
4. doc-writer: Document component props/events
```

---

## Anti-Patterns (Don't Do This)

❌ **Using general agent for specialized task**
- Wastes 60-70% more context
- Misses project-specific patterns

❌ **Giving agent too broad a scope**
- "Refactor the entire server" → Break into components
- Use multiple focused agent tasks instead

❌ **Skipping performance verification**
- Always measure latency after changes
- Use performance-agent to verify budgets

❌ **Not chaining agents**
- Don't extract code without writing tests
- Don't create plugins without documentation

❌ **Ignoring latency budgets**
- Every change must respect <4s end-to-end target
- Use performance-agent to enforce budgets

---

## Pro Tips

### 1. Start Small
Begin with one agent for repetitive task, measure context savings, expand from there.

### 2. Measure Everything
Track context usage before/after using agents. Document savings.

### 3. Reference Docs Explicitly
Point agents to:
- `CLAUDE.md` - Architecture and principles
- `ROADMAP.md` - Implementation plan
- `docs/PLUGIN_SPEC.md` - Plugin development
- `.env.example` - Configuration

### 4. Enforce Constraints
Include in every agent task:
- Latency budget
- Test coverage requirement
- Backward compatibility note
- Performance baseline

### 5. Use Agents for Repetitive Patterns
If you've done it twice, create an agent for it:
- Creating plugins (plugin-builder)
- Writing tests (test-engineer)
- Extracting components (refactor-agent)

---

## Context Reduction Tips

**To maximize context savings:**

1. **Specify exact files to read**
   - ✅ "Read src/audio/buffer.py and src/core/timing.py"
   - ❌ "Look at the audio code"

2. **Provide explicit scope**
   - ✅ "Extract lines 100-250 from optimized_stt_server_v3.py"
   - ❌ "Refactor the server"

3. **Reference patterns by name**
   - ✅ "Follow the TranscriberProtocol interface"
   - ❌ "Make it follow the same pattern as other components"

4. **Include examples**
   - Show desired output format
   - Reference similar existing code
   - Provide test case examples

5. **Use sequential tasks**
   - Break large work into 3-5 agent tasks
   - Each task reads <20 files
   - Chain results between tasks

---

## Emergency Overrides

**If agent is blocked or slow:**

1. **Check latency budgets** - May be profiling too deeply
2. **Reduce scope** - Break into smaller tasks
3. **Provide explicit file list** - Prevent exploratory reads
4. **Skip optional steps** - Remove "nice to have" requirements
5. **Use faster model** - Switch to haiku for simple tasks

---

## Metrics to Track

For each agent usage, track:
- Context tokens used
- Time to completion
- Quality of output (tests pass, docs complete, etc.)
- Latency impact (if applicable)

Target metrics:
- Context reduction: >60%
- First-attempt success: >80%
- Latency maintained: <4s end-to-end
- Test coverage: >80%

---

## Next Steps

1. Try refactor-agent on a simple extraction task
2. Measure context usage vs general agent
3. Document savings
4. Expand to other agents
5. Create custom agents for project-specific patterns

---

## Questions?

See full documentation: `.claude/agents/AGENTS_GUIDE.md`

Or ask:
- "Show me an example of using performance-agent"
- "How do I chain refactor-agent and test-engineer?"
- "What's the best agent for adding noise reduction?"
