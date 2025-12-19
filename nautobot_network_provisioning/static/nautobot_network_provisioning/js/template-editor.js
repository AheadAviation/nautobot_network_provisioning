/**
 * Jinja2 Template Editor - IDE-like editing experience
 * 
 * Provides:
 * - CodeMirror integration for syntax highlighting
 * - Live preview via AJAX
 * - Variable helper panel
 * - Real-time validation
 */

const Jinja2Editor = {
    // Store CodeMirror instances by field name
    editors: {},
    
    // Preview debounce timers
    previewTimers: {},
    
    /**
     * Initialize the editor for a textarea
     */
    init: function(textareaId) {
        const textarea = document.getElementById(textareaId);
        if (!textarea || this.editors[textareaId]) return;
        
        // Get the field name from the ID
        const name = textareaId.replace('id_', '');
        
        // Initialize CodeMirror
        const editor = CodeMirror.fromTextArea(textarea, {
            mode: 'jinja2',
            theme: 'material-darker',
            lineNumbers: true,
            lineWrapping: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            styleActiveLine: true,
            tabSize: 2,
            indentUnit: 2,
            placeholder: 'Enter your Jinja2 template here...',
            extraKeys: {
                'Tab': function(cm) {
                    if (cm.somethingSelected()) {
                        cm.indentSelection('add');
                    } else {
                        cm.replaceSelection('  ', 'end');
                    }
                },
                'Ctrl-S': function(cm) {
                    // Trigger form submit on Ctrl+S
                    const form = cm.getTextArea().closest('form');
                    if (form) {
                        form.submit();
                    }
                },
                'Ctrl-Enter': function(cm) {
                    Jinja2Editor.preview(name);
                },
            }
        });
        
        // Store reference
        this.editors[textareaId] = editor;
        
        // Set up auto-preview on change (debounced)
        editor.on('change', function() {
            Jinja2Editor.debouncedPreview(name);
            Jinja2Editor.clearValidation(name);
        });
        
        // Set up helper button click handlers
        this.setupHelperButtons(name, editor);
        
        // Trigger initial preview if content exists
        if (editor.getValue().trim()) {
            this.preview(name);
        }
        
        console.log('Jinja2Editor initialized for:', textareaId);
    },
    
    /**
     * Set up click handlers for helper buttons
     */
    setupHelperButtons: function(name, editor) {
        const container = document.getElementById('jinja2-ide-' + name);
        if (!container) return;
        
        container.querySelectorAll('.helper-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const insertText = this.getAttribute('data-insert');
                const insertType = this.getAttribute('data-insert-type') || 'normal';
                
                if (!insertText) return;
                
                // Unescape newlines
                const text = insertText.replace(/\\n/g, '\n');
                
                // Get cursor position
                const cursor = editor.getCursor();
                
                if (insertType === 'inline') {
                    // Insert at cursor (for filters)
                    editor.replaceRange(text, cursor);
                } else if (insertType === 'block') {
                    // Insert block on new lines
                    const currentLine = editor.getLine(cursor.line);
                    if (currentLine.trim() !== '') {
                        editor.replaceRange('\n' + text + '\n', {line: cursor.line, ch: currentLine.length});
                    } else {
                        editor.replaceRange(text + '\n', cursor);
                    }
                } else {
                    // Normal insert
                    editor.replaceRange(text, cursor);
                }
                
                editor.focus();
            });
        });
    },
    
    /**
     * Get editor instance by field name
     */
    getEditor: function(name) {
        return this.editors['id_' + name];
    },
    
    /**
     * Toggle the variable helper panel
     */
    toggleHelper: function(name) {
        const helper = document.getElementById('jinja2-helper-' + name);
        if (helper) {
            helper.style.display = helper.style.display === 'none' ? 'block' : 'none';
        }
    },
    
    /**
     * Format the template (basic indentation cleanup)
     */
    format: function(name) {
        const editor = this.getEditor(name);
        if (!editor) return;
        
        let content = editor.getValue();
        
        // Basic formatting rules for CLI-style templates
        const lines = content.split('\n');
        const formattedLines = [];
        let indentLevel = 0;
        
        for (let line of lines) {
            let trimmed = line.trim();
            
            // Check for dedent triggers
            if (trimmed.match(/^{% end(if|for|macro|block|call) %}/) ||
                trimmed.match(/^{% else %}/) ||
                trimmed.match(/^{% elif /)) {
                indentLevel = Math.max(0, indentLevel - 1);
            }
            
            // Apply indentation
            if (trimmed !== '') {
                formattedLines.push('  '.repeat(indentLevel) + trimmed);
            } else {
                formattedLines.push('');
            }
            
            // Check for indent triggers
            if (trimmed.match(/^{% (if|for|macro|block|call) /) && 
                !trimmed.match(/{% end/)) {
                indentLevel++;
            }
            if (trimmed.match(/^{% else %}/) ||
                trimmed.match(/^{% elif /)) {
                indentLevel++;
            }
        }
        
        editor.setValue(formattedLines.join('\n'));
        this.showNotification('Template formatted', 'success');
    },
    
    /**
     * Validate the template via AJAX
     */
    validate: function(name) {
        const editor = this.getEditor(name);
        if (!editor) return;
        
        const content = editor.getValue();
        const previewUrl = document.getElementById('id_' + name).getAttribute('data-preview-url');
        
        // Show loading state
        this.showValidation(name, 'validating', 'Validating...');
        
        fetch(previewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                template_text: content,
                validate_only: true,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.is_valid) {
                this.showValidation(name, 'valid', 'Template is valid ✓');
            } else {
                const errorMsg = data.errors ? data.errors.join('\n') : 'Invalid template';
                this.showValidation(name, 'invalid', errorMsg);
            }
        })
        .catch(error => {
            this.showValidation(name, 'error', 'Validation failed: ' + error.message);
        });
    },
    
    /**
     * Preview the template via AJAX
     */
    preview: function(name) {
        const editor = this.getEditor(name);
        if (!editor) return;
        
        const content = editor.getValue();
        const previewUrl = document.getElementById('id_' + name).getAttribute('data-preview-url');
        
        // Update status
        this.updatePreviewStatus(name, 'loading', 'Loading...');
        
        fetch(previewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                template_text: content,
            }),
        })
        .then(response => response.json())
        .then(data => {
            const previewContent = document.getElementById('preview-content-' + name);
            if (data.is_valid) {
                previewContent.innerHTML = '<pre><code>' + this.escapeHtml(data.rendered) + '</code></pre>';
                this.updatePreviewStatus(name, 'success', 'Rendered successfully');
            } else {
                const errorMsg = data.errors ? data.errors.join('\n') : 'Render failed';
                previewContent.innerHTML = '<pre class="text-danger"><code>' + this.escapeHtml(errorMsg) + '</code></pre>';
                this.updatePreviewStatus(name, 'error', 'Render error');
            }
        })
        .catch(error => {
            this.updatePreviewStatus(name, 'error', 'Preview failed');
            console.error('Preview error:', error);
        });
    },
    
    /**
     * Debounced preview (called on content change)
     */
    debouncedPreview: function(name) {
        // Clear existing timer
        if (this.previewTimers[name]) {
            clearTimeout(this.previewTimers[name]);
        }
        
        // Set new timer (1 second delay)
        this.previewTimers[name] = setTimeout(() => {
            this.preview(name);
        }, 1000);
    },
    
    /**
     * Show validation feedback
     */
    showValidation: function(name, status, message) {
        const container = document.getElementById('validation-' + name);
        if (!container) return;
        
        container.style.display = 'block';
        container.className = 'validation-feedback validation-' + status;
        
        const icon = container.querySelector('.validation-icon');
        const msg = container.querySelector('.validation-message');
        
        if (status === 'valid') {
            icon.innerHTML = '✓';
            icon.className = 'validation-icon text-success';
        } else if (status === 'invalid') {
            icon.innerHTML = '✗';
            icon.className = 'validation-icon text-danger';
        } else if (status === 'validating') {
            icon.innerHTML = '...';
            icon.className = 'validation-icon text-muted';
        } else {
            icon.innerHTML = '!';
            icon.className = 'validation-icon text-warning';
        }
        
        msg.textContent = message;
    },
    
    /**
     * Clear validation feedback
     */
    clearValidation: function(name) {
        const container = document.getElementById('validation-' + name);
        if (container) {
            container.style.display = 'none';
        }
    },
    
    /**
     * Update preview status indicator
     */
    updatePreviewStatus: function(name, status, message) {
        const statusEl = document.getElementById('preview-status-' + name);
        if (!statusEl) return;
        
        statusEl.textContent = message;
        statusEl.className = 'preview-status preview-status-' + status;
    },
    
    /**
     * Show a notification message
     */
    showNotification: function(message, type) {
        // Use Nautobot's notification system if available
        if (window.Nautobot && window.Nautobot.showMessage) {
            window.Nautobot.showMessage(message, type);
        } else {
            console.log('[' + type + '] ' + message);
        }
    },
    
    /**
     * Get CSRF token from cookies
     */
    getCSRFToken: function() {
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
        return cookieValue;
    },
    
    /**
     * Escape HTML special characters
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Find all jinja2 editor textareas
    document.querySelectorAll('.jinja2-editor-textarea').forEach(function(textarea) {
        Jinja2Editor.init(textarea.id);
    });
});

// Also initialize when new content is added dynamically
if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) {
                    node.querySelectorAll('.jinja2-editor-textarea').forEach(function(textarea) {
                        Jinja2Editor.init(textarea.id);
                    });
                }
            });
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
}

    // Export for global access
    window.Jinja2Editor = Jinja2Editor;

    /**
     * IDE Mode Implementation
     */
    Jinja2Editor.initIDE = function(config) {
        console.log('Jinja2Editor.initIDE called with config:', config);
        this.ideConfig = config;
        
        const templateArea = document.getElementById(config.templateEditorId);
        const variablesArea = document.getElementById(config.variablesEditorId);
        
        if (!templateArea || !variablesArea) {
            console.error('IDE textareas not found!', {templateArea, variablesArea});
            return;
        }

        console.log('Template content found in textarea:', templateArea.value.length, 'chars');

        // Initialize Template Editor
        this.templateEditor = CodeMirror.fromTextArea(templateArea, {
            mode: 'jinja2',
            theme: 'material-darker',
            lineNumbers: true,
            lineWrapping: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            tabSize: 2,
            indentUnit: 2,
            extraKeys: {"Tab": "indentMore", "Shift-Tab": "indentLess", "Ctrl-Enter": () => this.runPreviewIDE()}
        });

        // Initialize Variables Editor
        this.variablesEditor = CodeMirror.fromTextArea(variablesArea, {
            mode: 'application/json',
            theme: 'material-darker',
            lineNumbers: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            tabSize: 2,
            indentUnit: 2
        });

        console.log('Template IDE initialized successfully');
        
        // Auto-run preview if there is content
        if (this.templateEditor.getValue().trim()) {
            setTimeout(() => this.runPreviewIDE(), 500);
        }
    };

    Jinja2Editor.runPreviewIDE = function() {
        const template = this.templateEditor.getValue();
        let context = {};
        try {
            context = JSON.parse(this.variablesEditor.getValue());
        } catch (e) {
            this.updatePreviewStatusIDE('error', 'Invalid JSON context');
            return;
        }

        this.updatePreviewStatusIDE('loading', 'Rendering...');
        
        fetch(this.ideConfig.previewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                template_text: template,
                context: context
            }),
        })
        .then(response => response.json())
        .then(data => {
            const out = document.getElementById(this.ideConfig.previewOutputId);
            if (data.is_valid) {
                out.textContent = data.rendered;
                out.className = 'p-3 font-monospace text-body';
                this.updatePreviewStatusIDE('success', 'Rendered');
            } else {
                out.textContent = data.errors.join('\n');
                out.className = 'p-3 font-monospace text-danger';
                this.updatePreviewStatusIDE('error', 'Render Error');
            }
        })
        .catch(err => {
            this.updatePreviewStatusIDE('error', 'Fetch Error');
            console.error(err);
        });
    };

    Jinja2Editor.updatePreviewStatusIDE = function(status, message) {
        const el = document.getElementById(this.ideConfig.previewStatusId);
        if (!el) return;
        el.textContent = message;
        el.className = 'badge ' + (status === 'success' ? 'bg-success' : status === 'error' ? 'bg-danger' : 'bg-info');
    };

    Jinja2Editor.loadDeviceContext = function() {
        const deviceId = document.getElementById('device-select').value;
        if (!deviceId) return;

        const btn = document.getElementById('confirm-load-device');
        btn.disabled = true;
        btn.textContent = 'Loading...';

        fetch(this.ideConfig.deviceContextUrl + deviceId + '/', {
            headers: {'X-CSRFToken': this.getCSRFToken()}
        })
        .then(response => response.json())
        .then(data => {
            this.variablesEditor.setValue(JSON.stringify(data, null, 2));
            bootstrap.Modal.getInstance(document.getElementById('loadDeviceModal')).hide();
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Load Context';
        });
    };

    Jinja2Editor.runGraphQLQuery = function() {
        const query = document.getElementById('graphql-query-text').value;
        const btn = document.getElementById('confirm-load-graphql');
        btn.disabled = true;
        btn.textContent = 'Running...';

        fetch(this.ideConfig.graphqlUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({query: query}),
        })
        .then(response => response.json())
        .then(data => {
            const currentVars = JSON.parse(this.variablesEditor.getValue() || '{}');
            const merged = {...currentVars, graphql: data.data};
            this.variablesEditor.setValue(JSON.stringify(merged, null, 2));
            bootstrap.Modal.getInstance(document.getElementById('loadGraphQLModal')).hide();
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Run & Load Result';
        });
    };

    Jinja2Editor.formatIDE = function() {
        // Basic formatting for template
        let content = this.templateEditor.getValue();
        // ... (can reuse existing format logic but adapted for this.templateEditor)
        const lines = content.split('\n');
        const formattedLines = [];
        let indentLevel = 0;
        for (let line of lines) {
            let trimmed = line.trim();
            if (trimmed.match(/^{% end(if|for|macro|block|call) %}/) || trimmed.match(/^{% else %}/) || trimmed.match(/^{% elif /)) {
                indentLevel = Math.max(0, indentLevel - 1);
            }
            if (trimmed !== '') formattedLines.push('  '.repeat(indentLevel) + trimmed);
            else formattedLines.push('');
            if (trimmed.match(/^{% (if|for|macro|block|call) /) && !trimmed.match(/{% end/)) indentLevel++;
            if (trimmed.match(/^{% else %}/) || trimmed.match(/^{% elif /)) indentLevel++;
        }
        this.templateEditor.setValue(formattedLines.join('\n'));
        
        // Format variables if JSON
        try {
            const vars = JSON.parse(this.variablesEditor.getValue());
            this.variablesEditor.setValue(JSON.stringify(vars, null, 2));
        } catch (e) {}
    };

    Jinja2Editor.validateIDE = function() {
        const template = this.templateEditor.getValue();
        fetch(this.ideConfig.previewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                template_text: template,
                validate_only: true
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.is_valid) this.updatePreviewStatusIDE('success', 'Syntax Valid ✓');
            else this.updatePreviewStatusIDE('error', data.errors[0]);
        });
    };

    Jinja2Editor.saveIDE = function() {
        if (!this.ideConfig.implementationId) return;
        
        const template = this.templateEditor.getValue();
        const btn = document.getElementById('btn-save');
        const oldText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Saving...';

        // Use the API to save
        // We use the base URL from the config if provided, otherwise fallback
        const apiUrl = (this.ideConfig.apiUrl || '/api/plugins/network-provisioning/') + 'task-implementations/' + this.ideConfig.implementationId + '/';
        
        fetch(apiUrl, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
            body: JSON.stringify({
                template_content: template
            }),
        })
        .then(response => {
            if (response.ok) {
                this.updatePreviewStatusIDE('success', 'Saved successfully');
                this.showNotification('Template saved successfully', 'success');
            } else {
                this.updatePreviewStatusIDE('error', 'Save failed');
                this.showNotification('Failed to save template', 'error');
            }
        })
        .catch(err => {
            this.updatePreviewStatusIDE('error', 'Save error');
            console.error('Save error:', err);
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = oldText;
        });
    };
