# Claude Code Subagents for Interview Assistant

This document describes the specialized subagents designed to optimize development workflow for the Interview Assistant project.

## Why Subagents?

Subagents reduce context usage by **60-70%** through:
- **Focused Scope**: Each agent reads only relevant files (10-20 vs entire codebase)
- **Specialized Knowledge**: Pre-loaded domain expertise in agent prompts
- **Clear Boundaries**: Each agent works in specific directories
- **Incremental Work**: Handle single components at a time

## Available Agents

### 1. refactor-agent
**Purpose**: Extract monolithic code into modular components

**When to use:**
- Extracting components from `optimized_stt_server_v3.py`
- Creating plugin base classes
- Refactoring global state
- Converting code to match protocols

**Typical usage:**
```
/task Extract the Whisper transcription logic from optimized_stt_server_v3.py into src/transcription/whisper.py following the TranscriberProtocol interface. Maintain backward compatibility.
```

**Focus areas:**
- `src/plugins/`
- `src/core/protocols.py`
- `optimized_stt_server_v3.py`

---

### 2. performance-agent
**Purpose**: Measure, monitor, and optimize end-to-end latency (<4s p95 target)

**When to use:**
- Adding timing decorators
- Building metrics collection
- Profiling bottlenecks
- Implementing latency budgets
- Performance regression detection

**Typical usage:**
```
/task Add latency tracking to the transcription pipeline. Create timing decorators that measure and log duration for audio capture, Whisper processing, and question detection stages.
```

**Latency budgets:**
- Transcription: <500ms
- Audio preprocessing: <50ms
- LLM generation: <3s
- End-to-end (p95): <4s

**Focus areas:**
- `src/core/metrics.py`
- `src/core/timing.py`
- `src/core/budgets.py`

---

### 3. plugin-builder
**Purpose**: Create and integrate new plugins following plugin specification

**When to use:**
- Converting existing implementations to plugins
- Creating new plugin types
- Implementing plugin registry/loader
- Adding hot-swapping logic
- Building plugin tests

**Typical usage:**
```
/task Convert the Ollama LLM implementation into an OllamaPlugin following the LLMProviderProtocol. Include plugin manifest, configuration schema, and unit tests.
```

**Plugin categories:**
- `transcriber` - Speech-to-text
- `llm` - Language models
- `audio` - Audio sources
- `audio_processor` - Audio preprocessing
- `storage` - Persistence backends

**Focus areas:**
- `src/plugins/`
- `docs/PLUGIN_SPEC.md`
- `tests/unit/test_plugins.py`

---

### 4. test-engineer
**Purpose**: Write comprehensive tests (80%+ coverage target)

**When to use:**
- Creating pytest fixtures
- Writing unit tests
- Building integration tests
- Creating mocks/stubs
- Performance benchmarking
- Test coverage analysis

**Typical usage:**
```
/task Write comprehensive unit tests for the audio buffer management system in src/audio/buffer.py. Include tests for: buffer overflow handling, sliding window logic, energy gating, and edge cases.
```

**Test types:**
- Unit: `tests/unit/`
- Integration: `tests/integration/`
- Performance: `tests/performance/`

**Focus areas:**
- `tests/`
- `conftest.py`
- Coverage reports

---

### 5. audio-specialist
**Purpose**: Implement advanced audio features (Phase 3)

**When to use:**
- Audio quality monitoring
- Noise reduction
- Speaker diarization
- Multi-source audio handling
- Real-time preprocessing

**Typical usage:**
```
/task Implement audio quality monitoring that calculates SNR, detects clipping, and monitors audio levels in real-time. Add metrics to WebSocket stream for UI display.
```

**Latency budget:** <50ms for all preprocessing

**Focus areas:**
- `src/audio/`
- `src/plugins/audio/`
- Libraries: noisereduce, pyannote.audio, librosa

---

### 6. config-architect
**Purpose**: Build configuration, logging, and error handling infrastructure

**When to use:**
- Creating structured logging
- Building configuration management
- Implementing error handling
- Adding input validation
- Creating feature flags

**Typical usage:**
```
/task Create a structured JSON logging system with timing metadata. Include component-specific loggers, log level configuration, and request ID tracking.
```

**Focus areas:**
- `src/core/logger.py`
- `src/core/config.py`
- `src/core/errors.py`
- `src/core/features.py`

---

### 7. ui-builder
**Purpose**: Build card-based modular UI (Phase 3)

**When to use:**
- Creating card components
- Implementing drag-and-drop
- Building grid layout
- Adding WebSocket client
- Creating layout presets
- Implementing keyboard shortcuts

**Typical usage:**
```
/task Build the PerformanceCard component that displays real-time latency metrics, resource usage, and component breakdown with charts.
```

**Performance target:** 60fps rendering

**Grid system:** 20rem columns × 1rem rows

**Focus areas:**
- `src/ui/components/`
- `index.html`
- `src/ui/styles/`

---

### 8. doc-writer
**Purpose**: Maintain comprehensive documentation

**When to use:**
- Updating CLAUDE.md
- Writing plugin tutorials
- Creating API documentation
- Generating architecture diagrams
- Writing deployment guides

**Typical usage:**
```
/task Update CLAUDE.md to reflect the new plugin architecture. Document the plugin lifecycle, registry system, and hot-swapping mechanism.
```

**Focus areas:**
- `docs/`
- `README.md`
- `CLAUDE.md`

---

### 9. security-auditor
**Purpose**: Security hardening and validation

**When to use:**
- Adding input validation
- Implementing credential storage
- Adding rate limiting
- Security audits
- Dependency scanning

**Typical usage:**
```
/task Implement secure API key storage using macOS Keychain via the keyring library. Create CredentialManager class with methods for storing and retrieving API keys for OpenAI and Anthropic plugins.
```

**Focus areas:**
- `src/core/validation.py`
- `src/core/credentials.py`
- `src/server/rate_limit.py`

---

## Usage Patterns

### Pattern 1: Component Extraction
```
Step 1: Use refactor-agent to extract component
Step 2: Use test-engineer to write tests
Step 3: Use doc-writer to document changes
Step 4: Use performance-agent to verify no regression
```

### Pattern 2: New Plugin Development
```
Step 1: Use plugin-builder to create plugin structure
Step 2: Use test-engineer to create plugin tests
Step 3: Use doc-writer to add plugin documentation
```

### Pattern 3: Performance Optimization
```
Step 1: Use performance-agent to profile and identify bottlenecks
Step 2: Use refactor-agent to optimize code
Step 3: Use test-engineer to create performance regression tests
Step 4: Use performance-agent to verify improvements
```

### Pattern 4: UI Feature Development
```
Step 1: Use ui-builder to create component
Step 2: Use test-engineer to write UI tests
Step 3: Use performance-agent to verify 60fps rendering
Step 4: Use doc-writer to document component API
```

---

## Best Practices

### 1. Use the Right Agent for the Job
Don't use a general-purpose agent when a specialist exists. Specialists have pre-loaded context and patterns.

### 2. Chain Agents for Complex Tasks
For multi-phase work, use multiple agents sequentially:
1. refactor-agent → extract code
2. test-engineer → write tests
3. performance-agent → verify latency
4. doc-writer → document changes

### 3. Provide Clear Scope
Give agents specific, bounded tasks:
- ✅ "Extract Whisper logic to src/transcription/whisper.py"
- ❌ "Refactor the entire server"

### 4. Reference Architecture Documents
Point agents to relevant docs:
- Plugin development → `docs/PLUGIN_SPEC.md`
- Performance targets → `CLAUDE.md` (latency budgets)
- Architecture → `docs/ARCHITECTURE.md`

### 5. Measure Results
After using performance-agent, verify:
- Latency within budgets
- No regressions
- Metrics logged correctly

---

## Context Usage Comparison

| Task | General Agent | Specialist Agent | Savings |
|------|---------------|------------------|---------|
| Extract Whisper component | 50k tokens | 15k tokens | 70% |
| Add OpenAI plugin | 40k tokens | 12k tokens | 70% |
| Write buffer tests | 35k tokens | 10k tokens | 71% |
| Build performance card | 30k tokens | 12k tokens | 60% |
| Add noise reduction | 45k tokens | 18k tokens | 60% |

**Average savings: 66%**

---

## Invoking Agents

Agents are invoked using Claude Code's Task tool or slash commands:

```
/task [agent-specific instructions]
```

Example:
```
/task Use the plugin-builder agent to create a NoiseReductionPlugin that uses the noisereduce library. Include configuration for noise reduction strength (off, light, medium, aggressive) and ensure latency stays under 50ms.
```

---

## Future Agent Ideas

As the project evolves, consider adding:

- **crm-integrator**: Salesforce/Dynamics 365 integration specialist
- **deployment-engineer**: Docker, CI/CD, cloud deployment specialist
- **onboarding-builder**: Smart onboarding flow creation
- **analytics-agent**: Usage analytics and telemetry implementation

---

## Agent Development

To create a new agent:

1. Identify repetitive task pattern
2. Define agent scope and constraints
3. Document expertise areas
4. Create agent prompt template
5. Test with real scenarios
6. Measure context reduction
7. Document in this guide

---

## Troubleshooting

**Agent returns too broad results:**
- Provide more specific scope
- Reference specific files/directories
- Include concrete examples

**Agent misses important context:**
- Explicitly reference required docs
- Provide examples of expected output
- Include performance/quality constraints

**Agent uses too much context:**
- Break task into smaller chunks
- Use sequential agent chain
- Provide explicit file list to read

---

## Summary

Use specialized agents to:
- **Reduce context usage by 60-70%**
- **Speed up development** with pre-loaded expertise
- **Maintain quality** with focused, specialized work
- **Follow architecture** through agent constraints
- **Track progress** with clear, bounded tasks

Choose agents based on task type, not task size. Even small tasks benefit from specialist knowledge and reduced context.
