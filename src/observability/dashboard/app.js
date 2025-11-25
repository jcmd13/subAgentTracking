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
}

function handleMessage(event) {
    if (isPaused) return;

    try {
        const data = JSON.parse(event.data);

        if (data.type === 'event') {
            handleEventMessage(data.event);
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

    if (event.code !== 1000) {  // Not a normal closure
        showToast('Connection lost. Reconnecting...', 'warning');
        scheduleReconnect();
    }
}

// ============================================================================
// Message Handlers
// ============================================================================

function handleEventMessage(event) {
    // Add to event buffer
    eventBuffer.unshift(event);
    if (eventBuffer.length > config.maxEvents) {
        eventBuffer.pop();
    }

    // Apply filters
    const eventTypeFilter = document.getElementById('eventTypeFilter').value;
    const agentFilter = document.getElementById('agentFilter').value.toLowerCase();

    if (eventTypeFilter && event.event_type !== eventTypeFilter) return;
    if (agentFilter && !JSON.stringify(event).toLowerCase().includes(agentFilter)) return;

    // Add to stream
    addEventToStream(event);

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

function addEventToStream(event) {
    const stream = document.getElementById('eventStream');

    // Remove empty state
    const emptyState = stream.querySelector('.event-stream-empty');
    if (emptyState) {
        emptyState.remove();
    }

    // Create event element
    const eventEl = document.createElement('div');
    eventEl.className = `event-item event-${getEventCategory(event.event_type)}`;

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

function getEventCategory(eventType) {
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
