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
