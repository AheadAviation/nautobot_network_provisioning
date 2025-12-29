/**
 * Task Library Studio - JavaScript Application (Reimagined)
 * 
 * This application handles the Task Library Studio UI, implementing
 * real database-driven CRUD operations via the REST API.
 */

(function() {
    'use strict';

    // =========================================================================
    // STATE MANAGEMENT
    // =========================================================================
    
    const state = {
        config: {
            apiRoot: '',
            csrfToken: '',
        },
        data: {
            tasks: [],
            catalogs: [],
            manufacturers: [],
            platforms: [],
            objectModels: [],
        },
        currentTask: null,
        currentImpl: null,
        editors: {
            schema: null,
            impl: null
        }
    };

    // =========================================================================
    // DOM HELPERS
    // =========================================================================
    
    function $(selector) {
        if (selector.startsWith('#')) return document.getElementById(selector.slice(1));
        return document.querySelector(selector);
    }

    function $$(selector) {
        return document.querySelectorAll(selector);
    }

    function safeJsonParse(value, fallback) {
        if (!value) return fallback;
        try {
            return JSON.parse(value);
        } catch (e) {
            console.error('JSON parse error:', e);
            return fallback;
        }
    }

    // =========================================================================
    // INITIALIZATION
    // =========================================================================
    
    function init() {
        const root = $('#task-studio-root');
        if (!root) return;

        // 1. Load configuration and data from attributes
        state.config.apiRoot = root.dataset.apiRoot;
        state.config.csrfToken = root.dataset.csrfToken;
        
        state.data.tasks = safeJsonParse(root.dataset.tasksJson, []);
        state.data.catalogs = safeJsonParse(root.dataset.catalogsJson, []);
        state.data.manufacturers = safeJsonParse(root.dataset.manufacturersJson, []);
        state.data.platforms = safeJsonParse(root.dataset.platformsJson, []);
        state.data.objectModels = safeJsonParse(root.dataset.objectModelsJson, []);

        // 2. Initialize UI components
        initEditors();
        populateDropdowns();
        renderTaskList();
        initEventHandlers();

        // 3. Load initial task if provided
        const initialTask = safeJsonParse(root.dataset.currentTaskJson, null);
        if (initialTask && initialTask.id) {
            selectTask(initialTask.id);
        }

        console.log('Task Library Studio Reimagined Initialized');
    }

    function initEditors() {
        const schemaTextarea = $('#task-schema-editor');
        if (schemaTextarea && typeof CodeMirror !== 'undefined') {
            state.editors.schema = CodeMirror.fromTextArea(schemaTextarea, {
                mode: { name: "javascript", json: true },
                theme: "material-ocean",
                lineNumbers: true,
                tabSize: 2,
                matchBrackets: true,
                autoCloseBrackets: true
            });
        }

        const implTextarea = $('#impl-content-editor');
        if (implTextarea && typeof CodeMirror !== 'undefined') {
            state.editors.impl = CodeMirror.fromTextArea(implTextarea, {
                mode: "jinja2",
                theme: "material-ocean",
                lineNumbers: true,
                tabSize: 2,
                matchBrackets: true,
                autoCloseBrackets: true
            });
        }
    }

    function populateDropdowns() {
        const catalogSelect = $('#task-catalog');
        const newTaskCatalogSelect = $('#new-task-catalog');
        
        // Populate catalog dropdowns
        if (catalogSelect) {
            state.data.catalogs.forEach(c => {
                catalogSelect.add(new Option(c.name, c.id));
            });
        }
        if (newTaskCatalogSelect) {
            state.data.catalogs.forEach(c => {
                newTaskCatalogSelect.add(new Option(c.name, c.id));
            });
        }

        const targetModelSelect = $('#task-target-model');
        if (targetModelSelect) {
            state.data.objectModels.forEach(m => {
                const opt = new Option(`${m.app_label}.${m.model}`, m.id);
                targetModelSelect.add(opt);
            });
        }

        const manufacturerSelect = $('#impl-manufacturer');
        if (manufacturerSelect) {
            manufacturerSelect.add(new Option('-- Select Manufacturer --', ''));
            state.data.manufacturers.forEach(m => {
                manufacturerSelect.add(new Option(m.name, m.id));
            });
        }
    }

    function initEventHandlers() {
        // Defensive null checks for all event handlers
        const btnNewTask = $('#btn-new-task');
        const modalNewTask = $('#modal-new-task');
        const confirmNewTask = $('#confirm-new-task');
        const btnSaveTask = $('#btn-save-task');
        const btnDeleteTask = $('#btn-delete-task');
        const btnAddImpl = $('#btn-add-implementation');
        const btnSaveImpl = $('#btn-save-impl');
        const btnDeleteImpl = $('#btn-delete-impl');
        const implManufacturer = $('#impl-manufacturer');
        const implType = $('#impl-type');

        if (btnNewTask && modalNewTask) {
            btnNewTask.addEventListener('click', () => {
                const modal = new bootstrap.Modal(modalNewTask);
                modal.show();
            });
        }

        if (confirmNewTask) {
            confirmNewTask.addEventListener('click', createNewTask);
        }

        if (btnSaveTask) {
            btnSaveTask.addEventListener('click', saveTask);
        }

        if (btnDeleteTask) {
            btnDeleteTask.addEventListener('click', deleteTask);
        }
        
        if (btnAddImpl) {
            btnAddImpl.addEventListener('click', () => openImplementationModal());
        }

        if (btnSaveImpl) {
            btnSaveImpl.addEventListener('click', saveImplementation);
        }

        if (btnDeleteImpl) {
            btnDeleteImpl.addEventListener('click', deleteImplementation);
        }

        if (implManufacturer) {
            implManufacturer.addEventListener('change', function() {
                populatePlatforms(this.value);
            });
        }

        if (implType && state.editors.impl) {
            implType.addEventListener('change', function() {
                const type = this.value;
                let mode = 'jinja2';
                if (type === 'api_call') mode = { name: "javascript", json: true };
                if (type === 'python_code') mode = 'python';
                state.editors.impl.setOption('mode', mode);
            });
        }
    }

    // =========================================================================
    // TASK OPERATIONS
    // =========================================================================
    
    async function apiRequest(endpoint, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.config.csrfToken
            }
        };
        if (data) options.body = JSON.stringify(data);

        const response = await fetch(`${state.config.apiRoot}${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(JSON.stringify(error));
        }
        if (method === 'DELETE') return null;
        return response.json();
    }

    function renderTaskList() {
        const container = $('#task-list-items');
        if (!container) return;

        if (state.data.tasks.length === 0) {
            container.innerHTML = '<div class="p-3 text-muted small">No tasks found.</div>';
            return;
        }

        container.innerHTML = state.data.tasks.map(task => `
            <div class="task-item ${state.currentTask && state.currentTask.id === task.id ? 'active' : ''}" 
                 onclick="window.studioSelectTask('${task.id}')">
                <div class="fw-bold">${task.name}</div>
                <div class="small opacity-75">${task.category}</div>
            </div>
        `).join('');
    }

    window.studioSelectTask = selectTask; // Make accessible globally for onclick

    async function selectTask(taskId) {
        try {
            state.currentTask = await apiRequest(`tasks/${taskId}/`);
            
            // UI Updates
            $('#editor-empty-state').classList.add('d-none');
            $('#editor-content').classList.remove('d-none');
            $('#editor-title').textContent = `Edit Task: ${state.currentTask.name}`;
            
            $('#task-name').value = state.currentTask.name;
            $('#task-description').value = state.currentTask.description || '';
            $('#task-category').value = state.currentTask.category;
            $('#task-catalog').value = state.currentTask.catalog || '';
            $('#task-target-model').value = state.currentTask.target_model || '';
            
            const schema = state.currentTask.input_schema || { type: "object", properties: {} };
            state.editors.schema.setValue(JSON.stringify(schema, null, 2));
            
            renderImplementationList();
            renderTaskList();
        } catch (e) {
            alert('Failed to load task: ' + e.message);
        }
    }

    async function createNewTask() {
        const name = $('#new-task-name').value;
        const catalog = $('#new-task-catalog').value;
        const description = $('#new-task-description').value;

        if (!name) return alert('Name is required');

        try {
            const task = await apiRequest('tasks/', 'POST', {
                name,
                catalog: catalog || null,
                description,
                category: 'configuration',
                slug: name.toLowerCase().replace(/ /g, '-')
            });
            
            // Add to state and select
            state.data.tasks.push(task);
            bootstrap.Modal.getInstance($('#modal-new-task')).hide();
            selectTask(task.id);
        } catch (e) {
            alert('Failed to create task: ' + e.message);
        }
    }

    async function saveTask() {
        if (!state.currentTask) return;

        let schema;
        try {
            schema = JSON.parse(state.editors.schema.getValue());
        } catch (e) {
            return alert('Invalid Input Schema JSON');
        }

        const data = {
            name: $('#task-name').value,
            description: $('#task-description').value,
            category: $('#task-category').value,
            catalog: $('#task-catalog').value || null,
            target_model: $('#task-target-model').value || null,
            input_schema: schema
        };

        try {
            const updatedTask = await apiRequest(`tasks/${state.currentTask.id}/`, 'PUT', data);
            state.currentTask = updatedTask;
            
            // Update in tasks list
            const idx = state.data.tasks.findIndex(t => t.id === updatedTask.id);
            if (idx !== -1) state.data.tasks[idx] = updatedTask;
            
            renderTaskList();
            alert('Task saved successfully');
        } catch (e) {
            alert('Failed to save task: ' + e.message);
        }
    }

    async function deleteTask() {
        if (!state.currentTask) return;
        if (!confirm('Are you sure you want to delete this task?')) return;

        try {
            await apiRequest(`tasks/${state.currentTask.id}/`, 'DELETE');
            
            // Remove from state
            state.data.tasks = state.data.tasks.filter(t => t.id !== state.currentTask.id);
            state.currentTask = null;
            
            $('#editor-content').classList.add('d-none');
            $('#editor-empty-state').classList.remove('d-none');
            renderTaskList();
        } catch (e) {
            alert('Failed to delete task: ' + e.message);
        }
    }

    // =========================================================================
    // IMPLEMENTATION OPERATIONS
    // =========================================================================
    
    function renderImplementationList() {
        const container = $('#implementation-list');
        const impls = state.currentTask.implementations || [];

        if (impls.length === 0) {
            container.innerHTML = '<div class="text-muted small">No implementations yet.</div>';
            return;
        }

        container.innerHTML = impls.map(impl => {
            const m = state.data.manufacturers.find(m => m.id === impl.manufacturer) || { name: 'Unknown' };
            const p = state.data.platforms.find(p => p.id === impl.platform) || { name: 'Generic' };
            return `
                <div class="implementation-card">
                    <div>
                        <div class="fw-bold">${m.name} / ${p.name || 'Generic'}</div>
                        <div class="small text-muted">${impl.implementation_type} | Priority: ${impl.priority}</div>
                    </div>
                    <button class="btn-studio btn-secondary-studio" onclick="window.studioOpenImpl('${impl.id}')">Edit</button>
                </div>
            `;
        }).join('');
    }

    window.studioOpenImpl = (id) => openImplementationModal(id);

    function openImplementationModal(implId = null) {
        const modal = new bootstrap.Modal($('#modal-implementation'));
        state.currentImpl = implId ? state.currentTask.implementations.find(i => i.id === implId) : null;

        $('#impl-modal-title').textContent = state.currentImpl ? 'Edit Implementation' : 'Add Implementation';
        $('#impl-id').value = implId || '';
        
        if (state.currentImpl) {
            $('#impl-manufacturer').value = state.currentImpl.manufacturer;
            populatePlatforms(state.currentImpl.manufacturer);
            $('#impl-platform').value = state.currentImpl.platform || '';
            $('#impl-type').value = state.currentImpl.implementation_type;
            $('#impl-priority').value = state.currentImpl.priority;
            $('#impl-version').value = state.currentImpl.software_version_constraint || '';
            state.editors.impl.setValue(state.currentImpl.template_content || '');
            $('#btn-delete-impl').classList.remove('d-none');
        } else {
            $('#impl-manufacturer').value = '';
            $('#impl-platform').value = '';
            $('#impl-type').value = 'jinja2_config';
            $('#impl-priority').value = 100;
            $('#impl-version').value = '';
            state.editors.impl.setValue('');
            $('#btn-delete-impl').classList.add('d-none');
        }

        modal.show();
        setTimeout(() => state.editors.impl.refresh(), 200);
    }

    function populatePlatforms(manufacturerId) {
        const select = $('#impl-platform');
        select.innerHTML = '<option value="">-- Generic for Manufacturer --</option>';
        if (!manufacturerId) return;

        state.data.platforms
            .filter(p => p.manufacturer === manufacturerId)
            .forEach(p => select.add(new Option(p.name, p.id)));
    }

    async function saveImplementation() {
        const data = {
            task: state.currentTask.id,
            manufacturer: $('#impl-manufacturer').value,
            platform: $('#impl-platform').value || null,
            implementation_type: $('#impl-type').value,
            priority: parseInt($('#impl-priority').value),
            software_version_constraint: $('#impl-version').value,
            template_content: state.editors.impl.getValue(),
            enabled: true
        };

        if (!data.manufacturer) return alert('Manufacturer is required');

        try {
            const endpoint = state.currentImpl ? `task-implementations/${state.currentImpl.id}/` : 'task-implementations/';
            const method = state.currentImpl ? 'PUT' : 'POST';
            
            await apiRequest(endpoint, method, data);
            
            // Reload task to get updated implementations
            await selectTask(state.currentTask.id);
            bootstrap.Modal.getInstance($('#modal-implementation')).hide();
        } catch (e) {
            alert('Failed to save implementation: ' + e.message);
        }
    }

    async function deleteImplementation() {
        if (!state.currentImpl) return;
        if (!confirm('Are you sure you want to delete this implementation?')) return;

        try {
            await apiRequest(`task-implementations/${state.currentImpl.id}/`, 'DELETE');
            await selectTask(state.currentTask.id);
            bootstrap.Modal.getInstance($('#modal-implementation')).hide();
        } catch (e) {
            alert('Failed to delete implementation: ' + e.message);
        }
    }

    // =========================================================================
    // BOOTSTRAP
    // =========================================================================
    
    document.addEventListener('DOMContentLoaded', init);

})();
