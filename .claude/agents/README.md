# Specialized Claude Code Subagents

This directory contains documentation for specialized subagents designed to optimize development workflow for the Interview Assistant project.

## Overview

Specialized subagents reduce context usage by **60-70%** by focusing on specific domains with pre-loaded expertise and constrained scope.

## Documents

### [ORCHESTRATOR_GUIDE.md](./ORCHESTRATOR_GUIDE.md) ⭐ **START HERE**
Complete guide to the Orchestrator Agent - your AI development team lead:
- What the orchestrator does
- When to use it vs direct agents
- Common use cases with examples
- Validation and quality enforcement
- Advanced features and workflows

### [orchestrator-agent.md](./orchestrator-agent.md) 🤖 **FOR CLAUDE**
The orchestrator agent system prompt (used by Claude Code):
- Decision-making framework
- Standard workflows (extract, plugin, optimize, UI, audio)
- Validation checklists
- Correction templates
- Context optimization strategies

### [AGENTS_GUIDE.md](./AGENTS_GUIDE.md)
Complete guide to all 9 specialized agents:
- Agent descriptions and capabilities
- When to use each agent
- Usage patterns and best practices
- Context reduction strategies
- Troubleshooting guide

### [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
Quick lookup reference for daily use:
- Agent selector matrix
- Common task templates
- Latency budget reference
- Agent chaining workflows
- Pro tips and anti-patterns

## The Agent System: Orchestrator + PM + 9 Specialists

### 🎯 Orchestrator Agent (The Coordinator)
**The AI team lead** that manages the specialized agents:
- Breaks down complex requests into atomic tasks
- Assigns tasks to appropriate specialists
- Validates outputs against project standards
- Corrects agents when they don't meet requirements
- Coordinates with PM for progress tracking
- Provides intelligent next-step recommendations

**Use when:**
- Starting a roadmap phase: "Begin Phase 1"
- Complex multi-step tasks: "Extract the Whisper component"
- Uncertain what's next: "What should we work on?"
- Need validation: Ensures tests, performance, docs automatically

### 📊 Project Manager Agent (The Memory Keeper)
**The long-term memory** that tracks all project state:
- Maintains PROJECT_STATUS.md as single source of truth
- Logs task completions with outcomes
- Tracks performance baselines over time
- Records ad-hoc changes outside roadmap
- Identifies blockers and dependencies
- Generates progress reports

**Use when:**
- Checking status: "What's our current status?"
- Logging work: "I just changed [something]"
- Getting recommendations: "What should we work on next?"
- Performance tracking: Updates baselines automatically

**Benefits:**
- **90% context savings** for status checks (5k vs 50k tokens)
- **No lost work** - All changes tracked
- **Smart recommendations** - Dependency-aware next steps

### 🔧 The 9 Specialized Agents

1. **refactor-agent** - Component extraction and refactoring
2. **performance-agent** - Latency optimization and monitoring
3. **plugin-builder** - Plugin development and integration
4. **test-engineer** - Test writing and coverage
5. **audio-specialist** - Advanced audio features
6. **config-architect** - Configuration and infrastructure
7. **ui-builder** - Card-based UI development
8. **doc-writer** - Documentation maintenance
9. **security-auditor** - Security and validation

## Quick Start

### Example 1: Extract a Component
```
Use refactor-agent to extract the LLM analyzer logic from
optimized_stt_server_v3.py into src/llm/analyzer.py.
Follow the LLMProviderProtocol interface and maintain backward compatibility.
```

### Example 2: Add Performance Tracking
```
Use performance-agent to add latency tracking to the transcription pipeline.
Measure audio capture, Whisper processing, and question detection stages.
Enforce the 500ms transcription budget.
```

### Example 3: Create a Plugin
```
Use plugin-builder to create a NoiseReductionPlugin implementing AudioProcessorProtocol.
Include manifest, config schema (strength: off/light/medium/aggressive),
and ensure <50ms latency. Add unit tests.
```

## Why Specialized Agents?

### Context Savings
| Task | General | Specialized | Savings |
|------|---------|-------------|---------|
| Component extraction | 50k | 15k | 70% |
| Plugin creation | 40k | 12k | 70% |
| Test writing | 35k | 10k | 71% |
| UI component | 30k | 12k | 60% |

### Speed Improvements
- Pre-loaded domain knowledge
- Knows project patterns
- Enforces architectural constraints
- Focuses on specific file sets

### Quality Improvements
- Follows project conventions
- Enforces performance budgets
- Maintains test coverage goals
- Ensures backward compatibility

## Best Practices

### 1. Choose the Right Agent
Match task type to agent specialty, not task size.

### 2. Chain Agents
Complex tasks → Sequential agent workflow:
1. Extract → refactor-agent
2. Test → test-engineer
3. Document → doc-writer
4. Verify → performance-agent

### 3. Provide Clear Scope
- Reference specific files
- Include constraints (latency, coverage)
- Provide examples

### 4. Measure Results
Track context usage, time, quality for each agent use.

### 5. Enforce Budgets
Every task must respect:
- <4s end-to-end latency (p95)
- 80%+ test coverage
- Backward compatibility
- Security validation

## Agent Selection Matrix

**Need to...** | **Use...**
---|---
Extract monolithic code | refactor-agent
Optimize latency | performance-agent
Create plugin | plugin-builder
Write tests | test-engineer
Add audio feature | audio-specialist
Configure logging | config-architect
Build UI component | ui-builder
Update docs | doc-writer
Add validation | security-auditor

## Integration with Project

### Aligned with ROADMAP.md
Agents map to roadmap phases:
- **Phase 1** (Weeks 1-4): config-architect, refactor-agent, test-engineer
- **Phase 2** (Weeks 5-8): plugin-builder, performance-agent
- **Phase 3** (Weeks 9-13): ui-builder, audio-specialist
- **Phase 4** (Weeks 14-17): security-auditor, doc-writer

### Respects CLAUDE.md Principles
- Performance-first (latency budgets enforced)
- Zero-friction (agents know auto-detection patterns)
- Complete modularity (plugin architecture focus)
- Privacy-first (security-auditor validates)
- Structured logging (config-architect implements)

### Follows Architecture
Agents understand:
- Plugin lifecycle and protocols
- State management patterns
- Dependency injection
- Feature flag system
- Testing infrastructure

## Getting Started

1. **Read** [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for common patterns
2. **Try** refactor-agent on a simple extraction task
3. **Measure** context usage vs general approach
4. **Expand** to other agents based on need
5. **Document** your patterns and savings

## Advanced Usage

### Custom Agent Creation
As patterns emerge, create new agents:
1. Identify repetitive task
2. Define scope and constraints
3. Document expertise areas
4. Test and measure
5. Add to this guide

### Potential Future Agents
- crm-integrator (Salesforce/Dynamics 365)
- deployment-engineer (Docker, CI/CD, cloud)
- onboarding-builder (smart setup flows)
- analytics-agent (usage tracking)

## Troubleshooting

**Agent too slow?**
- Reduce scope
- Provide explicit file list
- Use haiku model for simple tasks

**Agent missing context?**
- Reference specific docs explicitly
- Include concrete examples
- Provide expected output format

**Agent using too much context?**
- Break into smaller tasks
- Use sequential agent chain
- Specify exact files to read

## Metrics

Track for each agent usage:
- Context tokens (target: <20k)
- Time to completion
- Quality score (tests pass, docs complete)
- Latency impact (if applicable)

Target outcomes:
- **60%+ context reduction**
- **80%+ first-attempt success**
- **<4s end-to-end latency maintained**
- **80%+ test coverage**

## Support

- Full guide: [AGENTS_GUIDE.md](./AGENTS_GUIDE.md)
- Quick ref: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- Project docs: `../CLAUDE.md`, `../ROADMAP.md`

## Summary

Specialized agents are **not about doing more with AI** - they're about **doing it more efficiently**:

- **Less context** = faster responses, lower costs
- **More focus** = better quality, fewer iterations
- **Clear constraints** = consistent architecture
- **Measurable results** = track improvements

Start with one agent. Measure the difference. Expand from there.

**The goal**: Reduce context usage by 60-70% while maintaining or improving code quality and development speed.
