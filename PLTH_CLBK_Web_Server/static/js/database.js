/**
 * Database JavaScript
 * Handles interaction with the database API
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize components
    initDatabaseUI();
    fetchDatabaseStatus();
    
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

function initDatabaseUI() {
    // Setup event listeners
    document.getElementById('recordingSwitch').addEventListener('change', toggleRecording);
    document.getElementById('setIntervalBtn').addEventListener('click', updateInterval);
    document.getElementById('setRetentionBtn').addEventListener('click', updateRetention);
    document.getElementById('db-refreshBtn').addEventListener('click', fetchDatabaseStatus);
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

            updateChart();
        }
    });
}

function fetchDatabaseStatus() {
    fetch('/api/data-recorder/status')
        .then(response => response.json())
        .then(data => {
            updateStatusUI(data);
        })
        .catch(error => {
            console.error('Error fetching database status:', error);
            showToast('Error', 'Failed to fetch database status');
        });
}

function updateStatusUI(data) {
    // Update recording status badge
    const recordingStatusEl = document.getElementById('recordingStatus');
    const badge = recordingStatusEl.querySelector('.badge') || document.createElement('span');
    badge.className = data.recording ? 'badge bg-success' : 'badge bg-secondary';
    badge.textContent = data.recording ? 'Aktif' : 'Tidak Aktif';
    recordingStatusEl.innerHTML = '';
    recordingStatusEl.appendChild(badge);
    
    // Update toggle switch without triggering event
    const switchEl = document.getElementById('recordingSwitch');
    switchEl.checked = data.recording;
    
    // Update other status info
    document.getElementById('currentInterval').textContent = `${data.record_interval || 60} detik`;
    document.getElementById('dataSource').textContent = data.data_source === 'real' ? 'Sensor Nyata' : 'Simulasi';
    document.getElementById('dbSize').textContent = data.db_size || 'Unknown';
    document.getElementById('recordCount').textContent = `${data.record_count || 0} record`;
    

    if (data.last_cleanup) {
        const date = new Date(data.last_cleanup);
        document.getElementById('lastCleanup').textContent = date.toLocaleString();
    }
    
    // Update form fields
    document.getElementById('recordInterval').value = data.record_interval || 60;
    document.getElementById('retentionDays').value = data.days_to_keep || 30;
}

function toggleRecording() {
    const isActive = document.getElementById('recordingSwitch').checked;
    
    fetch('/api/data-recorder/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ active: isActive })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', data.message);
            fetchDatabaseStatus(); // Refresh status
        } else {
            showToast('Error', data.message || 'Failed to toggle recording');
            // Reset switch to previous state
            document.getElementById('recordingSwitch').checked = !isActive;
        }
    })
    .catch(error => {
        console.error('Error toggling recording:', error);
        showToast('Error', 'Failed to toggle recording');
        // Reset switch to previous state
        document.getElementById('recordingSwitch').checked = !isActive;
    });
}

function updateInterval() {
    const interval = parseInt(document.getElementById('recordInterval').value);
    
    if (isNaN(interval) || interval < 1) {
        showToast('Error', 'Please enter a valid interval (minimum 1 second)');
        return;
    }
    
    fetch('/api/data-recorder/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ record_interval: interval })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Recording interval updated');
            fetchDatabaseStatus(); // Refresh status
        } else {
            showToast('Error', data.message || 'Failed to update interval');
        }
    })
    .catch(error => {
        console.error('Error updating interval:', error);
        showToast('Error', 'Failed to update interval');
    });
}

function updateRetention() {
    const days = parseInt(document.getElementById('retentionDays').value);
    
    if (isNaN(days) || days < 1) {
        showToast('Error', 'Please enter a valid number of days (minimum 1 day)');
        return;
    }
    
    fetch('/api/data-recorder/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ days_to_keep: days })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Data retention period updated');
            fetchDatabaseStatus(); // Refresh status
        } else {
            showToast('Error', data.message || 'Failed to update retention period');
        }
    })
    .catch(error => {
        console.error('Error updating retention period:', error);
        showToast('Error', 'Failed to update retention period');
    });
}
