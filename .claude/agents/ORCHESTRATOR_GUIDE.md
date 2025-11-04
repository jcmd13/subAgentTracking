# Orchestrator Agent - Quick Start Guide

## What is the Orchestrator?

The Orchestrator Agent is an intelligent project manager that coordinates the 9 specialized subagents to efficiently complete complex development tasks. Think of it as your **AI development team lead** that:

- 📋 Breaks down complex requests into manageable tasks
- 🎯 Assigns tasks to the right specialized agents
- ✅ Validates outputs against project standards
- 🔄 Corrects agents when they don't meet requirements
- 📊 Tracks progress and reports completion

## When to Use the Orchestrator

### Use the Orchestrator When You Want To:

✅ **"Start Phase X"** - Begin a new roadmap phase
✅ **"What's next?"** - Get intelligent next-step recommendations
✅ **"Extract the Whisper component"** - Complex multi-agent tasks
✅ **"Add noise reduction"** - New features requiring coordination
✅ **"Optimize the LLM pipeline"** - Multi-step optimization workflows
✅ **"Implement the plugin system"** - Large architectural changes

### Use a Specific Agent When You Want To:

❌ **Simple, single-agent tasks** - Direct agent invocation is faster
❌ **Very specific file edits** - Use the appropriate specialist directly
❌ **Quick tests or docs** - test-engineer or doc-writer directly

## How to Invoke the Orchestrator

### Method 1: Direct Request (Recommended)
Just ask naturally. The orchestrator will recognize complex requests:

```
I'm ready to start Phase 1 of the roadmap.
```

```
Extract the Whisper transcription logic into a modular component.
```

```
Add noise reduction to improve audio quality.
```

### Method 2: Explicit Orchestration
Be explicit if you want orchestration:

```
Use the orchestrator to coordinate implementing the plugin system.
```

```
Orchestrate the extraction of the LLM component with proper testing and documentation.
```

### Method 3: Next Steps
Ask for intelligent recommendations:

```
What should we work on next?
```

```
Phase 2 is complete. What's next?
```

```
We've finished the logging system. What's the next priority?
```

## Common Use Cases

### Use Case 1: Starting a Phase

**Request:**
```
Let's start Phase 1
```

**What the Orchestrator Does:**
1. ✅ Identifies Phase 1, Week 1, Task 1
2. ✅ Plans multi-step workflow (config-architect → test-engineer → doc-writer)
3. ✅ Provides detailed execution plan
4. ✅ Executes step by step
5. ✅ Validates each output
6. ✅ Reports completion with metrics

**Example Response:**
```markdown
## Starting Phase 1: Foundation & Infrastructure

I'll coordinate Week 1, Task 1.1: Implement Structured Logging System

### Execution Plan

Step 1: Create Logging Infrastructure (config-architect)
Step 2: Create Timing Decorators (config-architect)
Step 3: Write Tests (test-engineer)
Step 4: Update Documentation (doc-writer)

Proceeding with execution...
```

---

### Use Case 2: Extracting a Component

**Request:**
```
Extract the Whisper transcription logic
```

**What the Orchestrator Does:**
1. ✅ Recognizes as Phase 1, Week 3 task
2. ✅ Plans: refactor-agent → test-engineer → performance-agent → doc-writer
3. ✅ Includes backward compatibility requirements
4. ✅ Enforces feature flag usage
5. ✅ Validates latency budgets
6. ✅ Reports performance impact

**Key Features:**
- Automatically includes feature flags for compatibility
- Runs performance validation
- Ensures tests are written
- Updates documentation

---

### Use Case 3: Adding a New Feature

**Request:**
```
Add noise reduction for audio quality
```

**What the Orchestrator Does:**
1. ✅ Identifies as Phase 3 task
2. ✅ Checks prerequisites (plugin system, protocols)
3. ✅ Plans: audio-specialist → plugin-builder → test-engineer → performance-agent → ui-builder → doc-writer
4. ✅ Enforces <50ms latency budget
5. ✅ Validates end-to-end <4s maintained
6. ✅ Updates UI to show quality improvements

**Key Features:**
- Checks if prerequisites exist (creates if needed)
- Enforces strict latency budgets
- Coordinates backend + UI changes
- Validates quality improvements measurable

---

### Use Case 4: Getting Recommendations

**Request:**
```
What should we work on next?
```

**What the Orchestrator Does:**
1. ✅ Analyzes current project state
2. ✅ Reviews roadmap progress
3. ✅ Identifies incomplete items
4. ✅ Suggests next logical steps
5. ✅ Provides options with justification
6. ✅ Waits for user decision

**Example Response:**
```markdown
## Current Phase Analysis
Current Phase: Phase 1, Week 3
Completion: 2/4 tasks complete

## Recommended Next Steps

Option A: Complete Current Phase (Recommended)
- Extract WebSocket server component (refactor-agent)
- Write integration tests (test-engineer)

Option B: Begin Phase 2
- Design plugin architecture (doc-writer)
- Create plugin base classes (plugin-builder)

My Recommendation: Option A - solidify foundation before advancing

Shall I proceed with Option A?
```

---

### Use Case 5: Handling Corrections

**Request:**
```
The refactor-agent didn't add the feature flag
```

**What the Orchestrator Does:**
1. ✅ Analyzes the validation failure
2. ✅ Identifies specific issue (missing feature flag)
3. ✅ Creates detailed corrective instructions
4. ✅ Re-invokes agent with corrections
5. ✅ Validates fix
6. ✅ Reports corrected output

**Example Response:**
```markdown
## Correcting refactor-agent Output

Issue: Missing feature flag for USE_MODULAR_TRANSCRIBER
Impact: Violates backward compatibility requirement
Severity: High

### Correction Required
1. Add feature flag to src/core/features.py
2. Update server.py to check flag
3. Document in .env.example

Re-executing refactor-agent with corrective instructions...
```

---

## Orchestrator Capabilities

### 1. Intelligent Task Decomposition
Breaks complex requests into atomic steps with:
- Clear dependencies
- Parallel execution opportunities
- Specific success criteria
- Performance constraints

### 2. Phase-Aware Planning
Understands the roadmap and:
- Maps requests to specific phases/weeks/tasks
- Identifies prerequisites
- Suggests next steps
- Warns about dependencies

### 3. Agent Selection
Chooses the right agent based on:
- Task type (extract, test, optimize, document, etc.)
- Domain (audio, LLM, UI, infrastructure, etc.)
- Complexity (refactor vs simple edit)
- Phase context

### 4. Quality Validation
Checks every output for:
- Performance: Latency budgets maintained
- Testing: 80%+ coverage achieved
- Security: Inputs validated
- Documentation: Updated to reflect changes
- Compatibility: Backward compatible via feature flags

### 5. Self-Correction
When validation fails:
- Identifies specific issues
- Creates detailed corrective instructions
- Re-invokes agent with fixes
- Validates correction

### 6. Context Optimization
Reduces token usage by:
- Loading only relevant files
- Providing specific line ranges
- Referencing patterns by pointer
- Incremental file loading

---

## Validation Standards

The orchestrator enforces these requirements on all agent outputs:

### Code Quality
- ✅ Follows project patterns
- ✅ Uses config system (no hardcoded values)
- ✅ Proper error handling
- ✅ Type hints where applicable

### Testing
- ✅ Tests written and passing
- ✅ Coverage >80%
- ✅ Edge cases covered
- ✅ Error paths tested

### Performance
- ✅ Latency measured and logged
- ✅ Within budgets (<500ms transcription, <50ms preprocessing, <3s LLM, <4s end-to-end)
- ✅ No regression vs baseline
- ✅ Resource usage acceptable

### Security
- ✅ Inputs validated
- ✅ No sensitive data in logs/code
- ✅ Credentials stored securely (OS keychain)

### Documentation
- ✅ API documented
- ✅ CLAUDE.md updated if needed
- ✅ Examples provided

### Backward Compatibility
- ✅ Feature flag used for new behavior
- ✅ Legacy entry points still work
- ✅ Migration path documented

---

## Response Templates

The orchestrator uses structured responses:

### 1. Execution Plan
```markdown
## [Task Name]

### Execution Plan

Step 1: [Task]
- Agent: [agent-name]
- Objective: [goal]
- Files: [list]
- Constraints: [requirements]

Step 2: [Task]
- Agent: [agent-name]
- Dependencies: Step 1
...

### Validation Checkpoints
- [ ] Performance maintained
- [ ] Tests passing
- [ ] Documentation updated

Proceeding with execution...
```

### 2. Completion Report
```markdown
## Task Completion Report

### Steps Completed
1. ✅ Step 1 (agent-name)
2. ✅ Step 2 (agent-name)

### Validation Results
- ✅ Performance: [X]ms (budget: [Y]ms)
- ✅ Coverage: [X]% (target: 80%+)

### Files Modified
- src/[file].py - [description]

### Performance Impact
- Component latency: [X]ms
- End-to-end: [X]ms (no regression ✅)

### Next Steps
1. [Recommendation]
```

### 3. Next Steps Recommendation
```markdown
## Current Phase Analysis
Current: [Phase/Week/Task]
Completion: [X/Y tasks]

## Recommended Next Steps

Option A: [Description]
- Task 1 (agent)
- Task 2 (agent)

Option B: [Alternative]
- Task 1 (agent)

My Recommendation: [A/B with justification]

Shall I proceed?
```

---

## Advanced Features

### Parallel Agent Execution
The orchestrator can run independent tasks in parallel:

```
Track A (Backend):
├─ Extract component (refactor-agent)
├─ Write tests (test-engineer)

Track B (Frontend):
├─ Build UI card (ui-builder)
└─ Write UI tests (test-engineer)

Track C (Docs):
└─ Update docs (doc-writer)

Merge: Integration testing
```

### Progressive Refinement
For complex features:

```
1. Build minimal version
2. Add basic tests
3. Get user feedback
4. Refine implementation
5. Add comprehensive tests
6. Optimize performance
7. Polish UI
8. Complete documentation
```

### Risk-First Approach
Tackles high-risk items early:

```
1. Identify technical risks
2. Prototype risky component
3. Measure and validate
4. If viable → full implementation
5. If not → alternative approach
```

---

## Tips for Working with the Orchestrator

### 1. Be Clear About Intent
Good:
- ✅ "Extract the Whisper component"
- ✅ "Add noise reduction"
- ✅ "Start Phase 1"

Less Clear:
- ❌ "Fix the audio"
- ❌ "Make it better"
- ❌ "Do something with the server"

### 2. Trust the Process
The orchestrator will:
- Break tasks into proper steps
- Add tests automatically
- Validate performance
- Update documentation

You don't need to specify these - it knows to do them.

### 3. Provide Feedback
If an agent output isn't right:
- Point out the specific issue
- The orchestrator will correct it
- Example: "The refactor-agent didn't add feature flags"

### 4. Ask for Recommendations
When unsure what's next:
- "What should we work on next?"
- "Is Phase 1 complete?"
- "What are the priorities?"

### 5. Override When Needed
If you want a different approach:
- "Skip the UI changes for now"
- "Use OpenAI instead of Ollama"
- "Focus on performance first"

---

## Troubleshooting

### Orchestrator Seems Confused
**Issue**: Orchestrator doesn't understand the request

**Solution**: Be more specific
- Reference roadmap phase: "Let's do Phase 1, Week 2"
- Reference component: "Extract the LLM analyzer"
- Reference goal: "Optimize transcription latency"

### Agent Keeps Failing Validation
**Issue**: Same validation error multiple times

**Solution**: The orchestrator will recognize this and ask for your guidance
- Provide more context about requirements
- Suggest a different approach
- Break into smaller tasks

### Task Taking Too Long
**Issue**: Workflow seems stuck

**Solution**: Ask for status
- "What's the current status?"
- "Which step are you on?"
- "Can we skip [step] and continue?"

### Want to Skip Steps
**Issue**: Don't need all the steps

**Solution**: Be explicit
- "Extract the component but skip the UI changes"
- "Add noise reduction without updating the UI for now"
- "Focus on backend only"

---

## Comparison: Orchestrator vs Direct Agent Use

### When to Use Orchestrator

✅ **Complex multi-step tasks**
- Example: "Extract the Whisper component" (refactor → test → validate → document)

✅ **Phase-level work**
- Example: "Start Phase 1" (multiple weeks, many tasks)

✅ **Uncertain what's next**
- Example: "What should we work on?" (intelligent recommendations)

✅ **Need validation and correction**
- Example: Ensures feature flags, tests, performance checks

### When to Use Direct Agent

✅ **Simple, single-agent tasks**
- Example: "Write tests for the audio buffer" → test-engineer directly

✅ **Quick edits**
- Example: "Update the README" → doc-writer directly

✅ **Specialist work**
- Example: "Profile the transcription pipeline" → performance-agent directly

---

## Example Workflows

### Full Phase 1 Workflow

```
User: "I'm ready to start Phase 1"

Orchestrator:
1. Week 1: Logging & Config
   - config-architect: Create logging system
   - config-architect: Create config management
   - test-engineer: Write tests
   - doc-writer: Document

2. Week 2: State & Errors
   - refactor-agent: Extract state management
   - config-architect: Create error hierarchy
   - test-engineer: Write tests

3. Week 3: Component Extraction
   - refactor-agent: Extract Whisper
   - refactor-agent: Extract LLM
   - refactor-agent: Extract WebSocket
   - test-engineer: Write all tests
   - performance-agent: Validate no regression

4. Week 4: Migration
   - plugin-builder: Create feature flags
   - refactor-agent: Update entry points
   - test-engineer: Integration tests
   - doc-writer: Update docs

Validation: Performance <4s, coverage >80%, docs complete
```

### Single Feature Workflow

```
User: "Add speaker detection"

Orchestrator:
1. Prerequisites check
   - Verify AudioProcessorProtocol exists
   - Check if pyannote.audio is available

2. Implementation
   - audio-specialist: Implement speaker detection
   - plugin-builder: Create SpeakerDetectionPlugin

3. Testing
   - test-engineer: Unit tests (accuracy, latency)
   - test-engineer: Integration tests (multi-speaker audio)

4. Performance validation
   - performance-agent: Verify <200ms latency
   - performance-agent: Verify >80% accuracy

5. UI integration
   - ui-builder: Add speaker labels to TranscriptCard
   - ui-builder: Add speaker filtering/renaming

6. Documentation
   - doc-writer: Document speaker detection
   - doc-writer: Add to feature guide

Validation: Latency <200ms, accuracy >80%, end-to-end <4s maintained
```

---

## Summary

The Orchestrator Agent is your **intelligent development coordinator** that:

### Automates
- Task decomposition
- Agent selection
- Quality validation
- Progress tracking

### Enforces
- Performance budgets (<4s end-to-end)
- Test coverage (80%+)
- Backward compatibility
- Security validation
- Documentation updates

### Optimizes
- Context usage (60-70% reduction)
- Development speed (parallel execution)
- Code quality (validation standards)
- Workflow efficiency (right agent for right task)

### Start Using It

**Simple start:**
```
I'm ready to begin Phase 1
```

**Feature request:**
```
Add noise reduction to improve audio quality
```

**Get guidance:**
```
What should we work on next?
```

The orchestrator will handle the complexity - you just focus on the goals.

---

## Next Steps

1. **Try it**: Start with a simple request like "What should we work on next?"
2. **Learn**: Observe how it breaks down tasks
3. **Refine**: Provide feedback when outputs aren't quite right
4. **Scale**: Use for increasingly complex workflows

The orchestrator learns from your project patterns and gets better over time.

Happy building! 🚀
