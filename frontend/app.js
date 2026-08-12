const API_URL = 'http://192.111.111.80:8000/api/tasks';
const refreshBtn = document.getElementById('refresh-btn');
const tbody = document.getElementById('task-body');
const limitFilter = document.getElementById('limit-filter');
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

let isFetching = false;

async function fetchTasks() {
    if (isFetching) return;
    isFetching = true;
    try {
        refreshBtn.innerHTML = '<div class="spinner" style="width: 14px; height: 14px; border-width: 2px; margin:0;"></div> Refreshing...';
        
        // Show loading state in table
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 3rem;">
            <div class="spinner" style="width: 32px; height: 32px; border-width: 3px; margin: 0 auto 1rem;"></div>
            <div style="color: var(--text-muted); font-size: 0.9rem;">Memuat data dari server...</div>
        </td></tr>`;
        
        const limitValue = limitFilter.value;
        const statusValue = "safe";
        const fetchUrl = `${API_URL}?limit=${limitValue}&status=${statusValue}`;
        
        const response = await fetch(fetchUrl);
        const data = await response.json();
        
        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: #ff3366;">Error: ${data.error}</td></tr>`;
            return;
        }

        const tasks = data.tasks;
        if (tasks.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: #9ba1a6;">Tidak ada task ditemukan di database.</td></tr>`;
            return;
        }
        
        // Find oldest task time for date_range (tasks are sorted by DESC create_time, so the last is oldest)
        const oldestTask = tasks[tasks.length - 1];
        if (oldestTask && oldestTask.create_time) {
            const oldestDate = new Date(oldestTask.create_time * 1000);
            const today = new Date();
            window.currentDateRange = `${oldestDate.getFullYear()}-${String(oldestDate.getMonth() + 1).padStart(2, '0')}-${String(oldestDate.getDate()).padStart(2, '0')} - ${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        }

        // Render all rows IMMEDIATELY
        tbody.innerHTML = '';
        tasks.forEach((task, index) => {
            const tr = document.createElement('tr');
            const result = task.properties?.result;
            // Use container_no if returned, otherwise show '...' to fetch in background
            const showNo = task.container_no && task.container_no !== '-' ? task.container_no : '...';
            const colorStyle = showNo === '...' ? 'color: var(--text-muted);' : '';
            tr.innerHTML = `
                <td><input type="checkbox" class="task-checkbox" data-id="${task.id}" ${result === 'succeed' ? 'disabled' : ''}></td>
                <td>${index + 1}</td>
                <td><span class="uuid-cell">${task.task_id}</span></td>
                <td id="container-cell-${task.id}" style="${colorStyle}">${showNo}</td>
                <td style="text-transform: capitalize;">${task.model || '-'}</td>
                <td><span class="state-badge ${getStateClass(task.state)}">${task.state || 'UNKNOWN'}</span></td>
                <td style="color: #9ba1a6; font-size: 0.85rem;">${formatTime(task.create_time)}</td>
                <td>
                    <div style="display: flex; gap: 5px;">
                        <button class="btn action-btn" onclick="openDetails(${task.id})">Details</button>
                        <button class="btn action-btn primary-btn" onclick="window.open('inspection.html?id=${task.id}', '_blank')">Check</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
        updateCheckboxListeners();
        performSearch();
        
        // Keep track of tasks we've already tried to fetch in this session
        window.attemptedFetches = window.attemptedFetches || new Set();
        
        // Safe Fetching: Fetch container numbers ONLY for tasks that have finished scanning.
        // Doing this while state is 'scan.begin' will interrupt CCR image upload.
        const tasksToFetch = tasks.filter(task => 
            (!task.container_no || task.container_no === '-') && 
            task.state !== 'scan.begin' &&
            !window.attemptedFetches.has(task.id)
        );
        const BATCH_SIZE = 10;
        for (let i = 0; i < tasksToFetch.length; i += BATCH_SIZE) {
            const batch = tasksToFetch.slice(i, i + BATCH_SIZE);
            const batchPromises = batch.map(async (task) => {
                window.attemptedFetches.add(task.id);
                try {
                    const res = await fetch(`http://192.111.111.80:8000/api/tasks/${task.id}/manifest`);
                    if (res.ok) {
                        const mData = await res.json();
                        const cell = document.getElementById(`container-cell-${task.id}`);
                        if (cell) {
                            cell.textContent = mData.container_no || '-';
                            cell.style.color = '';
                        }
                        // Update the container_no on the task object in memory
                        task.container_no = mData.container_no || '-';
                    }
                } catch (e) {
                    const cell = document.getElementById(`container-cell-${task.id}`);
                    if (cell) { cell.textContent = '-'; cell.style.color = ''; }
                }
            });
            await Promise.all(batchPromises);
        }
        
        // Re-apply missing doc highlights after all containers are loaded
        if (typeof applyDocHighlights === 'function' && isHighlightingDocs) {
            applyDocHighlights();
        }

    } catch (error) {
        console.error('Failed to fetch tasks:', error);
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: #ff3366;">Koneksi ke backend gagal. Pastikan server backend berjalan di port 8000.</td></tr>`;
    } finally {
        setTimeout(() => {
            refreshBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.59-8.21l-5.6 5.6"/></svg> Refresh Manual`;
        }, 500);
        isFetching = false;
    }
}

// Event Listeners
refreshBtn.addEventListener('click', fetchTasks);

limitFilter.addEventListener('change', fetchTasks);

// ===== TABLE SORTING =====
let currentSortCol = null;
let currentSortDir = null; // 'asc' or 'desc'

// Column index mapping for data-sort attributes
const sortColMap = {
    'index': 1,
    'task_id': 2,
    'container_no': 3,
    'model': 4,
    'state': 5,
    'create_time': 6
};

function sortTable(colKey) {
    const colIndex = sortColMap[colKey];
    if (colIndex === undefined) return;
    
    // Toggle direction
    if (currentSortCol === colKey) {
        currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortCol = colKey;
        currentSortDir = 'asc';
    }
    
    // Update header icons
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const activeHeader = document.querySelector(`th[data-sort="${colKey}"]`);
    if (activeHeader) {
        activeHeader.classList.add(currentSortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    }
    
    // Get all data rows
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0 || rows[0].cells.length < 8) return;
    
    rows.sort((a, b) => {
        let valA = a.cells[colIndex]?.textContent.trim() || '';
        let valB = b.cells[colIndex]?.textContent.trim() || '';
        
        // Numeric sort for # column
        if (colKey === 'index') {
            return currentSortDir === 'asc' ? parseInt(valA) - parseInt(valB) : parseInt(valB) - parseInt(valA);
        }
        
        // Try date sort for create_time
        if (colKey === 'create_time') {
            const dateA = new Date(valA);
            const dateB = new Date(valB);
            if (!isNaN(dateA) && !isNaN(dateB)) {
                return currentSortDir === 'asc' ? dateA - dateB : dateB - dateA;
            }
        }
        
        // Default: case-insensitive string sort
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
        if (valA < valB) return currentSortDir === 'asc' ? -1 : 1;
        if (valA > valB) return currentSortDir === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Re-append sorted rows and re-number
    rows.forEach((row, idx) => {
        row.cells[1].textContent = idx + 1;
        tbody.appendChild(row);
    });
}

// Attach click listeners to sortable headers
document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        sortTable(th.dataset.sort);
    });
});

autoRefreshToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        fetchTasks();
        pollingInterval = setInterval(fetchTasks, 15000);
    } else {
        clearInterval(pollingInterval);
    }
});

// Initial fetch
document.addEventListener('DOMContentLoaded', () => {
    fetchTasks();
    
    // Auto-polling setup
    if (autoRefreshToggle.checked) {
        pollingInterval = setInterval(fetchTasks, 15000);
    }
});

// ===== DETAIL MODAL =====
const modal = document.getElementById('detail-modal');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');

function closeModal() {
    modal.style.display = 'none';
}

modal?.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

async function manualSubmitTask(taskId) {
    const result = await Swal.fire({
        title: 'Submit Task?',
        text: 'Apakah Anda yakin ingin mensubmit task ini sebagai "No Suspect"? Ini akan memanipulasi API Nuctech.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#2563EB',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Ya, Submit!'
    });
    
    if (!result.isConfirmed) return;

    try {
        const response = await fetch(`http://192.111.111.80:8000/api/tasks/${taskId}/submit`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            Swal.fire('Berhasil!', data.message || 'Task berhasil disubmit.', 'success');
            closeModal();
            fetchTasks();
        } else {
            Swal.fire('Error', data.detail || data.error, 'error');
        }
    } catch (error) {
        console.error('Error submitting:', error);
        Swal.fire('Gagal', 'Koneksi ke server gagal.', 'error');
    }
}

function updateCheckboxListeners() {
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const massBtn = document.getElementById('massSubmitBtn');
    
    function updateMassBtn() {
        const checked = document.querySelectorAll('.task-checkbox:checked').length;
        if (checked > 0) {
            massBtn.style.display = 'inline-flex';
            massBtn.textContent = `✅ Auto-Submit Selected (${checked})`;
        } else {
            massBtn.style.display = 'none';
        }
    }
    
    checkboxes.forEach(cb => cb.addEventListener('change', updateMassBtn));
    
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if(selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            checkboxes.forEach(cb => {
                if(!cb.disabled) cb.checked = e.target.checked;
            });
            updateMassBtn();
        });
    }
}

// ===== SEARCH FUNCTIONALITY =====
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');

function performSearch() {
    if (!searchInput) return;
    const query = searchInput.value.toLowerCase().trim();
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        if (row.cells.length < 8) return; // Skip error/info rows
        
        const taskId = row.querySelector('.uuid-cell')?.textContent.toLowerCase() || '';
        const containerNo = row.cells[3]?.textContent.toLowerCase() || '';
        
        if (taskId.includes(query) || containerNo.includes(query)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

if (searchInput) {
    searchInput.addEventListener('input', performSearch);
    searchBtn.addEventListener('click', performSearch);
}

// ===== HIGHLIGHT NO-DOC FUNCTIONALITY =====
const highlightToggle = document.getElementById('highlight-no-doc-toggle');
const moduleSelect = document.getElementById('highlight-module-select');
let missingDocsList = [];
let missingDocsModule = ''; // track which module the cached list belongs to
let isHighlightingDocs = false;

// Restore last selected module from localStorage
if (moduleSelect) {
    const savedModule = localStorage.getItem('highlight-module');
    if (savedModule) moduleSelect.value = savedModule;
}

async function applyDocHighlights() {
    if (!highlightToggle) return;
    
    isHighlightingDocs = highlightToggle.checked;
    const rows = tbody.querySelectorAll('tr');
    const selectedModule = moduleSelect ? moduleSelect.value : 'import';
    
    const countSpan = document.getElementById('missing-doc-count');
    
    if (!isHighlightingDocs) {
        // Remove all highlights and restore original order (by create_time desc)
        rows.forEach(row => row.classList.remove('highlight-no-doc'));
        if (countSpan) countSpan.style.display = 'none';
        
        const openAllBtn = document.getElementById('open-all-highlighted-btn');
        if (openAllBtn) openAllBtn.style.display = 'none';
        
        // Restore original order: sort by Waktu Masuk descending
        const allRows = Array.from(tbody.querySelectorAll('tr'));
        if (allRows.length > 0 && allRows[0].cells.length >= 8) {
            allRows.sort((a, b) => {
                const dateA = new Date(a.cells[6]?.textContent.trim());
                const dateB = new Date(b.cells[6]?.textContent.trim());
                return dateB - dateA;
            });
            allRows.forEach((row, idx) => {
                row.cells[1].textContent = idx + 1;
                tbody.appendChild(row);
            });
        }
        // Reset sort indicators
        currentSortCol = null;
        currentSortDir = null;
        document.querySelectorAll('th.sortable').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
        return;
    }
    
    // Re-fetch if list is empty or module changed
    if (missingDocsList.length === 0 || missingDocsModule !== selectedModule) {
        try {
            const labelSpan = highlightToggle.parentElement.nextElementSibling;
            const originalText = labelSpan.textContent;
            labelSpan.innerHTML = '<div class="spinner" style="width:10px;height:10px;border-width:2px;display:inline-block;margin:0 5px 0 0;"></div> Memuat...';
            if (countSpan) countSpan.style.display = 'none';
            
            let url = `/api/xraydash/no-docs?module=${selectedModule}`;
            if (window.currentDateRange) {
                url += `&date_range=${encodeURIComponent(window.currentDateRange)}`;
            }
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                missingDocsList = data.missing_docs || [];
                missingDocsModule = selectedModule;
            }
            labelSpan.textContent = originalText;
        } catch (e) {
            console.error("Failed to fetch missing docs:", e);
        }
    }
    
    let highlightCount = 0;
    const upperMissingDocs = missingDocsList.map(doc => String(doc).toUpperCase());
    // Apply highlights based on container number in cell index 3
    const allRows = Array.from(tbody.querySelectorAll('tr'));
    allRows.forEach(row => {
        if (row.cells.length < 8) return; // Skip error/info rows
        const containerNo = row.cells[3]?.textContent.trim().toUpperCase();
        
        let isMissing = false;
        
        if (containerNo) {
            // 1. Check against external API list
            if (upperMissingDocs.includes(containerNo)) {
                isMissing = true;
            } 
            // 2. Check for broken double container format (e.g., "ABCD1234567/" or "/ABCD1234567")
            else if (containerNo.includes('/')) {
                const parts = containerNo.split('/');
                // If it contains a slash, both sides should be valid container numbers (usually 10-11 chars)
                if (parts[0].trim().length < 10 || parts[1].trim().length < 10) {
                    isMissing = true;
                }
            }
        }
        
        if (isMissing) {
            row.classList.add('highlight-no-doc');
            highlightCount++;
        } else {
            row.classList.remove('highlight-no-doc');
        }
    });
    
    // Move highlighted rows to top, keep relative order within each group
    const highlighted = allRows.filter(r => r.classList.contains('highlight-no-doc'));
    const normal = allRows.filter(r => !r.classList.contains('highlight-no-doc'));
    const sorted = [...highlighted, ...normal];
    sorted.forEach((row, idx) => {
        row.cells[1].textContent = idx + 1;
        tbody.appendChild(row);
    });
    
    if (countSpan) {
        countSpan.textContent = `${highlightCount} Task`;
        countSpan.style.display = 'inline-block';
    }
    
    // Show/hide Open All button
    const openAllBtn = document.getElementById('open-all-highlighted-btn');
    if (openAllBtn) {
        if (isHighlightingDocs && highlightCount > 0) {
            openAllBtn.style.display = 'inline-flex';
            openAllBtn.style.alignItems = 'center';
            openAllBtn.style.gap = '5px';
            openAllBtn.textContent = `Open Red Task (${highlightCount})`;
            openAllBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                Open Red Task (${highlightCount})
            `;
        } else {
            openAllBtn.style.display = 'none';
        }
    }
}

if (highlightToggle) {
    highlightToggle.addEventListener('change', applyDocHighlights);
}

// Open all highlighted button logic
const openAllBtn = document.getElementById('open-all-highlighted-btn');
if (openAllBtn) {
    openAllBtn.addEventListener('click', () => {
        const highlightedRows = document.querySelectorAll('tr.highlight-no-doc');
        if (highlightedRows.length === 0) return;
        
        let opened = 0;
        highlightedRows.forEach((row, idx) => {
            const checkbox = row.querySelector('.task-checkbox');
            if (checkbox && checkbox.dataset.id) {
                // Add a slight delay to prevent browsers from blocking multiple popups
                setTimeout(() => {
                    window.open(`inspection.html?id=${checkbox.dataset.id}`, '_blank');
                }, idx * 200);
                opened++;
            }
        });
        
        if (opened > 0) {
            Swal.fire({
                title: 'Membuka Tab',
                text: `${opened} task sedang dibuka di tab baru. Pastikan browser Anda mengizinkan popup.`,
                icon: 'info',
                timer: 3000,
                showConfirmButton: false
            });
        }
    });
}

// When module changes, save to localStorage, reset cached data and re-apply if toggle is active
if (moduleSelect) {
    moduleSelect.addEventListener('change', () => {
        localStorage.setItem('highlight-module', moduleSelect.value);
        missingDocsList = [];
        missingDocsModule = '';
        if (isHighlightingDocs) {
            applyDocHighlights();
        }
    });
}

document.getElementById('massSubmitBtn')?.addEventListener('click', async () => {
    const checkedBoxes = document.querySelectorAll('.task-checkbox:checked');
    if (checkedBoxes.length === 0) return;
    
    const confirmResult = await Swal.fire({
        title: 'Konfirmasi Mass Submit',
        text: `Yakin ingin men-submit ${checkedBoxes.length} task terpilih secara otomatis?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#2563EB',
        confirmButtonText: 'Submit Semua'
    });
    
    if (!confirmResult.isConfirmed) return;
    
    const btn = document.getElementById('massSubmitBtn');
    btn.disabled = true;
    btn.textContent = 'Memproses...';
    
    let success = 0, fail = 0;
    for (const cb of checkedBoxes) {
        try {
            const res = await fetch(`http://192.111.111.80:8000/api/tasks/${cb.dataset.id}/submit`, { method: 'POST' });
            if (res.ok) success++;
            else fail++;
        } catch(e) {
            fail++;
        }
    }
    
    Swal.fire('Selesai', `Berhasil: ${success}\nGagal: ${fail}`, success > 0 ? 'success' : 'warning');
    btn.disabled = false;
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) selectAllCheckbox.checked = false;
    
    fetchTasks();
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
        
        // Section 3: Manifest / EDI Data
        const manifest = data.manifest_data;
        if (manifest) {
            html += `
            <div class="detail-section">
                <h4 style="color: var(--accent);">📄 Data Manifest / EDI</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="label">Container No</span>
                        <span class="value" style="font-weight: bold;">${manifest.container_no}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Container Type</span>
                        <span class="value">${manifest.container_type}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Container Weight</span>
                        <span class="value">${manifest.container_weight}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Vehicle Type</span>
                        <span class="value">${manifest.vehicle_type}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Vehicle Serial</span>
                        <span class="value">${manifest.vehicle_serial}</span>
                    </div>
                </div>
            </div>`;
        }

        // Section 4: IPS Inspection Data (if exists)
        const ips = data.ips_data;
        if (ips) {
            html += `
            <div class="detail-section">
                <h4 style="color: var(--status-ready);">🔍 Hasil Inspeksi IPS</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="label">Waktu Scan X-Ray</span>
                        <span class="value">${ips.scan_time.replace(/\.\d+/, '')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Operator IPS</span>
                        <span class="value" style="font-weight: bold;">${ips.operator_id}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Keputusan (Conclusion)</span>
                        <span class="value state-badge state-ready" style="display:inline-block; margin-top:4px;">${ips.conclusion}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Waktu Keputusan (Submit)</span>
                        <span class="value">${ips.submit_time.replace(/\.\d+/, '')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Scan Direction</span>
                        <span class="value">${ips.scan_direction}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Energy Mode</span>
                        <span class="value">${ips.energy_mode}</span>
                    </div>
                </div>
            </div>`;
        }
        
        // Section 5: State Timeline
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
        
        html += `</div></div>
        <div style="margin-top: 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--border-color); padding-top: 15px;">
            <button class="btn primary-btn" onclick="manualSubmitTask(${task.id})">
                ✅ Auto-Submit "No Suspect"
            </button>
        </div>`;
        
        modalBody.innerHTML = html;
        
    } catch (error) {
        console.error('Failed to fetch details:', error);
        modalBody.innerHTML = '<p style="color: #ff3366;">Gagal mengambil detail. Pastikan backend berjalan.</p>';
    }
}
