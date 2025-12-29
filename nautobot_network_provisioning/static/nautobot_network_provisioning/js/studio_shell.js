/**
 * StudioShell v4.0 - Multi-Modal IDE Manager
 * 
 * Manages:
 * - Activity Bar mode switching
 * - Context Sidebar (dynamic per mode)
 * - Bottom Panel (Flight Recorder)
 * - URL routing and deep-linking
 */

const StudioShell = {
    currentMode: 'code',
    sidebarCollapsed: false,
    bottomPanelExpanded: false,
    bottomPanelTab: 'output',

    init: function() {
        // Initialize from URL or config
        const urlMode = this.getModeFromURL();
        const initialMode = urlMode || window.STUDIO_SHELL_CONFIG?.mode || 'library';
        console.log('StudioShell.init() - urlMode:', urlMode, 'initialMode:', initialMode);
        
        this.setupActivityBar();
        this.setupSidebar();
        this.setupBottomPanel();
        this.setupKeyboardShortcuts();
        
        // Switch to the correct mode (force=true to ensure UI updates even if mode matches)
        this.switchMode(initialMode, true);
        
        // Restore state from localStorage
        this.restoreState();
    },

    getModeFromURL: function() {
        const path = window.location.pathname;
        console.log('getModeFromURL: path =', path);
        if (path.includes('/studio/library') || path.endsWith('/studio/library/')) return 'library';
        if (path.includes('/studio/code') || path.includes('/studio/tasks')) return 'code';
        if (path.includes('/studio/flow') || path.includes('/studio/workflows')) return 'flow';
        if (path.includes('/studio/ui') || path.includes('/studio/forms')) return 'ui';
        // Default to library if just /studio/ or /studio
        if (path.endsWith('/studio/') || path.endsWith('/studio')) return 'library';
        return null;
    },

    setupActivityBar: function() {
        const items = document.querySelectorAll('.activity-item');
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                const mode = e.currentTarget.dataset.mode;
                this.switchMode(mode);
            });
        });
    },

    setupSidebar: function() {
        const toggle = document.getElementById('sidebar-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
    },

    setupBottomPanel: function() {
        const toggle = document.getElementById('bottom-panel-toggle');
        const close = document.getElementById('bottom-panel-close');
        const tabs = document.querySelectorAll('.bottom-panel-tab');

        if (toggle) {
            toggle.addEventListener('click', () => {
                this.toggleBottomPanel();
            });
        }

        if (close) {
            close.addEventListener('click', () => {
                this.collapseBottomPanel();
            });
        }

        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchBottomPanelTab(e.currentTarget.dataset.tab);
            });
        });
    },

    setupKeyboardShortcuts: function() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + 1-4 for mode switching
            if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {
                const key = e.key;
                if (key === '1') {
                    e.preventDefault();
                    this.switchMode('library');
                } else if (key === '2') {
                    e.preventDefault();
                    this.switchMode('code');
                } else if (key === '3') {
                    e.preventDefault();
                    this.switchMode('flow');
                } else if (key === '4') {
                    e.preventDefault();
                    this.switchMode('ui');
                }
            }

            // Cmd/Ctrl + J to toggle bottom panel
            if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
                e.preventDefault();
                this.toggleBottomPanel();
            }

            // Cmd/Ctrl + B to toggle sidebar
            if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }
        });
    },

    switchMode: function(mode, force = false) {
        if (!force && mode === this.currentMode) {
            console.log('Mode already active, skipping switch');
            return;
        }

        console.log('switchMode called with mode:', mode, 'currentMode:', this.currentMode, 'force:', force);

        // Update activity bar
        document.querySelectorAll('.activity-item').forEach(item => {
            const isActive = item.dataset.mode === mode;
            item.classList.toggle('active', isActive);
        });

        // Hide all mode content
        document.querySelectorAll('.mode-content').forEach(content => {
            content.classList.remove('active');
        });

        // Show selected mode
        const modeContent = document.getElementById(`mode-${mode}`);
        if (modeContent) {
            modeContent.classList.add('active');
            console.log(`Mode content ${mode} is now active`);
        } else {
            console.error(`Mode content ${mode} not found!`);
        }

        // Update sidebar content
        this.updateSidebarForMode(mode);

        // Load mode-specific content
        if (mode === 'code') {
            this.loadTaskStudio();
        } else if (mode === 'library') {
            // Catalog Explorer is already loaded in the template
            // Wait a moment for the template to be fully rendered, then initialize
            setTimeout(() => {
                if (typeof window.CatalogExplorer !== 'undefined') {
                    if (!window.CatalogExplorer.initialized) {
                        console.log('Initializing CatalogExplorer from StudioShell...');
                        window.CatalogExplorer.init();
                    }
                } else {
                    console.warn('CatalogExplorer not defined, template may not be loaded. Retrying...');
                    // Retry after a longer delay
                    setTimeout(() => {
                        if (typeof window.CatalogExplorer !== 'undefined' && !window.CatalogExplorer.initialized) {
                            window.CatalogExplorer.init();
                        }
                    }, 500);
                }
            }, 200);
        }

        // Update URL
        this.updateURL(mode);

        // Save state
        this.currentMode = mode;
        this.saveState();
    },

    loadMode: function(mode) {
        this.switchMode(mode);
        
        // Load Code mode content immediately if it's the initial mode
        if (mode === 'code') {
            this.loadTaskStudio();
        }
    },

    updateSidebarForMode: function(mode) {
        const sidebarContent = document.getElementById('sidebar-content');
        if (!sidebarContent) return;

        // Clear existing content
        sidebarContent.innerHTML = '';

        switch(mode) {
            case 'library':
                this.renderLibrarySidebar(sidebarContent);
                break;
            case 'code':
                this.renderCodeSidebar(sidebarContent);
                break;
            case 'flow':
                this.renderFlowSidebar(sidebarContent);
                break;
            case 'ui':
                this.renderUISidebar(sidebarContent);
                break;
        }
    },

    renderLibrarySidebar: function(container) {
        container.innerHTML = `
            <div style="padding: 12px; color: #858585; font-size: 11px; text-transform: uppercase; font-weight: 600; border-bottom: 1px solid #3e3e42;">
                Catalog Explorer
            </div>
            <div style="padding: 12px; color: #858585; font-size: 12px;">
                <p>Tree browser coming soon</p>
            </div>
        `;
    },

    renderCodeSidebar: function(container) {
        // Sidebar will be managed by Task Studio when loaded
        container.innerHTML = `
            <div style="padding: 12px; color: #858585; font-size: 11px; text-transform: uppercase; font-weight: 600; border-bottom: 1px solid #3e3e42;">
                Task Context
            </div>
            <div id="task-studio-sidebar" style="flex: 1; overflow-y: auto;">
                <div style="padding: 12px; color: #858585; font-size: 12px;">
                    Loading Task Studio...
                </div>
            </div>
        `;
    },

    loadTaskStudio: function() {
        // Task Studio loads via iframe - just ensure it's visible
        const frame = document.getElementById('task-studio-frame');
        if (frame && !frame.src.includes('task')) {
            // Update iframe src if needed
            const taskId = window.STUDIO_SHELL_CONFIG.itemId && window.STUDIO_SHELL_CONFIG.itemType === 'task' 
                ? window.STUDIO_SHELL_CONFIG.itemId 
                : '';
            frame.src = `/plugins/network-provisioning/studio/tasks/${taskId ? taskId + '/' : ''}`;
        }
    },

    renderFlowSidebar: function(container) {
        container.innerHTML = `
            <div style="padding: 12px; color: #858585; font-size: 11px; text-transform: uppercase; font-weight: 600; border-bottom: 1px solid #3e3e42;">
                Workflow Toolbox
            </div>
            <div style="padding: 12px; color: #858585; font-size: 12px;">
                <p>Task library coming soon</p>
            </div>
        `;
    },

    renderUISidebar: function(container) {
        container.innerHTML = `
            <div style="padding: 12px; color: #858585; font-size: 11px; text-transform: uppercase; font-weight: 600; border-bottom: 1px solid #3e3e42;">
                Widget Library
            </div>
            <div style="padding: 12px; color: #858585; font-size: 12px;">
                <p>Widget library coming soon</p>
            </div>
        `;
    },

    toggleSidebar: function() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        const sidebar = document.getElementById('context-sidebar');
        const toggleIcon = document.getElementById('sidebar-toggle-icon');
        
        if (sidebar) {
            sidebar.classList.toggle('collapsed', this.sidebarCollapsed);
        }
        
        if (toggleIcon) {
            toggleIcon.textContent = this.sidebarCollapsed ? '▶' : '◀';
        }
        
        this.saveState();
    },

    toggleBottomPanel: function() {
        this.bottomPanelExpanded = !this.bottomPanelExpanded;
        const panel = document.getElementById('bottom-panel');
        const toggle = document.getElementById('bottom-panel-toggle');
        
        if (panel) {
            panel.classList.toggle('expanded', this.bottomPanelExpanded);
        }
        
        if (toggle) {
            toggle.classList.toggle('expanded', this.bottomPanelExpanded);
            toggle.querySelector('span').textContent = this.bottomPanelExpanded ? '▼' : '▲';
        }
        
        this.saveState();
    },

    collapseBottomPanel: function() {
        this.bottomPanelExpanded = false;
        const panel = document.getElementById('bottom-panel');
        const toggle = document.getElementById('bottom-panel-toggle');
        
        if (panel) {
            panel.classList.remove('expanded');
        }
        
        if (toggle) {
            toggle.classList.remove('expanded');
            toggle.querySelector('span').textContent = '▲';
        }
        
        this.saveState();
    },

    switchBottomPanelTab: function(tab) {
        this.bottomPanelTab = tab;
        
        // Update tab buttons
        document.querySelectorAll('.bottom-panel-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        
        // Update content (placeholder for now)
        const content = document.getElementById('bottom-panel-content');
        if (content) {
            content.innerHTML = `<div style="color: #858585;">${tab} content coming soon</div>`;
        }
    },

    updateURL: function(mode) {
        const basePath = '/plugins/network-provisioning/studio/';
        let newPath = basePath;
        
        switch(mode) {
            case 'library':
                newPath += 'library/';
                break;
            case 'code':
                newPath += 'code/';
                break;
            case 'flow':
                newPath += 'flow/';
                break;
            case 'ui':
                newPath += 'ui/';
                break;
        }
        
        // Update URL without reload
        if (window.history && window.history.pushState) {
            window.history.pushState({ mode }, '', newPath);
        }
    },

    saveState: function() {
        try {
            localStorage.setItem('studioShell_state', JSON.stringify({
                mode: this.currentMode,
                sidebarCollapsed: this.sidebarCollapsed,
                bottomPanelExpanded: this.bottomPanelExpanded,
                bottomPanelTab: this.bottomPanelTab
            }));
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    },

    restoreState: function() {
        try {
            const saved = localStorage.getItem('studioShell_state');
            if (saved) {
                const state = JSON.parse(saved);
                if (state.sidebarCollapsed !== undefined) {
                    this.sidebarCollapsed = state.sidebarCollapsed;
                    const sidebar = document.getElementById('context-sidebar');
                    const toggleIcon = document.getElementById('sidebar-toggle-icon');
                    if (sidebar) sidebar.classList.toggle('collapsed', this.sidebarCollapsed);
                    if (toggleIcon) toggleIcon.textContent = this.sidebarCollapsed ? '▶' : '◀';
                }
                if (state.bottomPanelExpanded !== undefined) {
                    this.bottomPanelExpanded = state.bottomPanelExpanded;
                    const panel = document.getElementById('bottom-panel');
                    const toggle = document.getElementById('bottom-panel-toggle');
                    if (panel) panel.classList.toggle('expanded', this.bottomPanelExpanded);
                    if (toggle) {
                        toggle.classList.toggle('expanded', this.bottomPanelExpanded);
                        toggle.querySelector('span').textContent = this.bottomPanelExpanded ? '▼' : '▲';
                    }
                }
                if (state.bottomPanelTab) {
                    this.switchBottomPanelTab(state.bottomPanelTab);
                }
            }
        } catch (e) {
            console.warn('Failed to restore state:', e);
        }
    },

    // Public API for mode content to communicate with shell
    setModeContent: function(mode, html) {
        const modeContent = document.getElementById(`mode-${mode}`);
        if (modeContent) {
            modeContent.innerHTML = html;
        }
    },

    logToBottomPanel: function(message, type = 'output') {
        const content = document.getElementById('bottom-panel-content');
        if (!content) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const color = type === 'error' ? '#f48771' : type === 'warning' ? '#f59e0b' : '#cccccc';
        const line = document.createElement('div');
        line.style.color = color;
        line.style.marginBottom = '4px';
        line.innerHTML = `<span style="color: #858585;">[${timestamp}]</span> ${message}`;
        content.appendChild(line);
        content.scrollTop = content.scrollHeight;
        
        // Auto-expand if collapsed
        if (!this.bottomPanelExpanded) {
            this.toggleBottomPanel();
        }
    }
};

// Expose globally for iframe communication and external access
window.StudioShell = StudioShell;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    StudioShell.init();
});
window.StudioShell = StudioShell;

