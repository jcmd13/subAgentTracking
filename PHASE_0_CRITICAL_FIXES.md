# SubAgent Control System - Critical Bug Fix Addendum

**Version:** 1.0.1  
**Updated:** 2025-12-06  
**Status:** BLOCKING - Must complete before Phase 1

---

## Code Review Summary

An independent deep inspection of the codebase revealed **18 issues** that must be addressed:

| Severity | Count | Status |
|----------|-------|--------|
| **Critical (Blocker)** | 3 | Must fix before ANY new development |
| **High Priority** | 4 | Must fix before Phase 1 |
| **Medium Priority** | 4 | Fix during Phase 0 |
| **Design Issues** | 5 | Address in Phase 0-1 |
| **Long-term** | 5 | Track for future phases |

**Assessment:** The core is 70% complete for MVP, but 3 critical blockers prevent immediate use. The backup feature is completely non-functional.

---

## Phase 0: Critical Bug Fixes (BLOCKING)

**This phase must complete before ANY new feature development.**

### 0.1 Critical Issues (System Non-Functional Without These)

#### Task 0.1.1: Fix BackupManager Missing Methods
**Severity:** CRITICAL  
**Location:** `src/core/backup_manager.py`  
**Impact:** Any automatic backup trigger crashes with `AttributeError`. Entire backup feature non-functional.

**Problem:**  
`backup_integration.py` calls three methods that don't exist:
```python
# backup_integration.py:112 - Called but doesn't exist
manager.is_available()

# backup_integration.py:129 - Called but doesn't exist  
manager.authenticate()

# backup_integration.py:145 - Called but doesn't exist
manager.backup_session(session_id=..., phase=..., compress=...)
```

**What exists:** `upload_file()`, `upload_activity_log()`, `upload_snapshots()`, `test_connection()` - but not the high-level session backup API.

**Fix Required:**
```python
# Add to BackupManager class in backup_manager.py

def is_available(self) -> bool:
    """Check if Google Drive backup is configured and accessible."""
    if not self.enabled:
        return False
    try:
        return self.test_connection()
    except Exception:
        return False

def authenticate(self) -> bool:
    """
    Authenticate with Google Drive.
    Returns True if authentication successful.
    """
    if not self.enabled:
        return False
    try:
        self._get_credentials()
        return True
    except Exception as e:
        import sys
        print(f"Authentication failed: {e}", file=sys.stderr)
        return False

def backup_session(
    self,
    session_id: str,
    phase: str = "checkpoint",
    compress: bool = True
) -> Optional[str]:
    """
    Backup an entire session including logs and snapshots.
    
    Args:
        session_id: The session identifier
        phase: Backup phase (checkpoint, shutdown, error)
        compress: Whether to compress files before upload
        
    Returns:
        Backup ID if successful, None otherwise
    """
    if not self.is_available():
        return None
        
    backup_id = f"backup_{session_id}_{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Upload activity log
        log_file = self.config.log_dir / f"{session_id}.jsonl"
        if log_file.exists():
            self.upload_activity_log(str(log_file), compress=compress)
        
        # Upload snapshots
        snapshot_dir = self.config.snapshot_dir / session_id
        if snapshot_dir.exists():
            self.upload_snapshots(str(snapshot_dir), compress=compress)
            
        return backup_id
    except Exception as e:
        import sys
        print(f"Session backup failed: {e}", file=sys.stderr)
        return None
```

**Acceptance Criteria:**
- [ ] `is_available()` returns `False` when not configured, `True` when ready
- [ ] `authenticate()` returns `True` after successful auth
- [ ] `backup_session()` uploads logs and snapshots
- [ ] `backup_on_shutdown()` in backup_integration.py works without crashing
- [ ] Unit tests added for all three methods

**Estimated Effort:** 4 hours

---

#### Task 0.1.2: Fix Deprecated datetime.utcnow()
**Severity:** CRITICAL  
**Location:** `src/core/snapshot_manager.py` lines 236, 248, 470, 526  
**Impact:** Python 3.12+ incompatibility. Will break on newer Python versions.

**Problem:**
```python
# DEPRECATED - will be removed in future Python
timestamp = datetime.utcnow().isoformat() + "Z"
```

**Note:** `activity_logger.py` correctly uses `datetime.now(timezone.utc)` (line 115), showing inconsistency.

**Fix Required:**
```python
# Replace all occurrences of:
datetime.utcnow()

# With:
from datetime import datetime, timezone
datetime.now(timezone.utc)

# For ISO format strings:
datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
```

**Files to Update:**
- `src/core/snapshot_manager.py` (4 occurrences)
- Search entire codebase for other occurrences: `grep -r "utcnow" src/`

**Acceptance Criteria:**
- [ ] No occurrences of `utcnow()` in codebase
- [ ] All datetime operations use timezone-aware objects
- [ ] Tests pass on Python 3.12+

**Estimated Effort:** 1 hour

---

#### Task 0.1.3: Fix Thread Safety on Global State
**Severity:** CRITICAL  
**Location:** `src/core/activity_logger.py` line 253  
**Impact:** Race conditions under concurrent agent invocations. Data corruption possible.

**Problem:**
```python
_parent_event_stack: List[str] = []  # Global list without synchronization
```

This is accessed from multiple context managers without thread protection:
- `tool_usage_context()` (lines 1214-1215, 1241-1245)
- `agent_invocation_context()` (lines 1278, 1284-1285)
- `log_agent_invocation()` (line 678)
- `log_tool_usage()` (line 754)

**Fix Required:**
```python
import threading
from contextlib import contextmanager
from typing import List, Optional
import contextvars

# Option A: Thread-local storage (simpler)
_parent_event_local = threading.local()

def _get_parent_stack() -> List[str]:
    if not hasattr(_parent_event_local, 'stack'):
        _parent_event_local.stack = []
    return _parent_event_local.stack

def _push_parent_event(event_id: str) -> None:
    _get_parent_stack().append(event_id)

def _pop_parent_event() -> Optional[str]:
    stack = _get_parent_stack()
    return stack.pop() if stack else None

def _current_parent_event() -> Optional[str]:
    stack = _get_parent_stack()
    return stack[-1] if stack else None

# Option B: ContextVars (better for async, Python 3.7+)
_parent_event_var: contextvars.ContextVar[List[str]] = contextvars.ContextVar(
    'parent_event_stack', 
    default=[]
)

def _get_parent_stack() -> List[str]:
    stack = _parent_event_var.get()
    if stack is _parent_event_var.get():  # Check if we got the default
        stack = []
        _parent_event_var.set(stack)
    return stack
```

**Recommendation:** Use Option B (ContextVars) for async compatibility.

**Acceptance Criteria:**
- [ ] Parent event stack is thread-safe
- [ ] Concurrent context managers don't interfere
- [ ] Test with multi-threaded agent invocations
- [ ] No race conditions under load

**Estimated Effort:** 3 hours

---

### 0.2 High Priority Issues (Fix Before Phase 1)

#### Task 0.2.1: Improve Exception Handling
**Severity:** HIGH  
**Location:** Multiple locations in `src/core/activity_logger.py`  
**Impact:** Operational blindspots - failures go unnoticed.

**Problem Areas:**
```python
# Line 206-210: Logs to stderr but continues
except Exception as e:
    import sys
    print(f"Error writing event: {e}", file=sys.stderr)

# Line 221-222: Silently breaks out of loop
except Exception:
    break

# Line 549-554: Catches ImportError/Exception, continues silently
except ImportError:
    pass
except Exception:
    pass
```

**Fix Required:**
1. Create custom exception hierarchy
2. Use structured logging instead of print statements
3. Emit events when errors occur (meta-logging)
4. Never silently swallow exceptions in production paths

```python
# src/core/exceptions.py (new file)

class SubAgentError(Exception):
    """Base exception for all SubAgent errors."""
    pass

class LogWriteError(SubAgentError):
    """Failed to write to activity log."""
    pass

class SnapshotError(SubAgentError):
    """Failed to create or restore snapshot."""
    pass

class BackupError(SubAgentError):
    """Failed to backup to remote storage."""
    pass

class ValidationError(SubAgentError):
    """Event validation failed."""
    pass

class ConfigurationError(SubAgentError):
    """Invalid configuration."""
    pass
```

**Acceptance Criteria:**
- [ ] Custom exception hierarchy created
- [ ] No bare `except Exception` without re-raise or logging
- [ ] Errors logged to activity log (when possible)
- [ ] Caller can distinguish error types

**Estimated Effort:** 4 hours

---

#### Task 0.2.2: Make Token Budget Configurable
**Severity:** HIGH  
**Location:** `src/core/snapshot_manager.py` line 272  
**Impact:** Hardcoded value cannot be adjusted without code change.

**Problem:**
```python
"tokens_total": 200000,  # Default budget - HARDCODED
```

**Fix Required:**
```python
# Use config system that already exists
from src.core.config import get_config

config = get_config()
"tokens_total": config.get("default_token_budget", 200000),
```

**Also add to config.py:**
```python
# In SubAgentConfig class
default_token_budget: int = 200000
```

**Acceptance Criteria:**
- [ ] Token budget read from config
- [ ] Can be overridden via environment variable
- [ ] Default still works if not specified

**Estimated Effort:** 30 minutes

---

#### Task 0.2.3: Fix ValidationEvent Type Mismatch
**Severity:** HIGH  
**Location:** `src/core/schemas.py:322` vs `src/core/activity_logger.py:1153`  
**Impact:** Case sensitivity issues ("pass" vs "PASS") break validation.

**Problem:**
```python
# Schema expects:
checks: Dict[str, ValidationStatus]  # Enum values

# But log_validation() accepts:
checks: Dict[str, str]  # Arbitrary strings
```

**Fix Required:**
```python
# In activity_logger.py log_validation():

def log_validation(
    validation_type: str,
    target: str,
    passed: bool,
    checks: Dict[str, str],  # Accept strings
    details: Optional[Dict[str, Any]] = None
) -> str:
    # Normalize check values to ValidationStatus
    normalized_checks = {}
    for key, value in checks.items():
        value_upper = str(value).upper()
        if value_upper in ("PASS", "PASSED", "TRUE", "1"):
            normalized_checks[key] = ValidationStatus.PASS
        elif value_upper in ("FAIL", "FAILED", "FALSE", "0"):
            normalized_checks[key] = ValidationStatus.FAIL
        elif value_upper in ("SKIP", "SKIPPED", "NA", "N/A"):
            normalized_checks[key] = ValidationStatus.SKIP
        elif value_upper in ("WARN", "WARNING"):
            normalized_checks[key] = ValidationStatus.WARN
        else:
            normalized_checks[key] = ValidationStatus.UNKNOWN
    # ... rest of function uses normalized_checks
```

**Acceptance Criteria:**
- [ ] Any reasonable string input normalized to enum
- [ ] Case-insensitive matching
- [ ] Unknown values mapped to UNKNOWN status
- [ ] Schema validation passes

**Estimated Effort:** 1 hour

---

#### Task 0.2.4: Fix Session Duration Timezone Bug
**Severity:** HIGH  
**Location:** `src/core/snapshot_manager.py` lines 243-249  
**Impact:** Duration calculation wrong on non-UTC systems.

**Problem:**
```python
if session_id.startswith("session_"):
    date_str = session_id.replace("session_", "")
    start_dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")  # Naive datetime
    now_dt = datetime.utcnow()  # UTC datetime
    elapsed_time_seconds = int((now_dt - start_dt).total_seconds())  # WRONG!
```

`strptime` creates naive datetime (local time), but `utcnow()` is UTC.

**Fix Required:**
```python
from datetime import datetime, timezone

if session_id.startswith("session_"):
    date_str = session_id.replace("session_", "")
    # Parse as UTC (session IDs should be created in UTC)
    start_dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    elapsed_time_seconds = int((now_dt - start_dt).total_seconds())
```

**Also:** Ensure session IDs are created using UTC timestamps.

**Acceptance Criteria:**
- [ ] Duration correct regardless of system timezone
- [ ] All session ID timestamps use UTC
- [ ] Test on system with non-UTC timezone

**Estimated Effort:** 1 hour

---

### 0.3 Medium Priority Issues (Fix During Phase 0)

#### Task 0.3.1: Fix Schema Validation Bypass
**Severity:** MEDIUM  
**Location:** `src/core/activity_logger.py` lines 610-623  
**Impact:** Invalid events written to log, break analytics later.

**Problem:**
```python
if config.validate_event_schemas:
    try:
        validated_event = validate_event(event)
        event = serialize_event(validated_event)
    except Exception as e:
        error_msg = f"Pydantic validation failed: {str(e)}"
        if config.strict_mode:
            raise ValueError(error_msg)
        else:
            print(f"Warning: {error_msg}", file=sys.stderr)
            # Event STILL gets written even if validation fails!
```

**Fix Required:**
```python
if config.validate_event_schemas:
    try:
        validated_event = validate_event(event)
        event = serialize_event(validated_event)
    except Exception as e:
        error_msg = f"Pydantic validation failed: {str(e)}"
        if config.strict_mode:
            raise ValueError(error_msg)
        else:
            # Log warning but DO NOT write invalid event
            import sys
            print(f"Warning: {error_msg} - Event discarded", file=sys.stderr)
            return None  # Or return a special "invalid event" marker
```

**Acceptance Criteria:**
- [ ] Invalid events never written to log
- [ ] Warning logged when event discarded
- [ ] Return value indicates success/failure

**Estimated Effort:** 30 minutes

---

#### Task 0.3.2: Make File Operations Atomic
**Severity:** MEDIUM  
**Location:** `src/core/backup_manager.py` lines 59-60  
**Impact:** Credential file corruption on crash.

**Problem:**
```python
with open(token_path, "w") as token:
    token.write(creds.to_json())
# If crash happens mid-write, file is corrupted
```

**Fix Required:**
```python
import tempfile
import os

def atomic_write(path: Path, content: str) -> None:
    """Write file atomically using temp file + rename."""
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    try:
        with os.fdopen(temp_fd, 'w') as f:
            f.write(content)
        os.rename(temp_path, path)  # Atomic on POSIX
    except Exception:
        os.unlink(temp_path)  # Clean up temp file
        raise

# Usage:
atomic_write(token_path, creds.to_json())
```

**Acceptance Criteria:**
- [ ] Credential writes are atomic
- [ ] No partial files on crash
- [ ] Works on macOS and Linux

**Estimated Effort:** 1 hour

---

#### Task 0.3.3: Add Retry on Snapshot Write Failure
**Severity:** MEDIUM  
**Location:** `src/core/snapshot_manager.py` lines 301-305  
**Impact:** Returns snapshot ID even when write failed.

**Problem:**
```python
except Exception as e:
    import sys
    print(f"Error writing snapshot {snapshot_id}: {e}", file=sys.stderr)
    return snapshot_id  # Returns ID even if write FAILED!
```

**Fix Required:**
```python
import time

MAX_RETRIES = 3
RETRY_DELAY = 0.1  # seconds

for attempt in range(MAX_RETRIES):
    try:
        # Write snapshot
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        return snapshot_id  # Success
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
            continue
        else:
            import sys
            print(f"Error writing snapshot {snapshot_id} after {MAX_RETRIES} attempts: {e}", file=sys.stderr)
            return None  # Indicate failure

# Or raise exception instead of returning None
raise SnapshotError(f"Failed to write snapshot {snapshot_id}")
```

**Acceptance Criteria:**
- [ ] Retries on transient failures
- [ ] Returns `None` or raises on permanent failure
- [ ] Caller can distinguish success from failure

**Estimated Effort:** 1 hour

---

#### Task 0.3.4: Expand Event ID Format
**Severity:** MEDIUM  
**Location:** `src/core/activity_logger.py` line 84  
**Impact:** At 1000 events, format breaks (`evt_1000` vs `evt_001`).

**Problem:**
```python
return f"evt_{self._counter:03d}"  # Only 3 digits
```

**Fix Required:**
```python
return f"evt_{self._counter:06d}"  # 6 digits: evt_000001 to evt_999999
```

Or use variable width with session prefix:
```python
return f"evt_{session_id}_{self._counter}"
```

**Acceptance Criteria:**
- [ ] Event IDs unique across long sessions
- [ ] Format consistent for sorting
- [ ] No collision on counter overflow

**Estimated Effort:** 15 minutes

---

#### Newly Discovered (Tests - 2025-12-08)

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 0.3.5 | Align Event bus defaults with realtime monitor fixtures (auto timestamp/trace/session defaults) | 0.5h | ✅ |
| 0.3.6 | Make error/context snapshot logging backward compatible (`message` alias, optional context, emit tokens budget in snapshots) | 1h | ⬜ |
| 0.3.7 | Bring BackupManager to test parity (GOOGLE_DRIVE_AVAILABLE gating, archive naming with activity.jsonl, list/find/upload/download stubs) | 3h | ⬜ |
| 0.3.8 | Harden realtime monitor server start under sandboxed/multi-agent runs (safe ports, graceful skip without network) | 2h | ⬜ |
| 0.3.9 | Normalize event type registry count to expected 20 (or reconcile spec/tests) | 0.5h | ⬜ |
| 0.3.10 | Mark async/smoke/LLM tests to assert instead of returning bool to avoid pytest warnings | 0.5h | ⬜ |

---

### 0.4 Design Issues (Address in Phase 0-1)

#### Task 0.4.1: Persist Snapshot Counter
**Severity:** DESIGN  
**Location:** `src/core/snapshot_manager.py` line 44  
**Impact:** Duplicate snapshot IDs on process restart.

**Problem:**
```python
_snapshot_counter: int = 0  # Resets on every process restart
```

**Fix Required:**
```python
import json

COUNTER_FILE = ".subagent/state/counters.json"

def _load_counters() -> dict:
    if Path(COUNTER_FILE).exists():
        with open(COUNTER_FILE) as f:
            return json.load(f)
    return {"snapshot": 0, "event": 0}

def _save_counters(counters: dict) -> None:
    Path(COUNTER_FILE).parent.mkdir(parents=True, exist_ok=True)
    atomic_write(Path(COUNTER_FILE), json.dumps(counters))

def _next_snapshot_id() -> str:
    counters = _load_counters()
    counters["snapshot"] += 1
    _save_counters(counters)
    return f"snap_{counters['snapshot']:06d}"
```

**Acceptance Criteria:**
- [ ] Counter persists across restarts
- [ ] No duplicate IDs within a project
- [ ] Counter file uses atomic writes

**Estimated Effort:** 2 hours

---

#### Task 0.4.2: Refactor Circular Dependencies
**Severity:** DESIGN  
**Location:** Multiple files  
**Impact:** Fragile imports, hard to refactor.

**Problem:**
```python
# snapshot_manager.py imports from activity_logger
from src.core import activity_logger

# activity_logger.py shutdown() imports backup_integration
from src.core.backup_integration import backup_on_shutdown

# backup_integration.py imports from activity_logger
from src.core import activity_logger
```

**Fix Required:**
1. Create interface/protocol layer
2. Use dependency injection
3. Late imports only where absolutely necessary

```python
# src/core/interfaces.py (new file)
from typing import Protocol

class Logger(Protocol):
    def log_event(self, event_type: str, data: dict) -> str: ...

class BackupProvider(Protocol):
    def backup_session(self, session_id: str) -> Optional[str]: ...

# Then each module depends on interfaces, not implementations
```

**Acceptance Criteria:**
- [ ] No circular imports
- [ ] Components can be tested in isolation
- [ ] Clear dependency graph

**Estimated Effort:** 4 hours

---

#### Task 0.4.3: Thread-Safe Shutdown
**Severity:** DESIGN  
**Location:** `src/core/activity_logger.py` lines 495-529  
**Impact:** Race condition on shutdown.

**Problem:**
```python
global _writer, _session_id, _event_counter, _initialized

with _init_lock:
    if _initialized:
        return
    # ... setup code ...
    _initialized = True

# But shutdown() doesn't use the lock!
def shutdown():
    global _initialized
    _initialized = False  # No lock!
```

**Fix Required:**
```python
def shutdown():
    global _writer, _session_id, _event_counter, _initialized
    
    with _init_lock:  # Use the same lock
        if not _initialized:
            return
            
        # ... cleanup code ...
        
        _initialized = False
```

**Acceptance Criteria:**
- [ ] Shutdown protected by same lock as init
- [ ] No race between init and shutdown
- [ ] Clean shutdown under concurrent access

**Estimated Effort:** 30 minutes

---

### 0.5 Long-Term Tracking (Future Phases)

These issues should be tracked but don't block MVP:

| Issue | Description | Target Phase |
|-------|-------------|--------------|
| Single-file logs | 50k+ events = slow queries | Phase 4 |
| No schema versioning | Breaking changes hard | Phase 4 |
| Test isolation | Global singletons hurt testing | Phase 0 (partial) |
| No rate limiting | High-frequency events overwhelm | Phase 4 |
| No internal observability | Can't monitor the monitor | Phase 8 |

---

## Updated Phase 0 Task List

### Week 1: Critical Bug Fixes

| Day | Task | Est. Hours |
|-----|------|------------|
| 1 | 0.1.1: BackupManager missing methods | 4 |
| 1 | 0.1.2: Fix datetime.utcnow() | 1 |
| 2 | 0.1.3: Thread safety on global state | 3 |
| 2 | 0.2.1: Exception hierarchy | 4 |
| 3 | 0.2.2: Configurable token budget | 0.5 |
| 3 | 0.2.3: ValidationEvent type mismatch | 1 |
| 3 | 0.2.4: Session duration timezone bug | 1 |
| 3 | 0.3.1: Schema validation bypass | 0.5 |
| 4 | 0.3.2: Atomic file operations | 1 |
| 4 | 0.3.3: Snapshot write retry | 1 |
| 4 | 0.3.4: Event ID format | 0.25 |
| 4 | 0.4.1: Persist snapshot counter | 2 |
| 5 | 0.4.2: Refactor circular dependencies | 4 |
| 5 | 0.4.3: Thread-safe shutdown | 0.5 |
| 5 | Run full test suite, fix any regressions | 4 |

**Total: ~28 hours (1 developer-week)**

### Week 1 Exit Criteria

- [ ] All 3 critical issues fixed and tested
- [ ] All 4 high priority issues fixed and tested
- [ ] All 4 medium priority issues fixed and tested
- [ ] Full test suite passes (631+ tests)
- [ ] Smoke test passes
- [ ] No `utcnow()` in codebase
- [ ] No bare `except Exception:` without logging
- [ ] BackupManager fully functional
- [ ] Clean install on fresh machine works

---

## Testing Requirements for Bug Fixes

### New Test Cases Required

```python
# tests/test_backup_manager.py - ADD

def test_is_available_when_not_configured():
    """is_available returns False when backup not enabled."""
    
def test_is_available_when_configured():
    """is_available returns True when backup enabled and working."""
    
def test_authenticate_success():
    """authenticate returns True after successful auth."""
    
def test_authenticate_failure():
    """authenticate returns False on auth failure."""
    
def test_backup_session_uploads_logs():
    """backup_session uploads activity logs."""
    
def test_backup_session_uploads_snapshots():
    """backup_session uploads all snapshots."""

# tests/test_thread_safety.py - NEW

def test_concurrent_tool_contexts():
    """Multiple tool_usage_context() calls don't interfere."""
    
def test_concurrent_agent_contexts():
    """Multiple agent_invocation_context() calls don't interfere."""
    
def test_concurrent_init_shutdown():
    """init() and shutdown() don't race."""

# tests/test_validation.py - ADD

def test_validation_status_normalization():
    """Various string inputs normalized to ValidationStatus."""
    
def test_validation_case_insensitive():
    """'pass', 'PASS', 'Pass' all become ValidationStatus.PASS."""

# tests/test_timezone.py - NEW

def test_session_duration_utc():
    """Session duration correct regardless of system timezone."""

def test_timestamps_always_utc():
    """All generated timestamps are UTC."""
```

---

## Verification Commands

After completing Phase 0, run these commands to verify:

```bash
# 1. Check for deprecated datetime usage
grep -r "utcnow" src/
# Should return nothing

# 2. Check for bare exception handlers
grep -r "except Exception:" src/ | grep -v "# OK"
# Review each occurrence

# 3. Run full test suite
python -m pytest tests/ -v --tb=short

# 4. Run smoke test
python smoke_test.py

# 5. Check for circular imports
python -c "from src.core import activity_logger, snapshot_manager, backup_manager"
# Should not hang or error

# 6. Verify backup works
python -c "
from src.core.backup_manager import BackupManager
bm = BackupManager()
print('is_available:', bm.is_available())
"

# 7. Test thread safety under load
python -c "
import threading
from src.core.activity_logger import tool_usage_context, log_tool_usage

def worker(n):
    for i in range(100):
        with tool_usage_context(f'tool_{n}', f'target_{i}'):
            pass

threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
for t in threads: t.start()
for t in threads: t.join()
print('Thread safety test passed')
"
```

---

## Multi-Agent Stability Notes (Uncoordinated AIs)

- Run smoke/tests sequentially; avoid concurrent realtime monitor servers on the same port (use ephemeral ports or skip when network unavailable).
- Share the same virtualenv across agents; record any new dependencies in `requirements.txt` before parallel work resumes.
- Prefer compatibility helpers (Event defaults, tolerant logging APIs) so fixtures from different agents interoperate cleanly.
- When sandboxed ports/files are blocked, switch components to no-op or skip mode rather than hard failing.
- Log new incompatibilities in the Phase 0 table (0.3.x) before handing off to another agent.

---

## Summary

**Before this code review:** "631 tests pass, ready for Phase 1"

**After this code review:** "18 issues found, 3 critical blockers, 1 week of fixes required"

The test suite tested what was built, not what was needed. The backup feature was completely broken despite "passing tests" because the tests didn't exercise the integration path.

**Lesson:** Tests passing ≠ system working. Integration tests and manual verification are essential.

---

*This addendum becomes Part 0 of the implementation plan. No work on Phase 1 should begin until all items in this document are resolved and verified.*
