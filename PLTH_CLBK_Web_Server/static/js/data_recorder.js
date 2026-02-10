/**
 * Data Recorder JavaScript
 * Handles interaction with the database API
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize components
    initRecorderUI();
    fetchRecorderStatus();
    
    // Set current date in summary date picker
    document.getElementById('summaryDate').valueAsDate = new Date();
    
    // Set default date range for queries (last 24 hours)
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    document.getElementById('startDate').value = formatDateTimeInput(yesterday);
    document.getElementById('endDate').value = formatDateTimeInput(now);
});

function formatDateTimeInput(date) {
    return date.toISOString().slice(0, 16);
}

function initRecorderUI() {
    // Setup event listeners
    document.getElementById('recordingSwitch').addEventListener('change', toggleRecording);
    document.getElementById('setIntervalBtn').addEventListener('click', updateInterval);
    document.getElementById('setRetentionBtn').addEventListener('click', updateRetention);
    document.getElementById('refreshBtn').addEventListener('click', fetchRecorderStatus);
    document.getElementById('queryForm').addEventListener('submit', queryData);
    document.getElementById('exportCsv').addEventListener('click', exportCSV);
    document.getElementById('exportJson').addEventListener('click', exportJSON);
    document.getElementById('exportXlsx').addEventListener('click', exportXLSX);
    document.getElementById('loadSummaryBtn').addEventListener('click', loadSummary);
    document.getElementById('generateSummaryBtn').addEventListener('click', generateSummary);
    
    // View toggle
    document.getElementById('tableView').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('tableViewContent').classList.remove('d-none');
            document.getElementById('chartViewContent').classList.add('d-none');
        }
    });
    
    document.getElementById('chartView').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('tableViewContent').classList.add('d-none');
            document.getElementById('chartViewContent').classList.remove('d-none');

            if (window.currentQueryData && window.currentQueryData.length > 0) {
                setupChartOptions();
            }
        }
    });
}

async function fetchRecorderStatus() {
    showSpinner('Fetching status...');
    
    try {
        const response = await fetch('/api/data-recorder/status');
        if (!response.ok) throw new Error('Failed to fetch recorder status');
        
        const data = await response.json();
        updateStatusUI(data);
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to fetch recorder status', 'danger');
    }
    
    hideSpinner();
}

function updateStatusUI(data) {
    // Update recorder status
    const statusElem = document.getElementById('recordingStatus');
    if (data.recording) {
        statusElem.innerHTML = '<span class="badge bg-success badge-recording">Recording</span>';
        document.getElementById('recordingSwitch').checked = true;
    } else {
        statusElem.innerHTML = '<span class="badge bg-secondary">Inactive</span>';
        document.getElementById('recordingSwitch').checked = false;
    }
    
    // Update other status info
    document.getElementById('currentInterval').textContent = `${data.record_interval} seconds`;
    document.getElementById('dataSource').textContent = data.data_source;
    document.getElementById('dbSize').textContent = data.db_size;
    document.getElementById('lastCleanup').textContent = formatDateTime(data.last_cleanup);
    document.getElementById('recordCount').textContent = data.record_count.toLocaleString();
    
    // Update input fields
    document.getElementById('recordInterval').value = data.record_interval;
    document.getElementById('retentionDays').value = data.days_to_keep;
}

async function toggleRecording() {
    const isActive = document.getElementById('recordingSwitch').checked;
    showSpinner(isActive ? 'Starting recording...' : 'Stopping recording...');
    
    try {
        const response = await fetch('/api/data-recorder/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ active: isActive })
        });
        
        if (!response.ok) throw new Error('Failed to toggle recording status');
        
        const result = await response.json();
        showToast(result.message, result.success ? 'success' : 'danger');
        
        // Update UI
        if (result.success) {
            fetchRecorderStatus();
        } else {
            // Revert UI state if operation failed
            document.getElementById('recordingSwitch').checked = !isActive;
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast(`Failed to ${isActive ? 'start' : 'stop'} recording`, 'danger');
        // Revert UI state
        document.getElementById('recordingSwitch').checked = !isActive;
    }
    
    hideSpinner();
}

async function updateInterval() {
    const interval = parseInt(document.getElementById('recordInterval').value);
    if (isNaN(interval) || interval < 1) {
        showToast('Please enter a valid interval (minimum 1 second)', 'warning');
        return;
    }
    
    showSpinner('Updating recording interval...');
    
    try {
        const response = await fetch('/api/data-recorder/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ record_interval: interval })
        });
        
        if (!response.ok) throw new Error('Failed to update interval');
        
        const result = await response.json();
        showToast(result.success ? `Recording interval updated to ${interval} seconds` : result.message, 
                  result.success ? 'success' : 'danger');
        
        if (result.success) {
            fetchRecorderStatus();
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to update recording interval', 'danger');
    }
    
    hideSpinner();
}

async function updateRetention() {
    const days = parseInt(document.getElementById('retentionDays').value);
    if (isNaN(days) || days < 1) {
        showToast('Please enter a valid number of days (minimum 1)', 'warning');
        return;
    }
    
    showSpinner('Updating data retention period...');
    
    try {
        const response = await fetch('/api/data-recorder/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days_to_keep: days })
        });
        
        if (!response.ok) throw new Error('Failed to update data retention');
        
        const result = await response.json();
        showToast(result.success ? `Data retention updated to ${days} days` : result.message,
                  result.success ? 'success' : 'danger');
        
        if (result.success) {
            fetchRecorderStatus();
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to update data retention period', 'danger');
    }
    
    hideSpinner();
}

// Global variable to store current query data
window.currentQueryData = [];
window.currentPage = 1;
window.itemsPerPage = 10;

async function queryData(event) {
    event.preventDefault();
    
    const moduleSelect = document.getElementById('moduleSelect').value;
    const startDate = document.getElementById('startDate').value ? new Date(document.getElementById('startDate').value).toISOString() : '';
    const endDate = document.getElementById('endDate').value ? new Date(document.getElementById('endDate').value).toISOString() : '';
    const limit = document.getElementById('limitRecords').value || 100;
    
    showSpinner('Querying database...');
    
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (moduleSelect) params.append('module', moduleSelect);
        if (startDate) params.append('start_time', startDate);
        if (endDate) params.append('end_time', endDate);
        if (limit) params.append('limit', limit);
        
        const response = await fetch(`/api/data-recorder/data?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to query data');
        
        const result = await response.json();
        
        // Store data globally
        window.currentQueryData = result.data || [];
        window.currentPage = 1;
        
        // Show data in current view
        if (document.getElementById('tableView').checked) {
            renderTableData();
        } else {
            setupChartOptions();
        }
        
        // Show result message
        showToast(`Found ${window.currentQueryData.length} records`, 
                 window.currentQueryData.length > 0 ? 'success' : 'info');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to query database', 'danger');
    }
    
    hideSpinner();
}

function renderTableData() {
    const tableBody = document.getElementById('dataTableBody');
    const pagination = document.getElementById('pagination');
    
    // If no data, show message
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No data found</td></tr>';
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

function renderPagination(totalPages) {
    const pagination = document.getElementById('pagination');
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

let chartInstance = null;

function setupChartOptions() {
    const chartContent = document.getElementById('chartViewContent');
    const chartVariableSelect = document.getElementById('chartVariable');
    
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        chartContent.innerHTML = '<div class="alert alert-info">No data available for charting</div>';
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
    
    // Setup chart variable change event
    chartVariableSelect.onchange = function() {
        renderChart(this.value);
    };
    
    // Initial chart render with first variable
    if (chartVariableSelect.options.length > 0) {
        renderChart(chartVariableSelect.value);
    } else {
        chartContent.innerHTML = '<div class="alert alert-warning">No numeric data available for charting</div>';
    }
}

function renderChart(variablePath) {
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
            '<div class="alert alert-warning">No data points available for selected variable</div>';
        return;
    }
    
    const ctx = document.getElementById('dataChart');
    
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
                        text: 'Time'
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

function formatDateTime(isoString) {
    if (!isoString) return '-';
    try {
        const date = new Date(isoString);
        return date.toLocaleString();
    } catch (e) {
        return isoString;
    }
}

function exportCSV() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    showSpinner('Preparing CSV export...');
    
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
        showToast('CSV export completed', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to export data to CSV', 'danger');
    }
    
    hideSpinner();
}

function exportJSON() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    showSpinner('Preparing JSON export...');
    
    try {
        const exportData = {
            exported_at: new Date().toISOString(),
            count: window.currentQueryData.length,
            data: window.currentQueryData
        };
        
        const json = JSON.stringify(exportData, null, 2);
        downloadFile(json, `sensor-data-${new Date().toISOString().slice(0,10)}.json`, 'application/json');
        showToast('JSON export completed', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to export data to JSON', 'danger');
    }
    
    hideSpinner();
}

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

async function loadSummary() {
    const date = document.getElementById('summaryDate').value;
    const module = document.getElementById('summaryModule').value;
    
    if (!date) {
        showToast('Please select a date', 'warning');
        return;
    }
    
    showSpinner('Loading summary data...');
    
    try {
        const params = new URLSearchParams();
        params.append('date', date);
        if (module) params.append('module', module);
        
        const response = await fetch(`/api/data-recorder/summary?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to load summary data');
        
        const result = await response.json();
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
                        showToast('Summary generated and loaded successfully', 'success');
                    } else {
                        showToast('No data available for selected date', 'info');
                    }
                } else {
                    renderSummaryTable([]);
                    showToast('Failed to generate summary: ' + (generateResult.message || 'Unknown error'), 'warning');
                }
            } else {
                renderSummaryTable([]);
                showToast('Failed to auto-generate summary', 'warning');
            }
        } else {
            renderSummaryTable(summaries);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to load summary data', 'danger');
    }
    
    hideSpinner();
}

function renderSummaryTable(summaries) {
    const tableBody = document.getElementById('summaryTableBody');
    
    if (!summaries || summaries.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No summary data found for selected date</td></tr>';
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

async function generateSummary() {
    const date = document.getElementById('summaryDate').value;
    
    if (!date) {
        showToast('Please select a date', 'warning');
        return;
    }
    
    showSpinner('Generating summary...');
    
    try {
        const response = await fetch('/api/data-recorder/generate-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date })
        });
        
        if (!response.ok) throw new Error('Failed to generate summary');
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Summary generated successfully', 'success');
            // Reload summary data
            await loadSummary();
        } else {
            showToast(result.message || 'Failed to generate summary', 'danger');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to generate summary', 'danger');
    }
    
    hideSpinner();
}

function showSpinner(message = 'Loading...') {
    const loadingModal = document.getElementById('loadingModal');
    document.getElementById('loadingMessage').textContent = message;
    
    if (window.bootstrap) {
        const modal = new bootstrap.Modal(loadingModal);
        modal.show();
    } else {
        loadingModal.style.display = 'block';
    }
}

function hideSpinner() {
    const loadingModal = document.getElementById('loadingModal');
    
    if (window.bootstrap) {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) modal.hide();
    } else {
        loadingModal.style.display = 'none';
    }
}

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
    if (window.bootstrap) {
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

function exportXLSX() {
    if (!window.currentQueryData || window.currentQueryData.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    if (typeof XLSX === 'undefined') {
        showToast('XLSX library not loaded. Cannot export to Excel format', 'danger');
        return;
    }
    
    showSpinner('Preparing Excel export...');
    
    try {
        // Get all unique data fields from all records
        const allFields = new Set();
        window.currentQueryData.forEach(item => {
            if (item.data) {
                Object.keys(item.data).forEach(key => allFields.add(key));
            }
        });
        
        // Transform data for Excel
        const excelData = window.currentQueryData.map(item => {
            // Create base record
            const record = {
                Timestamp: formatDateTime(item.timestamp),
                Module: item.module,
                DataSource: item.data_source
            };
            
            // Add all data fields
            if (item.data) {
                allFields.forEach(field => {
                    if (item.data[field] !== undefined) {
                        record[field] = item.data[field];
                    }
                });
            }
            
            return record;
        });
        
        // Create workbook and add worksheet
        const workbook = XLSX.utils.book_new();
        const worksheet = XLSX.utils.json_to_sheet(excelData);
        
        // Set column widths (optional)
        const columnWidths = [];
        worksheet['!cols'] = columnWidths;
        
        // Add worksheet to workbook
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Sensor Data');
        
        // Generate Excel file
        const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
        
        // Create Blob and trigger download
        const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `sensor-data-${new Date().toISOString().slice(0,10)}.xlsx`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
        
        showToast('Excel export completed', 'success');
        
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showToast('Failed to export data to Excel', 'danger');
    }
    
    hideSpinner();
}
