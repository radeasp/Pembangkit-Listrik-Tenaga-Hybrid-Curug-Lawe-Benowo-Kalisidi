import { initSensorModules, getModuleData, getAvailableParameters, getParameterData } from './sensorData.js';

const SENSOR_MODULES = {
    'picohydro_generator': {
        name: 'Picohydro Generator',
        sensors: {
            'picohydro_voltage': { name: 'Tegangan', unit: 'V', type: 'number' },
            'picohydro_current': { name: 'Arus', unit: 'A', type: 'number' },
            'picohydro_power': { name: 'Daya', unit: 'W', type: 'number', derived: true },
            'picohydro_rpm': { name: 'Putaran Turbin', unit: 'RPM', type: 'number' },
        }
    },
    'solar_panel_generator': {
        name: 'Solar Panel',
        sensors: {
            'solar_voltage': { name: 'Tegangan', unit: 'V', type: 'number' },
            'solar_current': { name: 'Arus', unit: 'A', type: 'number' },
            'solar_power': { name: 'Daya', unit: 'W', type: 'number', derived: true },
            'lighting': { name: 'Pencahayaan', unit: 'Lux', type: 'number' },
        }
    },
    'baterai': {
        name: 'Baterai',
        sensors: {
            'battery_voltage': { name: 'Tegangan', unit: 'V', type: 'number' },
            'battery_net_current': { name: 'Arus Total', unit: 'A', type: 'number', derived: true },
            'battery_input_current': { name: 'Arus Charging', unit: 'A', type: 'number' },
            'battery_output_current': { name: 'Arus Discharging', unit: 'A', type: 'number' },
        }
    },
    'beban': {
        name: 'Beban',
        sensors: {
            'battery_voltage': { name: 'Tegangan Baterai', unit: 'V', type: 'number' },
            'dc_input_current': { name: 'Arus DC Baterai', unit: 'A', type: 'number' },
            'dc_input_power': { name: 'Daya DC Baterai', unit: 'W', type: 'number', derived: true },
            'ac_output_voltage': { name: 'Tegangan AC Output', unit: 'V', type: 'number' },
            'ac_output_current': { name: 'Arus AC Output', unit: 'A', type: 'number' },
            'ac_output_power': { name: 'Daya AC Output', unit: 'W', type: 'number', derived: true }
        }
    },
    'dump_load': {
        name: 'Dump Load',
        sensors: {
            'picohydro_voltage': { name: 'Tegangan Generator', unit: 'V', type: 'number' },
            'picohydro_charging_current': { name: 'Arus Charging', unit: 'A', type: 'number' },
            'picohydro_charging_power': { name: 'Daya Charging', unit: 'W', type: 'number', derived: true },
            'dumpload_voltage': { name: 'Tegangan', unit: 'V', type: 'number' },
            'dumpload_current': { name: 'Arus', unit: 'A', type: 'number' },
            'dumpload_power': { name: 'Daya', unit: 'W', type: 'number', derived: true }
        }
    },
    'environment': {
        name: 'Environment',
        sensors: {
            'temperature': { name: 'Temperatur', unit: '°C', type: 'number' },
            'humidity': { name: 'Kelembapan', unit: '%', type: 'number' },
            'pressure': { name: 'Tekanan Udara', unit: 'Pa', type: 'number' },
            'tma_value': { name: 'Tinggi Muka Air', unit: 'cm', type: 'number' },
        }
    }
};

// Global variables
let isRecording = false;
let recordingStartTime = null;
let recordingInterval = null;
let recordedData = [];
let currentSensorData = {};
let durationTimer = null;
let sensorModulesInitialized = false;

// Utility function to get status display
function getStatusDisplay(value) {
    if (typeof value === 'boolean') {
        return value ? 'Terbuka' : 'Tertutup';
    }
    return value === 1 || value === '1' ? 'Terbuka' : 'Tertutup';
}

// Inisialisasi sensor modules
async function initializeSensorModules() {
    if (sensorModulesInitialized) return;
    
    try {
        const moduleNames = Object.keys(SENSOR_MODULES);
        console.log('Initializing sensor modules:', moduleNames);
        
        await initSensorModules(moduleNames);
        sensorModulesInitialized = true;
        
        console.log('All sensor modules initialized successfully');
        
        // Start collecting current data
        startDataCollection();
        
    } catch (error) {
        console.error('Failed to initialize sensor modules:', error);
        throw error;
    }
}

// Mulai pengumpulan data real-time
function startDataCollection() {
    // Update data setiap detik
    setInterval(async () => {
        await updateCurrentSensorData();
    }, 1000);
}

// Update data sensor saat ini dengan derived parameters
async function updateCurrentSensorData() {
    if (!sensorModulesInitialized) return;
    
    const allData = {};
    
    try {
        // Import processData dari sensorData.js untuk menggunakan perhitungan yang sudah ada
        const { processData } = await import('./sensorData.js');
        
        // Ambil data dari semua modul
        for (const moduleName of Object.keys(SENSOR_MODULES)) {
            const { latestData } = await getModuleData(moduleName);
            
            // Gunakan processData dari sensorData.js untuk mendapatkan data yang sudah dihitung
            const processedData = processData(moduleName, latestData);
            
            // Tambahkan data dengan prefix module
            Object.keys(processedData).forEach(sensorKey => {
                const fullKey = `${moduleName}.${sensorKey}`;
                allData[fullKey] = processedData[sensorKey];
            });
        }
        
        currentSensorData = allData;
        updateSensorDisplay();
        
    } catch (error) {
        console.error('Error updating current sensor data:', error);
    }
}

// Update tampilan sensor values
function updateSensorDisplay() {
    if (!currentSensorData) return;
    
    // Update nilai untuk setiap sensor yang ada
    Object.keys(currentSensorData).forEach(fullKey => {
        const valueElement = document.getElementById(`value_${fullKey.replace('.', '_')}`);
        if (valueElement) {
            const value = currentSensorData[fullKey];
            
            // Cek apakah ini sensor status
            const [moduleName, sensorKey] = fullKey.split('.');
            const sensorConfig = SENSOR_MODULES[moduleName]?.sensors[sensorKey];
            
            if (sensorConfig && sensorConfig.type === 'status') {
                valueElement.textContent = getStatusDisplay(value);
            } else {
                // Pastikan derived parameters ditampilkan dengan benar
                let displayValue;
                if (value === null || value === undefined) {
                    displayValue = '-';
                } else if (typeof value === 'number') {
                    // Untuk derived parameters, pastikan formatnya konsisten
                    displayValue = value.toFixed(2);
                } else {
                    displayValue = value;
                }
                valueElement.textContent = displayValue;
            }
        }
    });
    
    // Debug log untuk derived parameters
    const derivedValues = {};
    Object.keys(currentSensorData).forEach(fullKey => {
        const [moduleName, sensorKey] = fullKey.split('.');
        const sensorConfig = SENSOR_MODULES[moduleName]?.sensors[sensorKey];
        if (sensorConfig && sensorConfig.derived) {
            derivedValues[fullKey] = currentSensorData[fullKey];
        }
    });
    
    if (Object.keys(derivedValues).length > 0) {
        console.log('Current derived values:', derivedValues);
    }
}

// Generate sensor selection UI TANPA derived tags
function generateSensorSelectionUI() {
    const container = document.getElementById('sensorSelection');
    if (!container) return;
    
    container.innerHTML = '';
    
    Object.keys(SENSOR_MODULES).forEach(moduleName => {
        const moduleConfig = SENSOR_MODULES[moduleName];
        
        // Create module section
        const moduleDiv = document.createElement('div');
        moduleDiv.className = 'module-section';
        moduleDiv.innerHTML = `
            <h3>${moduleConfig.name}</h3>
            <div class="module-sensors" id="sensors_${moduleName}"></div>
        `;
        
        const sensorsDiv = moduleDiv.querySelector(`#sensors_${moduleName}`);
        
        // Add sensors for this module
        Object.keys(moduleConfig.sensors).forEach(sensorKey => {
            const sensorConfig = moduleConfig.sensors[sensorKey];
            const fullKey = `${moduleName}.${sensorKey}`;
            
            const sensorDiv = document.createElement('div');
            sensorDiv.className = 'sensor-item';
            // REMOVED: derived tag completely - no longer showing derived status
            sensorDiv.innerHTML = `
                <label>
                    <input type="checkbox" data-variable="${fullKey}" data-module="${moduleName}">
                    <span class="sensor-name">${sensorConfig.name}</span>
                    <span class="sensor-unit">(${sensorConfig.unit})</span>
                    <span class="sensor-value" id="value_${fullKey.replace('.', '_')}">-</span>
                </label>
            `;
            
            sensorsDiv.appendChild(sensorDiv);
        });
        
        container.appendChild(moduleDiv);
    });
}

// Fungsi untuk memulai recording
async function startRecording() {
    recordingStartTime = new Date();
    if (!sensorModulesInitialized) {
        alert('Sensor modules belum diinisialisasi. Mohon tunggu...');
        return;
    }
    
    const interval = parseInt(document.getElementById('recordingInterval').value);
    const maxPoints = parseInt(document.getElementById('maxDataPoints').value);
    
    if (interval < 100 || interval > 10000) {
        alert('Recording interval must be between 100-10000 ms');
        return;
    }
    
    const selectedSensors = getSelectedSensors();
    if (selectedSensors.length === 0) {
        alert('Please select at least one sensor to record');
        return;
    }
    
    isRecording = true;
    recordingStartTime = new Date();
    recordedData = [];
    
    // Update UI
    document.getElementById('statusText').textContent = 'Merekam...';
    document.getElementById('statusDot').classList.add('recording');
    document.getElementById('startRecording').disabled = true;
    document.getElementById('stopRecording').disabled = false;
    document.getElementById('downloadCSV').disabled = true;
    document.getElementById('downloadExcel').disabled = true;
    
    // Start recording interval
    recordingInterval = setInterval(() => {
        if (recordedData.length >= maxPoints) {
            clearInterval(recordingInterval);
            clearInterval(durationTimer);
            isRecording = false;

            // update state UI
            stopRecording();   // <-- memanggil sekali lagi, atau pisahkan logic enable
            alert(`Maximum data points (${maxPoints}) reached. Recording stopped.`);
            return;
        }
        
        recordDataPoint();
    }, interval);
    
    // Start duration timer
    durationTimer = setInterval(updateDuration, 1000);
    
    console.log('Recording started with', selectedSensors.length, 'sensors');
}

// Fungsi untuk menghentikan recording
function stopRecording() {
    isRecording = false;
    if (recordedData.length > 0) {
        document.getElementById('downloadCSV').disabled = false;
        document.getElementById('downloadExcel').disabled = false;
    }

    if (recordingInterval) {
        clearInterval(recordingInterval);
        recordingInterval = null;
    }
    
    if (durationTimer) {
        clearInterval(durationTimer);
        durationTimer = null;
    }
    
    // Update UI
    document.getElementById('statusText').textContent = 'Selesai';
    document.getElementById('statusDot').classList.remove('recording');
    document.getElementById('startRecording').disabled = false;
    document.getElementById('stopRecording').disabled = true;
    document.getElementById('downloadCSV').disabled = recordedData.length === 0;
    document.getElementById('downloadExcel').disabled = recordedData.length === 0;

    console.log('Recording stopped, total data points:', recordedData.length);
}

// Fungsi untuk merekam satu data point dengan derived parameters
function recordDataPoint() {
    const selectedSensors = getSelectedSensors();
    if (selectedSensors.length === 0) return;
    
    const timestamp = new Date().toISOString();
    const dataPoint = { timestamp };
    
    selectedSensors.forEach(fullKey => {
        if (currentSensorData[fullKey] !== undefined) {
            const [moduleName, sensorKey] = fullKey.split('.');
            const sensorConfig = SENSOR_MODULES[moduleName]?.sensors[sensorKey];
            
            if (sensorConfig && sensorConfig.type === 'status') {
                // Untuk status, simpan sebagai 1/0
                dataPoint[fullKey] = typeof currentSensorData[fullKey] === 'boolean' ? 
                    (currentSensorData[fullKey] ? 1 : 0) :
                    (getStatusDisplay(currentSensorData[fullKey]) === 'Terbuka' ? 1 : 0);
            } else {
                // Langsung ambil nilai dari currentSensorData yang sudah termasuk derived parameters
                dataPoint[fullKey] = currentSensorData[fullKey];
            }
        } else {
            // Jika data tidak tersedia di currentSensorData, coba ambil dari buffer DataManager
            const [moduleName, sensorKey] = fullKey.split('.');
            const manager = window.DataManager?.instances?.[moduleName];
            
            if (manager && manager.dataBuffers.has(sensorKey)) {
                const buffer = manager.dataBuffers.get(sensorKey);
                if (buffer.length > 0) {
                    const latest = buffer[buffer.length - 1];
                    dataPoint[fullKey] = latest.y;
                } else {
                    dataPoint[fullKey] = null;
                }
            } else {
                dataPoint[fullKey] = null;
            }
        }
    });
    
    recordedData.push(dataPoint);
    
    // Debug log untuk derived parameters
    const derivedParams = selectedSensors.filter(fullKey => {
        const [moduleName, sensorKey] = fullKey.split('.');
        return SENSOR_MODULES[moduleName]?.sensors[sensorKey]?.derived;
    });
    
    if (derivedParams.length > 0) {
        console.log('Recorded derived parameters:', derivedParams.map(key => ({
            param: key,
            value: dataPoint[key]
        })));
    }
    
    // Update UI counters
    updateCounters();
    updatePreviewTable();
}

// Get selected sensors
function getSelectedSensors() {
    const checkboxes = document.querySelectorAll('.sensor-item input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.dataset.variable);
}

// Update counters
function updateCounters() {
    document.getElementById('dataPointsCount').textContent = recordedData.length;
    
    // Estimate file size
    const csvSize = estimateCSVSize();
    document.getElementById('fileSize').textContent = formatBytes(csvSize);
}

// Estimate CSV file size
function estimateCSVSize() {
    if (recordedData.length === 0) return 0;
    
    const headers = Object.keys(recordedData[0]).join(',') + '\n';
    const avgRowSize = recordedData.slice(0, Math.min(10, recordedData.length))
        .reduce((acc, row) => acc + Object.values(row).join(',').length + 1, 0) / 
        Math.min(10, recordedData.length);
    
    return headers.length + (avgRowSize * recordedData.length);
}

// Format bytes to human readable
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Function to select/deselect sensors by module dengan update button state
function selectByModule(moduleName) {
    const checkboxes = document.querySelectorAll(`input[data-module="${moduleName}"]`);
    
    if (checkboxes.length === 0) {
        console.warn(`No sensors found for module: ${moduleName}`);
        return;
    }
    
    // Check if all checkboxes in this module are currently selected
    const allSelected = Array.from(checkboxes).every(checkbox => checkbox.checked);
    
    // Toggle selection: if all are selected, deselect all; otherwise select all
    const shouldSelect = !allSelected;
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = shouldSelect;
        // Trigger change event if you have listeners
        checkbox.dispatchEvent(new Event('change'));
    });
    
    // Update module button states
    updateModuleButtonStates();
}

// Function to update module button states based on checkbox states
function updateModuleButtonStates() {
    const moduleButtons = document.querySelectorAll('.btn-module[data-module]');
    
    moduleButtons.forEach(button => {
        const moduleName = button.getAttribute('data-module');
        const moduleCheckboxes = document.querySelectorAll(`input[data-module="${moduleName}"]`);
        
        if (moduleCheckboxes.length > 0) {
            const allSelected = Array.from(moduleCheckboxes).every(checkbox => checkbox.checked);
            
            if (allSelected) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        }
    });
}

// Function to handle select all functionality
function selectAllSensors() {
    const allCheckboxes = document.querySelectorAll('.sensor-item input[type="checkbox"]');
    allCheckboxes.forEach(checkbox => {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change'));
    });
    updateModuleButtonStates();
}

// Function to handle deselect all functionality
function deselectAllSensors() {
    const allCheckboxes = document.querySelectorAll('.sensor-item input[type="checkbox"]');
    allCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
        checkbox.dispatchEvent(new Event('change'));
    });
    updateModuleButtonStates();
}

// Function to create sensor HTML with unit after value - NO DERIVED TAG
function createSensorItemHTML(sensor, moduleName) {
    const isChecked = ''; // Semua sensor default unchecked
    // REMOVED: derivedTag completely - no longer showing derived status
    
    return `
        <div class="sensor-item">
            <input type="checkbox" id="${sensor.id}" data-module="${moduleName}" ${isChecked}>
            <label for="${sensor.id}">
                <div class="sensor-info">
                    <span class="sensor-name">${sensor.name}</span>
                </div>
                <div class="sensor-value-with-unit">
                    <span class="value">${sensor.value || '0'}</span>
                    <span class="unit">${sensor.unit || ''}</span>
                </div>
            </label>
        </div>
    `;
}

// Update duration display
function updateDuration() {
    if (!recordingStartTime) return;
    
    const now = new Date();
    const diff = now - recordingStartTime;
    
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    const formatted = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('recordingDuration').textContent = formatted;
}

// Update preview table
function updatePreviewTable() {
    const tableHeader = document.getElementById('tableHeader');
    const tableBody = document.getElementById('tableBody');
    
    if (recordedData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="100%">No data recorded yet</td></tr>';
        return;
    }
    
    // Update header
    const headers = Object.keys(recordedData[0]);
    tableHeader.innerHTML = '<tr>' + 
        headers.map(header => {
            if (header === 'timestamp') return '<th>Timestamp</th>';
            
            // Parse module and sensor name
            const [moduleName, sensorKey] = header.split('.');
            const sensorConfig = SENSOR_MODULES[moduleName]?.sensors[sensorKey];
            const displayName = sensorConfig ? 
                `${SENSOR_MODULES[moduleName].name} - ${sensorConfig.name}` : 
                header;
            
            return `<th>${displayName}</th>`;
        }).join('') + 
        '</tr>';
    
    // Update body with last 10 records
    const lastRecords = recordedData.slice(-10).reverse();
    tableBody.innerHTML = lastRecords.map(record => 
        '<tr>' + 
        headers.map(header => {
            if (header === 'timestamp') {
                return `<td>${new Date(record[header]).toLocaleString()}</td>`;
            }
            const value = record[header];
            if (value === null || value === undefined) return '<td>-</td>';
            
            // Check if this is a status sensor
            const [moduleName, sensorKey] = header.split('.');
            const sensorConfig = SENSOR_MODULES[moduleName]?.sensors[sensorKey];
            if (sensorConfig && sensorConfig.type === 'status') {
                return `<td>${value === 1 ? 'Terbuka' : 'Tertutup'}</td>`;
            }
            return `<td>${typeof value === 'number' ? value.toFixed(2) : value}</td>`;
        }).join('') + 
        '</tr>'
    ).join('');
}

// Download data as CSV
function downloadCSV() {
    if (recordedData.length === 0) {
        alert('No data to download');
        return;
    }
    
    const selectedSensors = getSelectedSensors();
    const filename = document.getElementById('filename').value.trim() || 'sensor_data';
    
    // Prepare CSV content
    const headers = ['timestamp', ...selectedSensors];
    const csvHeaders = headers.map(header => {
        if (header === 'timestamp') return 'Timestamp';
        
        const [moduleName, sensorKey] = header.split('.');
        const moduleConfig = SENSOR_MODULES[moduleName];
        const sensorConfig = moduleConfig?.sensors[sensorKey];
        
        if (sensorConfig) {
            return `${moduleConfig.name} - ${sensorConfig.name} (${sensorConfig.unit})`;
        }
        return header;
    });
    
    let csvContent = csvHeaders.join(',') + '\n';
    
    recordedData.forEach(record => {
        const row = headers.map(header => {
            const value = record[header];
            if (value === null || value === undefined) return '';
            if (header === 'timestamp') return `"${record[header]}"`;
            return value;
        });
        csvContent += row.join(',') + '\n';
    });
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('CSV downloaded with', selectedSensors.length, 'sensors');
}

function downloadExcel() {
    if (recordedData.length === 0) {
        alert('No data to download');
        return;
    }
    
    const selectedSensors = getSelectedSensors();
    const filename = document.getElementById('filename')?.value.trim() || 'sensor_data';
    
    try {
        // Cek apakah XLSX library tersedia (tanpa console log)
        if (typeof XLSX === 'undefined') {
            alert('Excel library not loaded. Please refresh the page and try again.');
            return;
        }
        
        // Prepare headers dengan informasi lengkap
        const headers = ['timestamp', ...selectedSensors];
        const excelHeaders = headers.map(header => {
            if (header === 'timestamp') return 'Timestamp';
            
            const [moduleName, sensorKey] = header.split('.');
            const moduleConfig = SENSOR_MODULES[moduleName];
            const sensorConfig = moduleConfig?.sensors[sensorKey];
            
            if (sensorConfig) {
                return `${moduleConfig.name} - ${sensorConfig.name} (${sensorConfig.unit})`;
            }
            return header;
        });
        
        // Prepare data array untuk Excel
        const excelData = [];
        
        // Add header row
        excelData.push(excelHeaders);
        
        // Add data rows
        recordedData.forEach(record => {
            const row = headers.map(header => {
                const value = record[header];
                if (value === null || value === undefined) return '';
                if (header === 'timestamp') {
                    return new Date(record[header]).toLocaleString();
                }
                if (typeof value === 'number') {
                    return value;
                }
                return value;
            });
            excelData.push(row);
        });
        
        // Create workbook dengan error handling
        let wb;
        try {
            wb = XLSX.utils.book_new();
        } catch (error) {
            throw new Error('Failed to create Excel workbook');
        }
        
        // Create worksheet dengan error handling
        let ws;
        try {
            ws = XLSX.utils.aoa_to_sheet(excelData);
        } catch (error) {
            throw new Error('Failed to create Excel worksheet');
        }
        
        // Set column widths (optional)
        try {
            const colWidths = excelHeaders.map(header => ({
                wch: Math.min(Math.max(header.length, 15), 50)
            }));
            ws['!cols'] = colWidths;
        } catch (error) {
            // Continue without column widths
        }
        
        // Add worksheet to workbook
        try {
            XLSX.utils.book_append_sheet(wb, ws, 'Sensor Data');
        } catch (error) {
            throw new Error('Failed to add worksheet to workbook');
        }
        
        // Add metadata sheet (simplified version)
        try {
            const metadataWs = createSimpleMetadataSheet(selectedSensors);
            XLSX.utils.book_append_sheet(wb, metadataWs, 'Info');
        } catch (error) {
            // Continue without metadata sheet
        }
        
        // Generate Excel file dengan error handling
        try {
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const excelFilename = `${filename}_${timestamp}.xlsx`;
            
            XLSX.writeFile(wb, excelFilename);
            
            // Hanya log ini jika sukses (atau bisa dihapus juga)
            // console.log('Excel file downloaded successfully');
            
            // Optional: tampilkan alert sukses (bisa dikomentari jika tidak perlu)
            // alert('Excel file downloaded successfully!');
            
        } catch (writeError) {
            // Fallback: coba download sebagai blob
            try {
                const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
                const blob = new Blob([wbout], { type: 'application/octet-stream' });
                
                const link = document.createElement('a');
                const url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                
                // Optional log untuk fallback method
                // console.log('Excel downloaded via fallback method');
                
            } catch (blobError) {
                throw new Error('All Excel download methods failed');
            }
        }
        
    } catch (error) {
        // Hanya log error yang penting
        console.error('Excel download failed:', error.message);
        alert(`Error creating Excel file: ${error.message}\nPlease try CSV export instead.`);
        
        // Sebagai fallback, tawarkan untuk download CSV
        if (confirm('Excel download failed. Would you like to download as CSV instead?')) {
            downloadCSV();
        }
    }
}

function createSimpleMetadataSheet(selectedSensors) {
    const metadataData = [
        ['Recording Information'],
        ['Recording Start Time', recordingStartTime ? recordingStartTime.toISOString() : 'N/A'],
        ['Recording End Time', new Date().toISOString()],
        ['Total Data Points', recordedData.length],
        ['Recording Interval (ms)', document.getElementById('recordingInterval')?.value || 'N/A'],
        ['Selected Sensors Count', selectedSensors.length],
        [''],
        ['Selected Sensors'],
        ['Module', 'Sensor Name', 'Unit']
    ];
    
    // Add sensor information (simplified)
    selectedSensors.forEach(fullKey => {
        const [moduleName, sensorKey] = fullKey.split('.');
        const moduleConfig = SENSOR_MODULES[moduleName];
        const sensorConfig = moduleConfig?.sensors[sensorKey];
        
        if (sensorConfig) {
            metadataData.push([
                moduleConfig.name,
                sensorConfig.name,
                sensorConfig.unit
            ]);
        }
    });
    
    const ws = XLSX.utils.aoa_to_sheet(metadataData);
    return ws;
}

// Clear all data
function clearData() {
    if (isRecording) {
        alert('Stop recording first before clearing data');
        return;
    }
    
    if (recordedData.length > 0 && !confirm('Are you sure you want to clear all recorded data?')) {
        return;
    }
    
    recordedData = [];
    recordingStartTime = null;
    
    // Reset UI
    document.getElementById('recordingDuration').textContent = '00:00:00';
    document.getElementById('downloadCSV').disabled = true;
    document.getElementById('downloadExcel').disabled = true;
    document.getElementById('statusText').textContent = 'Standby';
    document.getElementById('statusDot').classList.remove('recording');
    document.getElementById('startRecording').disabled = false;
    document.getElementById('stopRecording').disabled = true;
    
    updateCounters();
    updatePreviewTable();
    
    console.log('Data cleared');
}

// Fungsi untuk mengecek apakah XLSX library sudah loaded
function checkXLSXLibrary() {
    if (typeof XLSX === 'undefined') {
        return false;
    }
    
    // Test basic functionality tanpa console log
    try {
        const testWb = XLSX.utils.book_new();
        const testWs = XLSX.utils.aoa_to_sheet([['test']]);
        XLSX.utils.book_append_sheet(testWb, testWs, 'test');
        return true;
    } catch (error) {
        return false;
    }
}

// Debug function untuk troubleshooting
function debugExcelExport() {
    console.log('=== Excel Export Debug Info ===');
    console.log('XLSX available:', typeof XLSX !== 'undefined');
    console.log('Recorded data length:', recordedData.length);
    console.log('Selected sensors:', getSelectedSensors().length);
    console.log('Sample data:', recordedData.slice(0, 2));
    
    if (typeof XLSX !== 'undefined') {
        console.log('XLSX version:', XLSX.version || 'unknown');
        
        try {
            const testWb = XLSX.utils.book_new();
            const testData = [['Header1', 'Header2'], ['Data1', 'Data2']];
            const testWs = XLSX.utils.aoa_to_sheet(testData);
            XLSX.utils.book_append_sheet(testWb, testWs, 'Test');
            console.log('XLSX basic functionality: OK');
        } catch (error) {
            console.error('XLSX basic functionality: FAILED', error);
        }
    }
}

// Export functions for external use
export {
    initializeSensorModules,
    startRecording,
    stopRecording,
    downloadCSV,
    downloadExcel,
    clearData,
    selectAllSensors,
    deselectAllSensors,
    selectByModule,
    SENSOR_MODULES
};

// Event listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Make DataManager globally accessible for derived data access
    if (window.DataManager) {
        console.log('DataManager is available globally');
    } else {
        console.warn('DataManager is not available globally - derived data may not be recorded properly');
    }
    
    // Initialize sensor modules first
    try {
        await initializeSensorModules();
        console.log('Sensor modules initialized successfully');
    } catch (error) {
        console.error('Failed to initialize sensor modules:', error);
        alert('Failed to initialize sensor modules. Please check the console for details.');
        return;
    }
    
    // Generate sensor selection UI
    generateSensorSelectionUI();
    
    // Bind event listeners
    document.getElementById('startRecording').addEventListener('click', startRecording);
    document.getElementById('stopRecording').addEventListener('click', stopRecording);
    document.getElementById('downloadCSV').addEventListener('click', downloadCSV);
        
    const downloadExcelBtn = document.getElementById('downloadExcel');
    if (downloadExcelBtn) {
        downloadExcelBtn.addEventListener('click', function() {
            // Pre-check XLSX library
            if (!checkXLSXLibrary()) {
                alert('Excel library is not properly loaded. Please refresh the page and try again, or use CSV export instead.');
                return;
            }
            downloadExcel();
        });
    }
    
    document.getElementById('clearData').addEventListener('click', clearData);

    if (document.getElementById('selectAll')) {
        document.getElementById('selectAll').addEventListener('click', selectAllSensors);
    }
    if (document.getElementById('deselectAll')) {
        document.getElementById('deselectAll').addEventListener('click', deselectAllSensors);
    }
    
    // Add change listeners to all sensor checkboxes to update module button states
    document.addEventListener('change', function(event) {
        if (event.target.matches('.sensor-item input[type="checkbox"]')) {
            updateModuleButtonStates();
        }
    });
    
    // Initialize counters and preview
    updateCounters();
    updatePreviewTable();
    
    console.log('Data recorder initialized successfully');
});

// Make functions globally available for onclick handlers
window.selectByModule = selectByModule;
window.selectAllSensors = selectAllSensors;
window.deselectAllSensors = deselectAllSensors;
window.downloadExcel = downloadExcel;
document.getElementById('downloadCSV').disabled = true;
document.getElementById('downloadExcel').disabled = true;
