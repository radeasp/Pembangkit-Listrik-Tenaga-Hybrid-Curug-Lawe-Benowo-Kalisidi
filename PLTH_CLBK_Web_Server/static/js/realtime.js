class DataManager {
    constructor(moduleName) {
        this.module = moduleName;
        this.dataBuffers = new Map();
        this.isInitialized = false;
        this.updateInterval = null;
        this.lastUpdateTimestamp = 0; // Tambah untuk tracking timestamp terakhir
    }

    async initialize() {
        console.log(`Initializing DataManager for module: ${this.module}`);
        try {
            // Step 1: Load raw historical data
            await this.loadHistory();
            
            // Step 2: Create empty buffers for derived parameters
            this.createDerivedBuffers();
            
            // Step 3: Calculate derived data from loaded history
            this.recalculateFromHistory();
            
            // Step 4: Start real-time updates
            this.startRealTimeUpdates();
            
            this.isInitialized = true;
            console.log(`DataManager for module ${this.module} initialized successfully`);
        } catch (error) {
            console.error(`Error initializing DataManager for ${this.module}:`, error);
        }
    }

    createDerivedBuffers() {
        const derivedParams = {
            'baterai': ['battery_net_current'],
                        'beban': ['dc_input_power'],
            'picohydro_generator': ['picohydro_power'],
            'solar_panel_generator': ['solar_power']
        };
        
        const params = derivedParams[this.module] || [];
        params.forEach(param => {
            if (!this.dataBuffers.has(param)) {
                this.dataBuffers.set(param, []);
                console.log(`Pre-initialized buffer for derived parameter: ${param}`);
            }
        });
    }

    recalculateFromHistory() {
        switch (this.module) {
            case 'baterai':
                this.calculateNetCurrentFromHistory();
                break;
                
            case 'beban':
                this.calculatePowerFromHistory('dc_input_power', 'battery_voltage', 'dc_input_current');
                break;
                               
            case 'picohydro_generator':
                this.calculatePowerFromHistory('picohydro_power', 'picohydro_voltage', 'picohydro_current');
                break;
                
            case 'solar_panel_generator':
                this.calculatePowerFromHistory('solar_power', 'solar_voltage', 'solar_current');
                break;
        }
    }

    calculateNetCurrentFromHistory() {
        const inputBuffer = this.dataBuffers.get('battery_input_current') || [];
        const outputBuffer = this.dataBuffers.get('battery_output_current') || [];
        const netBuffer = this.dataBuffers.get('battery_net_current') || [];
        
        // Clear existing derived data
        netBuffer.length = 0;
        
        // Create maps for efficient lookup
        const inputMap = new Map(inputBuffer.map(point => [point.x, point.y]));
        const outputMap = new Map(outputBuffer.map(point => [point.x, point.y]));
        
        // Get all unique timestamps
        const allTimestamps = new Set([
            ...inputBuffer.map(p => p.x),
            ...outputBuffer.map(p => p.x)
        ]);
        
        // Calculate net current for each timestamp
        for (const timestamp of allTimestamps) {
            const inputValue = inputMap.get(timestamp) || 0;
            const outputValue = outputMap.get(timestamp) || 0;
            const netValue = inputValue - outputValue;
            
            netBuffer.push({
                x: timestamp,
                y: netValue
            });
        }
        
        // Sort by timestamp
        netBuffer.sort((a, b) => a.x - b.x);
        
        console.log(`Recalculated ${netBuffer.length} net current points from history`);
    }

    calculatePowerFromHistory(powerParam, voltageParam, currentParam) {
        const voltageBuffer = this.dataBuffers.get(voltageParam) || [];
        const currentBuffer = this.dataBuffers.get(currentParam) || [];
        const powerBuffer = this.dataBuffers.get(powerParam) || [];
        
        // Clear existing derived data
        powerBuffer.length = 0;
        
        if (voltageBuffer.length === 0 || currentBuffer.length === 0) {
            return;
        }
        
        // Create maps for efficient lookup
        const voltageMap = new Map(voltageBuffer.map(point => [point.x, point.y]));
        const currentMap = new Map(currentBuffer.map(point => [point.x, point.y]));
        
        // Get all unique timestamps
        const allTimestamps = new Set([
            ...voltageBuffer.map(p => p.x),
            ...currentBuffer.map(p => p.x)
        ]);
        
        // Calculate power for each timestamp
        for (const timestamp of allTimestamps) {
            const voltage = voltageMap.get(timestamp) || 0;
            const current = currentMap.get(timestamp) || 0;
            const power = voltage * current;
            
            powerBuffer.push({
                x: timestamp,
                y: power
            });
        }
        
        // Sort by timestamp
        powerBuffer.sort((a, b) => a.x - b.x);
        
        console.log(`Recalculated ${powerBuffer.length} ${powerParam} points from history`);
    }

    async loadHistory() {
        try {
            console.log(`Loading history for module: ${this.module}`);
            const response = await fetch(`/api/history/${this.module}`);
            
            if (!response.ok) {
                console.warn(`No history available for module ${this.module} (${response.status})`);
                return;
            }
            
            const data = await response.json();
            
            if (data.history && Array.isArray(data.history)) {
                console.log(`Loaded ${data.history.length} history entries for ${this.module}`);
                data.history.forEach(entry => {
                    if (entry.data && typeof entry.data === 'object') {
                        Object.entries(entry.data).forEach(([param, value]) => {
                            if (typeof value === 'number' && !isNaN(value)) {
                                if (!this.dataBuffers.has(param)) {
                                    this.dataBuffers.set(param, []);
                                }
                                this.dataBuffers.get(param).push({
                                    x: entry.timestamp,
                                    y: value
                                });
                            }
                        });
                    }
                });
                
                // Bersihkan data yang terlalu lama
                this.cleanOldData();
            }
        } catch (error) {
            console.error(`Error loading history for ${this.module}:`, error);
        }
    }

    startRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        this.updateInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/data/${this.module}`);
                
                if (!response.ok) {
                    console.warn(`Failed to fetch data for ${this.module}: ${response.status}`);
                    return;
                }
                
                const data = await response.json();
                
                if (data[this.module] && typeof data[this.module] === 'object') {

                    const timestamp = Math.floor(Date.now() / 1000);
                    
                    // Cek apakah timestamp sama dengan update terakhir
                    if (timestamp === this.lastUpdateTimestamp) {
                        // Skip update jika timestamp sama untuk menghindari duplikasi
                        return;
                    }
                    
                    this.lastUpdateTimestamp = timestamp;
                    
                    // Store raw data first
                    Object.entries(data[this.module]).forEach(([param, value]) => {
                        if (typeof value === 'number' && !isNaN(value)) {
                            if (!this.dataBuffers.has(param)) {
                                this.dataBuffers.set(param, []);
                            }
                            
                            const buffer = this.dataBuffers.get(param);
                            buffer.push({ x: timestamp, y: value });
                            
                            // Pertahankan hanya data 30 detik terakhir
                            while (buffer.length > 0 && (timestamp - buffer[0].x) > 30) {
                                buffer.shift();
                            }
                        }
                    });
                    

                    this.calculateDerivedDataRealTime(data[this.module], timestamp);
                    
                } else {
                    console.warn(`Invalid data structure received for ${this.module}`);
                }
            } catch (error) {
                console.error(`Error updating real-time data for ${this.module}:`, error);
            }
        }, 1000);
        
        console.log(`Started real-time updates for module: ${this.module}`);
    }

    
    calculateDerivedDataRealTime(rawData, timestamp) {
        switch (this.module) {
            case 'baterai':
                const inputCurrent = rawData.battery_input_current || 0;
                const outputCurrent = rawData.battery_output_current || 0;
                const netCurrent = inputCurrent - outputCurrent;
                
                this.addToBufferSafe('battery_net_current', timestamp, netCurrent);
                console.log(`Real-time battery_net_current: ${netCurrent}A at ${timestamp}`);
                break;
                
            case 'beban':
                // DC Input Power
                const batteryVoltage = rawData.battery_voltage || 0;
                const dcCurrent = rawData.dc_input_current || 0;
                const dcPower = batteryVoltage * dcCurrent;
                this.addToBufferSafe('dc_input_power', timestamp, dcPower);
                
                console.log(`Real-time dc_power: ${dcPower}W at ${timestamp}`);
                break;
                
            case 'dump_load':
                // Picohydro Charging Power - gunakan picohydro_voltage yang tersedia
                const picoVoltage = rawData.picohydro_voltage || 0;
                const picoChargingCurrent = rawData.picohydro_charging_current || 0;
                const picoChargingPower = picoVoltage * picoChargingCurrent;
                this.addToBufferSafe('picohydro_charging_power', timestamp, picoChargingPower);
                
                // Dumpload Power
                const dumpVoltage = rawData.dumpload_voltage || 0;
                const dumpCurrent = rawData.dumpload_current || 0;
                const dumpPower = dumpVoltage * dumpCurrent;
                this.addToBufferSafe('dumpload_power', timestamp, dumpPower);
                
                console.log(`Real-time picohydro_charging_power: ${picoChargingPower}W, dumpload_power: ${dumpPower}W at ${timestamp}`);
                break;
                
            case 'picohydro_generator':
                const picoGenVoltage = rawData.picohydro_voltage || 0;
                const picoGenCurrent = rawData.picohydro_current || 0;
                const picoGenPower = picoGenVoltage * picoGenCurrent;
                this.addToBufferSafe('picohydro_power', timestamp, picoGenPower);
                
                console.log(`Real-time picohydro_power: ${picoGenPower}W at ${timestamp}`);
                break;
                
            case 'solar_panel_generator':
                const solarVoltage = rawData.solar_voltage || 0;
                const solarCurrent = rawData.solar_current || 0;
                const solarPower = solarVoltage * solarCurrent;
                this.addToBufferSafe('solar_power', timestamp, solarPower);
                
                console.log(`Real-time solar_power: ${solarPower}W at ${timestamp}`);
                break;
        }
    }

    
    addToBufferSafe(param, timestamp, value) {
        if (!this.dataBuffers.has(param)) {
            this.dataBuffers.set(param, []);
        }
        
        const buffer = this.dataBuffers.get(param);
        
        // Cek apakah timestamp sudah ada di buffer
        const existingIndex = buffer.findIndex(point => point.x === timestamp);
        if (existingIndex !== -1) {

            buffer[existingIndex].y = value;
            console.log(`Updated existing ${param} at timestamp ${timestamp}: ${value}`);
        } else {
            // Tambah point baru
            buffer.push({ x: timestamp, y: value });
        }
        
        // Pertahankan hanya data 30 detik terakhir
        while (buffer.length > 0 && (timestamp - buffer[0].x) > 30) {
            buffer.shift();
        }
    }

    // DEPRECATED: Method lama, diganti dengan addToBufferSafe
    addToBuffer(param, timestamp, value) {
        console.warn(`addToBuffer is deprecated, use addToBufferSafe instead`);
        this.addToBufferSafe(param, timestamp, value);
    }

    cleanOldData() {
        const now = Date.now() / 1000;
        this.dataBuffers.forEach((buffer, param) => {
            const originalLength = buffer.length;
            const filtered = buffer.filter(point => (now - point.x) <= 30);
            if (filtered.length !== originalLength) {
                this.dataBuffers.set(param, filtered);
                console.log(`Cleaned old data for ${param}: ${originalLength} -> ${filtered.length}`);
            }
        });
    }

    getData(param) {
        return this.dataBuffers.get(param) || [];
    }

    async getLatestData() {
        try {
            const response = await fetch(`/api/data/${this.module}`);
            
            if (!response.ok) {
                console.warn(`Failed to fetch latest data for ${this.module}: ${response.status}`);
                return {};
            }
            
            const data = await response.json();
            return data[this.module] || {};
        } catch (error) {
            console.error(`Error getting latest data for ${this.module}:`, error);
            return {};
        }
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        this.dataBuffers.clear();
        this.isInitialized = false;
        this.lastUpdateTimestamp = 0;
        console.log(`DataManager for ${this.module} destroyed`);
    }
}

export { DataManager };
