/**
 * Task Studio Sidebar Manager
 * 
 * Manages the VS Code-style sidebar with 4 collapsible sections:
 * 1. Task Explorer (always visible)
 * 2. Input Variables (task-specific)
 * 3. Strategies/Implementations (task-specific)
 * 4. Device Context (device-specific)
 */

const TaskSidebar = {
    currentTaskId: null,
    currentDeviceId: null,
    tasks: [],
    filteredTasks: [],
    activeImplementationId: null,

    init: function() {
        this.setupSidebarToggle();
        this.setupSectionToggles();
        this.setupTaskExplorer();
        this.setupVariablesSection();
        this.setupStrategiesSection();
        this.setupDeviceContextSection();
        this.loadTasks();
    },

    /**
     * Sidebar Collapse/Expand
     */
    setupSidebarToggle: function() {
        const sidebar = document.getElementById('task-sidebar');
        const collapseBtn = document.getElementById('btn-collapse-sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle');

        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => {
                sidebar.classList.add('collapsed');
            });
        }

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.remove('collapsed');
            });
        }
    },

    /**
     * Section Accordion Toggles (Only for Properties Zone)
     * Explorer zone is never collapsible
     */
    setupSectionToggles: function() {
        // Only apply to sections within the properties-zone (accordion-container)
        const accordionContainer = document.querySelector('.accordion-container');
        if (!accordionContainer) return;
        
        const headers = accordionContainer.querySelectorAll('.sidebar-section-header');
        headers.forEach(header => {
            header.addEventListener('click', (e) => {
                // Don't toggle if clicking on a button inside the header
                if (e.target.closest('.btn-icon')) return;
                
                const body = header.nextElementSibling;
                const isCollapsed = body.classList.contains('collapsed');
                
                if (isCollapsed) {
                    body.classList.remove('collapsed');
                    header.classList.remove('collapsed');
                    header.querySelector('span').textContent = header.querySelector('span').textContent.replace('▶', '▼');
                } else {
                    body.classList.add('collapsed');
                    header.classList.add('collapsed');
                    header.querySelector('span').textContent = header.querySelector('span').textContent.replace('▼', '▶');
                }
            });
        });
    },

    /**
     * Section 1: Task Explorer
     */
    setupTaskExplorer: function() {
        const searchInput = document.getElementById('task-explorer-search');
        const refreshBtn = document.getElementById('btn-refresh-tasks');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTasks(e.target.value);
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadTasks();
            });
        }
    },

    loadTasks: async function() {
        const listContainer = document.getElementById('task-explorer-list');
        listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #858585; font-size: 11px;"><i class="mdi mdi-loading mdi-spin"></i> Loading tasks...</div>';

        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}task-intents/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                credentials: 'same-origin'
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            const data = await resp.json();
            this.tasks = data.results || data || [];
            this.filteredTasks = [...this.tasks];
            this.renderTaskList();
        } catch (e) {
            console.error('Failed to load tasks:', e);
            listContainer.innerHTML = `<div style="text-align: center; padding: 20px; color: #f48771; font-size: 11px;">Failed to load tasks</div>`;
        }
    },

    filterTasks: function(query) {
        const q = query.toLowerCase().trim();
        if (!q) {
            this.filteredTasks = [...this.tasks];
        } else {
            this.filteredTasks = this.tasks.filter(t => 
                (t.name || '').toLowerCase().includes(q) ||
                (t.description || '').toLowerCase().includes(q)
            );
        }
        this.renderTaskList();
    },

    renderTaskList: function() {
        const listContainer = document.getElementById('task-explorer-list');
        
        if (this.filteredTasks.length === 0) {
            listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #858585; font-size: 11px;">No tasks found</div>';
            return;
        }

        listContainer.innerHTML = '';
        this.filteredTasks.forEach(task => {
            const item = document.createElement('div');
            item.className = 'task-explorer-item';
            if (this.currentTaskId === task.id) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <i class="mdi mdi-lightning-bolt task-explorer-item-icon"></i>
                <span class="task-explorer-item-name" title="${this.escapeHtml(task.name)}">${this.escapeHtml(task.name)}</span>
            `;
            
            item.addEventListener('click', () => {
                this.selectTask(task.id);
            });
            
            listContainer.appendChild(item);
        });
    },

    selectTask: async function(taskId) {
        this.currentTaskId = taskId;
        this.renderTaskList(); // Update active state

        // Load task details
        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}task-intents/${taskId}/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                credentials: 'same-origin'
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            const task = await resp.json();
            
            // Update task name in toolbar
            const taskNameInput = document.getElementById('task-name');
            if (taskNameInput) {
                taskNameInput.value = task.name || '';
            }

            // Update Studio's global config
            window.STUDIO_CONFIG.task = task;

            // Load implementations
            this.renderVariables(task);
            this.renderStrategies(task);

            // Load the first implementation into the editor
            if (task.implementations && task.implementations.length > 0) {
                this.loadImplementation(task.implementations[0]);
            } else {
                // Clear editor for new implementation
                if (Studio && Studio.editors && Studio.editors.template) {
                    Studio.editors.template.setValue('');
                }
            }

            // Update status
            if (Studio && Studio.updateStatus) {
                Studio.updateStatus(`Loaded task: ${task.name}`, 'success');
            }
        } catch (e) {
            console.error('Failed to load task:', e);
            if (Studio && Studio.updateStatus) {
                Studio.updateStatus(`Error loading task: ${e.message}`, 'error');
            }
        }
    },

    /**
     * Section 2: Input Variables
     */
    setupVariablesSection: function() {
        const addBtn = document.getElementById('btn-add-variable');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.showAddVariableDialog();
            });
        }
    },

    renderVariables: function(task) {
        const container = document.getElementById('variable-list');
        
        if (!task || !task.input_schema || Object.keys(task.input_schema).length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #858585; font-size: 11px;">No input variables defined</div>';
            return;
        }

        container.innerHTML = '';
        Object.entries(task.input_schema).forEach(([name, type]) => {
            const item = document.createElement('div');
            item.className = 'variable-item';
            
            const mapping = (task.variable_mappings || []).find(m => m.name === name);
            const source = mapping ? mapping.source : 'user_input';
            const path = mapping ? mapping.path : '';
            
            item.innerHTML = `
                <div>
                    <span class="variable-name">${this.escapeHtml(name)}</span>
                    <span class="variable-type">${this.escapeHtml(type)}</span>
                </div>
                <div class="variable-source">Source: ${this.escapeHtml(source)}${path ? ' → ' + this.escapeHtml(path) : ''}</div>
            `;
            
            container.appendChild(item);
        });
    },

    showAddVariableDialog: function() {
        // TODO: Implement variable addition dialog
        alert('Variable editor coming soon! For now, use the API or Django admin.');
    },

    /**
     * Section 3: Strategies/Implementations
     */
    setupStrategiesSection: function() {
        const addBtn = document.getElementById('btn-add-strategy');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.showAddStrategyModal();
            });
        }

        // Setup strategy modal
        this.setupStrategyModal();
    },

    renderStrategies: function(task) {
        const container = document.getElementById('strategy-list');
        
        if (!task || !task.implementations || task.implementations.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #858585; font-size: 11px;">
                    No implementations yet<br>
                    <button class="add-strategy-btn" onclick="TaskSidebar.showAddStrategyModal()" style="margin-top: 10px;">
                        <i class="mdi mdi-plus"></i> Add Implementation
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        task.implementations.forEach(impl => {
            const card = document.createElement('div');
            card.className = 'strategy-card';
            if (this.activeImplementationId === impl.id) {
                card.classList.add('active');
            }
            
            const status = impl.template_content && impl.template_content.trim() ? 'implemented' : 'draft';
            const statusIcon = status === 'implemented' ? '✅' : '⚠️';
            
            card.innerHTML = `
                <div class="strategy-card-header">
                    <span class="strategy-platform">${this.escapeHtml(impl.platform?.name || impl.platform || 'Unknown')}</span>
                    <span class="strategy-status ${status}">${statusIcon}</span>
                </div>
                <div class="strategy-logic-type">${this.escapeHtml(impl.logic_type || 'jinja2')}</div>
            `;
            
            card.addEventListener('click', () => {
                this.loadImplementation(impl);
            });
            
            container.appendChild(card);
        });

        // Add "Add Strategy" button at the bottom
        const addBtn = document.createElement('button');
        addBtn.className = 'add-strategy-btn';
        addBtn.innerHTML = '<i class="mdi mdi-plus"></i> Add Implementation';
        addBtn.addEventListener('click', () => this.showAddStrategyModal());
        container.appendChild(addBtn);
    },

    loadImplementation: function(impl) {
        this.activeImplementationId = impl.id;
        
        // Update active state in UI
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.classList.remove('active');
        });
        event.currentTarget?.classList.add('active');

        // Load template into editor
        if (Studio && Studio.editors && Studio.editors.template) {
            const content = impl.template_content || '';
            Studio.editors.template.setValue(content);
            
            // Set editor language based on logic type
            const language = impl.logic_type === 'python' ? 'python' : 'jinja2';
            monaco.editor.setModelLanguage(Studio.editors.template.getModel(), language);
        }

        // Update status
        if (Studio && Studio.updateStatus) {
            Studio.updateStatus(`Loaded ${impl.platform?.name || 'implementation'} (${impl.logic_type})`, 'success');
        }
    },

    setupStrategyModal: function() {
        const modal = document.getElementById('strategy-modal');
        const closeBtn = document.getElementById('strategy-modal-close');
        const cancelBtn = document.getElementById('strategy-modal-cancel');
        const saveBtn = document.getElementById('strategy-modal-save');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.remove('active');
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                modal.classList.remove('active');
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.createStrategy();
            });
        }

        // Load platforms for dropdown
        this.loadPlatformsForModal();
    },

    loadPlatformsForModal: async function() {
        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}platforms/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                credentials: 'same-origin'
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            const data = await resp.json();
            const platforms = data.results || data || [];
            
            const select = document.getElementById('strategy-platform');
            if (select) {
                select.innerHTML = '<option value="">-- Select Platform --</option>';
                platforms.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.id;
                    option.textContent = p.name || p.display;
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error('Failed to load platforms:', e);
        }
    },

    showAddStrategyModal: function() {
        const modal = document.getElementById('strategy-modal');
        if (modal) {
            modal.classList.add('active');
        }
    },

    createStrategy: async function() {
        const logicType = document.getElementById('strategy-logic-type')?.value || 'jinja2';
        const platformId = document.getElementById('strategy-platform')?.value;
        const priority = document.getElementById('strategy-priority')?.value || 100;

        if (!platformId) {
            alert('Please select a platform');
            return;
        }

        if (!this.currentTaskId) {
            alert('Please select a task first');
            return;
        }

        try {
            const resp = await fetch(`${window.STUDIO_CONFIG.apiRoot}task-implementations/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': window.STUDIO_CONFIG.csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    task_intent: this.currentTaskId,
                    platform: platformId,
                    logic_type: logicType,
                    priority: parseInt(priority),
                    template_content: '',
                    enabled: true
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || `HTTP ${resp.status}`);
            }

            const newImpl = await resp.json();
            
            // Close modal
            document.getElementById('strategy-modal').classList.remove('active');
            
            // Reload task to refresh implementations
            this.selectTask(this.currentTaskId);
            
            if (Studio && Studio.updateStatus) {
                Studio.updateStatus('Implementation created successfully', 'success');
            }
        } catch (e) {
            console.error('Failed to create implementation:', e);
            alert(`Error creating implementation: ${e.message}`);
        }
    },

    /**
     * Section 4: Device Context
     */
    setupDeviceContextSection: function() {
        // This section is populated when a device is selected in the main UI
    },

    renderDeviceContext: function(device, context) {
        this.currentDeviceId = device?.id;
        const container = document.getElementById('device-context-tree');
        
        if (!device || !context) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: #858585; font-size: 11px;">Select a device to explore its data</div>';
            return;
        }

        // Expand the device context section
        const deviceSection = document.querySelector('[data-section="device"]');
        const deviceBody = document.getElementById('device-section');
        if (deviceSection && deviceBody) {
            deviceBody.classList.remove('collapsed');
            deviceSection.classList.remove('collapsed');
            deviceSection.querySelector('span').textContent = '▼ DEVICE CONTEXT';
        }

        // Render context tree
        container.innerHTML = '';
        this.renderContextTree(context, container);
    },

    renderContextTree: function(obj, container, prefix = '') {
        Object.entries(obj).forEach(([key, value]) => {
            const item = document.createElement('div');
            item.className = 'context-item';
            
            const type = Array.isArray(value) ? 'array' : typeof value;
            const displayValue = typeof value === 'object' && value !== null ? 
                (Array.isArray(value) ? `[${value.length}]` : '{...}') : 
                String(value);
            
            item.innerHTML = `
                <span class="context-item-name">${this.escapeHtml(prefix + key)}</span>
                <span class="context-item-type">${this.escapeHtml(type)}</span>
            `;
            
            item.addEventListener('click', () => {
                // Insert variable into editor at cursor
                const varPath = `{{ ${prefix}${key} }}`;
                if (Studio && Studio.editors && Studio.editors.template) {
                    const editor = Studio.editors.template;
                    const selection = editor.getSelection();
                    editor.executeEdits('', [{
                        range: selection,
                        text: varPath
                    }]);
                    editor.focus();
                }
            });
            
            container.appendChild(item);
            
            // Recursively render nested objects (limit depth)
            if (typeof value === 'object' && value !== null && !Array.isArray(value) && prefix.split('.').length < 2) {
                this.renderContextTree(value, container, `${prefix}${key}.`);
            }
        });
    },

    /**
     * Utility Functions
     */
    escapeHtml: function(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TaskSidebar.init());
} else {
    TaskSidebar.init();
}

