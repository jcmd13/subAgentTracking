/**
 * SubAgent Tracking Dashboard - Real-Time WebSocket Client
 *
 * Connects to RealtimeMonitor WebSocket server and displays live metrics,
 * event stream, and workflow visualizations.
 *
 * Links Back To: Main Plan → Phase 3 → Task 3.2
 */

// ============================================================================
// Configuration & State
// ============================================================================

const DEFAULT_CONFIG = {
    wsHost: 'localhost',
    wsPort: 8765,
    reconnectDelay: 3000,
    maxEvents: 100,
    autoReconnect: true,
    showTimestamps: true,
    windowSize: 300  // Default to 5 minutes
};

let config = { ...DEFAULT_CONFIG };
let ws = null;
let reconnectTimer = null;
let isPaused = false;
let eventBuffer = [];
let metricsHistory = {
    timestamps: [],
    eventRates: [],
    maxPoints: 60  // Last 60 seconds
};

let approvalsState = {
    approvals: [],
    lastUpdated: null
};

let approvalsTimer = null;

let taskState = {
    taskId: null,
    taskName: 'No active task',
    stage: '--',
    status: 'Idle',
    updatedAt: null,
    progressPct: null
};

let lastTest = {
    status: 'Not run',
    summary: '--',
    updatedAt: null
};

let sessionSummary = {
    summaryType: 'start',
    summaryText: 'No summary yet.'
};

// Chart instances
let eventRateChart = null;
let eventTypeChart = null;
let performanceChart = null;

// ============================================================================
// WebSocket Connection Management
// ============================================================================

function connect() {
    const wsUrl = `ws://${config.wsHost}:${config.wsPort}`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = handleOpen;
        ws.onmessage = handleMessage;
        ws.onerror = handleError;
        ws.onclose = handleClose;

        updateConnectionStatus('connecting', 'Connecting...');
    } catch (error) {
        console.error('WebSocket connection error:', error);
        updateConnectionStatus('error', 'Connection failed');
        scheduleReconnect();
    }
}

function disconnect() {
    if (ws) {
        ws.close();
        ws = null;
    }
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
}

function scheduleReconnect() {
    if (!config.autoReconnect) return;

    if (reconnectTimer) clearTimeout(reconnectTimer);

    reconnectTimer = setTimeout(() => {
        console.log('Attempting reconnect...');
        connect();
    }, config.reconnectDelay);
}

// ============================================================================
// WebSocket Event Handlers
// ============================================================================

function handleOpen(event) {
    console.log('WebSocket connected');
    updateConnectionStatus('connected', 'Connected');
    showToast('Connected to monitoring server', 'success');

    // Subscribe to all events (no filters)
    const subscribeMsg = {
        type: 'subscribe',
        filters: []
    };
    ws.send(JSON.stringify(subscribeMsg));

    fetchApprovals();
    if (!approvalsTimer) {
        approvalsTimer = setInterval(fetchApprovals, 5000);
    }
}

function handleMessage(event) {
    if (isPaused) return;

    try {
        const data = JSON.parse(event.data);

        if (data.type === 'event') {
            const eventPayload = data.event || {
                event_type: data.event_type,
                timestamp: data.timestamp,
                payload: data.payload || {},
                metadata: data.metadata || {}
            };
            handleEventMessage(eventPayload);
        } else if (data.type === 'metrics') {
            handleMetricsMessage(data.metrics);
        } else if (data.type === 'error') {
            console.error('Server error:', data.message);
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('Message parsing error:', error);
    }
}

function handleError(error) {
    console.error('WebSocket error:', error);
    updateConnectionStatus('error', 'Connection error');
}

function handleClose(event) {
    console.log('WebSocket closed:', event.code, event.reason);
    updateConnectionStatus('disconnected', 'Disconnected');

    if (approvalsTimer) {
        clearInterval(approvalsTimer);
        approvalsTimer = null;
    }

    if (event.code !== 1000) {  // Not a normal closure
        showToast('Connection lost. Reconnecting...', 'warning');
        scheduleReconnect();
    }
}

// ============================================================================
// Message Handlers
// ============================================================================

function handleEventMessage(event) {
    const normalized = normalizeEvent(event);

    updateTaskFromEvent(normalized);
    updateTestFromEvent(normalized);
    updateSessionSummaryFromEvent(normalized);
    if (normalized.event_type && normalized.event_type.startsWith('approval.')) {
        fetchApprovals();
    }

    // Add to event buffer
    eventBuffer.unshift(normalized);
    if (eventBuffer.length > config.maxEvents) {
        eventBuffer.pop();
    }

    // Apply filters
    const eventTypeFilter = document.getElementById('eventTypeFilter').value;
    const agentFilter = document.getElementById('agentFilter').value.toLowerCase();

    if (eventTypeFilter && normalized.event_type !== eventTypeFilter) return;
    if (agentFilter && !JSON.stringify(normalized).toLowerCase().includes(agentFilter)) return;

    // Add to stream
    addEventToStream(normalized);

    // Update metrics history for event rate chart
    updateMetricsHistory();
}

function handleMetricsMessage(metrics) {
    updateMetricsDisplay(metrics);
}

// ============================================================================
// UI Updates
// ============================================================================

function updateConnectionStatus(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('connectionStatus');
    const pauseBtn = document.getElementById('pauseBtn');

    indicator.className = `status-indicator status-${status}`;
    statusText.textContent = text;

    // Enable/disable pause button
    pauseBtn.disabled = status !== 'connected';
}

function updateMetricsDisplay(metrics) {
    // Update metric cards
    document.getElementById('eventsPerSec').textContent =
        metrics.events_per_second?.toFixed(2) || '0.0';
    document.getElementById('activeAgents').textContent =
        metrics.agents_active || 0;
    document.getElementById('agentsPerMin').textContent =
        metrics.agents_per_minute?.toFixed(2) || '0.0';
    document.getElementById('activeWorkflows').textContent =
        metrics.workflows_active || 0;
    document.getElementById('activeTasks').textContent =
        metrics.tasks_active || 0;
    const progressAvg = metrics.task_progress_avg;
    document.getElementById('taskProgressAvg').textContent =
        progressAvg != null ? `${progressAvg.toFixed(1)}%` : '0%';
    document.getElementById('testsPassFail').textContent =
        `${metrics.tests_passed || 0} / ${metrics.tests_failed || 0}`;
    document.getElementById('totalTokens').textContent =
        (metrics.total_tokens || 0).toLocaleString();
    document.getElementById('totalCost').textContent =
        `$${(metrics.total_cost || 0).toFixed(4)}`;
    document.getElementById('avgDuration').textContent =
        Math.round(metrics.avg_agent_duration_ms || 0);
    document.getElementById('p95Duration').textContent =
        Math.round(metrics.p95_agent_duration_ms || 0);

    // Update charts
    updateEventTypeChart(metrics.events_by_type || {});
    updatePerformanceChart(metrics);
}

function normalizeEvent(event) {
    return {
        event_type: event.event_type,
        timestamp: event.timestamp,
        payload: event.payload || {},
        metadata: event.metadata || {}
    };
}

function updateTaskFromEvent(event) {
    const payload = event.payload || {};

    if (event.event_type === 'task.started') {
        const progress = payload.progress_pct != null ? payload.progress_pct : 0;
        taskState = {
            taskId: payload.task_id || null,
            taskName: payload.task_name || 'Unnamed task',
            stage: payload.stage || '--',
            status: 'In Progress',
            updatedAt: event.timestamp,
            progressPct: progress
        };
        renderTaskStrip();
        return;
    }

    if (event.event_type === 'task.stage_changed') {
        const progress = payload.progress_pct != null ? payload.progress_pct : taskState.progressPct;
        taskState = {
            taskId: payload.task_id || taskState.taskId,
            taskName: payload.task_name || taskState.taskName,
            stage: payload.stage || taskState.stage,
            status: 'In Progress',
            updatedAt: event.timestamp,
            progressPct: progress
        };
        renderTaskStrip();
        return;
    }

    if (event.event_type === 'task.completed') {
        const status = payload.status === 'failed' ? 'Failed' : 'Completed';
        const progress = payload.progress_pct != null
            ? payload.progress_pct
            : payload.status === 'success'
                ? 100
                : taskState.progressPct;
        taskState = {
            taskId: payload.task_id || taskState.taskId,
            taskName: payload.task_name || taskState.taskName,
            stage: payload.stage || 'Done',
            status,
            updatedAt: event.timestamp,
            progressPct: progress
        };
        renderTaskStrip();
    }
}

function updateTestFromEvent(event) {
    const payload = event.payload || {};

    if (event.event_type === 'test.run_started') {
        lastTest = {
            status: 'Running',
            summary: payload.test_suite || 'Test suite',
            updatedAt: event.timestamp
        };
        renderTestStatus();
        return;
    }

    if (event.event_type === 'test.run_completed') {
        const status = payload.status || 'unknown';
        const label = status === 'passed' ? 'Passed' : status === 'failed' ? 'Failed' : 'Warning';
        const summary = payload.summary || payload.test_suite || 'Test run';
        lastTest = {
            status: label,
            summary,
            updatedAt: event.timestamp
        };
        renderTestStatus();
    }
}

function updateSessionSummaryFromEvent(event) {
    const payload = event.payload || {};
    if (event.event_type !== 'session.summary') return;

    sessionSummary = {
        summaryType: payload.summary_type || 'start',
        summaryText: payload.summary_text || 'No summary available.'
    };
    renderSessionSummary(true);
}

function renderTaskStrip() {
    document.getElementById('taskName').textContent = taskState.taskName || 'No active task';
    document.getElementById('taskStage').textContent = `Stage: ${taskState.stage || '--'}`;
    document.getElementById('taskStatus').textContent = taskState.status || 'Idle';
    document.getElementById('taskUpdated').textContent = `Updated: ${formatTimestamp(taskState.updatedAt)}`;
    const progressEl = document.getElementById('taskProgress');
    const progressFill = document.getElementById('taskProgressFill');
    const progressValue = typeof taskState.progressPct === 'number' ? taskState.progressPct : null;
    if (progressEl) {
        progressEl.textContent = progressValue != null
            ? `Progress: ${Math.round(progressValue)}%`
            : 'Progress: --';
    }
    if (progressFill) {
        const clamped = progressValue != null ? Math.min(Math.max(progressValue, 0), 100) : 0;
        progressFill.style.width = `${clamped}%`;
    }
}

function renderTestStatus() {
    document.getElementById('lastTestStatus').textContent = lastTest.status || 'Not run';
    document.getElementById('lastTestSummary').textContent = lastTest.summary || '--';
}

function renderSessionSummary(show) {
    const summaryEl = document.getElementById('sessionSummary');
    const summaryText = document.getElementById('summaryText');
    const summaryType = document.getElementById('summaryType');

    summaryText.textContent = sessionSummary.summaryText || 'No summary available.';
    summaryType.textContent = sessionSummary.summaryType === 'end' ? 'End' : 'Start';

    if (show) {
        summaryEl.classList.remove('hidden');
    }
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
    try {
        return new Date(timestamp).toLocaleTimeString();
    } catch (e) {
        return '--';
    }
}

function toggleSessionSummary(forceShow) {
    const summaryEl = document.getElementById('sessionSummary');
    const shouldShow = forceShow !== undefined
        ? forceShow
        : summaryEl.classList.contains('hidden');

    if (shouldShow) {
        summaryEl.classList.remove('hidden');
    } else {
        summaryEl.classList.add('hidden');
    }
}

async function fetchApprovals() {
    const listEl = document.getElementById('approvalsList');
    if (!listEl) return;

    try {
        const response = await fetch('/api/approvals?status=required');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        approvalsState.approvals = data.approvals || [];
        approvalsState.lastUpdated = new Date().toISOString();
        renderApprovals();
    } catch (error) {
        console.error('Failed to fetch approvals:', error);
    }
}

function renderApprovals() {
    const listEl = document.getElementById('approvalsList');
    const countEl = document.getElementById('approvalsCount');
    if (!listEl || !countEl) return;

    const approvals = approvalsState.approvals || [];
    countEl.textContent = approvals.length;
    listEl.innerHTML = '';

    if (approvals.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'approvals-empty';
        empty.textContent = 'No pending approvals';
        listEl.appendChild(empty);
        return;
    }

    approvals.forEach((approval) => {
        listEl.appendChild(buildApprovalItem(approval));
    });
}

function buildApprovalItem(approval) {
    const item = document.createElement('div');
    item.className = 'approval-item';

    const header = document.createElement('div');
    header.className = 'approval-item-header';

    const title = document.createElement('div');
    title.className = 'approval-title';
    const fallbackTitle = approval.tool ? `Tool: ${approval.tool}` : 'Approval request';
    title.textContent = approval.summary || fallbackTitle;

    const risk = document.createElement('div');
    risk.className = 'approval-risk';
    if (approval.risk_score !== undefined && approval.risk_score !== null) {
        risk.textContent = `Risk ${approval.risk_score.toFixed(2)}`;
    } else {
        risk.textContent = 'Risk --';
    }

    header.appendChild(title);
    header.appendChild(risk);

    const meta = document.createElement('div');
    meta.className = 'approval-meta';
    const metaParts = [];
    if (approval.operation) metaParts.push(`op: ${approval.operation}`);
    if (approval.file_path) metaParts.push(approval.file_path);
    if (Array.isArray(approval.reasons) && approval.reasons.length > 0) {
        metaParts.push(approval.reasons.join(', '));
    }
    meta.textContent = metaParts.length > 0 ? metaParts.join(' • ') : 'No details provided';

    const idLine = document.createElement('div');
    idLine.className = 'approval-id';
    idLine.textContent = approval.approval_id ? `ID: ${approval.approval_id}` : 'ID: --';

    const actions = document.createElement('div');
    actions.className = 'approval-actions';

    const approveBtn = document.createElement('button');
    approveBtn.className = 'btn btn-primary btn-small';
    approveBtn.textContent = 'Approve';
    approveBtn.disabled = !approval.approval_id;
    approveBtn.addEventListener('click', () => {
        submitApprovalDecision(approval.approval_id, 'granted');
    });

    const denyBtn = document.createElement('button');
    denyBtn.className = 'btn btn-danger btn-small';
    denyBtn.textContent = 'Deny';
    denyBtn.disabled = !approval.approval_id;
    denyBtn.addEventListener('click', () => {
        submitApprovalDecision(approval.approval_id, 'denied');
    });

    actions.appendChild(approveBtn);
    actions.appendChild(denyBtn);

    item.appendChild(header);
    item.appendChild(meta);
    item.appendChild(idLine);
    item.appendChild(actions);

    return item;
}

async function submitApprovalDecision(approvalId, status) {
    if (!approvalId) return;
    try {
        const response = await fetch(`/api/approvals/${approvalId}/decision`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, actor: 'dashboard' })
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const label = status === 'granted' ? 'approved' : 'denied';
        showToast(`Approval ${label}`, status === 'granted' ? 'success' : 'warning');
        fetchApprovals();
    } catch (error) {
        console.error('Failed to submit approval decision:', error);
        showToast('Failed to update approval', 'error');
    }
}

function addEventToStream(event) {
    const stream = document.getElementById('eventStream');

    // Remove empty state
    const emptyState = stream.querySelector('.event-stream-empty');
    if (emptyState) {
        emptyState.remove();
    }

    // Create event element
    const eventEl = document.createElement('div');
    eventEl.className = `event-item event-${getEventCategory(event)}`;

    const timestamp = new Date(event.timestamp).toLocaleTimeString();
    const showTimestamp = config.showTimestamps;

    eventEl.innerHTML = `
        ${showTimestamp ? `<span class="event-time">${timestamp}</span>` : ''}
        <span class="event-type">${event.event_type}</span>
        <span class="event-details">${formatEventDetails(event)}</span>
    `;

    stream.insertBefore(eventEl, stream.firstChild);

    // Limit stream size
    while (stream.children.length > config.maxEvents) {
        stream.removeChild(stream.lastChild);
    }
}

function getEventCategory(event) {
    const eventType = event.event_type || '';
    const payload = event.payload || {};

    if (eventType === 'approval.required') return 'warning';
    if (eventType === 'approval.granted') return 'success';
    if (eventType === 'approval.denied') return 'error';
    if (eventType === 'test.run_completed' && payload.status === 'failed') return 'error';
    if (eventType === 'task.completed' && payload.status === 'failed') return 'error';

    if (eventType.includes('failed') || eventType.includes('error')) return 'error';
    if (eventType.includes('completed')) return 'success';
    if (eventType.includes('invoked') || eventType.includes('started')) return 'info';
    return 'default';
}

function formatEventDetails(event) {
    const payload = event.payload || {};

    // Extract agent name
    if (payload.agent) {
        const agentName = typeof payload.agent === 'string'
            ? payload.agent
            : payload.agent.name || payload.agent.id || 'unknown';
        return `Agent: ${agentName}`;
    }

    // Extract tool name
    if (payload.tool) {
        return `Tool: ${payload.tool}`;
    }

    // Extract task info
    if (payload.task_id || payload.task_name) {
        const taskLabel = payload.task_name || payload.task_id;
        return `Task: ${taskLabel}`;
    }

    // Extract test info
    if (payload.test_suite) {
        const status = payload.status ? ` (${payload.status})` : '';
        return `Test: ${payload.test_suite}${status}`;
    }

    // Extract session summary info
    if (event.event_type === 'session.summary') {
        return `Summary: ${payload.summary_type || 'start'}`;
    }

    if (event.event_type === 'approval.required') {
        const score = payload.risk_score != null ? ` (${payload.risk_score})` : '';
        const target = payload.file_path ? ` ${payload.file_path}` : '';
        return `Approval required${score}${target}`;
    }

    if (event.event_type === 'approval.granted') {
        const target = payload.file_path ? ` ${payload.file_path}` : '';
        return `Approval granted${target}`;
    }

    if (event.event_type === 'approval.denied') {
        const target = payload.file_path ? ` ${payload.file_path}` : '';
        return `Approval denied${target}`;
    }

    // Extract workflow ID
    if (payload.workflow_id) {
        return `Workflow: ${payload.workflow_id}`;
    }

    // Default: show first few payload keys
    const keys = Object.keys(payload).slice(0, 2);
    if (keys.length > 0) {
        return keys.map(k => `${k}: ${JSON.stringify(payload[k]).slice(0, 30)}`).join(', ');
    }

    return '';
}

function updateMetricsHistory() {
    const now = Date.now();
    metricsHistory.timestamps.push(now);
    metricsHistory.eventRates.push(1);  // Count event

    // Remove old points (older than 60 seconds)
    const cutoff = now - 60000;
    while (metricsHistory.timestamps.length > 0 &&
           metricsHistory.timestamps[0] < cutoff) {
        metricsHistory.timestamps.shift();
        metricsHistory.eventRates.shift();
    }

    updateEventRateChart();
}

// ============================================================================
// Chart Management
// ============================================================================

function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 300
        }
    };

    // Event Rate Chart (Line)
    const eventRateCtx = document.getElementById('eventRateChart').getContext('2d');
    eventRateChart = new Chart(eventRateCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Events/sec',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                x: {
                    display: false
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Event Type Chart (Doughnut)
    const eventTypeCtx = document.getElementById('eventTypeChart').getContext('2d');
    eventTypeChart = new Chart(eventTypeCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)',
                    'rgb(255, 159, 64)'
                ]
            }]
        },
        options: {
            ...commonOptions,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });

    // Performance Chart (Bar)
    const performanceCtx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(performanceCtx, {
        type: 'bar',
        data: {
            labels: ['p50', 'p95', 'p99'],
            datasets: [{
                label: 'Duration (ms)',
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(255, 205, 86, 0.6)',
                    'rgba(255, 99, 132, 0.6)'
                ]
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateEventRateChart() {
    if (!eventRateChart) return;

    // Calculate events per second over last 60 seconds
    const now = Date.now();
    const buckets = new Array(60).fill(0);

    metricsHistory.timestamps.forEach((ts, idx) => {
        const secondsAgo = Math.floor((now - ts) / 1000);
        if (secondsAgo < 60) {
            buckets[59 - secondsAgo]++;
        }
    });

    eventRateChart.data.labels = buckets.map((_, i) => `${60 - i}s`);
    eventRateChart.data.datasets[0].data = buckets;
    eventRateChart.update('none');  // Update without animation
}

function updateEventTypeChart(eventsByType) {
    if (!eventTypeChart) return;

    const labels = Object.keys(eventsByType);
    const data = Object.values(eventsByType);

    if (labels.length === 0) {
        labels.push('No events');
        data.push(1);
    }

    eventTypeChart.data.labels = labels;
    eventTypeChart.data.datasets[0].data = data;
    eventTypeChart.update();
}

function updatePerformanceChart(metrics) {
    if (!performanceChart) return;

    performanceChart.data.datasets[0].data = [
        metrics.p50_agent_duration_ms || 0,
        metrics.p95_agent_duration_ms || 0,
        metrics.p99_agent_duration_ms || 0
    ];
    performanceChart.update();
}

// ============================================================================
// Event Handlers
// ============================================================================

function setupEventHandlers() {
    // Pause/Resume button
    document.getElementById('pauseBtn').addEventListener('click', () => {
        isPaused = !isPaused;
        const btn = document.getElementById('pauseBtn');
        const icon = document.getElementById('pauseIcon');

        if (isPaused) {
            btn.classList.add('btn-warning');
            icon.textContent = '▶️';
            btn.innerHTML = `${icon.outerHTML} Resume`;
            showToast('Stream paused', 'info');
        } else {
            btn.classList.remove('btn-warning');
            icon.textContent = '⏸️';
            btn.innerHTML = `${icon.outerHTML} Pause`;
            showToast('Stream resumed', 'info');
        }
    });

    // Clear button
    document.getElementById('clearBtn').addEventListener('click', () => {
        const stream = document.getElementById('eventStream');
        stream.innerHTML = '<div class="event-stream-empty"><p>Stream cleared</p></div>';
        eventBuffer = [];
        metricsHistory = { timestamps: [], eventRates: [], maxPoints: 60 };
        showToast('Stream cleared', 'info');
    });

    // Settings button
    document.getElementById('settingsBtn').addEventListener('click', () => {
        document.getElementById('settingsModal').style.display = 'flex';
    });

    // Close settings
    document.getElementById('closeSettings').addEventListener('click', closeSettings);
    document.getElementById('cancelSettings').addEventListener('click', closeSettings);

    // Save settings
    document.getElementById('saveSettings').addEventListener('click', () => {
        config.wsHost = document.getElementById('wsHost').value;
        config.wsPort = parseInt(document.getElementById('wsPort').value);
        config.reconnectDelay = parseInt(document.getElementById('reconnectDelay').value);
        config.maxEvents = parseInt(document.getElementById('maxEvents').value);
        config.autoReconnect = document.getElementById('autoReconnect').checked;
        config.showTimestamps = document.getElementById('showTimestamps').checked;

        // Save to localStorage
        localStorage.setItem('dashboardConfig', JSON.stringify(config));

        closeSettings();

        // Reconnect with new settings
        disconnect();
        connect();

        showToast('Settings saved', 'success');
    });

    // Window size selector
    document.getElementById('windowSelect').addEventListener('change', (e) => {
        config.windowSize = parseInt(e.target.value);
        // Request new metrics with updated window size
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'set_window',
                window_size: config.windowSize
            }));
        }
    });

    // Event filters
    document.getElementById('eventTypeFilter').addEventListener('change', filterEventStream);
    document.getElementById('agentFilter').addEventListener('input', filterEventStream);

    // Session summary toggles
    document.getElementById('summaryToggle').addEventListener('click', () => {
        toggleSessionSummary();
    });
    document.getElementById('summaryClose').addEventListener('click', () => {
        toggleSessionSummary(false);
    });

    const refreshApprovals = document.getElementById('refreshApprovals');
    if (refreshApprovals) {
        refreshApprovals.addEventListener('click', () => {
            fetchApprovals();
        });
    }

    // Click outside modal to close
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('settingsModal');
        if (e.target === modal) {
            closeSettings();
        }
    });
}

function closeSettings() {
    document.getElementById('settingsModal').style.display = 'none';
}

function filterEventStream() {
    const stream = document.getElementById('eventStream');
    stream.innerHTML = '';

    const eventTypeFilter = document.getElementById('eventTypeFilter').value;
    const agentFilter = document.getElementById('agentFilter').value.toLowerCase();

    // Re-add filtered events from buffer
    eventBuffer.forEach(event => {
        if (eventTypeFilter && event.event_type !== eventTypeFilter) return;
        if (agentFilter && !JSON.stringify(event).toLowerCase().includes(agentFilter)) return;

        addEventToStream(event);
    });

    if (stream.children.length === 0) {
        stream.innerHTML = '<div class="event-stream-empty"><p>No matching events</p></div>';
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast toast-${type} toast-show`;

    setTimeout(() => {
        toast.classList.remove('toast-show');
    }, 3000);
}

// ============================================================================
// Initialization
// ============================================================================

function loadConfig() {
    const saved = localStorage.getItem('dashboardConfig');
    if (saved) {
        try {
            config = { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
        } catch (e) {
            console.error('Failed to load config:', e);
        }
    }

    // Update settings modal with loaded config
    document.getElementById('wsHost').value = config.wsHost;
    document.getElementById('wsPort').value = config.wsPort;
    document.getElementById('reconnectDelay').value = config.reconnectDelay;
    document.getElementById('maxEvents').value = config.maxEvents;
    document.getElementById('autoReconnect').checked = config.autoReconnect;
    document.getElementById('showTimestamps').checked = config.showTimestamps;
}

function init() {
    console.log('Initializing dashboard...');

    loadConfig();
    setupEventHandlers();
    initCharts();
    connect();
    fetchApprovals();

    console.log('Dashboard initialized');
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    disconnect();
});
