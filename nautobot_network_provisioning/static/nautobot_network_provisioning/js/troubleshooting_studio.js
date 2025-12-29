/**
 * Troubleshooting Studio - Real-time Network Path Tracer
 * 
 * SPA Island Pattern: This JavaScript application mounts into the Nautobot shell
 * and provides a real-time, interactive troubleshooting interface.
 */

window.TroubleshootingStudio = {
    config: null,
    state: {
        currentRecordId: null,
        isRunning: false,
        pollingInterval: null,
        history: [],
        lastHopCount: 0,
    },
    
    /**
     * Initialize the Troubleshooting Studio application
     */
    init: function(config) {
        this.config = config;
        
        // Ensure DOM is ready before setting up the layout
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this._doInit());
        } else {
            this._doInit();
        }
    },
    
    /**
     * Internal initialization once DOM is ready
     */
    _doInit: function() {
        const root = document.getElementById('troubleshooting-studio-root');
        if (!root) {
            console.error('TroubleshootingStudio: Root element not found');
            return;
        }
        
        this.setupLayout();
        
        // Wait a tick to ensure DOM is fully updated before accessing elements
        setTimeout(() => {
            this.loadHistory();
            this.setupEventListeners();
            
            if (!this.config.networkPathTracingAvailable) {
                this.showAlert('warning', 'Network path tracing module is not available. Please install the required dependencies.');
            }
        }, 0);
    },
    
    /**
     * Setup the 2-pane layout
     */
    setupLayout: function() {
        const root = document.getElementById('troubleshooting-studio-root');
        root.innerHTML = `
            <div class="troubleshooting-zone-a">
                <div class="troubleshooting-form-panel">
                    <h3><i class="mdi mdi-map-marker-path"></i> Network Path Trace</h3>
                    
                    <form id="troubleshooting-form">
                        <div class="troubleshooting-form-group">
                            <label for="source-ip">Source IP or FQDN</label>
                            <input type="text" id="source-ip" name="source_ip" 
                                   placeholder="e.g., 10.0.0.1 or server01.example.com" required>
                        </div>
                        
                        <div class="troubleshooting-form-group">
                            <label for="destination-ip">Destination IP or FQDN</label>
                            <input type="text" id="destination-ip" name="destination_ip" 
                                   placeholder="e.g., 8.8.8.8 or google.com" required>
                        </div>
                        
                        <div class="troubleshooting-form-group">
                            <label for="secrets-group">Secrets Group</label>
                            <select id="secrets-group" name="secrets_group_id" required>
                                <option value="">-- Select Secrets Group --</option>
                                ${(this.config.secretsGroups || []).map(group => 
                                    `<option value="${group.id}">${this.escapeHtml(group.name)}</option>`
                                ).join('')}
                            </select>
                        </div>
                        
                        <div class="troubleshooting-form-group">
                            <div class="troubleshooting-form-group-inline">
                                <input type="checkbox" id="enable-layer2" name="enable_layer2_discovery" checked>
                                <label for="enable-layer2">Enable Layer 2 Discovery</label>
                            </div>
                        </div>
                        
                        <div class="troubleshooting-form-group">
                            <div class="troubleshooting-form-group-inline">
                                <input type="checkbox" id="ping-endpoints" name="ping_endpoints">
                                <label for="ping-endpoints">Ping Endpoints First</label>
                            </div>
                        </div>
                        
                        <button type="submit" class="troubleshooting-run-btn" id="run-btn">
                            <i class="mdi mdi-play"></i> Run Trace
                        </button>
                    </form>
                </div>
                
                <div class="troubleshooting-history-panel">
                    <div class="troubleshooting-history-header">
                        <i class="mdi mdi-history"></i> Trace History
                    </div>
                    <ul class="troubleshooting-history-list" id="history-list">
                        <li style="padding: 20px; text-align: center; color: #999;">
                            Loading history...
                        </li>
                    </ul>
                </div>
            </div>
            
            <div class="troubleshooting-zone-b">
                <div class="troubleshooting-visualization-header">
                    <h4 class="troubleshooting-visualization-title">
                        <i class="mdi mdi-graph"></i> Network Path Visualization
                    </h4>
                    <div class="troubleshooting-visualization-status" id="viz-status">
                        <span>Ready</span>
                    </div>
                </div>
                
                <div class="troubleshooting-progress-bar" id="progress-bar" style="display: none;">
                    <div class="troubleshooting-progress-bar-fill indeterminate"></div>
                </div>
                
                <div class="troubleshooting-visualization-body">
                    <iframe class="troubleshooting-visualization-iframe" 
                            id="visualization-iframe" 
                            style="display: none;"></iframe>
                    
                    <div class="troubleshooting-visualization-placeholder" id="viz-placeholder">
                        <i class="mdi mdi-map-marker-path"></i>
                        <p>Run a trace to visualize the network path</p>
                    </div>
                </div>
                
                <div class="troubleshooting-log-panel" id="log-panel">
                    <div class="troubleshooting-log-entry info">
                        <span class="timestamp">[Ready]</span>
                        Troubleshooting Studio initialized. Ready to trace network paths.
                    </div>
                </div>
            </div>
        `;
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners: function() {
        const form = document.getElementById('troubleshooting-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.runTrace();
        });
    },
    
    /**
     * Load trace history
     */
    loadHistory: async function() {
        try {
            const response = await fetch(this.config.apiHistoryUrl, {
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load history');
            }
            
            const data = await response.json();
            this.state.history = data.records;
            this.renderHistory();
        } catch (error) {
            console.error('Failed to load history:', error);
            this.log('error', 'Failed to load trace history');
        }
    },
    
    /**
     * Render trace history
     */
    renderHistory: function() {
        const historyList = document.getElementById('history-list');
        
        if (this.state.history.length === 0) {
            historyList.innerHTML = `
                <li style="padding: 20px; text-align: center; color: #999;">
                    No trace history found. Run your first trace!
                </li>
            `;
            return;
        }
        
        historyList.innerHTML = this.state.history.map(record => `
            <li class="troubleshooting-history-item ${record.id === this.state.currentRecordId ? 'active' : ''}" 
                data-record-id="${record.id}">
                <div class="troubleshooting-history-item-title">
                    ${this.escapeHtml(record.source_host)} → ${this.escapeHtml(record.destination_host)}
                </div>
                <div class="troubleshooting-history-item-meta">
                    <span>${this.formatTime(record.start_time)}</span>
                    <span class="troubleshooting-history-item-status ${record.status}">
                        ${record.status_display}
                    </span>
                </div>
            </li>
        `).join('');
        
        // Add click listeners
        historyList.querySelectorAll('.troubleshooting-history-item').forEach(item => {
            item.addEventListener('click', () => {
                const recordId = item.getAttribute('data-record-id');
                this.loadRecord(recordId);
            });
        });
    },
    
    /**
     * Run a new trace
     */
    runTrace: async function() {
        if (this.state.isRunning) {
            return;
        }
        
        const form = document.getElementById('troubleshooting-form');
        const formData = new FormData(form);
        
        const payload = {
            source_ip: formData.get('source_ip'),
            destination_ip: formData.get('destination_ip'),
            secrets_group_id: formData.get('secrets_group_id'),
            enable_layer2_discovery: formData.get('enable_layer2_discovery') === 'on',
            ping_endpoints: formData.get('ping_endpoints') === 'on',
        };
        
        // Validate
        if (!payload.source_ip || !payload.destination_ip || !payload.secrets_group_id) {
            this.showAlert('error', 'Please fill in all required fields');
            return;
        }
        
        this.state.isRunning = true;
        this.updateRunButton(true);
        this.showProgress(true);
        this.clearLog();
        // Reset hop tracking for new trace
        this.state.lastHopCount = 0;
        this.log('info', `Starting trace: ${payload.source_ip} → ${payload.destination_ip}`);
        
        try {
            const response = await fetch(this.config.apiRunUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken,
                },
                body: JSON.stringify(payload),
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to start trace');
            }
            
            const data = await response.json();
            this.state.currentRecordId = data.record_id;
            this.log('success', `Trace started (ID: ${data.record_id})`);
            this.log('info', 'Tracing network path...');
            
            // Start polling for status
            this.startPolling(data.record_id);
            
        } catch (error) {
            console.error('Failed to run trace:', error);
            this.log('error', `Failed to start trace: ${error.message}`);
            this.state.isRunning = false;
            this.updateRunButton(false);
            this.showProgress(false);
        }
    },
    
    /**
     * Start polling for trace status
     */
    startPolling: function(recordId) {
        if (this.state.pollingInterval) {
            clearInterval(this.state.pollingInterval);
        }
        
        this.state.pollingInterval = setInterval(() => {
            this.checkStatus(recordId);
        }, 2000); // Poll every 2 seconds
        
        // Check immediately
        this.checkStatus(recordId);
    },
    
    /**
     * Check trace status
     */
    checkStatus: async function(recordId) {
        try {
            const url = this.config.apiStatusUrlBase + recordId + '/';
            const response = await fetch(url, {
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to check status');
            }
            
            const data = await response.json();
            this.updateStatus(data);
            
            // Update real-time hops display
            if (data.hops_data && data.hops_data.hops) {
                this.displayRealtimeHops(data.hops_data.hops);
            }
            
            // Stop polling if completed or failed
            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(this.state.pollingInterval);
                this.state.pollingInterval = null;
                this.state.isRunning = false;
                this.updateRunButton(false);
                this.showProgress(false);
                
                if (data.status === 'completed') {
                    this.log('success', 'Trace completed successfully!');
                    this.loadVisualization(recordId);
                    this.displayResults(data.result_data);
                } else {
                    this.log('error', `Trace failed: ${data.result_data.error || 'Unknown error'}`);
                }
                
                // Reload history
                this.loadHistory();
            }
            
        } catch (error) {
            console.error('Failed to check status:', error);
            this.log('error', `Failed to check status: ${error.message}`);
        }
    },
    
    /**
     * Update status display
     */
    updateStatus: function(data) {
        const statusEl = document.getElementById('viz-status');
        
        let statusHtml = '';
        if (data.status === 'running') {
            statusHtml = '<span class="spinner"></span><span>Running...</span>';
        } else if (data.status === 'completed') {
            statusHtml = '<span style="color: #5cb85c;"><i class="mdi mdi-check-circle"></i> Completed</span>';
        } else if (data.status === 'failed') {
            statusHtml = '<span style="color: #d9534f;"><i class="mdi mdi-alert-circle"></i> Failed</span>';
        } else {
            statusHtml = `<span>${data.status_display}</span>`;
        }
        
        statusEl.innerHTML = statusHtml;
    },
    
    /**
     * Load visualization for a record
     */
    loadVisualization: function(recordId) {
        const iframe = document.getElementById('visualization-iframe');
        const placeholder = document.getElementById('viz-placeholder');
        
        const url = this.config.visualizationUrlBase + recordId + '/';
        iframe.src = url;
        iframe.style.display = 'block';
        placeholder.style.display = 'none';
    },
    
    /**
     * Load a specific record
     */
    loadRecord: async function(recordId) {
        this.state.currentRecordId = recordId;
        this.renderHistory(); // Update active state
        
        try {
            const url = this.config.apiStatusUrlBase + recordId + '/';
            const response = await fetch(url, {
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load record');
            }
            
            const data = await response.json();
            this.updateStatus(data);
            
            if (data.has_visualization) {
                this.loadVisualization(recordId);
            }
            
            this.clearLog();
            this.log('info', `Loaded trace: ${data.source_host} → ${data.destination_host}`);
            this.log('info', `Status: ${data.status_display}`);
            
            if (data.result_data && Object.keys(data.result_data).length > 0) {
                this.displayResults(data.result_data);
            }
            
        } catch (error) {
            console.error('Failed to load record:', error);
            this.log('error', `Failed to load record: ${error.message}`);
        }
    },
    
    /**
     * Display real-time hops as they are discovered
     */
    displayRealtimeHops: function(hops) {
        if (!hops || hops.length === 0) {
            return;
        }
        
        // Get the last few hops that haven't been displayed yet
        const logPanel = document.getElementById('log-panel');
        if (!logPanel) {
            return;
        }
        
        const existingHopCount = this.state.lastHopCount || 0;
        const newHops = hops.slice(existingHopCount);
        
        newHops.forEach((hop, index) => {
            const hopNum = existingHopCount + index + 1;
            let hopType = hop.hop_type || 'layer3';
            let icon = 'mdi-router';
            if (hopType === 'layer2') {
                icon = 'mdi-switch';
            }
            
            const entry = document.createElement('div');
            entry.className = `troubleshooting-log-entry info troubleshooting-hop-entry`;
            entry.innerHTML = `
                <span class="timestamp">[Hop ${hopNum}]</span>
                <i class="mdi ${icon}"></i>
                <strong>${this.escapeHtml(hop.device_name || 'Unknown')}</strong>
                ${hop.interface_name ? `via ${this.escapeHtml(hop.interface_name)}` : ''}
                ${hop.next_hop_ip ? `→ ${this.escapeHtml(hop.next_hop_ip)}` : ''}
                ${hop.details ? `<span class="hop-details">(${this.escapeHtml(hop.details)})</span>` : ''}
            `;
            
            logPanel.appendChild(entry);
        });
        
        // Update last hop count
        this.state.lastHopCount = hops.length;
        logPanel.scrollTop = logPanel.scrollHeight;
    },
    
    /**
     * Display trace results in the log
     */
    displayResults: function(resultData) {
        if (resultData.error) {
            this.log('error', `Error: ${resultData.error}`);
            return;
        }
        
        if (resultData.source) {
            this.log('info', `Source: ${resultData.source.address} (${resultData.source.device_name})`);
        }
        
        if (resultData.gateway) {
            this.log('info', `Gateway: ${resultData.gateway.address} (${resultData.gateway.device_name})`);
        }
        
        if (resultData.paths && resultData.paths.length > 0) {
            this.log('info', `Found ${resultData.paths.length} path(s):`);
            
            resultData.paths.forEach((path, index) => {
                this.log('info', `  Path ${index + 1}: ${path.hops.length} hop(s) - ${path.reached_destination ? 'Reached destination' : 'Did not reach destination'}`);
                
                path.hops.forEach((hop, hopIndex) => {
                    this.log('info', `    Hop ${hopIndex + 1}: ${hop.device_name} (${hop.next_hop_ip})`);
                });
            });
        }
        
        if (resultData.issues && resultData.issues.length > 0) {
            this.log('warning', `Issues found:`);
            resultData.issues.forEach(issue => {
                this.log('warning', `  - ${issue}`);
            });
        }
    },
    
    /**
     * Update run button state
     */
    updateRunButton: function(isRunning) {
        const btn = document.getElementById('run-btn');
        if (isRunning) {
            btn.disabled = true;
            btn.classList.add('running');
            btn.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Running...';
        } else {
            btn.disabled = false;
            btn.classList.remove('running');
            btn.innerHTML = '<i class="mdi mdi-play"></i> Run Trace';
        }
    },
    
    /**
     * Show/hide progress bar
     */
    showProgress: function(show) {
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.display = show ? 'block' : 'none';
    },
    
    /**
     * Log a message
     */
    log: function(level, message) {
        const logPanel = document.getElementById('log-panel');
        const timestamp = new Date().toLocaleTimeString();
        
        const entry = document.createElement('div');
        entry.className = `troubleshooting-log-entry ${level}`;
        entry.innerHTML = `<span class="timestamp">[${timestamp}]</span>${this.escapeHtml(message)}`;
        
        logPanel.appendChild(entry);
        logPanel.scrollTop = logPanel.scrollHeight;
    },
    
    /**
     * Clear log
     */
    clearLog: function() {
        const logPanel = document.getElementById('log-panel');
        if (logPanel) {
            logPanel.innerHTML = '';
        }
    },
    
    /**
     * Show alert
     */
    showAlert: function(type, message) {
        const formPanel = document.querySelector('.troubleshooting-form-panel');
        if (!formPanel) {
            console.warn('TroubleshootingStudio: Form panel not found, cannot show alert');
            return;
        }
        
        // Remove existing alerts
        const existingAlerts = formPanel.querySelectorAll('.troubleshooting-alert');
        existingAlerts.forEach(alert => alert.remove());
        
        const alert = document.createElement('div');
        alert.className = `troubleshooting-alert ${type}`;
        alert.innerHTML = message;
        
        formPanel.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    },
    
    /**
     * Escape HTML
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    /**
     * Format time
     */
    formatTime: function(isoString) {
        if (!isoString) return 'N/A';
        
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    }
};

