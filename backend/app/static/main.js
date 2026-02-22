// WebSocket client for real-time updates
let ws = null;
let reconnectTimer = null;
const MAX_EVENTS = 50;
const events = [];

// DOM elements
const inCounter = document.getElementById('inCounter');
const outCounter = document.getElementById('outCounter');
const activeTracks = document.getElementById('activeTracks');
const cameraStatus = document.getElementById('cameraStatus');
const modelStatus = document.getElementById('modelStatus');
const wsStatus = document.getElementById('wsStatus');
const statusIndicator = document.getElementById('statusIndicator');
const eventsList = document.getElementById('eventsList');

// Connect to WebSocket
function connect() {
    const wsUrl = `ws://${window.location.host}/ws`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        wsStatus.textContent = 'Подключено';
        wsStatus.style.color = '#10b981';
        
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        
        // Load initial events from REST API
        loadInitialEvents();
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        wsStatus.textContent = 'Ошибка';
        wsStatus.style.color = '#ef4444';
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        wsStatus.textContent = 'Отключено';
        wsStatus.style.color = '#ef4444';
        statusIndicator.className = 'status-indicator status-offline';
        
        // Attempt to reconnect after 3 seconds
        reconnectTimer = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
        }, 3000);
    };
}

// Handle WebSocket messages
function handleMessage(message) {
    switch (message.type) {
        case 'stats':
            updateStats(message.data);
            break;
        
        case 'event':
            addEvent(message.data);
            break;
        
        case 'status':
            console.log('Status:', message.data);
            if (message.data.message) {
                // Could show a toast notification here
            }
            break;
        
        default:
            console.warn('Unknown message type:', message.type);
    }
}

// Update statistics
function updateStats(data) {
    inCounter.textContent = data.in_count;
    outCounter.textContent = data.out_count;
    activeTracks.textContent = data.active_tracks;
    
    // Camera status
    const cameraStatusText = {
        'online': 'Онлайн',
        'offline': 'Отключена',
        'initializing': 'Инициализация...'
    };
    cameraStatus.textContent = cameraStatusText[data.camera_status] || data.camera_status;
    cameraStatus.style.color = data.camera_status === 'online' ? '#10b981' : '#ef4444';
    
    // Model status
    modelStatus.textContent = data.model_loaded ? 'Загружена' : 'Не загружена';
    modelStatus.style.color = data.model_loaded ? '#10b981' : '#ef4444';
    
    // Status indicator
    if (data.camera_status === 'online' && data.model_loaded) {
        statusIndicator.className = 'status-indicator status-online';
    } else {
        statusIndicator.className = 'status-indicator status-offline';
    }
}

// Add new event to the list
function addEvent(eventData) {
    events.unshift(eventData);
    
    // Keep only MAX_EVENTS
    if (events.length > MAX_EVENTS) {
        events.pop();
    }
    
    renderEvents();
}

// Render events list
function renderEvents() {
    if (events.length === 0) {
        eventsList.innerHTML = '<div class="empty-state">Ожидание событий...</div>';
        return;
    }
    
    eventsList.innerHTML = events.map(event => {
        const time = new Date(event.timestamp);
        const timeStr = time.toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        
        const badgeClass = event.direction === 'IN' ? 'badge-in' : 'badge-out';
        
        return `
            <div class="event-item">
                <div>
                    <span class="event-badge ${badgeClass}">${event.direction}</span>
                    <span class="event-track">Track #${event.track_id}</span>
                </div>
                <div class="event-time">${timeStr}</div>
            </div>
        `;
    }).join('');
}

// Load initial events from REST API
async function loadInitialEvents() {
    try {
        const response = await fetch('/api/events?limit=50');
        const data = await response.json();
        
        // Add events in reverse order (newest first)
        events.length = 0;
        events.push(...data);
        
        renderEvents();
    } catch (error) {
        console.error('Error loading initial events:', error);
    }
}

// Reset counters
async function resetCounters() {
    if (!confirm('⚠️ Сбросить счетчики IN/OUT? (События сохранятся)')) {
        return;
    }
    
    try {
        const response = await fetch('/api/reset', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            console.log('Counters reset successfully');
            updateStats(data.new_stats);
            alert('✓ Счетчики успешно сброшены');
        } else {
            alert('Ошибка сброса счетчиков: ' + data.message);
        }
    } catch (error) {
        console.error('Error resetting counters:', error);
        alert('Ошибка сброса счетчиков. Проверьте консоль.');
    }
}

// Clear events
async function clearEvents() {
    if (!confirm('⚠️ Удалить все события из базы данных? Это действие необратимо!')) {
        return;
    }
    
    try {
        const response = await fetch('/api/events/clear', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            console.log('Events cleared successfully');
            // Clear local events array
            events.length = 0;
            renderEvents();
            alert('✓ Все события успешно удалены');
        } else {
            alert('Ошибка удаления событий: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error clearing events:', error);
        alert('Ошибка удаления событий. Проверьте консоль.');
    }
}

// ============================================
// Camera Source Switching
// ============================================

const cameraSourceSelect = document.getElementById('cameraSource');
const switchStatus = document.getElementById('switchStatus');

/**
 * Switch camera source
 */
async function switchCamera() {
    const source = cameraSourceSelect.value;
    console.log('Switching camera to:', source);
    
    switchStatus.textContent = '⏳ Переключение...';
    switchStatus.style.color = '#fbbf24';
    cameraSourceSelect.disabled = true;
    
    try {
        const response = await fetch('/api/camera/switch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ source })
        });
        
        const data = await response.json();
        
        if (data.success) {
            switchStatus.textContent = '✓ Подключено';
            switchStatus.style.color = '#10b981';
            console.log('Camera switched successfully:', data);
        } else {
            switchStatus.textContent = '✗ Ошибка подключения';
            switchStatus.style.color = '#ef4444';
            alert('Не удалось переключить камеру: ' + data.message);
            console.error('Switch failed:', data);
        }
    } catch (error) {
        switchStatus.textContent = '✗ Ошибка';
        switchStatus.style.color = '#ef4444';
        alert('Ошибка переключения камеры. Проверьте консоль.');
        console.error('Error switching camera:', error);
    } finally {
        cameraSourceSelect.disabled = false;
    }
}

// ============================================
// Initialize on page load
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing...');
    
    // Initialize WebSocket
    connect();
    
    // Camera source switcher
    cameraSourceSelect.addEventListener('change', switchCamera);
});
