/**
 * Database Manager JavaScript
 * Handles interaction with the SQLite database API
 */

// Wait for content to be loaded
document.addEventListener('DOMContentLoaded', () => {
    // Clean up any orphaned modal components first
    cleanupModalComponents();
    
    try {
        console.log("Database manager initializing...");
        
        // Check if we're on the database page with database elements
        const recordingSwitchExists = document.getElementById('recordingSwitch') !== null;
        const queryFormExists = document.getElementById('queryForm') !== null;
        const isDatabasePage = window.location.pathname === '/data_recorder';
        
        if (recordingSwitchExists && queryFormExists && isDatabasePage) {
            console.log("Database UI elements found on database page, initializing...");
            
            // Initialize UI components
            initDatabaseUI();
            
            // Set current date in summary date picker
            const summaryDateEl = document.getElementById('summaryDate');
            if (summaryDateEl) {
                summaryDateEl.valueAsDate = new Date();
            }
            
            // Set default date range for queries (last 24 hours)
            const startDateEl = document.getElementById('startDate');
            const endDateEl = document.getElementById('endDate');
            if (startDateEl && endDateEl) {
                const now = new Date();
                const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                startDateEl.value = formatDateTimeInput(yesterday);
                endDateEl.value = formatDateTimeInput(now);
            }
            
            // Use a small timeout to ensure the UI is fully rendered before fetching status
            setTimeout(() => {
                console.log("Fetching database status...");
                fetchDatabaseStatus();
            }, 500);
        } else {
            console.log("Database UI elements not found, skipping initialization");
        }
    } catch (error) {
        console.error("Error initializing database manager:", error);
    }
});

/**
 * Format a Date object to a datetime-local input value
 */
function formatDateTimeInput(date) {
    if (!date) return '';
    return date.toISOString().slice(0, 16);
}

/**
 * Initialize the database UI components and event listeners
 */
function initDatabaseUI() {
    // Setup event listeners for database controls
    const recordingSwitch = document.getElementById('recordingSwitch');
    const setIntervalBtn = document.getElementById('setIntervalBtn');
    const setRetentionBtn = document.getElementById('setRetentionBtn');
    const refreshBtn = document.getElementById('db-refreshBtn');
    const queryForm = document.getElementById('queryForm');
    const exportCsv = document.getElementById('exportCsv');
    const exportJson = document.getElementById('exportJson');
    const exportXlsx = document.getElementById('exportXlsx');
    const loadSummaryBtn = document.getElementById('loadSummaryBtn');
    const generateSummaryBtn = document.getElementById('generateSummaryBtn');
    const tableView = document.getElementById('tableView');
    const chartView = document.getElementById('chartView');
    
    // Add event listeners if elements exist
    if (recordingSwitch) recordingSwitch.addEventListener('change', toggleRecording);
    if (setIntervalBtn) setIntervalBtn.addEventListener('click', updateInterval);
    if (setRetentionBtn) setRetentionBtn.addEventListener('click', updateRetention);
    if (refreshBtn) refreshBtn.addEventListener('click', fetchDatabaseStatus);
    if (queryForm) queryForm.addEventListener('submit', queryData);
    if (exportCsv) exportCsv.addEventListener('click', exportCSV);
    if (exportJson) exportJson.addEventListener('click', exportJSON);
    if (exportXlsx) exportXlsx.addEventListener('click', exportXLSX);
    if (loadSummaryBtn) loadSummaryBtn.addEventListener('click', loadSummary);
    if (generateSummaryBtn) generateSummaryBtn.addEventListener('click', generateSummary);
    
    // View toggle event listeners
    if (tableView) {
        tableView.addEventListener('change', function() {
            if (this.checked) {
                document.getElementById('tableViewContent').classList.remove('d-none');
                document.getElementById('chartViewContent').classList.add('d-none');
            }
        });
    }
    
    if (chartView) {
        chartView.addEventListener('change', function() {
            if (this.checked) {
                document.getElementById('tableViewContent').classList.add('d-none');
                document.getElementById('chartViewContent').classList.remove('d-none');
                
                if (window.currentQueryData && window.currentQueryData.length > 0) {
                    setupChartOptions();
                }
            }
        });
    }
    
    // Chart variable selection event listener
    const chartVariable = document.getElementById('chartVariable');
    if (chartVariable) {
        chartVariable.addEventListener('change', function() {
            if (window.currentQueryData && window.currentQueryData.length > 0) {
                renderChart(this.value);
            }
        });
    }
}

/**
 * Fetch the recorder status from the server
 */
/**
 * Fetch the recorder status from the server with robust error handling
 * @param {boolean} skipSpinner - If true, doesn't show the loading spinner
 * @param {number} retryCount - Number of retries attempted
 */
// Cache for status data
const statusCache = {
    data: null,
    timestamp: 0,
    TTL: 5000 // 5 seconds cache TTL
};

async function fetchDatabaseStatus(skipSpinner = false, retryCount = 0) {
    console.log(`Fetching recorder status (retry: ${retryCount})`);
    
    // Check if we have cached data and fresh
    const now = Date.now();
    if (statusCache.data && (now - statusCache.timestamp < statusCache.TTL)) {
        console.log('Using cached status data');
        updateStatusUI(statusCache.data);
        return true;
    }
    
    // Check if another request is already in progress (prevent multiple concurrent requests)
    if (window._fetchingStatus && !skipSpinner) {
        console.log('Another status fetch already in progress, skipping');
        return;
    }
    
    window._fetchingStatus = true;
    
    // Show loading spinner with message (unless skipped)
    if (!skipSpinner) {
        showSpinner('Mengambil status...');
    }
    
    // Always ensure spinner gets hidden, even if function crashes
    const safetyTimeout = setTimeout(() => {
        console.warn('Safety timeout triggered for spinner');
        try {
            hideSpinner();
            
            if (typeof window.forceCloseModal === 'function') {
                console.log('Calling force close from safety timeout');
                window.forceCloseModal();
            }
        } catch (e) {
            console.error('Error in safety timeout:', e);
            // Manual force cleanup if all else fails
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        }
    }, 3000); // 3 second safety net (reduced from 5)
    
    try {
        // Add timeout to prevent hanging indefinitely
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 seconds timeout (reduced from 3)
        
        // Make the fetch request with timeout
        const response = await fetch('/api/data-recorder/status', {
            signal: controller.signal,
            cache: 'no-store', // Avoid caching issues
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                // Add a random query param to truly prevent caching
                'X-Request-Time': Date.now().toString()
            }
        });
        
        clearTimeout(timeoutId); // Clear the timeout if fetch completes
        
        // Parse response - even if it's not 200, it might have useful data
        let data;
        try {
            const text = await response.text(); // Get raw text first
            console.log('Response text:', text.substring(0, 100) + '...'); // Log first 100 chars
            data = JSON.parse(text);
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        // Validate that data has expected structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response format');
        }
        
        // Handle response - our backend always returns HTTP 200 now
        if (data.database_available === false) {
            console.log('Database not available, showing fallback UI');
            // Don't throw an error, just show the data we have
        }
        
        // Always consider a valid JSON response as successful
        console.log('Valid response received:', data);
        
        // Clear safety timeout as we've succeeded
        clearTimeout(safetyTimeout);
        
        // Store data in cache
        statusCache.data = data;
        statusCache.timestamp = Date.now();
        
        // Update UI with received data
        updateStatusUI(data);
        
        // Success notification (but not on retries to avoid spam)
        if (retryCount === 0 && !skipSpinner) {
            if (data.database_available === true) {
                showToast('Status berhasil diperbarui', 'success');
            } else {
                showToast('Status diperbarui - database tidak tersedia', 'warning');
            }
        }
        
        // Success - hide spinner
        if (!skipSpinner) hideSpinner();
        
        // Clear the fetch in progress flag
        window._fetchingStatus = false;
        
        return true;
        
    } catch (error) {
        console.error('Error fetching status:', error);
        clearTimeout(safetyTimeout); // Clear safety timeout
        
        // Different handling based on error type and retry count
        if (error.name === 'AbortError' && retryCount < 2) {
            // Timeout but retries left - try once more silently
            console.log('Request timed out, retrying silently...');
            setTimeout(() => {
                fetchDatabaseStatus(true, retryCount + 1); // Retry without showing spinner
            }, 1000); // Wait 1 second before retry
            
        } else if (retryCount >= 2) {
            // Set default values
            showToast('Gagal mengambil status database setelah beberapa percobaan', 'warning');
            
            // Set default UI values since fetch failed
            updateStatusUI({
                recording: false,
                record_interval: 60,
                days_to_keep: 30,
                data_source: 'unknown',
                db_size: 'Tidak tersedia',
                record_count: 0,
                database_available: false
            });
            
        } else {
            showToast(`Gagal mengambil status: ${error.message}`, 'danger');
            
            
            updateStatusUI({
                recording: false,
                record_interval: 60,
                days_to_keep: 30,
                data_source: 'unknown',
                db_size: 'Tidak tersedia',
                record_count: 0,
                database_available: false
            });
        }
        
        // Always hide spinner on error, unless we're retrying silently
        if (!skipSpinner) hideSpinner();
        
        // Clear the fetch in progress flag
        window._fetchingStatus = false;
        
        return false;
    }
}

/**
 * Update the UI with recorder status information
 */
function updateStatusUI(data) {
    if (!data) {
        showToast('Data status tidak valid', 'warning');
        return;
    }

    const statusEl = document.getElementById('recordingStatus');
    const currentIntervalEl = document.getElementById('currentInterval');
    const dataSourceEl = document.getElementById('dataSource');
    const dbSizeEl = document.getElementById('dbSize');
    const lastCleanupEl = document.getElementById('lastCleanup');
    const recordCountEl = document.getElementById('recordCount');
    const recordIntervalEl = document.getElementById('recordInterval');
    const retentionDaysEl = document.getElementById('retentionDays');
    const recordingSwitch = document.getElementById('recordingSwitch');
    const databaseStatus = document.getElementById('databaseStatus');
    
    // Check database availability first
    const isDatabaseAvailable = data.database_available === true;
    
    // Update recorder status
    if (statusEl) {
        const isRecording = data.recording === true && isDatabaseAvailable;
        statusEl.innerHTML = isRecording ? 
            '<span class="badge bg-success badge-recording">Aktif</span>' : 
            '<span class="badge bg-secondary">Tidak Aktif</span>';
        
        // Update switch if it exists
        if (recordingSwitch) {
            recordingSwitch.checked = isRecording;
            recordingSwitch.disabled = !isDatabaseAvailable; 
        }
        
        // Update database status text
        if (databaseStatus) {
            if (isDatabaseAvailable) {
                databaseStatus.textContent = isRecording ? 'AKTIF' : 'NONAKTIF';
                databaseStatus.className = isRecording ? 'text-success' : 'text-secondary';
            } else {
                databaseStatus.textContent = 'TIDAK TERSEDIA';
                databaseStatus.className = 'text-danger';
            }
        }
    }
    
    // Update interval display based on availability
    if (currentIntervalEl) {
        currentIntervalEl.textContent = isDatabaseAvailable && data.record_interval ? 
            `${data.record_interval} detik` : 'N/A';
    }
    if (dataSourceEl) dataSourceEl.textContent = data.data_source || 'Unknown';
    if (dbSizeEl) {
        dbSizeEl.textContent = isDatabaseAvailable ? (data.db_size || 'N/A') : 'Tidak tersedia';
    }
    if (lastCleanupEl) {
        lastCleanupEl.textContent = isDatabaseAvailable ? 
            (formatDateTime(data.last_cleanup) || 'Belum pernah') : 'Tidak tersedia';
    }
    if (recordCountEl) {
        recordCountEl.textContent = isDatabaseAvailable && typeof data.record_count === 'number' ? 
            data.record_count.toLocaleString() : '0';
    }
    
    // Update input field values with default fallbacks
    if (recordIntervalEl) {
        recordIntervalEl.value = data.record_interval || 60;
        recordIntervalEl.disabled = !isDatabaseAvailable;
    }
    if (retentionDaysEl) {
        retentionDaysEl.value = data.days_to_keep || 30;
        retentionDaysEl.disabled = !isDatabaseAvailable;
    }
    
    
    if (!isDatabaseAvailable) {
        showToast('Database tidak tersedia - fitur recording dinonaktifkan', 'warning');
    }
}

/**
 * Toggle recording on/off
 */
async function toggleRecording() {
    const switchElement = document.getElementById('recordingSwitch');
    const isActive = switchElement.checked;
    
    // Check database availability before attempting to toggle
    if (isActive && switchElement.disabled) {
        showToast('Database tidak tersedia - tidak dapat memulai perekaman', 'warning');
        switchElement.checked = false;
        return;
    }
    
    showSpinner(isActive ? 'Memulai perekaman...' : 'Menghentikan perekaman...');
    
    try {
        const response = await fetch('/api/data-recorder/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ active: isActive })
        });
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        // Handle the response - our backend always returns HTTP 200 now
        if (result.database_available === false) {
            showToast('Database tidak tersedia - perekaman tidak dapat dilakukan', 'warning');
            switchElement.checked = false;
            switchElement.disabled = true;
        } else if (result.success) {
            showToast(result.message, 'success');
            fetchDatabaseStatus(); // Refresh status
        } else {
            showToast(result.message || 'Gagal mengubah status perekaman', 'danger');
            // Revert UI state if operation failed
            switchElement.checked = !isActive;
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast(`Gagal ${isActive ? 'memulai' : 'menghentikan'} perekaman`, 'danger');
        // Revert UI state
        switchElement.checked = !isActive;
    }
    
    hideSpinner();
}

/**
 * Update the recording interval
 */
async function updateInterval() {
    const interval = parseInt(document.getElementById('recordInterval').value);
    if (isNaN(interval) || interval < 1) {
        showToast('Masukkan interval valid (minimum 1 detik)', 'warning');
        return;
    }
    
    showSpinner('Mengupdate interval perekaman...');
    
    try {
        const response = await fetch('/api/data-recorder/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ record_interval: interval })
        });
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        showToast(
            result.success ? `Interval perekaman diupdate: ${interval} detik` : result.message, 
            result.success ? 'success' : 'danger'
        );
        
        if (result.success) {
            fetchDatabaseStatus();
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengupdate interval perekaman', 'danger');
    }
    
    hideSpinner();
}

/**
 * Update the data retention period
 */
async function updateRetention() {
    const days = parseInt(document.getElementById('retentionDays').value);
    if (isNaN(days) || days < 1) {
        showToast('Masukkan jumlah hari yang valid (minimum 1)', 'warning');
        return;
    }
    
    showSpinner('Mengupdate periode retensi data...');
    
    try {
        const response = await fetch('/api/data-recorder/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days_to_keep: days })
        });
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        showToast(
            result.success ? `Retensi data diupdate: ${days} hari` : result.message,
            result.success ? 'success' : 'danger'
        );
        
        if (result.success) {
            fetchDatabaseStatus();
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengupdate periode retensi data', 'danger');
    }
    
    hideSpinner();
}

// Global variables to store query data and pagination state
window.currentQueryData = [];
window.currentPage = 1;
window.itemsPerPage = 10;

/**
 * Query data from the database
 */
// Query result cache
const queryCache = new Map();

async function queryData(event) {
    if (event) event.preventDefault();
    
    const moduleSelect = document.getElementById('moduleSelect').value;
    const startDate = document.getElementById('startDate').value ? 
                     new Date(document.getElementById('startDate').value).toISOString() : '';
    const endDate = document.getElementById('endDate').value ? 
                   new Date(document.getElementById('endDate').value).toISOString() : '';
    const limit = document.getElementById('limitRecords').value || 100;
    
    // Create a cache key from the query parameters
    const cacheKey = `${moduleSelect}|${startDate}|${endDate}|${limit}`;
    
    // Check if we have a cached result for this query
    const cachedResult = queryCache.get(cacheKey);
    const now = Date.now();
    if (cachedResult && (now - cachedResult.timestamp < 60000)) { // 1 minute cache
        console.log('Using cached query data');
        window.currentQueryData = cachedResult.data;
        window.currentPage = 1;
        
        // Show data in current view
        if (document.getElementById('tableView').checked) {
            renderTableData();
        } else {
            setupChartOptions();
        }
        
        showToast(`Ditemukan ${window.currentQueryData.length} rekaman data (dari cache)`, 
                 window.currentQueryData.length > 0 ? 'success' : 'info');
        return;
    }
    
    showSpinner('Mengambil data...');
    
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (moduleSelect) params.append('module', moduleSelect);
        if (startDate) params.append('start_time', startDate);
        if (endDate) params.append('end_time', endDate);
        if (limit) params.append('limit', limit);
        
        // Add a timeout to the fetch
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`/api/data-recorder/data?${params.toString()}`, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        // Store data globally
        window.currentQueryData = result.data || [];
        window.currentPage = 1;
        
        // Store in cache
        queryCache.set(cacheKey, {
            data: window.currentQueryData,
            timestamp: Date.now()
        });
        
        // Limit cache size to avoid memory issues
        if (queryCache.size > 10) {
            // Delete the oldest entry
            const oldestKey = Array.from(queryCache.keys())[0];
            queryCache.delete(oldestKey);
        }
        
        // Show data in current view
        if (document.getElementById('tableView').checked) {
            renderTableData();
        } else {
            setupChartOptions();
        }
        
        // Show result message
        showToast(`Ditemukan ${window.currentQueryData.length} rekaman data`, 
                 window.currentQueryData.length > 0 ? 'success' : 'info');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengambil data dari database', 'danger');
    }
    
    hideSpinner();
}

/**
 * Render the query results in table format
 */
function renderTableData() {
    const tableBody = document.getElementById('dataTableBody');
    const pagination = document.getElementById('pagination');
    
    if (!tableBody || !pagination) return;
    
    // If no data, show message
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Tidak ada data</td></tr>';
        pagination.innerHTML = '';
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(window.currentQueryData.length / window.itemsPerPage);
    const startIdx = (window.currentPage - 1) * window.itemsPerPage;
    const endIdx = Math.min(startIdx + window.itemsPerPage, window.currentQueryData.length);
    const pageData = window.currentQueryData.slice(startIdx, endIdx);
    
    // Render table rows
    tableBody.innerHTML = pageData.map(item => `
        <tr>
            <td>${formatDateTime(item.timestamp)}</td>
            <td>${item.module}</td>
            <td>${item.data_source}</td>
            <td class="data-cell">${formatDataObject(item.data)}</td>
        </tr>
    `).join('');
    
    // Render pagination
    renderPagination(totalPages);
}

/**
 * Render the pagination controls
 */
function renderPagination(totalPages) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    html += `<li class="page-item ${window.currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${window.currentPage - 1}" aria-label="Previous">
            <span aria-hidden="true">&laquo;</span>
        </a>
    </li>`;
    
    // Page numbers
    let startPage = Math.max(1, window.currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    // Adjust start page if we're near the end
    if (endPage === totalPages) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<li class="page-item ${i === window.currentPage ? 'active' : ''}">
            <a class="page-link" href="#" data-page="${i}">${i}</a>
        </li>`;
    }
    
    // Next button
    html += `<li class="page-item ${window.currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${window.currentPage + 1}" aria-label="Next">
            <span aria-hidden="true">&raquo;</span>
        </a>
    </li>`;
    
    pagination.innerHTML = html;
    
    // Add event listeners to pagination links
    const pageLinks = pagination.querySelectorAll('.page-link');
    pageLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            if (!isNaN(page) && page >= 1 && page <= totalPages) {
                window.currentPage = page;
                renderTableData();
            }
        });
    });
}

// Variable to store chart instance
let chartInstance = null;

/**
 * Set up chart options based on available data
 */
function setupChartOptions() {
    const chartContent = document.getElementById('chartViewContent');
    const chartVariableSelect = document.getElementById('chartVariable');
    
    if (!chartContent || !chartVariableSelect) return;
    
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        chartContent.innerHTML = '<div class="alert alert-info">Tidak ada data untuk ditampilkan</div>';
        return;
    }
    
    // Find all numeric data fields from all modules
    const variables = new Set();
    window.currentQueryData.forEach(item => {
        if (item.data && typeof item.data === 'object') {
            Object.entries(item.data).forEach(([key, value]) => {
                if (typeof value === 'number') {
                    variables.add(`${item.module}.${key}`);
                }
            });
        }
    });
    
    // Populate variable select
    chartVariableSelect.innerHTML = '';
    Array.from(variables).sort().forEach(variable => {
        const option = document.createElement('option');
        option.value = variable;
        option.textContent = variable;
        chartVariableSelect.appendChild(option);
    });
    
    // Initial chart render with first variable
    if (chartVariableSelect.options.length > 0) {
        renderChart(chartVariableSelect.value);
    } else {
        chartContent.innerHTML = '<div class="alert alert-warning">Tidak ada data numerik tersedia</div>';
    }
}

/**
 * Render a chart for the selected variable
 */
function renderChart(variablePath) {
    if (!variablePath) return;
    
    // Parse module and field name
    const [module, field] = variablePath.split('.');
    
    // Extract data for the selected variable
    const chartData = window.currentQueryData
        .filter(item => item.module === module && item.data && typeof item.data[field] === 'number')
        .map(item => ({
            x: new Date(item.timestamp),
            y: item.data[field]
        }))
        .sort((a, b) => a.x - b.x); // Sort by timestamp
    
    if (chartData.length === 0) {
        document.getElementById('chartViewContent').innerHTML = 
            '<div class="alert alert-warning">Tidak ada data untuk variabel yang dipilih</div>';
        return;
    }
    
    const ctx = document.getElementById('dataChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    // Create new chart
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: variablePath,
                data: chartData,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                borderWidth: 2,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'YYYY-MM-DD HH:mm:ss',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Waktu'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: variablePath
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            return new Date(tooltipItems[0].raw.x).toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Format data object for display in table
 */
function formatDataObject(data) {
    if (!data || typeof data !== 'object') return String(data || '');
    
    let result = '<div class="small">';
    Object.entries(data).forEach(([key, value]) => {
        let displayValue = value;
        if (typeof value === 'number') {
            // Format numbers with 2 decimal places if they have decimals
            displayValue = Number.isInteger(value) ? value : value.toFixed(2);
        }
        result += `<div><strong>${key}:</strong> ${displayValue}</div>`;
    });
    result += '</div>';
    
    return result;
}

/**
 * Format ISO date string to localized date/time
 */
function formatDateTime(isoString) {
    if (!isoString) return '-';
    try {
        const date = new Date(isoString);
        return date.toLocaleString();
    } catch (e) {
        return isoString;
    }
}

/**
 * Export data to CSV format
 */
function exportCSV() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('Tidak ada data untuk diekspor', 'warning');
        return;
    }
    
    showSpinner('Mempersiapkan ekspor CSV...');
    
    try {
        // Get all unique data fields from all records
        const allFields = new Set();
        window.currentQueryData.forEach(item => {
            if (item.data) {
                Object.keys(item.data).forEach(key => allFields.add(key));
            }
        });
        
        // Create CSV header
        let csv = 'Timestamp,Module,DataSource';
        allFields.forEach(field => {
            csv += `,${field}`;
        });
        csv += '\n';
        
        // Add data rows
        window.currentQueryData.forEach(item => {
            // Add timestamp, module, data_source
            csv += `"${item.timestamp}","${item.module}","${item.data_source}"`;
            
            // Add data fields
            allFields.forEach(field => {
                const value = item.data && item.data[field] !== undefined ? item.data[field] : '';
                csv += `,"${value}"`;
            });
            
            csv += '\n';
        });
        
        // Create and trigger download
        downloadFile(csv, `sensor-data-${new Date().toISOString().slice(0,10)}.csv`, 'text/csv');
        showToast('Ekspor CSV selesai', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengekspor data ke CSV', 'danger');
    }
    
    hideSpinner();
}

/**
 * Export data to JSON format
 */
function exportJSON() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('Tidak ada data untuk diekspor', 'warning');
        return;
    }
    
    showSpinner('Mempersiapkan ekspor JSON...');
    
    try {
        const exportData = {
            exported_at: new Date().toISOString(),
            count: window.currentQueryData.length,
            data: window.currentQueryData
        };
        
        const json = JSON.stringify(exportData, null, 2);
        downloadFile(json, `sensor-data-${new Date().toISOString().slice(0,10)}.json`, 'application/json');
        showToast('Ekspor JSON selesai', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengekspor data ke JSON', 'danger');
    }
    
    hideSpinner();
}

/**
 * Export data to XLSX (Excel) format
 */
function exportXLSX() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('Tidak ada data untuk diekspor', 'warning');
        return;
    }
    
    showSpinner('Mempersiapkan ekspor Excel...');
    
    try {
        
        if (typeof XLSX === 'undefined') {
            throw new Error('XLSX library not loaded');
        }
        
        // Extract all unique data fields
        const allFields = extractUniqueDataFields();
        
        // Create worksheet data
        const wsData = [];
        
        // Add headers
        const headers = ['Timestamp', 'Module', 'Data Source', ...allFields];
        wsData.push(headers);
        
        // Add data rows
        window.currentQueryData.forEach(item => {
            const row = [
                item.timestamp,
                item.module,
                item.data_source
            ];
            
            // Add data fields
            allFields.forEach(field => {
                const value = item.data && item.data[field] !== undefined ? item.data[field] : '';
                row.push(value);
            });
            
            wsData.push(row);
        });
        
        // Create worksheet and workbook
        const ws = XLSX.utils.aoa_to_sheet(wsData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Sensor Data");
        
        // Generate Excel file and trigger download
        XLSX.writeFile(wb, `sensor-data-${new Date().toISOString().slice(0,10)}.xlsx`);
        showToast('Ekspor Excel selesai', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal mengekspor data ke Excel: ' + error.message, 'danger');
    }
    
    hideSpinner();
}

/**
 * Download a file to the client
 */
function downloadFile(content, fileName, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
}

/**
 * Load daily summary data
 */
async function loadSummary() {
    const date = document.getElementById('summaryDate').value;
    const module = document.getElementById('summaryModule').value;
    
    if (!date) {
        showToast('Pilih tanggal terlebih dahulu', 'warning');
        return;
    }
    
    showSpinner('Memuat data ringkasan...');
    
    try {
        const params = new URLSearchParams();
        params.append('date', date);
        if (module) params.append('module', module);
        
        const response = await fetch(`/api/data-recorder/summary?${params.toString()}`);
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        const summaries = result.summaries || [];
        
        // If no summaries found, try to generate them automatically
        if (summaries.length === 0) {
            console.log('No summaries found, attempting to generate...');
            const generateResponse = await fetch('/api/data-recorder/generate-summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ date })
            });
            
            if (generateResponse.ok) {
                const generateResult = await generateResponse.json();
                if (generateResult.success) {
                    // Retry loading summaries after generation
                    const retryResponse = await fetch(`/api/data-recorder/summary?${params.toString()}`);
                    const retryResult = await retryResponse.json();
                    const retrySummaries = retryResult.summaries || [];
                    
                    renderSummaryTable(retrySummaries);
                    
                    if (retrySummaries.length > 0) {
                        showToast('Ringkasan berhasil dibuat dan dimuat', 'success');
                    } else {
                        showToast('Tidak ada data untuk tanggal yang dipilih', 'info');
                    }
                } else {
                    renderSummaryTable([]);
                    showToast('Gagal membuat ringkasan: ' + (generateResult.message || 'Unknown error'), 'warning');
                }
            } else {
                renderSummaryTable([]);
                showToast('Gagal membuat ringkasan otomatis', 'warning');
            }
        } else {
            renderSummaryTable(summaries);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal memuat data ringkasan', 'danger');
    }
    
    hideSpinner();
}

/**
 * Render the summary table
 */
function renderSummaryTable(summaries) {
    const tableBody = document.getElementById('summaryTableBody');
    if (!tableBody) return;
    
    if (!summaries || summaries.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Tidak ada data ringkasan</td></tr>';
        return;
    }
    
    tableBody.innerHTML = summaries.map(summary => `
        <tr>
            <td>${summary.date}</td>
            <td>${summary.module}</td>
            <td class="data-cell">${formatDataObject(summary.min_values)}</td>
            <td class="data-cell">${formatDataObject(summary.max_values)}</td>
            <td class="data-cell">${formatDataObject(summary.avg_values)}</td>
            <td>${summary.samples_count}</td>
        </tr>
    `).join('');
}

/**
 * Generate a daily summary
 */
async function generateSummary() {
    const date = document.getElementById('summaryDate').value;
    
    if (!date) {
        showToast('Pilih tanggal terlebih dahulu', 'warning');
        return;
    }
    
    showSpinner('Membuat ringkasan...');
    
    try {
        const response = await fetch('/api/data-recorder/generate-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date })
        });
        
        let result;
        try {
            result = await response.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            throw new Error('Response data format invalid');
        }
        
        if (result.success) {
            showToast('Ringkasan berhasil dibuat', 'success');
            // Reload summary data
            await loadSummary();
        } else {
            showToast(result.message || 'Gagal membuat ringkasan', 'danger');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Gagal membuat ringkasan', 'danger');
    }
    
    hideSpinner();
}

// Global variable to track spinner timeouts
let spinnerTimeoutId = null;

/**
 * Show loading spinner with automatic timeout
 */
function showSpinner(message = 'Loading...') {
    // Clear any existing timeout to avoid conflicts
    if (spinnerTimeoutId) {
        clearTimeout(spinnerTimeoutId);
        spinnerTimeoutId = null;
    }
    
    const loadingModal = document.getElementById('loadingModal');
    if (!loadingModal) {
        console.warn('Loading modal element not found');
        return;
    }
    
    const loadingMessage = document.getElementById('loadingMessage');
    if (loadingMessage) {
        loadingMessage.textContent = message;
    }
    
    try {
        // First make sure no old modal or backdrop is still present
        try {
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        } catch (e) {
            console.error('Error cleaning up before showing modal:', e);
        }
        
        // Now show the modal properly
        if (window.bootstrap && bootstrap.Modal) {
            // Check if modal is already shown
            try {
                const existingModal = bootstrap.Modal.getInstance(loadingModal);
                if (existingModal) {
                    // Just update the message
                    return;
                }
            } catch (e) {
                console.error('Error checking if modal exists:', e);
            }
            
            // Try to create a new modal instance
            try {
                const modal = new bootstrap.Modal(loadingModal);
                modal.show();
            } catch (e) {
                console.error('Error showing bootstrap modal:', e);
                // Fallback to manual display
                loadingModal.classList.add('show');
                loadingModal.style.display = 'block';
                document.body.classList.add('modal-open');
            }
        } else {
            // Manual modal display
            loadingModal.classList.add('show');
            loadingModal.style.display = 'block';
            document.body.classList.add('modal-open');
        }
        
        // Set a safety timeout to hide the spinner after 7 seconds
        spinnerTimeoutId = setTimeout(() => {
            console.warn('Spinner timeout reached, forcing hide');
            hideSpinner();
            
            
            if (typeof window.forceCloseModal === 'function') {
                window.forceCloseModal();
            }
            
            showToast('Operasi terlalu lama, silakan coba lagi', 'warning');
        }, 7000); // 7 seconds timeout (reduced from 10)
        
    } catch (error) {
        console.error('Error showing spinner:', error);
    }
}

/**
 * Hide loading spinner
 */
function hideSpinner() {
    // Clear timeout if exists
    if (spinnerTimeoutId) {
        clearTimeout(spinnerTimeoutId);
        spinnerTimeoutId = null;
    }
    
    const loadingModal = document.getElementById('loadingModal');
    if (!loadingModal) {
        console.warn('Loading modal element not found');
        return;
    }
    
    // Try multiple approaches to ensure the modal is properly hidden
    console.log('Hiding spinner with multiple methods...');
    
    // Method 1: Bootstrap API
    try {
        if (window.bootstrap && bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(loadingModal);
            if (modal) modal.hide();
        }
    } catch (error) {
        console.error('Error hiding spinner via Bootstrap:', error);
    }
    
    // Method 2: Direct DOM manipulation (always run this as a fallback)
    try {
        // Remove any modal backdrops
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        
        // Hide and clean up the modal
        loadingModal.classList.remove('show');
        loadingModal.style.display = 'none';
        
        // Clean up body
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    } catch (e) {
        console.error('Fallback spinner hide failed:', e);
    }
    
    // Method 3: Last resort - try global force close
    try {
        if (typeof window.forceCloseModal === 'function') {
            window.forceCloseModal();
        }
    } catch (e) {
        console.error('Global force close failed:', e);
    }
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    // Get or create container - do not create it
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    container.appendChild(toastEl);
    
    // Initialize and show toast
    if (window.bootstrap && bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();
    } else {
        
        setTimeout(() => toastEl.remove(), 3000);
    }
    
    // Auto remove when hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

/**
 * Function to clean up any orphaned modal components
 */
function cleanupModalComponents() {
    // Clean up any orphaned modal backdrops
    const modalBackdrops = document.querySelectorAll('.modal-backdrop');
    if (modalBackdrops.length > 0) {
        console.log(`Cleaning up ${modalBackdrops.length} orphaned modal backdrops`);
        modalBackdrops.forEach(backdrop => backdrop.remove());
    }
    
    // Check if no modals are visible
    const visibleModals = document.querySelectorAll('.modal.show');
    if (visibleModals.length === 0 && document.body.classList.contains('modal-open')) {
        console.log('Removing modal-open class from body');
        document.body.classList.remove('modal-open');
    }
    
    // Reset any stuck modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (modal.classList.contains('show') && !modal.classList.contains('fade')) {
            console.log('Resetting stuck modal:', modal.id);
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
    });
}
