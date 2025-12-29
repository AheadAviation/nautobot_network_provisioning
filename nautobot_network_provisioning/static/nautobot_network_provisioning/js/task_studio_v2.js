/**
 * Automation Studio - Functional IDE
 * 
 * Features:
 * - Context Explorer (like GraphQL schema)
 * - Live Validation
 * - Test Execution
 * - IntelliSense from context
 */

require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' }});

const Studio = {
    editors: {
        template: null,
        preview: null,
        context: null,
        schema: null
    },
    data: {
        selectedDeviceId: null,
        context: {},
        errors: [],
        platforms: [],
        selectedPlatformId: null,
        implementations: [],
        activeImplementationId: 'default',
        editingImplementation: null,
        inputSchema: {},
        variableMappings: [],
        roles: []
    },
    debounceTimer: null,
    activeTab: 'preview',

    init: function() {
        require(['vs/editor/editor.main'], () => {
            this.setupEditors();
            this.loadPlatforms();
            this.loadRoles();
            this.setupEventListeners();
            this.setupConditionModal();
            this.setupPlatformConfigPanel();
            this.loadManufacturers();
            this.loadInitialData();
            this.registerJinja2Language();
            this.setupIntelliSense();
            this.updateStatus('Ready - Start typing your template', 'success');
        });
    },

    setupEditors: function() {
        const commonOptions = {
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 13,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: 'on',
            folding: true
        };

        // Template Editor - Start with helpful example if new task
        const isNewTask = !window.STUDIO_CONFIG.task || !window.STUDIO_CONFIG.task.id;
        const templateValue = window.STUDIO_CONFIG.task?.implementations?.[0]?.template_content || 
                              window.STUDIO_CONFIG.task?.template_content || 
                              (isNewTask ? 
                                "{# Welcome to Automation Studio!\n\n1. Enter a task name above\n2. Search for a device below and click 'Load Context'\n3. View the Context tab in the preview pane to see available variables\n4. Write your Jinja2 template here\n5. Click 'Platform' button to configure target platform settings\n\nExample:\n#}\ninterface {{ device.name }}\n description {{ intended.description }}\n switchport mode access\n switchport access vlan {{ intended.vlan_id }}\n" :
                                "{# Write your Jinja2 template here\nUse variables from the Context tab in the preview pane\n#}\n\n");
        
        this.editors.template = monaco.editor.create(document.getElementById('monaco-editor'), {
            ...commonOptions,
            value: templateValue,
            language: 'jinja2'
        });

        // Preview Editor
        const previewElement = document.getElementById('monaco-preview');
        if (previewElement) {
            this.editors.preview = monaco.editor.create(previewElement, {
                ...commonOptions,
                value: "Select a device and click 'Load Context', then 'Test' to see preview...",
                language: 'text',
                readOnly: true
            });
        } else {
            console.error('Preview editor element not found');
        }

        // Context Editor
        this.editors.context = monaco.editor.create(document.getElementById('monaco-context'), {
            ...commonOptions,
            value: '{\n  "Select a device to load context..."\n}',
            language: 'json',
            readOnly: true
        });

        // Schema editor removed - no longer needed

        // Hot reload
        this.editors.template.onDidChangeModelContent(() => {
            // Update active implementation's template
            const activeImpl = this.data.implementations.find(i => i.id === this.data.activeImplementationId);
            if (activeImpl) {
                activeImpl.template = this.editors.template.getValue();
            }
            this.validateTemplate();
            // Only auto-render if device and context are loaded
            if (this.data.selectedDeviceId && this.data.context && Object.keys(this.data.context).length > 0) {
                this.debouncedRender();
            }
        });
    },

    setupEventListeners: function() {
        // Device search with auto-populating dropdown
        const deviceSearch = document.getElementById('device-search');
        let resultsDiv = document.getElementById('device-results');
        
        if (!resultsDiv) {
            resultsDiv = document.createElement('div');
            resultsDiv.id = 'device-results';
            resultsDiv.className = 'device-results';
            deviceSearch.parentElement.style.position = 'relative';
            deviceSearch.parentElement.appendChild(resultsDiv);
        }
        
        // Ensure styling is correct
        resultsDiv.style.cssText = 'position: absolute; top: 100%; left: 0; right: 0; background: #252526; border: 1px solid #3e3e42; z-index: 1000; max-height: 300px; overflow-y: auto; display: none; margin-top: 2px; border-radius: 3px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';

        // Search function
        const performSearch = async (query = '') => {
            try {
                const queryParam = query.trim() ? `&q=${encodeURIComponent(query.trim())}` : '';
                const platformParam = this.data.selectedPlatformId ? `&platform_id=${this.data.selectedPlatformId}` : '';
                const limit = query.trim() ? 20 : 5; // Show 5 devices when empty, 20 when searching
                const url = `${window.STUDIO_CONFIG.apiRoot}device-search/?limit=${limit}${queryParam}${platformParam}`;
                console.log('Device search URL:', url);
                
                const resp = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': window.STUDIO_CONFIG.csrfToken,
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin'
                });
                
                console.log('Device search response status:', resp.status);
                
                if (!resp.ok) {
                    const errorText = await resp.text();
                    console.error('Device search error:', errorText);
                    throw new Error(`HTTP ${resp.status}: ${errorText.substring(0, 100) || resp.statusText}`);
                }
                
                const data = await resp.json();
                console.log('Device search results:', data);
                
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response format');
                }
                
                resultsDiv.innerHTML = '';
                
                if (!data.results || data.results.length === 0) {
                    const noResults = document.createElement('div');
                    noResults.style.cssText = 'padding: 12px; color: #858585; font-size: 12px; text-align: center;';
                    noResults.textContent = query.trim() ? 'No devices found' : 'No devices available';
                    resultsDiv.appendChild(noResults);
                    resultsDiv.style.display = 'block';
                    return;
                }
                
                data.results.forEach(d => {
                    const div = document.createElement('div');
                    div.className = 'device-result-item';
                    div.innerHTML = `
                        <div class="device-result-name">${this.escapeHtml(d.name || d.display || 'Unknown')}</div>
                        <div class="device-result-meta">${this.escapeHtml([d.platform, d.location].filter(Boolean).join(' • ') || 'No details')}</div>
                    `;
                    div.onclick = () => {
                        this.data.selectedDeviceId = d.id;
                        deviceSearch.value = d.name || d.display || '';
                        resultsDiv.style.display = 'none';
                        this.updateStatus('Loading context...', null);
                        this.loadContext();
                    };
                    div.onmouseenter = () => div.style.background = '#2d2d30';
                    div.onmouseleave = () => div.style.background = 'transparent';
                    resultsDiv.appendChild(div);
                });
                resultsDiv.style.display = 'block';
            } catch (e) {
                console.error("Device search failed", e);
                resultsDiv.innerHTML = `<div style="padding: 12px; color: #f48771; font-size: 12px;">Error: ${this.escapeHtml(e.message)}</div>`;
                resultsDiv.style.display = 'block';
                this.updateStatus(`Search error: ${e.message}`, 'error');
            }
        };

        // Platform filter change
        const platformFilter = document.getElementById('platform-filter');
        platformFilter.addEventListener('change', (e) => {
            this.data.selectedPlatformId = e.target.value;
            // Trigger search again with new filter
            performSearch(deviceSearch.value.trim());
        });

        // Auto-populate on focus (show top 5 devices)
        deviceSearch.addEventListener('focus', () => {
            if (!deviceSearch.value.trim()) {
                performSearch('');
            }
        });

        // Search as user types
        deviceSearch.addEventListener('input', this.debounce(async (e) => {
            const query = e.target.value.trim();
            performSearch(query);
        }, 300));

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!deviceSearch.contains(e.target) && !resultsDiv.contains(e.target)) {
                resultsDiv.style.display = 'none';
            }
        });

        // Keyboard navigation
        deviceSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                resultsDiv.style.display = 'none';
            }
        });

        // Buttons
        document.getElementById('btn-resolve').onclick = () => this.loadContext();
        document.getElementById('btn-validate').onclick = () => this.validateTemplate(true);
        document.getElementById('btn-test').onclick = () => this.testTemplate();
        document.getElementById('btn-save').onclick = () => this.saveIntent();
        document.getElementById('btn-format').onclick = () => this.formatTemplate();
        
        // Platform config panel buttons
        const platformConfigBtn = document.getElementById('btn-platform-config');
        const platformConfigToggle = document.getElementById('platform-config-toggle');
        const platformConfigPane = document.getElementById('platform-config-pane');
        const closePlatformConfigBtn = document.getElementById('btn-close-platform-config');
        
        if (platformConfigBtn) {
            platformConfigBtn.onclick = () => this.togglePlatformConfigPanel();
        }
        if (platformConfigToggle) {
            platformConfigToggle.onclick = () => this.togglePlatformConfigPanel();
        }
        if (closePlatformConfigBtn) {
            closePlatformConfigBtn.onclick = () => this.togglePlatformConfigPanel();
        }
        if (document.getElementById('btn-save-platform-config')) {
            document.getElementById('btn-save-platform-config').onclick = () => this.savePlatformConfig();
        }

        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.onclick = () => this.switchTab(tab.dataset.tab);
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // ESC to exit (if not typing in input/editor)
            if (e.key === 'Escape' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                const exitBtn = document.querySelector('.exit-btn');
                if (exitBtn) exitBtn.click();
            }
            // Ctrl+S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                document.getElementById('btn-save').click();
            }
            // Ctrl+Enter to test
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('btn-test').click();
            }
        });
    },

    setupPlatformConfigPanel: function() {
        // Initialize platform config panel - OPEN by default (no collapsed class)
        const panel = document.getElementById('platform-config-pane');
        const toggle = document.getElementById('platform-config-toggle');
        // Panel starts open, so toggle button should be hidden
        if (toggle) {
            toggle.style.display = 'none';
        }
        
        // Load current implementation data if editing
        if (window.STUDIO_CONFIG.task && window.STUDIO_CONFIG.task.implementations) {
            const impl = window.STUDIO_CONFIG.task.implementations[0];
            if (impl) {
                this.loadPlatformConfigData(impl);
            }
        }
        
        // Setup manufacturer change handler
        const manufacturerSelect = document.getElementById('platform-manufacturer');
        if (manufacturerSelect) {
            manufacturerSelect.addEventListener('change', () => {
                this.loadPlatformsForManufacturer(manufacturerSelect.value);
            });
        }
        
        // Setup platform change handler
        const platformSelect = document.getElementById('platform-select');
        if (platformSelect) {
            platformSelect.addEventListener('change', () => {
                this.loadDeviceTypesForPlatform(platformSelect.value);
            });
        }
    },
    
    togglePlatformConfigPanel: function() {
        const panel = document.getElementById('platform-config-pane');
        const toggle = document.getElementById('platform-config-toggle');
        const closeBtn = document.getElementById('btn-close-platform-config');
        
        if (panel) {
            const isCollapsed = panel.classList.contains('collapsed');
            panel.classList.toggle('collapsed');
            
            // Update toggle button visibility
            if (toggle) {
                toggle.style.display = isCollapsed ? 'none' : 'flex';
            }
            
            // Update close button icon
            if (closeBtn) {
                const icon = closeBtn.querySelector('i');
                if (icon) {
                    icon.className = isCollapsed ? 'mdi mdi-chevron-right' : 'mdi mdi-chevron-right';
                }
            }
        }
    },
    
    loadManufacturers: async function() {
        const select = document.getElementById('platform-manufacturer');
        if (!select) return;
        
        try {
            // Use Nautobot's DCIM API endpoint
            const apiBase = window.STUDIO_CONFIG.apiRoot.replace('/plugins/network-provisioning/api/', '/api/');
            const resp = await fetch(`${apiBase}dcim/manufacturers/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                }
            });
            
            if (resp.ok) {
                const data = await resp.json();
                select.innerHTML = '<option value="">-- Select Manufacturer --</option>';
                (data.results || []).forEach(mfg => {
                    const option = document.createElement('option');
                    option.value = mfg.id;
                    option.textContent = mfg.name || mfg.display;
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error('Failed to load manufacturers:', e);
        }
    },
    
    loadPlatformsForManufacturer: async function(manufacturerId) {
        const select = document.getElementById('platform-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">-- Select Platform --</option>';
        if (!manufacturerId) return;
        
        try {
            const apiBase = window.STUDIO_CONFIG.apiRoot.replace('/plugins/network-provisioning/api/', '/api/');
            const url = `${apiBase}dcim/platforms/?manufacturer_id=${manufacturerId}`;
            const resp = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                }
            });
            
            if (resp.ok) {
                const data = await resp.json();
                (data.results || []).forEach(platform => {
                    const option = document.createElement('option');
                    option.value = platform.id;
                    option.textContent = platform.name || platform.display;
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error('Failed to load platforms:', e);
        }
    },
    
    loadDeviceTypesForPlatform: async function(platformId) {
        const select = document.getElementById('platform-device-type');
        if (!select) return;
        
        select.innerHTML = '<option value="">-- Any Device Type --</option>';
        if (!platformId) return;
        
        try {
            // Get platform details to find device types
            const apiBase = window.STUDIO_CONFIG.apiRoot.replace('/plugins/network-provisioning/api/', '/api/');
            const url = `${apiBase}dcim/platforms/${platformId}/`;
            const resp = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                }
            });
            
            if (resp.ok) {
                const platform = await resp.json();
                // Load device types for this platform's manufacturer
                if (platform.manufacturer) {
                    const deviceTypesUrl = `${apiBase}dcim/device-types/?manufacturer_id=${platform.manufacturer}`;
                    const dtResp = await fetch(deviceTypesUrl, {
                        headers: {
                            'Accept': 'application/json',
                            'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                        }
                    });
                    
                    if (dtResp.ok) {
                        const dtData = await dtResp.json();
                        (dtData.results || []).forEach(dt => {
                            const option = document.createElement('option');
                            option.value = dt.id;
                            option.textContent = dt.model || dt.display;
                            select.appendChild(option);
                        });
                    }
                }
            }
        } catch (e) {
            console.error('Failed to load device types:', e);
        }
    },
    
    loadPlatformConfigData: function(implementation) {
        // Populate form with existing implementation data
        if (implementation.platform) {
            // Load manufacturer first, then platform
            // This would require additional API calls to get platform details
            const platformSelect = document.getElementById('platform-select');
            if (platformSelect && implementation.platform) {
                // Set platform - this will trigger device type loading
                platformSelect.value = implementation.platform;
            }
        }
        
        const priorityInput = document.getElementById('platform-priority');
        if (priorityInput) {
            priorityInput.value = implementation.priority || 100;
        }
        
        const enabledCheckbox = document.getElementById('platform-enabled');
        if (enabledCheckbox) {
            enabledCheckbox.checked = implementation.enabled !== false;
        }
        
        // Version pattern if stored
        const versionPatternInput = document.getElementById('platform-version-pattern');
        if (versionPatternInput && implementation.version_pattern) {
            versionPatternInput.value = implementation.version_pattern;
        }
    },
    
    savePlatformConfig: async function() {
        const platformId = document.getElementById('platform-select').value;
        const manufacturerId = document.getElementById('platform-manufacturer').value;
        const deviceTypeId = document.getElementById('platform-device-type').value;
        const versionPattern = document.getElementById('platform-version-pattern').value;
        const priority = parseInt(document.getElementById('platform-priority').value) || 100;
        const enabled = document.getElementById('platform-enabled').checked;
        
        if (!platformId) {
            alert('Please select a platform');
            return;
        }
        
        const taskId = window.STUDIO_CONFIG.task?.id;
        if (!taskId) {
            alert('Please save the task first before configuring platform');
            return;
        }
        
        try {
            const payload = {
                task_intent: taskId,
                platform: platformId,
                priority: priority,
                enabled: enabled,
                logic_type: 'jinja2',
                template_content: this.editors.template.getValue()
            };
            
            // Add optional fields
            if (versionPattern) {
                payload.version_pattern = versionPattern;
            }
            
            const url = `${window.STUDIO_CONFIG.apiRoot}task-implementations/`;
            const resp = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken,
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (resp.ok) {
                this.updateStatus('Platform configuration saved', 'success');
                // Optionally close the panel
                setTimeout(() => this.togglePlatformConfigPanel(), 1000);
            } else {
                const error = await resp.json();
                this.updateStatus(`Error: ${error.detail || 'Failed to save'}`, 'error');
            }
        } catch (e) {
            console.error('Failed to save platform config:', e);
            this.updateStatus(`Error: ${e.message}`, 'error');
        }
    },

    setupResizer: function(resizer, targetSelector, minHeight, maxHeight) {
        let isResizing = false;
        let startY = 0;
        let startHeight = 0;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            const targetSection = document.querySelector(targetSelector);
            if (targetSection) {
                startHeight = targetSection.offsetHeight;
            }
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
        });

        const mousemove = (e) => {
            if (!isResizing) return;
            const targetSection = document.querySelector(targetSelector);
            if (targetSection) {
                const deltaY = e.clientY - startY;
                const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight + deltaY));
                targetSection.style.flex = `0 0 ${newHeight}px`;
            }
        };

        const mouseup = () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
            }
        };

        document.addEventListener('mousemove', mousemove);
        document.addEventListener('mouseup', mouseup);
    },

    setupConditionModal: function() {
        const modal = document.getElementById('condition-modal');
        if (!modal) return;
        
        const closeBtn = document.getElementById('modal-close');
        const cancelBtn = document.getElementById('modal-cancel');
        const saveBtn = document.getElementById('modal-save');

        [closeBtn, cancelBtn].forEach(btn => {
            if (btn) btn.onclick = () => {
                modal.classList.remove('active');
                this.data.editingImplementation = null;
            };
        });

        if (saveBtn) saveBtn.onclick = () => {
            this.saveImplementationConditions();
        };
    },

    // setupConfigTabs and setupVariableMapper removed - no longer needed

    updateSchemaFromEditor: function() {
        if (!this.editors.schema) return;
        
        try {
            const schemaText = this.editors.schema.getValue();
            this.data.inputSchema = JSON.parse(schemaText);
            this.renderVariableMapper();
        } catch (e) {
            // Invalid JSON, ignore for now
            console.warn('Invalid schema JSON:', e);
        }
    },

    renderVariableMapper: function() {
        const tbody = document.getElementById('var-mapper-body');
        if (!tbody) return;

        const schema = this.data.inputSchema || {};
        const mappings = this.data.variableMappings || [];

        tbody.innerHTML = '';

        if (Object.keys(schema).length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 20px; color: #858585; font-size: 11px;">
                        Define variables in Schema tab first
                    </td>
                </tr>
            `;
            return;
        }

        Object.keys(schema).forEach(varName => {
            const varType = schema[varName];
            const mapping = mappings.find(m => m.variable === varName) || {
                variable: varName,
                type: varType,
                source: 'user_input',
                path: '',
                default: ''
            };

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="text" class="var-mapper-input" value="${this.escapeHtml(varName)}" readonly></td>
                <td><input type="text" class="var-mapper-input" value="${this.escapeHtml(varType)}" readonly></td>
                <td>
                    <select class="var-mapper-select" data-var="${varName}" data-field="source">
                        <option value="user_input" ${mapping.source === 'user_input' ? 'selected' : ''}>User Input</option>
                        <option value="config_context" ${mapping.source === 'config_context' ? 'selected' : ''}>Config Context</option>
                        <option value="local_context" ${mapping.source === 'local_context' ? 'selected' : ''}>Local Context</option>
                        <option value="device_attribute" ${mapping.source === 'device_attribute' ? 'selected' : ''}>Device Attribute</option>
                        <option value="default" ${mapping.source === 'default' ? 'selected' : ''}>Default Value</option>
                    </select>
                </td>
                <td><input type="text" class="var-mapper-input" data-var="${varName}" data-field="path" value="${this.escapeHtml(mapping.path)}" placeholder="e.g., device.name"></td>
                <td><input type="text" class="var-mapper-input" data-var="${varName}" data-field="default" value="${this.escapeHtml(mapping.default)}" placeholder="Default value"></td>
                <td>
                    <button class="btn-icon-small" onclick="Studio.removeVariableMapping('${varName}')">
                        <i class="mdi mdi-delete"></i>
                    </button>
                </td>
            `;

            // Add change listeners
            row.querySelectorAll('select, input[type="text"]').forEach(input => {
                if (!input.readOnly) {
                    input.addEventListener('change', () => {
                        this.updateVariableMapping(varName);
                    });
                }
            });

            tbody.appendChild(row);
        });
    },

    addVariableMapping: function() {
        const varName = prompt('Variable name:');
        if (!varName) return;

        const varType = prompt('Variable type (string/integer/boolean):', 'string');
        if (!varType) return;

        // Update schema
        if (!this.data.inputSchema) this.data.inputSchema = {};
        this.data.inputSchema[varName] = varType;

        // Update schema editor
        if (this.editors.schema) {
            this.editors.schema.setValue(JSON.stringify(this.data.inputSchema, null, 2));
        }

        this.renderVariableMapper();
    },

    removeVariableMapping: function(varName) {
        if (!confirm(`Remove variable "${varName}"?`)) return;

        delete this.data.inputSchema[varName];
        this.data.variableMappings = this.data.variableMappings.filter(m => m.variable !== varName);

        if (this.editors.schema) {
            this.editors.schema.setValue(JSON.stringify(this.data.inputSchema, null, 2));
        }

        this.renderVariableMapper();
    },

    updateVariableMapping: function(varName) {
        const row = document.querySelector(`tr:has(input[data-var="${varName}"])`);
        if (!row) return;

        const source = row.querySelector(`select[data-var="${varName}"][data-field="source"]`).value;
        const path = row.querySelector(`input[data-var="${varName}"][data-field="path"]`).value;
        const defaultValue = row.querySelector(`input[data-var="${varName}"][data-field="default"]`).value;

        const existing = this.data.variableMappings.findIndex(m => m.variable === varName);
        const mapping = {
            variable: varName,
            type: this.data.inputSchema[varName],
            source: source,
            path: path,
            default: defaultValue
        };

        if (existing >= 0) {
            this.data.variableMappings[existing] = mapping;
        } else {
            this.data.variableMappings.push(mapping);
        }
    },

    loadImplementations: function() {
        const task = window.STUDIO_CONFIG.task;
        if (!task || !task.id) {
            // New task - just show default
            this.data.implementations = [{ id: 'default', platform: null, conditions: null, template: '' }];
            this.renderImplementations();
            return;
        }

        // Load implementations from API
        fetch(`${window.STUDIO_CONFIG.apiRoot}task-intents/${task.id}/`, {
            headers: {
                'X-CSRFToken': window.STUDIO_CONFIG.csrfToken,
                'Accept': 'application/json'
            }
        })
        .then(resp => resp.json())
        .then(data => {
            this.data.implementations = [
                { id: 'default', platform: null, conditions: null, template: '' },
                ...(data.implementations || []).map(impl => ({
                    id: impl.id,
                    platform: impl.platform,
                    conditions: null, // TODO: Add conditions field to model
                    template: impl.template_content || ''
                }))
            ];
            this.renderImplementations();
        })
        .catch(e => {
            console.error('Failed to load implementations:', e);
            this.data.implementations = [{ id: 'default', platform: null, conditions: null, template: '' }];
            this.renderImplementations();
        });
    },

    renderImplementations: function() {
        const container = document.getElementById('implementations-list');
        if (!container) return;
        
        container.innerHTML = '';

        this.data.implementations.forEach(impl => {
            const card = document.createElement('div');
            card.className = `implementation-card ${impl.id === this.data.activeImplementationId ? 'active' : ''}`;
            card.dataset.implId = impl.id;
            
            const platformName = impl.platform ? impl.platform.name : 'Default Strategy';
            const conditionText = impl.conditions ? this.formatConditions(impl.conditions) : 'Fallback (no conditions)';
            
            card.innerHTML = `
                <div class="impl-card-content">
                    <div class="impl-card-header">
                        <span class="impl-platform">${this.escapeHtml(platformName)}</span>
                        ${impl.id !== 'default' ? `
                            <button class="btn-icon-small impl-settings" title="Settings" onclick="Studio.editImplementationConditions('${impl.id}')">
                                <i class="mdi mdi-cog"></i>
                            </button>
                        ` : ''}
                    </div>
                    <div class="impl-condition">${this.escapeHtml(conditionText)}</div>
                </div>
            `;
            
            card.onclick = (e) => {
                if (!e.target.closest('.impl-settings')) {
                    this.selectImplementation(impl.id);
                }
            };
            
            container.appendChild(card);
        });
    },

    selectImplementation: function(implId) {
        this.data.activeImplementationId = implId;
        const impl = this.data.implementations.find(i => i.id === implId);
        
        if (impl && this.editors.template) {
            this.editors.template.setValue(impl.template || '');
        }
        
        this.renderImplementations();
    },

    formatConditions: function(conditions) {
        if (!conditions || !conditions.length) return 'Fallback (no conditions)';
        
        const formatted = conditions.map(c => {
            if (c.field === 'version' && c.operator === 'matches') {
                return `Version matches ${c.value}`;
            } else if (c.field === 'role' && c.operator === 'equals') {
                const role = this.data.roles.find(r => r.id === c.value);
                return `Role: ${role ? role.name : c.value}`;
            } else {
                const opMap = {
                    'equals': '=',
                    'contains': 'contains',
                    'matches': 'matches',
                    'lt': '<',
                    'gt': '>',
                    'lte': '<=',
                    'gte': '>=',
                    'in': 'in',
                    'not_in': 'not in'
                };
                return `${c.field} ${opMap[c.operator] || c.operator} ${c.value}`;
            }
        });
        
        return formatted.join(' AND ');
    },

    editImplementationConditions: function(implId) {
        const impl = this.data.implementations.find(i => i.id === implId);
        if (!impl) return;

        this.data.editingImplementation = impl;
        const modal = document.getElementById('condition-modal');
        const platformSelect = document.getElementById('condition-platform');
        const versionRegex = document.getElementById('condition-version-regex');
        const roleSelect = document.getElementById('condition-role');
        const rulesContainer = document.getElementById('condition-rules');
        
        if (platformSelect) {
            platformSelect.value = impl.platform ? impl.platform.id : '';
        }

        // Clear existing rules
        if (rulesContainer) {
            rulesContainer.innerHTML = '';
        }

        if (versionRegex) versionRegex.value = '';
        if (roleSelect) roleSelect.value = '';

        // Load existing conditions
        if (impl.conditions && impl.conditions.length > 0) {
            impl.conditions.forEach(condition => {
                if (condition.field === 'version' && condition.operator === 'matches') {
                    if (versionRegex) versionRegex.value = condition.value;
                } else if (condition.field === 'role' && condition.operator === 'equals') {
                    if (roleSelect) roleSelect.value = condition.value;
                } else {
                    // Add as regular rule
                    const rule = document.createElement('div');
                    rule.className = 'condition-rule';
                    rule.innerHTML = `
                        <select class="condition-field">
                            <option value="version" ${condition.field === 'version' ? 'selected' : ''}>Version</option>
                            <option value="role" ${condition.field === 'role' ? 'selected' : ''}>Role</option>
                            <option value="tag" ${condition.field === 'tag' ? 'selected' : ''}>Tag</option>
                            <option value="manufacturer" ${condition.field === 'manufacturer' ? 'selected' : ''}>Manufacturer</option>
                            <option value="location" ${condition.field === 'location' ? 'selected' : ''}>Location</option>
                            <option value="site" ${condition.field === 'site' ? 'selected' : ''}>Site</option>
                        </select>
                        <select class="condition-operator">
                            <option value="equals" ${condition.operator === 'equals' ? 'selected' : ''}>equals</option>
                            <option value="contains" ${condition.operator === 'contains' ? 'selected' : ''}>contains</option>
                            <option value="matches" ${condition.operator === 'matches' ? 'selected' : ''}>matches regex</option>
                            <option value="lt" ${condition.operator === 'lt' ? 'selected' : ''}>&lt;</option>
                            <option value="gt" ${condition.operator === 'gt' ? 'selected' : ''}>&gt;</option>
                        </select>
                        <input type="text" class="condition-value" value="${this.escapeHtml(condition.value)}" placeholder="Value">
                        <button class="btn-icon-small" onclick="this.parentElement.remove()">
                            <i class="mdi mdi-close"></i>
                        </button>
                    `;
                    if (rulesContainer) rulesContainer.appendChild(rule);
                }
            });
        }
        
        if (modal) modal.classList.add('active');
    },

    addNewVariant: function() {
        // Create a new implementation variant
        const newImpl = {
            id: `impl-${Date.now()}`,
            platform: null,
            conditions: null,
            template: ''
        };
        this.data.implementations.push(newImpl);
        this.selectImplementation(newImpl.id);
        this.editImplementationConditions(newImpl.id);
    },

    addConditionRule: function() {
        const container = document.getElementById('condition-rules');
        if (!container) return;
        
        const rule = document.createElement('div');
        rule.className = 'condition-rule';
        rule.innerHTML = `
            <select class="condition-field">
                <option value="version">Version</option>
                <option value="role">Role</option>
                <option value="tag">Tag</option>
                <option value="manufacturer">Manufacturer</option>
                <option value="location">Location</option>
                <option value="site">Site</option>
            </select>
            <select class="condition-operator">
                <option value="equals">equals</option>
                <option value="contains">contains</option>
                <option value="matches">matches regex</option>
                <option value="lt">&lt;</option>
                <option value="gt">&gt;</option>
                <option value="lte">&lt;=</option>
                <option value="gte">&gt;=</option>
                <option value="in">in list</option>
                <option value="not_in">not in list</option>
            </select>
            <input type="text" class="condition-value" placeholder="Value">
            <button class="btn-icon-small" onclick="this.parentElement.remove()">
                <i class="mdi mdi-close"></i>
            </button>
        `;
        container.appendChild(rule);
    },

    saveImplementationConditions: function() {
        const modal = document.getElementById('condition-modal');
        const platformSelect = document.getElementById('condition-platform');
        const versionRegex = document.getElementById('condition-version-regex');
        const roleSelect = document.getElementById('condition-role');
        
        const rules = Array.from(document.querySelectorAll('.condition-rule')).map(rule => ({
            field: rule.querySelector('.condition-field').value,
            operator: rule.querySelector('.condition-operator').value,
            value: rule.querySelector('.condition-value').value
        })).filter(r => r.value);

        // Add version regex if provided
        if (versionRegex && versionRegex.value.trim()) {
            rules.push({
                field: 'version',
                operator: 'matches',
                value: versionRegex.value.trim()
            });
        }

        // Add role if provided
        if (roleSelect && roleSelect.value) {
            rules.push({
                field: 'role',
                operator: 'equals',
                value: roleSelect.value
            });
        }

        if (this.data.editingImplementation) {
            this.data.editingImplementation.platform = this.data.platforms.find(p => p.id === platformSelect.value) || null;
            this.data.editingImplementation.conditions = rules;
            this.renderImplementations();
        }

        if (modal) modal.classList.remove('active');
        this.data.editingImplementation = null;
    },

    loadContext: async function() {
        if (!this.data.selectedDeviceId) {
            this.updateStatus('Please select a device first', 'error');
            return;
        }

        this.updateStatus('Loading context...', null);

        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}resolve-variables/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                body: JSON.stringify({
                    device_id: this.data.selectedDeviceId,
                    variable_mappings: []
                })
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${resp.status}: ${resp.statusText}`);
            }

            const data = await resp.json();
            
            // Build context object from response
            this.data.context = {
                device: data.device || {},
                intended: data.variables || {},
                config_context: data.config_context || {},
                local_context_data: data.local_context_data || {}
            };

            // Update context editor
            this.editors.context.setValue(JSON.stringify(this.data.context, null, 2));
            
            // Update context explorer
            this.renderContextExplorer();
            
            // Update IntelliSense
            this.updateIntelliSense();
            
            // Switch to context tab to show loaded data
            this.switchTab('context');
            
            this.updateStatus('Context loaded successfully', 'success');
            
            // Auto-render preview after context is loaded
            setTimeout(() => {
                this.debouncedRender();
            }, 100);
        } catch (e) {
            console.error('Context load error:', e);
            this.updateStatus(`Failed to load context: ${e.message}`, 'error');
            this.editors.context.setValue(`{\n  "error": "Failed to load context: ${e.message}"\n}`);
        }
    },

    renderContextExplorer: function() {
        const container = document.getElementById('context-explorer');
        const ctx = this.data.context;
        
        if (!this.data.selectedDeviceId) {
            container.innerHTML = `
                <div style="padding: 12px; font-size: 11px; color: #858585; line-height: 1.6;">
                    <div style="margin-bottom: 8px; font-weight: 600; color: #cccccc;">Getting Started:</div>
                    <div style="margin-bottom: 4px;">1. Search for a device above</div>
                    <div style="margin-bottom: 4px;">2. Click "Load Context"</div>
                    <div style="margin-bottom: 4px;">3. Browse available variables here</div>
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #3e3e42;">
                        <div style="font-weight: 600; color: #4ec9b0; margin-bottom: 4px;">Tip:</div>
                        <div>Click any variable to insert it into your template</div>
                    </div>
                </div>
            `;
            return;
        }
        
        if (!ctx.device || Object.keys(ctx.device).length === 0) {
            container.innerHTML = '<div style="padding: 12px; font-size: 11px; color: #858585;">Loading context...</div>';
            return;
        }

        let html = '';

        // Device attributes
        if (ctx.device) {
            html += '<div class="context-section"><div class="context-section-title">device</div>';
            Object.keys(ctx.device).slice(0, 20).forEach(key => {
                const value = ctx.device[key];
                const type = typeof value === 'object' ? 'object' : typeof value;
                html += `<div class="context-item" onclick="Studio.insertVariable('device.${key}')">
                    <span class="context-item-name">device.${key}</span>
                    <span class="context-item-type">${type}</span>
                </div>`;
            });
            html += '</div>';
        }

        // Intended variables
        if (ctx.intended && Object.keys(ctx.intended).length > 0) {
            html += '<div class="context-section"><div class="context-section-title">intended</div>';
            Object.keys(ctx.intended).forEach(key => {
                const value = ctx.intended[key];
                const type = typeof value === 'object' ? 'object' : typeof value;
                html += `<div class="context-item" onclick="Studio.insertVariable('intended.${key}')">
                    <span class="context-item-name">intended.${key}</span>
                    <span class="context-item-type">${type}</span>
                </div>`;
            });
            html += '</div>';
        }

        container.innerHTML = html || '<div style="padding: 8px; font-size: 11px; color: #858585;">No context data available</div>';
    },

    insertVariable: function(varName) {
        const editor = this.editors.template;
        const position = editor.getPosition();
        const range = new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column);
        editor.executeEdits('', [{
            range: range,
            text: `{{ ${varName} }}`
        }]);
        editor.focus();
    },

    validateTemplate: async function(showErrors = false) {
        const template = this.editors.template.getValue();
        this.data.errors = [];

        if (!template.trim()) {
            if (showErrors) {
                this.updateStatus('Template is empty', 'warning');
            }
            return true;
        }

        // Basic Jinja2 syntax check
        const openBlocks = (template.match(/\{%/g) || []).length;
        const closeBlocks = (template.match(/%\}/g) || []).length;
        const openExpr = (template.match(/\{\{/g) || []).length;
        const closeExpr = (template.match(/\}\}/g) || []).length;

        if (openBlocks !== closeBlocks) {
            this.data.errors.push({
                message: `Mismatched block tags: ${openBlocks} opening, ${closeBlocks} closing`,
                line: 1
            });
        }

        if (openExpr !== closeExpr) {
            this.data.errors.push({
                message: `Mismatched expression tags: ${openExpr} opening, ${closeExpr} closing`,
                line: 1
            });
        }

        // If device is selected, try to render for validation
        if (this.data.selectedDeviceId && Object.keys(this.data.context).length > 0) {
            try {
                const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}render-preview/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                    },
                    body: JSON.stringify({
                        template_code: template,
                        device_id: this.data.selectedDeviceId,
                        context_overrides: this.data.context.intended || {},
                        variable_mappings: []
                    })
                });

                if (!resp.ok) {
                    const errorText = await resp.text();
                    this.data.errors.push({
                        message: `Validation failed: HTTP ${resp.status}`,
                        line: 1
                    });
                } else {
                    const data = await resp.json();
                    if (data.error || data.success === false) {
                        this.data.errors.push({
                            message: data.error || 'Template validation failed',
                            line: 1
                        });
                    }
                }
            } catch (e) {
                this.data.errors.push({
                    message: `Validation error: ${e.message}`,
                    line: 1
                });
            }
        }

        if (this.data.errors.length > 0) {
            this.renderErrors();
            if (showErrors) {
                this.switchTab('errors');
                this.updateStatus(`Found ${this.data.errors.length} error(s)`, 'error');
            }
            return false;
        }

        if (showErrors) {
            this.updateStatus('Template is valid', 'success');
        }
        return true;
    },

    renderErrors: function() {
        const container = document.getElementById('error-list');
        if (this.data.errors.length === 0) {
            container.innerHTML = '<div style="padding: 8px; color: #858585;">No errors</div>';
            return;
        }

        container.innerHTML = this.data.errors.map(err => `
            <div class="error-item">
                <div>${err.message}</div>
                ${err.line ? `<div class="error-line">Line ${err.line}</div>` : ''}
            </div>
        `).join('');
    },

    testTemplate: async function() {
        if (!this.data.selectedDeviceId) {
            this.updateStatus('Please select a device first', 'error');
            return;
        }

        // Ensure context is loaded
        if (!this.data.context || Object.keys(this.data.context).length === 0) {
            this.updateStatus('Loading context first...', null);
            await this.loadContext();
        }

        const isValid = await this.validateTemplate(true);
        if (!isValid) {
            this.switchTab('errors');
            return;
        }

        this.updateStatus('Testing template...', null);
        await this.renderPreview();
        // renderPreview already switches to preview tab, but ensure it's visible
        this.switchTab('preview');
    },

    renderPreview: async function() {
        const template = this.editors.template.getValue();
        
        if (!template.trim()) {
            if (this.editors.preview) {
                this.editors.preview.setValue('Template is empty');
            }
            this.updateStatus('Template is empty', 'warning');
            return;
        }

        if (!this.data.selectedDeviceId) {
            if (this.editors.preview) {
                this.editors.preview.setValue('Please select a device to see preview');
            }
            this.updateStatus('Please select a device first', 'warning');
            return;
        }

        // Check if context is loaded
        if (!this.data.context || Object.keys(this.data.context).length === 0) {
            this.updateStatus('Loading context first...', null);
            await this.loadContext();
            // After loading context, continue with render
        }

        this.updateStatus('Rendering preview...', null);

        try {
            console.log('Rendering preview with:', {
                template: template.substring(0, 100),
                device_id: this.data.selectedDeviceId,
                context: this.data.context
            });

            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}render-preview/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                body: JSON.stringify({
                    template_code: template,
                    device_id: this.data.selectedDeviceId,
                    context_overrides: this.data.context.intended || {},
                    variable_mappings: []
                })
            });

            console.log('Render preview response status:', resp.status);

            if (!resp.ok) {
                const errorText = await resp.text();
                console.error('Render preview error response:', errorText);
                throw new Error(`HTTP ${resp.status}: ${errorText.substring(0, 200)}`);
            }

            const data = await resp.json();
            console.log('Render preview response data:', data);

            if (this.editors.preview) {
                if (data.success !== false && !data.error) {
                    const rendered = data.rendered_result || '(No output)';
                    this.editors.preview.setValue(rendered);
                    this.updateStatus('Rendered successfully', 'success');
                    // Switch to preview tab to show result
                    this.switchTab('preview');
                } else {
                    const errorMsg = data.error || data.rendered_result || 'Render error';
                    this.editors.preview.setValue(`Error: ${errorMsg}`);
                    this.data.errors.push({
                        message: errorMsg,
                        line: 1
                    });
                    this.renderErrors();
                    this.updateStatus('Render error', 'error');
                    this.switchTab('errors');
                }
            } else {
                console.error('Preview editor not initialized');
                this.updateStatus('Preview editor not ready', 'error');
            }
        } catch (e) {
            console.error('Render preview error:', e);
            const errorMsg = e.message || 'Unknown error';
            if (this.editors.preview) {
                this.editors.preview.setValue(`Error: ${errorMsg}`);
            }
            this.updateStatus(`Error: ${errorMsg}`, 'error');
            this.switchTab('preview');
        }
    },

    debouncedRender: function() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            if (this.data.selectedDeviceId) {
                this.renderPreview();
            }
        }, 500);
    },

    formatTemplate: function() {
        // Simple formatting
        try {
            this.editors.template.getAction('editor.action.formatDocument').run();
            this.updateStatus('Formatted', 'success');
        } catch (e) {
            this.updateStatus('Format not available', 'warning');
        }
    },

    switchTab: function(tab) {
        this.activeTab = tab;
        
        // Update tab buttons
        document.querySelectorAll('.tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });

        // Update content
        const previewContent = document.getElementById('preview-content');
        const contextContent = document.getElementById('context-content');
        const errorsContent = document.getElementById('errors-content');
        
        if (previewContent) previewContent.classList.toggle('active', tab === 'preview');
        if (contextContent) contextContent.classList.toggle('active', tab === 'context');
        if (errorsContent) errorsContent.classList.toggle('active', tab === 'errors');

        // Refresh editors - ensure they're visible and laid out correctly
        setTimeout(() => {
            if (tab === 'preview' && this.editors.preview) {
                this.editors.preview.layout();
                // Make sure editor is visible
                const previewEl = document.getElementById('monaco-preview');
                if (previewEl && previewEl.offsetParent === null) {
                    console.warn('Preview editor element is not visible');
                }
            }
            if (tab === 'context' && this.editors.context) {
                this.editors.context.layout();
            }
        }, 150);
    },

    updateStatus: function(message, type) {
        const statusBar = document.getElementById('status-bar');
        const statusText = document.getElementById('status-text');
        
        statusText.textContent = message || 'Ready';
        statusBar.className = 'status-bar';
        if (type === 'error') statusBar.classList.add('error');
        else if (type === 'success') statusBar.classList.add('success');
        else if (type === 'warning') statusBar.classList.add('warning');
    },

    saveIntent: async function() {
        const name = document.getElementById('task-name').value;
        if (!name) {
            this.updateStatus('Task name required', 'error');
            document.getElementById('task-name').focus();
            return;
        }

        this.updateStatus('Saving...', null);

        try {
            const templateContent = this.editors.template.getValue();
            const isUpdate = window.STUDIO_CONFIG.task && window.STUDIO_CONFIG.task.id;
            
            // Step 1: Save/Update TaskIntent
            const taskPayload = {
                name: name,
                slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
                variable_mappings: this.data.variableMappings || [],
                input_schema: this.data.inputSchema || {}
            };

            const taskUrl = isUpdate 
                ? `${window.STUDIO_CONFIG.apiRoot}task-intents/${window.STUDIO_CONFIG.task.id}/`
                : `${window.STUDIO_CONFIG.apiRoot}task-intents/`;

            const taskResp = await fetch(taskUrl, {
                method: isUpdate ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                body: JSON.stringify(taskPayload)
            });

            if (!taskResp.ok) {
                const err = await taskResp.json();
                throw new Error(`Failed to save task: ${JSON.stringify(err)}`);
            }

            const task = await taskResp.json();
            
            // Step 2: Save all implementations
            for (const impl of this.data.implementations) {
                if (impl.id === 'default') continue; // Skip default
                
                const implPayload = {
                    task_intent: task.id,
                    platform: impl.platform ? impl.platform.id : null,
                    priority: 100,
                    logic_type: 'jinja2',
                    template_content: impl.template || '',
                    enabled: true
                };

                const isUpdate = impl.id && !impl.id.startsWith('impl-'); // Real ID vs temp ID
                const implUrl = isUpdate
                    ? `${window.STUDIO_CONFIG.apiRoot}task-implementations/${impl.id}/`
                    : `${window.STUDIO_CONFIG.apiRoot}task-implementations/`;

                try {
                    const implResp = await fetch(implUrl, {
                        method: isUpdate ? 'PATCH' : 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                        },
                        body: JSON.stringify(implPayload)
                    });

                    if (implResp.ok) {
                        const savedImpl = await implResp.json();
                        impl.id = savedImpl.id; // Update temp ID to real ID
                    } else {
                        const err = await implResp.json();
                        console.warn('Failed to save implementation:', err);
                    }
                } catch (e) {
                    console.error('Error saving implementation:', e);
                }
            }

            this.updateStatus('Saved successfully', 'success');
            
            if (!isUpdate) {
                // Redirect to edit view with correct URL pattern: /studio/tasks/<uuid>/
                setTimeout(() => {
                    const basePath = '/plugins/network-provisioning/studio/tasks/';
                    window.location.href = `${basePath}${task.id}/`;
                }, 1000);
            } else {
                // Update the task config for future saves
                window.STUDIO_CONFIG.task = task;
            }
        } catch (e) {
            console.error('Save error:', e);
            this.updateStatus(`Error: ${e.message}`, 'error');
        }
    },

    registerJinja2Language: function() {
        monaco.languages.register({ id: 'jinja2' });
        monaco.languages.setMonarchTokensProvider('jinja2', {
            tokenizer: {
                root: [
                    [/\{%/, { token: 'keyword', next: '@block' }],
                    [/\{\{/, { token: 'keyword', next: '@expression' }],
                    [/[^\{]+/, 'text']
                ],
                block: [
                    [/%\}/, { token: 'keyword', next: '@root' }],
                    [/\b(if|else|elif|endif|for|in|endfor|set|with|endwith|filter|endfilter|macro|endmacro|call|endcall|import|from|include|extends|block|endblock)\b/, 'keyword'],
                    [/[a-zA-Z_]\w*/, 'variable'],
                    [/\d+/, 'number'],
                    [/"/, { token: 'string', next: '@string' }],
                    [/\s+/, '']
                ],
                expression: [
                    [/\}\}/, { token: 'keyword', next: '@root' }],
                    [/[a-zA-Z_][\w\.]*/, 'variable'],
                    [/\s+/, '']
                ],
                string: [
                    [/[^"]+/, 'string'],
                    [/"/, { token: 'string', next: '@pop' }]
                ]
            }
        });
    },

    setupIntelliSense: function() {
        monaco.languages.registerCompletionItemProvider('jinja2', {
            provideCompletionItems: (model, position) => {
                const suggestions = [];
                const ctx = this.data.context;

                // Add device variables
                if (ctx.device) {
                    Object.keys(ctx.device).forEach(key => {
                        suggestions.push({
                            label: `device.${key}`,
                            kind: monaco.languages.CompletionItemKind.Field,
                            insertText: `device.${key}`,
                            detail: `Device: ${JSON.stringify(ctx.device[key])}`
                        });
                    });
                }

                // Add intended variables
                if (ctx.intended) {
                    Object.keys(ctx.intended).forEach(key => {
                        suggestions.push({
                            label: `intended.${key}`,
                            kind: monaco.languages.CompletionItemKind.Variable,
                            insertText: `intended.${key}`,
                            detail: `Intended: ${JSON.stringify(ctx.intended[key])}`
                        });
                    });
                }

                return { suggestions };
            }
        });
    },

    updateIntelliSense: function() {
        // Trigger IntelliSense update by touching the model
        if (this.editors.template) {
            const model = this.editors.template.getModel();
            if (model) {
                // Force refresh
                monaco.editor.setModelMarkers(model, 'validation', []);
            }
        }
    },

    loadPlatforms: async function() {
        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}platforms/`, {
                headers: {
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken,
                    'Accept': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (resp.ok) {
                const data = await resp.json();
                this.data.platforms = data.results || [];
                
                const platformFilter = document.getElementById('platform-filter');
                if (platformFilter) {
                    platformFilter.innerHTML = '<option value="">All Platforms</option>';
                    this.data.platforms.forEach(platform => {
                        const option = document.createElement('option');
                        option.value = platform.id;
                        option.textContent = platform.display || platform.name;
                        platformFilter.appendChild(option);
                    });
                }

                // Also populate condition modal
                const conditionPlatform = document.getElementById('condition-platform');
                if (conditionPlatform) {
                    conditionPlatform.innerHTML = '<option value="">Any Platform (Default)</option>';
                    this.data.platforms.forEach(platform => {
                        const option = document.createElement('option');
                        option.value = platform.id;
                        option.textContent = platform.display || platform.name;
                        conditionPlatform.appendChild(option);
                    });
                }
            }
        } catch (e) {
            console.error('Failed to load platforms:', e);
        }
    },

    loadRoles: async function() {
        try {
            // Load device roles from Nautobot API
            const resp = await fetch('/api/dcim/device-roles/', {
                headers: {
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken,
                    'Accept': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (resp.ok) {
                const data = await resp.json();
                this.data.roles = data.results || [];
                
                const conditionRole = document.getElementById('condition-role');
                if (conditionRole) {
                    conditionRole.innerHTML = '<option value="">Any Role</option>';
                    this.data.roles.forEach(role => {
                        const option = document.createElement('option');
                        option.value = role.id;
                        option.textContent = role.name;
                        conditionRole.appendChild(option);
                    });
                }
            }
        } catch (e) {
            console.error('Failed to load roles:', e);
        }
    },

    loadInitialData: function() {
        const task = window.STUDIO_CONFIG.task;
        const isNewTask = !task || !task.id;
        
        if (task && task.id) {
            document.getElementById('task-name').value = task.name || '';
            
            // Load input schema
            if (task.input_schema) {
                this.data.inputSchema = task.input_schema;
                if (this.editors.schema) {
                    this.editors.schema.setValue(JSON.stringify(task.input_schema, null, 2));
                }
            }

            // Load variable mappings
            if (task.variable_mappings) {
                this.data.variableMappings = Array.isArray(task.variable_mappings) 
                    ? task.variable_mappings 
                    : [];
            }
            
            if (task.implementations && task.implementations.length > 0) {
                const impl = task.implementations[0];
                if (impl.template_content && this.editors.template) {
                    this.editors.template.setValue(impl.template_content);
                }
            }
            
            this.renderVariableMapper();
            this.updateStatus(`Editing: ${task.name}`, 'success');
        } else {
            // New task - show welcome message
            this.updateStatus('New Task - Enter a name, select a device, and start coding!', null);
            document.getElementById('task-name').focus();
        }
    },

    debounce: function(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => Studio.init());
