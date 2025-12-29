/**
 * Catalog Explorer - Tree Browser and Item Management
 * 
 * Features:
 * - Hierarchical folder tree
 * - Task/Workflow/Form browsing
 * - Dashboard view for folders
 * - Item detail view
 * - Task creation flow
 */

const CatalogExplorer = {
    selectedFolder: null,
    selectedItem: null,
    selectedItemType: null,
    folders: [],
    tasks: [],
    workflows: [],
    forms: [],
    searchQuery: '',
    initialized: false,

    init: function() {
        console.log('CatalogExplorer.init() called');
        // Check if container exists
        const container = document.getElementById('catalog-explorer');
        if (!container) {
            console.warn('catalog-explorer container not found, retrying...');
            setTimeout(() => this.init(), 100);
            return;
        }
        console.log('Container found, setting up event listeners...');
        this.setupEventListeners();
        this.loadData();
        this.initialized = true;
        console.log('CatalogExplorer initialized');
    },

    setupEventListeners: function() {
        // Search
        document.getElementById('tree-search')?.addEventListener('input', (e) => {
            this.searchQuery = e.target.value.toLowerCase();
            this.renderTree();
        });

        // New folder button
        document.getElementById('btn-new-folder')?.addEventListener('click', () => {
            this.createFolder();
        });

        // Dashboard action buttons
        document.getElementById('btn-new-task')?.addEventListener('click', () => {
            this.openTaskCreationModal();
        });
        document.getElementById('btn-new-workflow')?.addEventListener('click', () => {
            this.createWorkflow();
        });
        document.getElementById('btn-new-form')?.addEventListener('click', () => {
            this.createForm();
        });

        // Empty state button
        const btnCreateFirst = document.getElementById('btn-create-first-task');
        if (btnCreateFirst) {
            btnCreateFirst.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Create First Task button clicked');
                this.openTaskCreationModal();
            });
        } else {
            console.warn('btn-create-first-task button not found');
        }

        // Task creation modal
        document.getElementById('modal-close')?.addEventListener('click', () => {
            this.closeTaskCreationModal();
        });
        document.getElementById('modal-cancel')?.addEventListener('click', () => {
            this.closeTaskCreationModal();
        });
        document.getElementById('modal-create')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Create Task button clicked');
            this.createTask();
        });
        
        // Prevent form submission on Enter key
        const form = document.getElementById('task-creation-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Form submit prevented, calling createTask');
                this.createTask();
            });
        }

        // Item action buttons
        document.getElementById('btn-edit-item')?.addEventListener('click', () => {
            this.editItem();
        });
        document.getElementById('btn-test-item')?.addEventListener('click', () => {
            this.testItem();
        });
        document.getElementById('btn-delete-item')?.addEventListener('click', () => {
            this.deleteItem();
        });
    },

    loadData: async function() {
        try {
            const apiRoot = window.STUDIO_SHELL_CONFIG?.apiRoot || '/plugins/network-provisioning/api/';

            // Load folders
            const foldersResp = await fetch(`${apiRoot}folders/`, {
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            if (foldersResp.ok) {
                const foldersData = await foldersResp.json();
                this.folders = foldersData.results || [];
            }

            // Load tasks
            const tasksResp = await fetch(`${apiRoot}task-intents/`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            if (tasksResp.ok) {
                const tasksData = await tasksResp.json();
                this.tasks = tasksData.results || [];
            }

            // Load workflows
            const workflowsResp = await fetch(`${apiRoot}workflows/`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            if (workflowsResp.ok) {
                const workflowsData = await workflowsResp.json();
                this.workflows = workflowsData.results || [];
            } else if (workflowsResp.status === 401 || workflowsResp.status === 403) {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return;
            } else if (workflowsResp.status === 401 || workflowsResp.status === 403) {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            // Load forms
            const formsResp = await fetch(`${apiRoot}request-forms/`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            if (formsResp.ok) {
                const formsData = await formsResp.json();
                this.forms = formsData.results || [];
            } else if (formsResp.status === 401 || formsResp.status === 403) {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return;
            } else if (formsResp.status === 401 || formsResp.status === 403) {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return;
            }

            this.renderTree();
        } catch (e) {
            console.error('Failed to load catalog data:', e);
        }
    },

    renderTree: function() {
        const container = document.getElementById('tree-container');
        if (!container) return;

        container.innerHTML = '';

        // Build folder hierarchy
        const rootFolders = this.folders.filter(f => !f.parent);
        rootFolders.forEach(folder => {
            this.renderFolderNode(container, folder, 0);
        });

        // Show items without folders
        const itemsWithoutFolders = [
            ...this.tasks.filter(t => !t.folder).map(t => ({ ...t, type: 'task' })),
            ...this.workflows.filter(w => !w.folder).map(w => ({ ...w, type: 'workflow' })),
            ...this.forms.filter(f => !f.folder).map(f => ({ ...f, type: 'form' }))
        ];

        if (itemsWithoutFolders.length > 0 && !this.searchQuery) {
            const uncategorizedDiv = document.createElement('div');
            uncategorizedDiv.className = 'tree-node';
            uncategorizedDiv.innerHTML = `
                <span class="tree-node-icon">📦</span>
                <span class="tree-node-label">Uncategorized</span>
            `;
            container.appendChild(uncategorizedDiv);
        }
    },

    renderFolderNode: function(container, folder, depth) {
        // Filter by search query
        if (this.searchQuery && !folder.name.toLowerCase().includes(this.searchQuery)) {
            // Check if any children match
            const children = this.folders.filter(f => f.parent === folder.id);
            const hasMatchingChildren = children.some(c => this.renderFolderNode(null, c, depth + 1));
            if (!hasMatchingChildren) return false;
        }

        const folderDiv = document.createElement('div');
        folderDiv.className = 'tree-node';
        folderDiv.dataset.folderId = folder.id;
        folderDiv.style.paddingLeft = `${depth * 16 + 8}px`;

        const itemsCount = this.getFolderItemsCount(folder.id);
        const icon = folder.parent ? '📁' : '📂';

        folderDiv.innerHTML = `
            <span class="tree-node-icon">${icon}</span>
            <span class="tree-node-label">${this.escapeHtml(folder.name)}</span>
            <span class="tree-node-count">${itemsCount}</span>
        `;

        folderDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectFolder(folder);
        });

        if (container) {
            container.appendChild(folderDiv);
        }

        // Render children
        const children = this.folders.filter(f => f.parent === folder.id);
        if (children.length > 0) {
            children.forEach(child => {
                this.renderFolderNode(container, child, depth + 1);
            });
        }

        // Render items in this folder
        const folderItems = [
            ...this.tasks.filter(t => t.folder === folder.id).map(t => ({ ...t, type: 'task' })),
            ...this.workflows.filter(w => w.folder === folder.id).map(w => ({ ...w, type: 'workflow' })),
            ...this.forms.filter(f => f.folder === folder.id).map(f => ({ ...f, type: 'form' }))
        ];

        folderItems.forEach(item => {
            if (this.searchQuery && !item.name.toLowerCase().includes(this.searchQuery)) {
                return;
            }
            this.renderItemNode(container, item, depth + 1);
        });

        return true;
    },

    renderItemNode: function(container, item, depth) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'tree-node';
        itemDiv.dataset.itemId = item.id;
        itemDiv.dataset.itemType = item.type;
        itemDiv.style.paddingLeft = `${depth * 16 + 8}px`;

        const icons = {
            task: '⚡',
            workflow: '☍',
            form: '📋'
        };

        itemDiv.innerHTML = `
            <span class="tree-node-icon">${icons[item.type] || '📄'}</span>
            <span class="tree-node-label">${this.escapeHtml(item.name)}</span>
        `;

        itemDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectItem(item, item.type);
        });

        if (container) {
            container.appendChild(itemDiv);
        }
    },

    getFolderItemsCount: function(folderId) {
        const tasks = this.tasks.filter(t => t.folder === folderId).length;
        const workflows = this.workflows.filter(w => w.folder === folderId).length;
        const forms = this.forms.filter(f => f.folder === folderId).length;
        return tasks + workflows + forms;
    },

    selectFolder: function(folder) {
        this.selectedFolder = folder;
        this.selectedItem = null;
        this.selectedItemType = null;

        // Update tree selection
        document.querySelectorAll('.tree-node').forEach(node => {
            node.classList.remove('selected');
        });
        document.querySelector(`[data-folder-id="${folder.id}"]`)?.classList.add('selected');

        // Show dashboard view
        this.showDashboardView(folder);
    },

    selectItem: function(item, type) {
        this.selectedItem = item;
        this.selectedItemType = type;
        this.selectedFolder = null;

        // Update tree selection
        document.querySelectorAll('.tree-node').forEach(node => {
            node.classList.remove('selected');
        });
        document.querySelector(`[data-item-id="${item.id}"]`)?.classList.add('selected');

        // Show item detail view
        this.showItemDetailView(item, type);
    },

    showDashboardView: function(folder) {
        document.getElementById('empty-view').style.display = 'none';
        document.getElementById('item-detail-view').style.display = 'none';
        document.getElementById('dashboard-view').style.display = 'block';

        // Update dashboard content
        document.getElementById('dashboard-folder-name').textContent = folder.name;
        document.getElementById('dashboard-folder-desc').textContent = folder.description || 'No description';

        // Update stats
        const tasks = this.tasks.filter(t => t.folder === folder.id);
        const workflows = this.workflows.filter(w => w.folder === folder.id);
        const forms = this.forms.filter(f => f.folder === folder.id);

        document.getElementById('stat-tasks').textContent = tasks.length;
        document.getElementById('stat-workflows').textContent = workflows.length;
        document.getElementById('stat-forms').textContent = forms.length;

        // Render items list
        const itemsList = document.getElementById('dashboard-items-list');
        itemsList.innerHTML = '';

        const allItems = [
            ...tasks.map(t => ({ ...t, type: 'task', icon: '⚡' })),
            ...workflows.map(w => ({ ...w, type: 'workflow', icon: '☍' })),
            ...forms.map(f => ({ ...f, type: 'form', icon: '📋' }))
        ];

        if (allItems.length === 0) {
            itemsList.innerHTML = '<p class="text-muted">No items in this folder</p>';
        } else {
            const itemsGrid = document.createElement('div');
            itemsGrid.className = 'item-list';
            allItems.forEach(item => {
                const card = document.createElement('div');
                card.className = 'item-card';
                card.innerHTML = `
                    <div class="item-card-icon">${item.icon}</div>
                    <div class="item-card-name">${this.escapeHtml(item.name)}</div>
                    <div class="item-card-desc">${this.escapeHtml(item.description || 'No description')}</div>
                `;
                card.addEventListener('click', () => {
                    this.selectItem(item, item.type);
                });
                itemsGrid.appendChild(card);
            });
            itemsList.appendChild(itemsGrid);
        }
    },

    showItemDetailView: function(item, type) {
        document.getElementById('empty-view').style.display = 'none';
        document.getElementById('dashboard-view').style.display = 'none';
        document.getElementById('item-detail-view').style.display = 'block';

        const icons = {
            task: '⚡',
            workflow: '☍',
            form: '📋'
        };

        document.getElementById('item-icon').textContent = icons[type] || '📄';
        document.getElementById('item-name').textContent = item.name;
        document.getElementById('item-description').textContent = item.description || 'No description';

        // Render metadata
        const metadataDiv = document.getElementById('item-metadata');
        metadataDiv.innerHTML = `
            <div class="form-group">
                <label>Type</label>
                <div>${type.charAt(0).toUpperCase() + type.slice(1)}</div>
            </div>
            <div class="form-group">
                <label>Slug</label>
                <div>${item.slug || 'N/A'}</div>
            </div>
            ${item.folder ? `
            <div class="form-group">
                <label>Folder</label>
                <div>${this.folders.find(f => f.id === item.folder)?.name || 'Unknown'}</div>
            </div>
            ` : ''}
        `;
    },

    openTaskCreationModal: function() {
        console.log('openTaskCreationModal() called');
        const modal = document.getElementById('task-creation-modal');
        if (!modal) {
            console.error('task-creation-modal not found in DOM');
            alert('Task creation modal not found. Please refresh the page.');
            return;
        }
        console.log('Modal found, showing...');

        // Populate folder dropdown
        const folderSelect = document.getElementById('task-folder');
        if (!folderSelect) {
            console.error('task-folder select not found');
            return;
        }
        folderSelect.innerHTML = '<option value="">-- No Folder --</option>';
        this.folders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder.id;
            option.textContent = folder.name;
            if (this.selectedFolder && folder.id === this.selectedFolder.id) {
                option.selected = true;
            }
            folderSelect.appendChild(option);
        });

        // Reset form
        const form = document.getElementById('task-creation-form');
        if (form) {
            form.reset();
        }
        const openStudioCheckbox = document.getElementById('task-open-studio');
        if (openStudioCheckbox) {
            openStudioCheckbox.checked = true;
        }

        modal.style.display = 'flex';
        console.log('Modal displayed');
    },

    closeTaskCreationModal: function() {
        const modal = document.getElementById('task-creation-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    createTask: async function() {
        console.log('createTask() called');
        const form = document.getElementById('task-creation-form');
        if (!form) {
            console.error('task-creation-form not found');
            alert('Form not found. Please refresh the page.');
            return;
        }

        // Get form values directly from inputs
        const nameInput = document.getElementById('task-name');
        const descriptionInput = document.getElementById('task-description');
        const folderSelect = document.getElementById('task-folder');
        
        if (!nameInput) {
            console.error('task-name input not found');
            alert('Task name field not found. Please refresh the page.');
            return;
        }

        const taskName = nameInput.value.trim();
        if (!taskName) {
            alert('Task name is required.');
            nameInput.focus();
            return;
        }

        const taskData = {
            name: taskName,
            slug: this.slugify(taskName),
            description: descriptionInput ? descriptionInput.value.trim() : '',
            folder: folderSelect && folderSelect.value ? folderSelect.value : null,
            input_schema: {},
            variable_mappings: {}
        };

        console.log('Creating task with data:', taskData);

        try {
            const apiRoot = window.STUDIO_SHELL_CONFIG?.apiRoot || '/plugins/network-provisioning/api/';
            // Get CSRF token from cookie
            const csrfToken = this.getCSRFToken();
            
            if (!csrfToken) {
                console.warn('No CSRF token found, request may fail');
            }
            
            console.log('Sending POST request to:', `${apiRoot}task-intents/`);
            
            const resp = await fetch(`${apiRoot}task-intents/`, {
                method: 'POST',
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify(taskData)
            });

            console.log('Response status:', resp.status, resp.statusText);

            if (resp.ok) {
                const task = await resp.json();
                console.log('Task created successfully:', task);
                this.closeTaskCreationModal();
                
                // Reload data
                await this.loadData();
                
                // Select the new task
                this.selectItem(task, 'task');

                // Open in Task Studio if requested
                const openStudioCheckbox = document.getElementById('task-open-studio');
                if (openStudioCheckbox && openStudioCheckbox.checked) {
                    // Switch to Code mode in StudioShell instead of redirecting
                    if (window.StudioShell) {
                        // Update URL to include task ID
                        const newUrl = `/plugins/network-provisioning/studio/code/task/${task.id}/`;
                        window.history.pushState({}, '', newUrl);
                        window.StudioShell.switchMode('code');
                        // Load the task in the iframe
                        setTimeout(() => {
                            const iframe = document.getElementById('task-studio-frame');
                            if (iframe) {
                                iframe.src = `/plugins/network-provisioning/studio/tasks/${task.id}/`;
                            }
                        }, 100);
                    } else {
                        // Fallback to full redirect if StudioShell not available
                        const basePath = '/plugins/network-provisioning/studio/tasks/';
                        window.location.href = `${basePath}${task.id}/`;
                    }
                }
            } else {
                const errorMessage = await this.handleAPIError(resp, 'Failed to create task');
                console.error('Task creation failed:', errorMessage);
                alert(`Error creating task: ${errorMessage}`);
            }
        } catch (e) {
            console.error('Failed to create task:', e);
            alert(`Error: ${e.message || 'Unknown error occurred. Check console for details.'}`);
        }
    },

    createFolder: async function() {
        const name = prompt('Enter folder name:');
        if (!name) return;

        const folderData = {
            name: name,
            slug: this.slugify(name),
            description: '',
            parent: this.selectedFolder ? this.selectedFolder.id : null
        };

        try {
            const apiRoot = window.STUDIO_SHELL_CONFIG?.apiRoot || '/plugins/network-provisioning/api/';
            // Get CSRF token from cookie
            const folderCsrfToken = this.getCSRFToken();
            
            const resp = await fetch(`${apiRoot}folders/`, {
                method: 'POST',
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': folderCsrfToken
                },
                body: JSON.stringify(folderData)
            });

            if (resp.ok) {
                const folder = await resp.json();
                await this.loadData();
                this.selectFolder(folder);
            } else {
                const errorMessage = await this.handleAPIError(resp, 'Failed to create folder');
                alert(`Error creating folder: ${errorMessage}`);
            }
        } catch (e) {
            console.error('Failed to create folder:', e);
            alert(`Error: ${e.message}`);
        }
    },

    createWorkflow: function() {
        // Navigate to workflow orchestrator
        window.location.href = '/plugins/network-provisioning/studio/workflows/';
    },

    createForm: function() {
        // Navigate to form builder
        window.location.href = '/plugins/network-provisioning/studio/forms/';
    },

    editItem: function() {
        if (!this.selectedItem || !this.selectedItemType) return;

        const basePath = '/plugins/network-provisioning/studio/';
        let url = '';

        if (this.selectedItemType === 'task') {
            url = `${basePath}tasks/${this.selectedItem.id}/`;
        } else if (this.selectedItemType === 'workflow') {
            url = `${basePath}workflows/${this.selectedItem.id}/`;
        } else if (this.selectedItemType === 'form') {
            url = `${basePath}forms/${this.selectedItem.id}/`;
        }

        if (url) {
            window.location.href = url;
        }
    },

    testItem: function() {
        // TODO: Implement test functionality
        alert('Test functionality coming soon');
    },

    deleteItem: function() {
        if (!this.selectedItem || !this.selectedItemType) return;
        if (!confirm(`Are you sure you want to delete "${this.selectedItem.name}"?`)) return;

        // TODO: Implement delete functionality
        alert('Delete functionality coming soon');
    },

    slugify: function(text) {
        return text.toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/[\s_-]+/g, '-')
            .replace(/^-+|-+$/g, '');
    },

    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    getCSRFToken: function() {
        // Try to get CSRF token from cookie
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        // Fallback to config if available
        return cookieValue || window.STUDIO_SHELL_CONFIG?.csrfToken || '';
    },

    handleAPIError: async function(response, defaultMessage) {
        // Check if response is HTML (error page) instead of JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/html')) {
            // Likely an authentication error or 404
            if (response.status === 401 || response.status === 403) {
                // Redirect to login
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return 'Authentication required. Redirecting to login...';
            } else if (response.status === 404) {
                return 'API endpoint not found. Please check the API URL.';
            } else {
                return `Server error (${response.status}). Please check the server logs.`;
            }
        }
        // Try to parse JSON error
        try {
            const data = await response.json();
            return data.detail || data.error || data.message || defaultMessage;
        } catch (e) {
            return defaultMessage || `Error: ${response.status} ${response.statusText}`;
        }
    }
};

// Expose CatalogExplorer globally for onclick handlers and external access
window.CatalogExplorer = CatalogExplorer;

// Initialize when DOM is ready
// Wait a bit to ensure the template is fully loaded (especially when loaded via include)
function initializeCatalogExplorer() {
    // Check if the catalog explorer container exists
    const container = document.getElementById('catalog-explorer');
    if (container && typeof CatalogExplorer !== 'undefined') {
        if (!CatalogExplorer.initialized) {
            CatalogExplorer.init();
        }
    } else {
        // Retry after a short delay if container not found yet
        if (typeof CatalogExplorer !== 'undefined') {
            setTimeout(initializeCatalogExplorer, 100);
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCatalogExplorer);
} else {
    // DOM already loaded, but might need to wait for template include
    setTimeout(initializeCatalogExplorer, 100);
}

