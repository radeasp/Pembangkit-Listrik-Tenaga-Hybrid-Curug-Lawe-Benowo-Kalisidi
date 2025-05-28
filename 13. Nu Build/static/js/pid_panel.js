// PID Controller Panel JavaScript
class PIDController {
    constructor() {
        this.isProtected = true;
        this.currentTab = 'voltage';
        this.defaultSettings = {
            setpoints: {
                voltage: 12.0
            },
            pid: {
                voltage: { kp: 1.0, ki: 0.1, kd: 0.01 }
            }
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateProtectionUI();
        this.updateLastUpdate();
    }

    bindEvents() {
        // Protection switch
        const protectionSwitch = document.getElementById('protectionSwitch');
        if (protectionSwitch) {
            protectionSwitch.addEventListener('change', () => {
                this.toggleProtection();
            });
        }

        // Control buttons
        const saveBtn = document.getElementById('savePidSettings');
        const resetBtn = document.getElementById('resetPidSettings');
        const loadBtn = document.getElementById('loadPidSettings');

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveSettings();
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetSettings();
            });
        }

        if (loadBtn) {
            loadBtn.addEventListener('click', () => {
                this.loadSettings();
            });
        }

        // Input change listeners for real-time validation
        this.bindInputValidation();
    }

    bindInputValidation() {
        const inputs = document.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.validateInput(e.target);
            });

            input.addEventListener('change', (e) => {
                this.onSettingChange(e.target);
            });
        });
    }

    toggleProtection() {
        const protectionSwitch = document.getElementById('protectionSwitch');
        const protectionStatus = document.getElementById('protectionStatus');
        const protectionPanel = document.querySelector('.protection-panel');

        this.isProtected = protectionSwitch.checked;
        
        protectionPanel.classList.toggle('unlocked', !this.isProtected);

        // Update status text
        if (protectionStatus) {
            protectionStatus.textContent = this.isProtected ? 'TERKUNCI' : 'TERBUKA';
        }

        this.updateProtectionUI();
        this.showNotification(
            this.isProtected ? 'Parameter Kontroler Terkunci untuk Keamanan' : 'Parameter Kontroler Terbuka untuk Diedit',
            this.isProtected ? 'warning' : 'success'
        );
    }

    updateProtectionUI() {
        const inputs = document.querySelectorAll(`
            .pid-controller-panel input[type="number"],
            .pid-controller-panel input[type="text"]
        `);

        const buttons = document.querySelectorAll('#savePidSettings, #resetPidSettings');
        
        inputs.forEach(input => {
            input.disabled = this.isProtected;
        });

        buttons.forEach(button => {
            button.disabled = this.isProtected;
        });

        // Update controller status
        const controllerStatus = document.getElementById('controllerStatus');
        if (controllerStatus) {
            controllerStatus.textContent = this.isProtected ? 'Terkunci' : 'Terbuka';
            controllerStatus.className = this.isProtected ? 'status-value disabled' : 'status-value enabled';
        }
    }

    switchTab(tabName) {
        // Update current tab
        this.currentTab = tabName;

        // Update tab buttons
        const tabs = document.querySelectorAll('.pid-tab');
        tabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.getAttribute('data-tab') === tabName) {
                tab.classList.add('active');
            }
        });

        // Update tab content
        const contents = document.querySelectorAll('.pid-tab-content');
        contents.forEach(content => {
            content.classList.remove('active');
        });

        const activeContent = document.getElementById(`${tabName}-pid`);
        if (activeContent) {
            activeContent.classList.add('active');
        }
    }

    updateTabContent() {
        // This method can be used to update tab content dynamically
        this.switchTab(this.currentTab);
    }

    validateInput(input) {
        const value = parseFloat(input.value);
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);

        // Remove previous validation classes
        input.classList.remove('valid', 'invalid');

        if (isNaN(value) || value < min || value > max) {
            input.classList.add('invalid');
            return false;
        } else {
            input.classList.add('valid');
            return true;
        }
    }

    onSettingChange(input) {
        if (!this.isProtected) {
            // Log the change for debugging
            console.log(`Setting changed: ${input.id} = ${input.value}`);
            
            // Here you would typically send the data to your backend
            // this.sendSettingUpdate(input.id, input.value);
            
            // Update last update time
            this.updateLastUpdate();
        }
    }

    saveSettings() {
        if (this.isProtected) {
            this.showNotification('Cannot save: Parameters are protected', 'error');
            return;
        }

        try {
            const settings = this.getCurrentSettings();
            
            // Here you would send settings to your backend
            console.log('Saving PID settings:', settings);
            
            // Simulate API call
            this.simulateSaveToBackend(settings)
                .then(() => {
                    this.showNotification('Settings saved successfully!', 'success');
                    this.updateLastUpdate();
                })
                .catch((error) => {
                    this.showNotification('Failed to save settings: ' + error.message, 'error');
                });

        } catch (error) {
            this.showNotification('Error saving settings: ' + error.message, 'error');
        }
    }

    resetSettings() {
        if (this.isProtected) {
            this.showNotification('Cannot reset: Parameters are protected', 'error');
            return;
        }

        if (confirm('Are you sure you want to reset all PID parameters to default values?')) {
            this.applySettings(this.defaultSettings);
            this.showNotification('Settings reset to default values', 'success');
            this.updateLastUpdate();
        }
    }

    loadSettings() {
        // This would typically load from your backend
        console.log('Loading PID settings from backend...');
        
        // Simulate loading from backend
        this.simulateLoadFromBackend()
            .then((settings) => {
                this.applySettings(settings);
                this.showNotification('Settings loaded successfully!', 'success');
                this.updateLastUpdate();
            })
            .catch((error) => {
                this.showNotification('Failed to load settings: ' + error.message, 'error');
            });
    }

    getCurrentSettings() {
        return {
            setpoints: {
                voltage: parseFloat(document.getElementById('voltageSetpoint')?.value || 0)
            },
            pid: {
                voltage: {
                    kp: parseFloat(document.getElementById('voltageKp')?.value || 0),
                    ki: parseFloat(document.getElementById('voltageKi')?.value || 0),
                    kd: parseFloat(document.getElementById('voltageKd')?.value || 0)
                }
            }
        };
    }

    applySettings(settings) {
        // Apply setpoints
        if (settings.setpoints) {
            const voltageSetpoint = document.getElementById('voltageSetpoint');
            if (voltageSetpoint) voltageSetpoint.value = settings.setpoints.voltage;
        }

        // Apply PID parameters
        if (settings.pid && settings.pid.voltage) {
            const params = settings.pid.voltage;
            const kpInput = document.getElementById('voltageKp');
            const kiInput = document.getElementById('voltageKi');
            const kdInput = document.getElementById('voltageKd');

            if (kpInput) kpInput.value = params.kp;
            if (kiInput) kiInput.value = params.ki;
            if (kdInput) kdInput.value = params.kd;
        }
    }

    updateLastUpdate() {
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = now.toLocaleTimeString();
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Add styles if not already added
        this.addNotificationStyles();

        // Add to page
        document.body.appendChild(notification);

        // Close button functionality
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            notification.remove();
        });

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    addNotificationStyles() {
        if (document.getElementById('pid-notification-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'pid-notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 1000;
                animation: slideIn 0.3s ease-out;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            .notification-success {
                background-color: #439B57;
            }

            .notification-error {
                background-color: #9B4343;
            }

            .notification-warning {
                background-color: #f39c12;
            }

            .notification-info {
                background-color: #274C77;
            }

            .notification-close {
                background: none;
                border: none;
                color: white;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                margin-left: auto;
            }

            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            .invalid {
                border-color: #9B4343 !important;
                background-color: #ffe6e6 !important;
            }

            .valid {
                border-color: #439B57 !important;
            }
        `;
        document.head.appendChild(styles);
    }

    // Simulate backend API calls
    async simulateSaveToBackend(settings) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Simulate random success/failure for demo
                if (Math.random() > 0.1) {
                    resolve({ success: true, message: 'Settings saved successfully' });
                } else {
                    reject(new Error('Network error occurred'));
                }
            }, 1000);
        });
    }

    async simulateLoadFromBackend() {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Simulate random success/failure for demo
                if (Math.random() > 0.1) {
                    // Return sample loaded settings for voltage only
                    resolve({
                        setpoints: {
                            voltage: 13.5
                        },
                        pid: {
                            voltage: { kp: 1.2, ki: 0.15, kd: 0.008 }
                        }
                    });
                } else {
                    reject(new Error('Failed to connect to server'));
                }
            }, 800);
        });
    }

    // Method to send real-time updates to backend (placeholder)
    async sendSettingUpdate(parameterId, value) {
        // This would be your actual API call
        console.log(`Sending update: ${parameterId} = ${value}`);
        
        // Example fetch call:
        /*
        try {
            const response = await fetch('/api/pid/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    parameter: parameterId,
                    value: value,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update parameter');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error updating parameter:', error);
            this.showNotification('Failed to update parameter: ' + error.message, 'error');
        }
        */
    }

    // Method to get current system status
    async getSystemStatus() {
        // This would fetch real-time status from your backend
        return {
            controllerEnabled: !this.isProtected,
            lastUpdate: new Date().toISOString(),
            connectionStatus: 'connected'
        };
    }

    // Method to enable/disable the entire PID controller system
    async toggleController(enable) {
        try {
            // This would be your API call to enable/disable the controller
            console.log(`${enable ? 'Enabling' : 'Disabling'} PID controller system`);
            
            const controllerStatus = document.getElementById('controllerStatus');
            if (controllerStatus) {
                controllerStatus.textContent = enable ? 'Enabled' : 'Disabled';
                controllerStatus.className = enable ? 'status-value enabled' : 'status-value disabled';
            }

            this.showNotification(
                `PID Controller ${enable ? 'enabled' : 'disabled'}`,
                enable ? 'success' : 'warning'
            );

        } catch (error) {
            this.showNotification('Failed to toggle controller: ' + error.message, 'error');
        }
    }
}

// Initialize PID Controller when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if PID controller elements exist before initializing
    if (document.querySelector('.pid-controller-panel')) {
        window.pidController = new PIDController();
        console.log('PID Controller initialized');
    }
});

// Export for module use if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PIDController;
}