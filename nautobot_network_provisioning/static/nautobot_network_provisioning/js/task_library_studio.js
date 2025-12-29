/**
 * Task Library Studio JS (Professional Redesign)
 * Implements the Studio pattern: Palette -> Canvas -> Inspector
 */

class TaskLibraryStudio {
    constructor(options) {
        this.objectPk = options.objectPk;
        this.components = options.visualComponents || [];
        this.variables = options.variables || [];
        this.apiUrl = options.apiUrl;
        this.selectedIndex = -1;
        
        // DOM Elements
        this.canvas = document.getElementById('builder-visual');
        this.varContainer = document.getElementById('variable-container');
        this.inspector = document.getElementById('inspector-content');
        this.sourceContainer = document.getElementById('builder-source');
        
        this.init();
    }

    init() {
        // 1. Initialize CodeMirror for Source View
        this.editor = CodeMirror.fromTextArea(document.getElementById('template-editor'), {
            mode: 'jinja2',
            theme: 'material-darker',
            lineNumbers: true,
            tabSize: 4,
            indentUnit: 4
        });

        // 2. Drag & Drop Setup
        this.setupDragAndDrop();

        // 3. View Switching
        document.getElementById('btn-view-visual').addEventListener('click', () => this.switchView('visual'));
        document.getElementById('btn-view-source').addEventListener('click', () => this.switchView('source'));

        // 4. Variables Initialization
        document.getElementById('add-variable').addEventListener('click', () => this.addVariableRow());
        this.variables.forEach(v => this.addVariableRow(v));

        document.getElementById('id_target_model').addEventListener('change', () => this.loadModelMetadata());
        this.loadModelMetadata(); // Initial load

        // 5. Actions
        document.getElementById('btn-validate').addEventListener('click', () => this.runValidator());
        document.getElementById('task-studio-form').addEventListener('submit', (e) => this.handleSubmit(e));

        // 6. Initial Render
        this.renderCanvas();
    }

    setupDragAndDrop() {
        const tools = document.querySelectorAll('.lego-block-tool');
        tools.forEach(tool => {
            tool.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('type', tool.getAttribute('data-type'));
                e.dataTransfer.effectAllowed = 'copy';
            });
        });

        this.canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.canvas.classList.add('drag-over');
        });

        this.canvas.addEventListener('dragleave', () => {
            this.canvas.classList.remove('drag-over');
        });

        this.canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            this.canvas.classList.remove('drag-over');
            const type = e.dataTransfer.getData('type');
            if (type) {
                this.addComponent(type);
            }
        });
    }

    addComponent(type) {
        const component = {
            id: 'id-' + Date.now(),
            type: type,
            data: {}
        };
        
        // Defaults
        if (type === 'loop') {
            component.data = { item: 'item', list: 'list' };
        } else if (type === 'if') {
            component.data = { condition: 'variable == "value"' };
        } else {
            component.data = { content: '' };
        }

        this.components.push(component);
        this.renderCanvas();
        this.selectBlock(this.components.length - 1);
        this.syncToSource();
    }

    renderCanvas() {
        const hint = document.getElementById('drop-hint');
        if (this.components.length > 0) {
            hint.classList.add('d-none');
        } else {
            hint.classList.remove('d-none');
        }

        // We only want to re-render instances, not clear the whole thing if we want to preserve selection focus
        // But for simplicity in this draft, we re-render
        this.canvas.querySelectorAll('.block-instance').forEach(el => el.remove());
        
        this.components.forEach((comp, index) => {
            const el = this.createBlockElement(comp, index);
            this.canvas.appendChild(el);
        });
    }

    createBlockElement(comp, index) {
        const div = document.createElement('div');
        div.className = `block-instance type-${comp.type} ${index === this.selectedIndex ? 'selected' : ''}`;
        
        let icon = '';
        let title = '';
        let previewText = '';

        switch(comp.type) {
            case 'command':
                icon = 'mdi-console'; title = 'CLI Command';
                previewText = comp.data.content || '...';
                break;
            case 'config_block':
                icon = 'mdi-text-box-outline'; title = 'Config Snippet';
                previewText = comp.data.content || '...';
                break;
            case 'loop':
                icon = 'mdi-repeat'; title = 'Loop';
                previewText = `for ${comp.data.item || '?'} in ${comp.data.list || '?'}`;
                break;
            case 'if':
                icon = 'mdi-source-branch'; title = 'Conditional';
                previewText = `if ${comp.data.condition || '?'}`;
                break;
        }

        div.innerHTML = `
            <div class="block-instance-header">
                <div class="block-title"><i class="mdi ${icon}"></i> ${title}</div>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-link text-muted p-0 me-2 delete-block"><i class="mdi mdi-delete-outline"></i></button>
                </div>
            </div>
            <div class="block-preview">${this.escapeHtml(previewText)}</div>
        `;

        div.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-block')) {
                this.selectBlock(index);
            }
        });

        div.querySelector('.delete-block').addEventListener('click', (e) => {
            e.stopPropagation();
            this.components.splice(index, 1);
            this.selectedIndex = -1;
            this.renderCanvas();
            this.updateInspector();
            this.syncToSource();
        });

        return div;
    }

    selectBlock(index) {
        this.selectedIndex = index;
        this.renderCanvas();
        this.updateInspector();
    }

    updateInspector() {
        this.inspector.innerHTML = '';
        if (this.selectedIndex === -1) {
            this.inspector.innerHTML = `
                <div class="text-center py-5 opacity-50">
                    <i class="mdi mdi-selection-search mdi-48px"></i>
                    <p class="small">Select a block on the canvas to edit its properties.</p>
                </div>`;
            return;
        }

        const comp = this.components[this.selectedIndex];
        const template = document.getElementById(`inspector-${comp.type}`);
        if (!template) return;

        const clone = template.content.cloneNode(true);
        
        // Fill data
        clone.querySelectorAll('[data-prop]').forEach(input => {
            const prop = input.getAttribute('data-prop');
            input.value = comp.data[prop] || '';
            
            // Listen for live updates
            input.addEventListener('input', (e) => {
                comp.data[prop] = e.target.value;
                this.syncBlockPreview(this.selectedIndex);
                this.syncToSource();
            });
        });

        this.inspector.appendChild(clone);
    }

    syncBlockPreview(index) {
        const el = this.canvas.querySelectorAll('.block-instance')[index];
        if (!el) return;
        
        const comp = this.components[index];
        let previewText = '';
        if (comp.type === 'command' || comp.type === 'config_block') previewText = comp.data.content;
        else if (comp.type === 'loop') previewText = `for ${comp.data.item} in ${comp.data.list}`;
        else if (comp.type === 'if') previewText = `if ${comp.data.condition}`;

        el.querySelector('.block-preview').textContent = previewText || '...';
    }

    syncToSource() {
        let source = '';
        this.components.forEach(comp => {
            if (comp.type === 'command' || comp.type === 'config_block') {
                source += (comp.data.content || '') + '\n';
            } else if (comp.type === 'loop') {
                source += `{% for ${comp.data.item || 'item'} in ${comp.data.list || 'list'} %}\n  # ...\n{% endfor %}\n`;
            } else if (comp.type === 'if') {
                source += `{% if ${comp.data.condition || 'true'} %}\n  # ...\n{% endif %}\n`;
            }
        });
        this.editor.setValue(source.trim());
    }

    switchView(view) {
        const visualBtn = document.getElementById('btn-view-visual');
        const sourceBtn = document.getElementById('btn-view-source');
        
        if (view === 'visual') {
            visualBtn.classList.add('active');
            sourceBtn.classList.remove('active');
            this.sourceContainer.classList.add('d-none');
        } else {
            sourceBtn.classList.add('active');
            visualBtn.classList.remove('active');
            this.sourceContainer.classList.remove('d-none');
            this.editor.refresh();
        }
    }

    addVariableRow(data = {}) {
        const template = document.getElementById('variable-template');
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.variable-card');
        
        if (data.name) {
            card.querySelector('.var-name').value = data.name;
            card.querySelector('.var-source').value = data.source;
            card.querySelector('.var-path').value = data.path || data.fallback || '';
        }

        card.querySelector('.remove-variable').addEventListener('click', () => card.remove());
        this.varContainer.appendChild(clone);
    }

    getVariables() {
        const vars = [];
        this.varContainer.querySelectorAll('.variable-card').forEach(card => {
            const name = card.querySelector('.var-name').value.trim();
            if (name) {
                vars.push({
                    name: name,
                    source: card.querySelector('.var-source').value,
                    path: card.querySelector('.var-path').value.trim()
                });
            }
        });
        return vars;
    }

    async runValidator() {
        const btn = document.getElementById('btn-validate');
        const oldHtml = btn.innerHTML;
        btn.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Checking...';
        btn.disabled = true;

        const payload = {
            template_content: this.editor.getValue(),
            variables: this.getVariables()
        };

        try {
            const response = await fetch(`${this.apiUrl}validate-task/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            alert(data.success ? "✅ Task Logic Validated" : "❌ Validation Failed: Check syntax.");
        } catch (e) {
            alert("Error: " + e.message);
        } finally {
            btn.innerHTML = oldHtml;
            btn.disabled = false;
        }
    }

    async loadModelMetadata() {
        const select = document.getElementById('id_target_model');
        if (!select) return;
        const option = select.selectedOptions[0];
        const container = document.getElementById('variable-container');
        
        if (!option || !option.value) {
            // Keep user-defined variables only
            return;
        }

        const modelPath = option.getAttribute('data-model');
        try {
            const response = await fetch(`${this.apiUrl}model-metadata/?model=${modelPath}`);
            const data = await response.json();
            
            // Add a "Model Fields" section to the variable container
            const header = document.createElement('div');
            header.className = 'panel-header small mt-3';
            header.style.background = 'none';
            header.style.paddingLeft = '0';
            header.textContent = `SoT Fields: ${modelPath}`;
            container.appendChild(header);

            data.fields.forEach(f => {
                const item = document.createElement('div');
                item.className = 'small text-muted py-1 border-bottom d-flex justify-content-between align-items-center';
                item.style.cursor = 'pointer';
                item.innerHTML = `<span>device.${f.name}</span> <i class="mdi mdi-plus-circle-outline"></i>`;
                item.addEventListener('click', () => {
                    this.insertAtInspector(`{{ device.${f.name} }}`);
                });
                container.appendChild(item);
            });
        } catch (e) {
            console.error('Error loading metadata:', e);
        }
    }

    insertAtInspector(text) {
        // If there's an active inspector with a textarea, insert there
        const activeArea = this.inspector.querySelector('textarea');
        if (activeArea) {
            const start = activeArea.selectionStart;
            const end = activeArea.selectionEnd;
            const val = activeArea.value;
            activeArea.value = val.slice(0, start) + text + val.slice(end);
            activeArea.dispatchEvent(new Event('input'));
        }
    }

    handleSubmit(e) {
        document.getElementById('id_visual_components').value = JSON.stringify(this.components);
        document.getElementById('id_template_content').value = this.editor.getValue();
        document.getElementById('id_variables').value = JSON.stringify(this.getVariables());
        return true;
    }

    escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

