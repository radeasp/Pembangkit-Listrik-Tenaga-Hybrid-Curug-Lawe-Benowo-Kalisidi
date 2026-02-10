// data_source_switch.js - Data Source Switching System

class DataSourceSwitcher {
    constructor() {
        this.currentMode = 'simulasi';
        this.isLoading = false;
        this.connectionStatus = {
            simulasi: true,
            aktual: false
        };
        this.availableModes = {
            simulasi: true,
            aktual: false
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialStatus();
        this.startStatusMonitoring();
    }

    bindEvents() {
        // Radio button change events
        const dummyRadio = document.getElementById('dummySource');
        const realRadio = document.getElementById('realSource');
        
        if (dummyRadio) {
            dummyRadio.addEventListener('change', () => {
                if (dummyRadio.checked) {
                    this.selectSource('simulasi');
                }
            });
        }
        
        if (realRadio) {
            realRadio.addEventListener('change', () => {
                if (realRadio.checked) {
                    this.selectSource('aktual');
                }
            });
        }

        // Source option click events
        const dummyOption = document.getElementById('dummySourceOption');
        const realOption = document.getElementById('realSourceOption');
        
        if (dummyOption) {
            dummyOption.addEventListener('click', (e) => {
                if (e.target.type === 'radio') return;

                if (dummyRadio && !dummyRadio.checked) {
                    dummyRadio.checked = true;
                    dummyRadio.dispatchEvent(new Event('change'));
                    this.selectSource('simulasi');
                }
            });
        }
        
        if (realOption) {
            realOption.addEventListener('click', (e) => {
                if (e.target.type === 'radio') return;

                if (realRadio && !realRadio.checked && this.availableModes.aktual) {
                    realRadio.checked = true;
                    realRadio.dispatchEvent(new Event('change'));
                    this.selectSource('aktual');
                }
            });
        }

        // Control button events
        const applyBtn = document.getElementById('applySourceChange');
        const testBtn = document.getElementById('testConnection');
        const resetBtn = document.getElementById('resetConnection');

        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applySourceChange());
        }

        if (testBtn) {
            testBtn.addEventListener('click', () => this.testConnection());
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetConnection());
        }
    }

    async loadInitialStatus() {
        try {
            const response = await fetch('/api/sensor-mode');
            if (response.ok) {
                const data = await response.json();
                this.currentMode = data.current_mode;
                this.availableModes = data.available_modes;
                this.connectionStatus = data.connection_status;

                // Check if available modes and current_mode is aktual
                const realRadio = document.getElementById('realSource');
                const realOption = document.getElementById('realSourceOption');
                const dummyRadio = document.getElementById('dummySource');
                const dummyOption = document.getElementById('dummySourceOption');
                if (this.availableModes.aktual && this.currentMode === 'aktual') {
                    if (realRadio) {
                        realRadio.checked = true;
                        realRadio.disabled = false;
                    }
                    if (realOption) {
                        realOption.classList.add('selected');
                        realOption.style.opacity = '1';
                        realOption.style.pointerEvents = 'auto';
                    }
                    if (dummyRadio) dummyRadio.checked = false;
                    if (dummyOption) dummyOption.classList.remove('selected');
                } else {
                    if (dummyRadio) dummyRadio.checked = true;
                    if (dummyOption) {
                        dummyOption.classList.add('selected');
                        dummyOption.style.opacity = '1';
                        dummyOption.style.pointerEvents = 'auto';
                    }
                    if (realRadio) realRadio.checked = false;
                    if (realOption) realOption.classList.remove('selected');
                }

                this.updateUI();
                this.updateConnectionStatus(data.connection_status);
            }
        } catch (error) {
            console.error('Failed to load initial status:', error);
            this.showNotification('Gagal memuat status awal', 'error');
        }
    }

    selectSource(source) {
        const dummyOption = document.getElementById('dummySourceOption');
        const realOption = document.getElementById('realSourceOption');
        
        // Update visual selection
        if (dummyOption) dummyOption.classList.toggle('selected', source === 'simulasi');
        if (realOption) realOption.classList.toggle('selected', source === 'aktual');
        
        
        if (source === 'aktual' && !this.availableModes.aktual) {
            this.showNotification('Sensor aktual tidak tersedia. Silakan periksa koneksi hardware.', 'warning');
            // Revert to simulasi
            const dummyRadio = document.getElementById('dummySource');
            if (dummyRadio) dummyRadio.checked = true;
            if (dummyOption) dummyOption.classList.add('selected');
            if (realOption) realOption.classList.remove('selected');
            return;
        }

        this.updateApplyButtonState();
    }

    async applySourceChange() {
        const selectedRadio = document.querySelector('input[name="dataSource"]:checked');
        if (!selectedRadio) return;

        const newMode = selectedRadio.value;
        if (newMode === this.currentMode) {
            this.showNotification('Mode yang dipilih sudah aktif', 'info');
            return;
        }

        if (!this.availableModes[newMode]) {
            const modeName = newMode === 'simulasi' ? 'simulasi' : 'aktual';
            this.showNotification(`Mode ${modeName} tidak tersedia`, 'error');
            return;
        }

        this.setLoading(true);
        
        try {
            const response = await fetch('/api/sensor-mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mode: newMode })
            });

            const result = await response.json();

            if (result.success) {
                this.currentMode = newMode;
                this.updateUI();
                this.updateLastUpdate();
                const modeName = newMode === 'simulasi' ? 'simulasi' : 'aktual';
                this.showNotification(`Berhasil beralih ke mode ${modeName}`, 'success');
                
                // Trigger page data refresh if needed
                if (window.refreshPageData) {
                    window.refreshPageData();
                }
            } else {
                const modeName = newMode === 'simulasi' ? 'simulasi' : 'aktual';
                this.showNotification(`Gagal beralih ke mode ${modeName}: ${result.message}`, 'error');
                // Revert UI to current mode
                this.revertToCurrentMode();
            }
        } catch (error) {
            console.error('Error switching mode:', error);
            this.showNotification('Error dalam mengganti mode sensor', 'error');
            this.revertToCurrentMode();
        } finally {
            this.setLoading(false);
        }
    }

    async testConnection() {
        this.setLoading(true, 'testConnection');
        
        try {
            const response = await fetch('/api/connection-status');
            if (response.ok) {
                const data = await response.json();
                this.updateConnectionStatus(data.connection_status);
                this.availableModes = data.connection_status.available_modes || this.availableModes;
                this.showNotification('Test koneksi selesai', 'success');
            } else {
                throw new Error('Failed to test connection');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            this.showNotification('Test koneksi gagal', 'error');
        } finally {
            this.setLoading(false, 'testConnection');
        }
    }

    async resetConnection() {
        this.setLoading(true, 'resetConnection');
        
        try {
            // Force switch back to dummy mode
            const response = await fetch('/api/sensor-mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mode: 'dummy' })
            });

            if (response.ok) {
                this.currentMode = 'simulasi';
                this.updateUI();
                this.updateLastUpdate();
                this.showNotification('Koneksi direset ke mode simulasi', 'success');
                
                // Reload connection status
                await this.testConnection();
            } else {
                throw new Error('Failed to reset connection');
            }
        } catch (error) {
            console.error('Reset failed:', error);
            this.showNotification('Reset koneksi gagal', 'error');
        } finally {
            this.setLoading(false, 'resetConnection');
        }
    }

    updateUI() {
        // Update radio buttons
        const dummyRadio = document.getElementById('dummySource');
        const realRadio = document.getElementById('realSource');
        
        if (dummyRadio) dummyRadio.checked = (this.currentMode === 'simulasi');
        if (realRadio) realRadio.checked = (this.currentMode === 'aktual');
        
        // Update visual selection
        const dummyOption = document.getElementById('dummySourceOption');
        const realOption = document.getElementById('realSourceOption');
        
        if (dummyOption) dummyOption.classList.toggle('selected', this.currentMode === 'simulasi');
        if (realOption) realOption.classList.toggle('selected', this.currentMode === 'aktual');
        
        // Update status indicators
        this.updateStatusIndicators();
        
        // Update active source info
        const activeSourceEl = document.getElementById('activeSource');
        if (activeSourceEl) {
            activeSourceEl.textContent = this.currentMode === 'simulasi' ? 'Mode Simulasi' : 'Mode Aktual';
        }
        
        // Update apply button state
        this.updateApplyButtonState();
        
        // Update option availability
        this.updateOptionAvailability();
    }

    updateStatusIndicators() {
        const dummyStatus = document.getElementById('dummyStatus');
        const realStatus = document.getElementById('realStatus');
        
        if (dummyStatus) {
            const indicator = dummyStatus.querySelector('.status-indicator');
            const text = dummyStatus.querySelector('.status-text');
            
            if (this.currentMode === 'simulasi') {
                indicator.classList.add('active');
                text.textContent = 'Aktif';
            } else {
                indicator.classList.remove('active');
                text.textContent = 'Tidak Aktif';
            }
        }
        
        if (realStatus) {
            const indicator = realStatus.querySelector('.status-indicator');
            const text = realStatus.querySelector('.status-text');
            
            if (this.currentMode === 'aktual' && this.availableModes.aktual) {
                indicator.classList.add('active');
                text.textContent = 'Aktif';
            } else if (this.availableModes.aktual) {
                indicator.classList.remove('active');
                text.textContent = 'Tersedia';
            } else {
                indicator.classList.remove('active');
                text.textContent = 'Tidak Tersedia';
            }
        }
    }

    updateConnectionStatus(connectionStatus) {
        const esp32StatusEl = document.getElementById('esp32ConnectionStatus');
        const stm32StatusEl = document.getElementById('stm32ConnectionStatus');
        
        if (connectionStatus && connectionStatus.real_sensors_detail) {
            const realDetail = connectionStatus.real_sensors_detail;
            
            if (esp32StatusEl) {
                if (realDetail.esp32 !== undefined) {
                    this.updateConnectionElement(esp32StatusEl, realDetail.esp32);
                } else {
                    this.updateConnectionElement(esp32StatusEl, false);
                }
            }
            
            if (stm32StatusEl) {
                if (realDetail.stm32 !== undefined) {
                    this.updateConnectionElement(stm32StatusEl, realDetail.stm32);
                } else {
                    this.updateConnectionElement(stm32StatusEl, false);
                }
            }
        } else {
            
            if (esp32StatusEl) this.updateConnectionElement(esp32StatusEl, false);
            if (stm32StatusEl) this.updateConnectionElement(stm32StatusEl, false);
        }
    }

    updateConnectionElement(element, isConnected) {
        element.className = 'connection-status';
        if (isConnected) {
            element.classList.add('connected');
            element.textContent = 'Terhubung';
        } else {
            element.classList.add('disconnected');
            element.textContent = 'Terputus';
        }
    }

    updateApplyButtonState() {
        const applyBtn = document.getElementById('applySourceChange');
        const selectedRadio = document.querySelector('input[name="dataSource"]:checked');
        
        if (applyBtn && selectedRadio) {
            const hasChanges = selectedRadio.value !== this.currentMode;
            const isAvailable = this.availableModes[selectedRadio.value];
            
            applyBtn.disabled = !hasChanges || !isAvailable || this.isLoading;
            
            if (!isAvailable && selectedRadio.value === 'real') {
                applyBtn.title = 'Sensor real tidak tersedia';
            } else if (!hasChanges) {
                applyBtn.title = 'Tidak ada perubahan untuk diterapkan';
            } else {
                applyBtn.title = 'Terapkan perubahan sumber data';
            }
        }
    }

    updateOptionAvailability() {
        const realOption = document.getElementById('realSourceOption');
        const realRadio = document.getElementById('realSource');
        if (realOption && realRadio) {
            if (this.availableModes.aktual) {
                realOption.style.opacity = '1';
                realOption.style.pointerEvents = 'auto';
                realRadio.disabled = false;
            } else {
                realOption.style.opacity = '0.6';
                realOption.style.pointerEvents = 'none';
                realRadio.disabled = true;
                // Auto switch to dummy
                if (realRadio.checked) {
                    const dummyRadio = document.getElementById('dummySource');
                    if (dummyRadio) {
                        dummyRadio.checked = true;
                        this.selectSource('simulasi');
                    }
                }
            }
        }
    }

    revertToCurrentMode() {
        // Map current mode to radio button ID
        const radioId = this.currentMode === 'simulasi' ? 'dummySource' : 'realSource';
        const currentRadio = document.getElementById(radioId);
        if (currentRadio) {
            currentRadio.checked = true;
            this.selectSource(this.currentMode);
        }
    }

    updateLastUpdate() {
        const lastUpdateEl = document.getElementById('lastSourceUpdate');
        if (lastUpdateEl) {
            const now = new Date();
            lastUpdateEl.textContent = now.toLocaleTimeString('id-ID');
        }
    }

    setLoading(loading, specificButton = null) {
        this.isLoading = loading;
        
        const buttons = specificButton ? 
            [document.getElementById(specificButton)] : 
            [
                document.getElementById('applySourceChange'),
                document.getElementById('testConnection'),
                document.getElementById('resetConnection')
            ];
        
        buttons.forEach(btn => {
            if (btn) {
                btn.disabled = loading;
                btn.classList.toggle('loading', loading);
            }
        });
        
        // Update apply button state if not specifically loading it
        if (!specificButton || specificButton !== 'applySourceChange') {
            this.updateApplyButtonState();
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${this.getNotificationIcon(type)}</span>
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        // Add styles if not already added
        this.addNotificationStyles();
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        const autoRemove = setTimeout(() => {
            this.removeNotification(notification);
        }, 5000);
        
        // Manual close
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            clearTimeout(autoRemove);
            this.removeNotification(notification);
        });
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
    }

    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }

    removeNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    addNotificationStyles() {
        if (document.getElementById('notification-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 10000;
                transform: translateX(400px);
                opacity: 0;
                transition: all 0.3s ease;
                min-width: 300px;
                max-width: 500px;
            }
            .notification.show {
                transform: translateX(0);
                opacity: 1;
            }
            .notification-content {
                display: flex;
                align-items: center;
                padding: 1rem 1.5rem;
                gap: 0.75rem;
            }
            .notification-icon {
                font-size: 1.2rem;
                flex-shrink: 0;
            }
            .notification-message {
                flex-grow: 1;
                color: #333;
                font-weight: 500;
            }
            .notification-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #666;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s ease;
            }
            .notification-close:hover {
                background-color: rgba(0,0,0,0.1);
            }
            .notification-success {
                border-left: 4px solid #28a745;
            }
            .notification-error {
                border-left: 4px solid #dc3545;
            }
            .notification-warning {
                border-left: 4px solid #ffc107;
            }
            .notification-info {
                border-left: 4px solid #17a2b8;
            }
        `;
        document.head.appendChild(styles);
    }

    startStatusMonitoring() {
        // Monitor connection status every 5 seconds (lebih sering)
        setInterval(async () => {
            try {
                const response = await fetch('/api/sensor-mode');
                if (response.ok) {
                    const data = await response.json();
                    this.availableModes = data.available_modes;
                    this.updateOptionAvailability();
                    this.updateApplyButtonState();
                    if (data.connection_status) {
                        this.updateConnectionStatus(data.connection_status);
                    }
                }
            } catch (error) {
                console.error('Status monitoring error:', error);
            }
        }, 5000); // 5 detik
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dataSourceSwitcher = new DataSourceSwitcher();
});

// Export for use in other scripts
export default DataSourceSwitcher;
