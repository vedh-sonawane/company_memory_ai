// API Base URL
const API_BASE = '';

// DOM Elements
const tasksContainer = document.getElementById('tasks-container');
const decisionsContainer = document.getElementById('decisions-container');
const totalTasksEl = document.getElementById('total-tasks');
const totalDecisionsEl = document.getElementById('total-decisions');
const recentActivityEl = document.getElementById('recent-activity');
const lastUpdatedEl = document.getElementById('last-updated');
const refreshBtn = document.getElementById('refresh-btn');

// Format timestamp to readable date
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    // Try to parse as Unix timestamp first
    let date;
    if (timestamp.includes('.')) {
        // Handle Slack timestamp format (seconds with decimal)
        date = new Date(parseFloat(timestamp) * 1000);
    } else {
        // Handle standard timestamp
        date = new Date(timestamp);
    }
    
    if (isNaN(date.getTime())) return 'Invalid Date';
    
    return date.toLocaleString();
}

// Format date for "recent activity" (last 7 days)
function isRecent(timestamp) {
    if (!timestamp) return false;
    
    let date;
    if (timestamp.includes('.')) {
        date = new Date(parseFloat(timestamp) * 1000);
    } else {
        date = new Date(timestamp);
    }
    
    if (isNaN(date.getTime())) return false;
    
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    return date > sevenDaysAgo;
}

// Create task card HTML
function createTaskCard(task) {
    return `
        <div class="item-card">
            <div class="item-header">
                <div>
                    <div class="item-title">${task.task || 'No task description'}</div>
                    <div>
                        ${task.owner ? `<span class="item-owner">${task.owner}</span>` : ''}
                        ${task.deadline ? `<span class="item-deadline">${task.deadline}</span>` : ''}
                    </div>
                </div>
            </div>
            ${task.source_message ? `
                <div class="item-source">
                    <div class="item-source-label"><i class="fas fa-comment"></i> Source Message</div>
                    <div class="item-source-text text-truncate">${task.source_message}</div>
                </div>
            ` : ''}
            <div class="item-timestamp">
                <i class="far fa-clock"></i> ${formatTimestamp(task.timestamp)}
            </div>
        </div>
    `;
}

// Create decision card HTML
function createDecisionCard(decision) {
    return `
        <div class="item-card">
            <div class="item-header">
                <div class="item-title">${decision.decision || 'No decision description'}</div>
            </div>
            ${decision.context ? `
                <div class="item-context text-truncate">${decision.context}</div>
            ` : ''}
            ${decision.source_message ? `
                <div class="item-source">
                    <div class="item-source-label"><i class="fas fa-comment"></i> Source Message</div>
                    <div class="item-source-text text-truncate">${decision.source_message}</div>
                </div>
            ` : ''}
            <div class="item-timestamp">
                <i class="far fa-clock"></i> ${formatTimestamp(decision.timestamp)}
            </div>
        </div>
    `;
}

// Render tasks
function renderTasks(tasks) {
    if (!tasks || tasks.length === 0) {
        tasksContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-tasks"></i>
                <p>No open tasks found</p>
            </div>
        `;
        return;
    }
    
    tasksContainer.innerHTML = tasks.map(createTaskCard).join('');
}

// Render decisions
function renderDecisions(decisions) {
    if (!decisions || decisions.length === 0) {
        decisionsContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-gavel"></i>
                <p>No decisions found</p>
            </div>
        `;
        return;
    }
    
    decisionsContainer.innerHTML = decisions.map(createDecisionCard).join('');
}

// Update summary stats
function updateSummary(tasks, decisions) {
    totalTasksEl.textContent = tasks.length;
    totalDecisionsEl.textContent = decisions.length;
    
    // Count recent activity (items from last 7 days)
    const recentTasks = tasks.filter(task => isRecent(task.timestamp));
    const recentDecisions = decisions.filter(decision => isRecent(decision.timestamp));
    const recentCount = recentTasks.length + recentDecisions.length;
    recentActivityEl.textContent = recentCount;
    
    // Update last updated time
    lastUpdatedEl.textContent = new Date().toLocaleString();
}

// Show loading state
function showLoading() {
    tasksContainer.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Loading tasks...</p>
        </div>
    `;
    decisionsContainer.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Loading decisions...</p>
        </div>
    `;
}

// Show error state
function showError(message) {
    tasksContainer.innerHTML = `
        <div class="error-state">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Error loading tasks: ${message}</p>
        </div>
    `;
    decisionsContainer.innerHTML = `
        <div class="error-state">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Error loading decisions: ${message}</p>
        </div>
    `;
}

// Fetch data from API
async function fetchData() {
    try {
        showLoading();
        
        // Fetch tasks
        const tasksResponse = await fetch(`${API_BASE}/tasks`);
        if (!tasksResponse.ok) throw new Error(`Tasks API error: ${tasksResponse.status}`);
        const tasks = await tasksResponse.json();
        
        // Fetch decisions
        const decisionsResponse = await fetch(`${API_BASE}/decisions`);
        if (!decisionsResponse.ok) throw new Error(`Decisions API error: ${decisionsResponse.status}`);
        const decisions = await decisionsResponse.json();
        
        // Render data
        renderTasks(tasks);
        renderDecisions(decisions);
        updateSummary(tasks, decisions);
        
    } catch (error) {
        console.error('Error fetching data:', error);
        showError(error.message);
    }
}

// Initialize dashboard
function initDashboard() {
    // Load data on page load
    fetchData();
    
    // Set up refresh button
    refreshBtn.addEventListener('click', fetchData);
    
    // Set up auto-refresh every 30 seconds
    setInterval(fetchData, 30000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);
