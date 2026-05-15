const API_URL = 'http://192.111.111.80:8000/api/tasks';
const refreshBtn = document.getElementById('refresh-btn');
const tbody = document.getElementById('task-body');
const limitFilter = document.getElementById('limit-filter');
const statusFilter = document.getElementById('status-filter');
const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
let pollingInterval = null;

// Format timestamp to readable date
function formatTime(unixTimestamp) {
    if (!unixTimestamp) return '-';
    // The timestamp seems to be in seconds
    const date = new Date(unixTimestamp * 1000);
    return date.toLocaleString('id-ID', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function getStateClass(state) {
    if (!state) return 'state-default';
    state = state.toLowerCase();
    if (state.includes('ready')) return 'state-ready';
    if (state.includes('end')) return 'state-end';
    return 'state-default';
}

async function fetchTasks() {
    try {
        refreshBtn.innerHTML = '<div class="spinner" style="width: 14px; height: 14px; border-width: 2px; margin:0;"></div> Refreshing...';
        
        const limitValue = limitFilter.value;
        const statusValue = statusFilter.value;
        const fetchUrl = `${API_URL}?limit=${limitValue}&status=${statusValue}`;
        
        const response = await fetch(fetchUrl);
        const data = await response.json();
        
        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: #ff3366;">Error: ${data.error}</td></tr>`;
            return;
        }

        const tasks = data.tasks;
        if (tasks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: #9ba1a6;">Tidak ada task ditemukan di database.</td></tr>`;
            return;
        }

        tbody.innerHTML = '';
        tasks.forEach((task, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td><span class="uuid-cell">${task.task_id}</span></td>
                <td style="text-transform: capitalize;">${task.model || '-'}</td>
                <td><span class="state-badge ${getStateClass(task.state)}">${task.state || 'UNKNOWN'}</span></td>
                <td style="color: #9ba1a6; font-size: 0.85rem;">${formatTime(task.create_time)}</td>
                <td>
                    <button class="btn action-btn" onclick="openDetails(${task.id})">Details</button>
                </td>
            `;
            // Add subtle animation for new rows
            tr.style.opacity = '0';
            tr.style.transform = 'translateY(10px)';
            tr.style.transition = `all 0.3s ease ${index * 0.05}s`;
            tbody.appendChild(tr);
            
            // Trigger reflow
            setTimeout(() => {
                tr.style.opacity = '1';
                tr.style.transform = 'translateY(0)';
            }, 10);
        });

    } catch (error) {
        console.error('Failed to fetch tasks:', error);
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: #ff3366;">Koneksi ke backend gagal. Pastikan server backend berjalan di port 8000.</td></tr>`;
    } finally {
        setTimeout(() => {
            refreshBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.59-8.21l-5.6 5.6"/></svg> Refresh Manual`;
        }, 500);
    }
}

// Event Listeners
refreshBtn.addEventListener('click', fetchTasks);

limitFilter.addEventListener('change', fetchTasks);
statusFilter.addEventListener('change', fetchTasks);

autoRefreshToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        fetchTasks();
        pollingInterval = setInterval(fetchTasks, 10000);
    } else {
        clearInterval(pollingInterval);
    }
});

// Initial fetch
document.addEventListener('DOMContentLoaded', () => {
    fetchTasks();
    
    // Auto-polling setup
    if (autoRefreshToggle.checked) {
        pollingInterval = setInterval(fetchTasks, 10000);
    }
});

// ===== DETAIL MODAL =====
const modal = document.getElementById('detail-modal');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');

function closeModal() {
    modal.style.display = 'none';
}

// Close modal on overlay click
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

async function openDetails(objId) {
    modal.style.display = 'flex';
    modalTitle.textContent = 'Memuat Detail...';
    modalBody.innerHTML = '<div class="spinner"></div><p style="text-align:center; color: var(--text-secondary);">Mengambil data dari server...</p>';
    
    try {
        const response = await fetch(`http://192.111.111.80:8000/api/tasks/${objId}/details`);
        const data = await response.json();
        
        if (data.error) {
            modalBody.innerHTML = `<p style="color: #ff3366;">Error: ${data.error}</p>`;
            return;
        }
        
        const task = data.task;
        const props = data.properties;
        const states = data.state_history;
        const container = data.container;
        
        modalTitle.textContent = task.task_id;
        
        let html = '';
        
        // Section 1: Task Info
        html += `
        <div class="detail-section">
            <h4>📋 Informasi Task</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="label">Task ID</span>
                    <span class="value mono">${task.task_id}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Model</span>
                    <span class="value" style="text-transform: capitalize;">${task.model}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Waktu Masuk</span>
                    <span class="value">${formatTime(task.create_time)}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Terakhir Diubah</span>
                    <span class="value">${formatTime(task.modify_time)}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Hasil (Result)</span>
                    <span class="value">${props.result ? '✅ ' + props.result : '⏳ Belum ada'}</span>
                </div>
            </div>
        </div>`;
        
        // Section 2: Container (if linked)
        if (container) {
            html += `
            <div class="detail-section">
                <h4>📦 Kontainer Terkait</h4>
                <div class="container-badge">🚛 ${container.container_id}</div>
            </div>`;
        }
        
        // Section 3: State Timeline
        html += `
        <div class="detail-section">
            <h4>🔄 Riwayat Status (State Timeline)</h4>
            <div class="state-timeline">`;
        
        states.forEach((s) => {
            html += `
                <div class="timeline-item">
                    <div class="timeline-dot">${s.seq}</div>
                    <div class="timeline-info">
                        <div class="timeline-state">
                            <span class="state-badge ${getStateClass(s.state)}">${s.state}</span>
                        </div>
                        <div class="timeline-time">${formatTime(s.set_time)}</div>
                        ${s.operator ? `<div class="timeline-operator">${s.operator}</div>` : ''}
                    </div>
                </div>`;
        });
        
        html += '</div></div>';
        
        modalBody.innerHTML = html;
        
    } catch (error) {
        console.error('Failed to fetch details:', error);
        modalBody.innerHTML = '<p style="color: #ff3366;">Gagal mengambil detail. Pastikan backend berjalan.</p>';
    }
}
