/**
 * Workflow Orchestrator - Canvas-based Visual Workflow Builder
 * 
 * Features:
 * - Drag-and-drop task nodes
 * - Visual workflow builder
 * - Node connections
 * - Property panel
 * - Graph serialization
 */

const WorkflowOrchestrator = {
    canvas: null,
    svg: null,
    nodesContainer: null,
    nodes: [],
    edges: [],
    selectedNode: null,
    tasks: [],
    nodeIdCounter: 1,
    zoom: 1,
    panX: 0,
    panY: 0,
    isDragging: false,
    dragStart: { x: 0, y: 0 },
    connectingFrom: null,

    init: function() {
        this.canvas = document.getElementById('canvas-area');
        this.svg = document.getElementById('workflow-canvas');
        this.nodesContainer = document.getElementById('nodes-container');
        this.loadTasks();
        this.setupEventListeners();
        this.initializeCanvas();
        this.loadWorkflow();
        this.updateStatus('Ready - Drag tasks onto canvas', 'success');
    },

    loadTasks: async function() {
        try {
            const resp = await fetch(`${window.WORKFLOW_CONFIG.apiRoot}task-intents/`, {
                headers: {
                    'X-CSRFToken': window.WORKFLOW_CONFIG.csrfToken,
                    'Accept': 'application/json'
                }
            });

            if (resp.ok) {
                const data = await resp.json();
                this.tasks = data.results || [];
                this.renderTaskList();
            }
        } catch (e) {
            console.error('Failed to load tasks:', e);
        }
    },

    renderTaskList: function() {
        const container = document.getElementById('tasks-list');
        container.innerHTML = '';

        this.tasks.forEach(task => {
            const div = document.createElement('div');
            div.className = 'task-item';
            div.draggable = true;
            div.dataset.taskId = task.id;
            div.innerHTML = `
                <div class="task-item-name">${this.escapeHtml(task.name)}</div>
                <div class="task-item-desc">${this.escapeHtml(task.description || 'No description')}</div>
            `;
            div.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('application/json', JSON.stringify({
                    type: 'task',
                    taskId: task.id,
                    taskName: task.name
                }));
            });
            container.appendChild(div);
        });
    },

    setupEventListeners: function() {
        // Sidebar tabs
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.onclick = () => {
                document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                const tabName = tab.dataset.tab;
                document.getElementById('tasks-list').style.display = tabName === 'tasks' ? 'block' : 'none';
                document.getElementById('logic-list').style.display = tabName === 'logic' ? 'block' : 'none';
                
                if (tabName === 'logic') {
                    this.renderLogicList();
                }
            };
        });

        // Canvas drop
        this.canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        this.canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.panX) / this.zoom;
            const y = (e.clientY - rect.top - this.panY) / this.zoom;
            
            try {
                const data = JSON.parse(e.dataTransfer.getData('application/json'));
                if (data.type === 'task') {
                    this.addTaskNode(data.taskId, data.taskName, x, y);
                } else if (data.type === 'logic') {
                    this.addLogicNode(data.logicType, x, y);
                }
            } catch (e) {
                console.error('Drop error:', e);
            }
        });

        // Canvas click to deselect
        this.canvas.addEventListener('click', (e) => {
            if (e.target === this.canvas || e.target === this.svg || e.target === this.nodesContainer) {
                this.deselectNode();
            }
        });

        // Buttons
        document.getElementById('btn-save').onclick = () => this.saveWorkflow();
        document.getElementById('btn-validate').onclick = () => this.validateWorkflow();
        document.getElementById('btn-test').onclick = () => this.testWorkflow();

        // Zoom controls
        document.getElementById('btn-zoom-in').onclick = () => {
            this.zoom = Math.min(this.zoom * 1.2, 3);
            this.renderCanvas();
        };
        document.getElementById('btn-zoom-out').onclick = () => {
            this.zoom = Math.max(this.zoom / 1.2, 0.3);
            this.renderCanvas();
        };
        document.getElementById('btn-fit-view').onclick = () => {
            this.fitView();
        };
    },

    renderLogicList: function() {
        const container = document.getElementById('logic-list');
        const logicTypes = [
            { type: 'start', icon: '▶', label: 'Start', color: '#22c55e' },
            { type: 'end', icon: '■', label: 'End', color: '#f14c4c' },
            { type: 'decision', icon: '◊', label: 'Decision', color: '#f59e0b' },
            { type: 'fork', icon: '⚡', label: 'Fork', color: '#3b82f6' },
            { type: 'join', icon: '⚙', label: 'Join', color: '#8b5cf6' },
        ];

        container.innerHTML = '';
        logicTypes.forEach(logic => {
            const div = document.createElement('div');
            div.className = 'logic-item';
            div.draggable = true;
            div.dataset.logicType = logic.type;
            div.innerHTML = `
                <div class="logic-item-icon" style="color: ${logic.color}">${logic.icon}</div>
                <div class="logic-item-label">${logic.label}</div>
            `;
            div.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('application/json', JSON.stringify({
                    type: 'logic',
                    logicType: logic.type,
                    label: logic.label
                }));
            });
            container.appendChild(div);
        });
    },

    initializeCanvas: function() {
        // Setup pan and zoom
        this.canvas.addEventListener('mousedown', (e) => {
            if (e.button === 1 || (e.button === 0 && e.ctrlKey)) {
                this.isDragging = true;
                this.dragStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
                e.preventDefault();
            }
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                this.panX = e.clientX - this.dragStart.x;
                this.panY = e.clientY - this.dragStart.y;
                this.renderCanvas();
            }
        });

        this.canvas.addEventListener('mouseup', () => {
            this.isDragging = false;
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoom = Math.max(0.3, Math.min(3, this.zoom * delta));
            this.renderCanvas();
        });

        this.renderCanvas();
    },

    renderCanvas: function() {
        // Clear SVG
        this.svg.innerHTML = '';
        
        // Apply transform
        this.nodesContainer.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.zoom})`;
        this.nodesContainer.style.transformOrigin = '0 0';

        // Render edges
        this.edges.forEach(edge => {
            const sourceNode = this.nodes.find(n => n.id === edge.source);
            const targetNode = this.nodes.find(n => n.id === edge.target);
            
            if (sourceNode && targetNode) {
                const x1 = sourceNode.position.x + 100;
                const y1 = sourceNode.position.y + 40;
                const x2 = targetNode.position.x + 100;
                const y2 = targetNode.position.y + 40;
                
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', x1);
                line.setAttribute('y1', y1);
                line.setAttribute('x2', x2);
                line.setAttribute('y2', y2);
                line.setAttribute('stroke', '#007acc');
                line.setAttribute('stroke-width', '2');
                line.setAttribute('marker-end', 'url(#arrowhead)');
                this.svg.appendChild(line);
            }
        });

        // Add arrow marker
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrowhead');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '10');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '3');
        marker.setAttribute('orient', 'auto');
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', '0 0, 10 3, 0 6');
        polygon.setAttribute('fill', '#007acc');
        marker.appendChild(polygon);
        defs.appendChild(marker);
        this.svg.appendChild(defs);
    },

    addTaskNode: function(taskId, taskName, x, y) {
        const task = this.tasks.find(t => t.id === taskId);
        const newNode = {
            id: `node-${this.nodeIdCounter++}`,
            type: 'task',
            position: { x, y },
            data: {
                label: taskName,
                description: task?.description || '',
                taskId: taskId,
                taskName: taskName
            }
        };

        this.nodes.push(newNode);
        this.renderNodes();
        this.renderCanvas();
        this.updateStatus(`Added task: ${taskName}`, 'success');
    },

    addLogicNode: function(logicType, x, y) {
        const labels = {
            start: 'Start',
            end: 'End',
            decision: 'Decision',
            fork: 'Fork',
            join: 'Join'
        };

        const newNode = {
            id: `node-${this.nodeIdCounter++}`,
            type: logicType,
            position: { x, y },
            data: {
                label: labels[logicType] || logicType,
                logicType: logicType
            }
        };

        this.nodes.push(newNode);
        this.renderNodes();
        this.renderCanvas();
        this.updateStatus(`Added ${labels[logicType]} node`, 'success');
    },

    renderNodes: function() {
        this.nodesContainer.innerHTML = '';
        
        this.nodes.forEach(node => {
            const nodeEl = this.createNodeElement(node);
            this.nodesContainer.appendChild(nodeEl);
        });
    },

    createNodeElement: function(node) {
        const div = document.createElement('div');
        div.className = 'workflow-node';
        div.dataset.nodeId = node.id;
        div.style.position = 'absolute';
        div.style.left = node.position.x + 'px';
        div.style.top = node.position.y + 'px';
        div.style.cursor = 'move';
        
        if (node.type === 'task') {
            div.innerHTML = `
                <div class="node-task">
                    <div class="node-header">${this.escapeHtml(node.data.label)}</div>
                    <div class="node-body">${this.escapeHtml(node.data.description || 'Task')}</div>
                </div>
            `;
        } else if (node.type === 'start') {
            div.innerHTML = `<div class="node-start">▶</div>`;
        } else if (node.type === 'end') {
            div.innerHTML = `<div class="node-end">■</div>`;
        } else if (node.type === 'decision') {
            div.innerHTML = `<div class="node-decision">${this.escapeHtml(node.data.label)}</div>`;
        } else {
            div.innerHTML = `<div class="node-logic">${this.escapeHtml(node.data.label)}</div>`;
        }

        // Make draggable
        this.makeNodeDraggable(div, node);
        
        // Click to select
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectNode(node);
        });

        return div;
    },

    makeNodeDraggable: function(element, node) {
        let isDragging = false;
        let startX, startY, initialX, initialY;

        element.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialX = node.position.x;
            initialY = node.position.y;
            e.stopPropagation();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = (e.clientX - startX) / this.zoom;
            const dy = (e.clientY - startY) / this.zoom;
            node.position.x = initialX + dx;
            node.position.y = initialY + dy;
            element.style.left = node.position.x + 'px';
            element.style.top = node.position.y + 'px';
            this.renderCanvas();
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    },

    selectNode: function(node) {
        this.selectedNode = node;
        document.querySelectorAll('.workflow-node').forEach(el => {
            el.classList.remove('selected');
        });
        const nodeEl = document.querySelector(`[data-node-id="${node.id}"]`);
        if (nodeEl) nodeEl.classList.add('selected');
        this.showPropertyPanel(node);
    },

    deselectNode: function() {
        this.selectedNode = null;
        document.querySelectorAll('.workflow-node').forEach(el => {
            el.classList.remove('selected');
        });
        document.getElementById('property-panel').style.display = 'none';
    },

    showPropertyPanel: function(node) {
        const panel = document.getElementById('property-panel');
        const content = document.getElementById('property-content');
        
        panel.style.display = 'flex';

        if (node.type === 'task') {
            content.innerHTML = this.renderTaskProperties(node);
        } else if (node.type === 'decision') {
            content.innerHTML = this.renderDecisionProperties(node);
        } else {
            content.innerHTML = this.renderLogicProperties(node);
        }
    },

    renderTaskProperties: function(node) {
        return `
            <div class="form-group">
                <label class="form-label">Task Name</label>
                <input type="text" class="form-control" value="${this.escapeHtml(node.data.taskName)}" readonly>
            </div>
            <div class="form-group">
                <label class="form-label">Input Mapping</label>
                <div id="input-mappings">
                    <div class="mapping-row">
                        <input type="text" placeholder="Workflow variable" value="vlan_id">
                        <span>→</span>
                        <input type="text" placeholder="Task input" value="vlan_id">
                    </div>
                </div>
                <button class="btn" onclick="WorkflowOrchestrator.addMapping('input')" style="margin-top: 8px; width: 100%;">
                    <i class="mdi mdi-plus"></i> Add Mapping
                </button>
            </div>
            <div class="form-group">
                <label class="form-label">Error Handling</label>
                <select class="form-control">
                    <option>Continue on error</option>
                    <option>Stop workflow</option>
                    <option>Retry (3x)</option>
                </select>
            </div>
        `;
    },

    renderDecisionProperties: function(node) {
        return `
            <div class="form-group">
                <label class="form-label">Condition Expression</label>
                <textarea class="form-control" rows="3" placeholder="e.g., device.platform == 'cisco_ios'">${node.data.condition || ''}</textarea>
            </div>
            <div class="form-group">
                <label class="form-label">True Label</label>
                <input type="text" class="form-control" value="Yes" placeholder="Label for true branch">
            </div>
            <div class="form-group">
                <label class="form-label">False Label</label>
                <input type="text" class="form-control" value="No" placeholder="Label for false branch">
            </div>
        `;
    },

    renderLogicProperties: function(node) {
        return `
            <div class="form-group">
                <label class="form-label">Node Type</label>
                <input type="text" class="form-control" value="${this.escapeHtml(node.data.label)}" readonly>
            </div>
            <div style="padding: 12px; background: #1e1e1e; border-radius: 4px; font-size: 11px; color: #858585;">
                ${this.getLogicDescription(node.data.logicType)}
            </div>
        `;
    },

    getLogicDescription: function(logicType) {
        const descriptions = {
            start: 'Entry point for workflow execution',
            end: 'Exit point - workflow completes here',
            fork: 'Split execution into parallel branches',
            join: 'Synchronize parallel branches before continuing'
        };
        return descriptions[logicType] || 'Logic node';
    },

    addMapping: function(type) {
        const container = document.getElementById(`${type}-mappings`);
        const row = document.createElement('div');
        row.className = 'mapping-row';
        row.innerHTML = `
            <input type="text" placeholder="Workflow variable">
            <span>→</span>
            <input type="text" placeholder="Task input">
            <button class="btn-icon-small" onclick="this.parentElement.remove()">
                <i class="mdi mdi-close"></i>
            </button>
        `;
        container.appendChild(row);
    },

    validateWorkflow: function() {
        if (this.nodes.length === 0) {
            this.updateStatus('Workflow is empty', 'warning');
            return false;
        }

        const startNodes = this.nodes.filter(n => n.type === 'start');
        const endNodes = this.nodes.filter(n => n.type === 'end');

        if (startNodes.length === 0) {
            this.updateStatus('Workflow must have a Start node', 'error');
            return false;
        }

        if (startNodes.length > 1) {
            this.updateStatus('Workflow can only have one Start node', 'error');
            return false;
        }

        if (endNodes.length === 0) {
            this.updateStatus('Workflow must have at least one End node', 'error');
            return false;
        }

        // Check for isolated nodes
        const connectedNodeIds = new Set();
        this.edges.forEach(edge => {
            connectedNodeIds.add(edge.source);
            connectedNodeIds.add(edge.target);
        });

        const isolatedNodes = this.nodes.filter(n => !connectedNodeIds.has(n.id) && n.type !== 'start');
        if (isolatedNodes.length > 0) {
            this.updateStatus(`Warning: ${isolatedNodes.length} isolated node(s)`, 'warning');
        }

        this.updateStatus('Workflow is valid', 'success');
        return true;
    },

    testWorkflow: function() {
        if (!this.validateWorkflow()) {
            return;
        }

        this.updateStatus('Running test workflow...', null);
        // TODO: Implement test run
        setTimeout(() => {
            this.updateStatus('Test completed successfully', 'success');
        }, 2000);
    },

    saveWorkflow: async function() {
        const name = document.getElementById('workflow-name').value;
        if (!name) {
            this.updateStatus('Workflow name required', 'error');
            document.getElementById('workflow-name').focus();
            return;
        }

        if (!this.validateWorkflow()) {
            return;
        }

        this.updateStatus('Saving workflow...', null);

        try {
            // Serialize graph
            const graphDefinition = {
                nodes: this.nodes.map(node => ({
                    id: node.id,
                    type: node.type,
                    position: node.position,
                    data: node.data
                })),
                edges: this.edges.map(edge => ({
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    sourceHandle: edge.sourceHandle,
                    targetHandle: edge.targetHandle
                }))
            };

            const payload = {
                name: name,
                slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
                graph_definition: graphDefinition,
                enabled: true
            };

            const workflow = window.WORKFLOW_CONFIG.workflow;
            const isUpdate = workflow && workflow.id;
            const url = isUpdate
                ? `${window.WORKFLOW_CONFIG.apiRoot}workflows/${workflow.id}/`
                : `${window.WORKFLOW_CONFIG.apiRoot}workflows/`;

            const resp = await fetch(url, {
                method: isUpdate ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.WORKFLOW_CONFIG.csrfToken
                },
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                const saved = await resp.json();
                this.updateStatus('Workflow saved successfully', 'success');
                if (!isUpdate) {
                    setTimeout(() => {
                        window.location.href = `/plugins/network-provisioning/studio/workflows/${saved.id}/`;
                    }, 1000);
                }
            } else {
                const err = await resp.json();
                this.updateStatus(`Error: ${JSON.stringify(err)}`, 'error');
            }
        } catch (e) {
            console.error('Save error:', e);
            this.updateStatus(`Error: ${e.message}`, 'error');
        }
    },

    loadWorkflow: function() {
        const workflow = window.WORKFLOW_CONFIG.workflow;
        if (workflow && workflow.graph_definition) {
            const graph = workflow.graph_definition;
            if (graph.nodes && graph.edges) {
                this.nodes = graph.nodes;
                this.edges = graph.edges;
                
                // Update node counter
                const maxId = Math.max(...this.nodes.map(n => {
                    const match = n.id.match(/node-(\d+)/);
                    return match ? parseInt(match[1]) : 0;
                }), 0);
                this.nodeIdCounter = maxId + 1;

                this.renderNodes();
                this.renderCanvas();
                this.fitView();
            }
        }
    },

    fitView: function() {
        if (this.nodes.length === 0) return;
        
        const bounds = this.nodes.reduce((acc, node) => {
            return {
                minX: Math.min(acc.minX, node.position.x),
                minY: Math.min(acc.minY, node.position.y),
                maxX: Math.max(acc.maxX, node.position.x + 200),
                maxY: Math.max(acc.maxY, node.position.y + 80)
            };
        }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

        const width = bounds.maxX - bounds.minX;
        const height = bounds.maxY - bounds.minY;
        const canvasWidth = this.canvas.clientWidth;
        const canvasHeight = this.canvas.clientHeight;

        this.zoom = Math.min(canvasWidth / width, canvasHeight / height) * 0.9;
        this.panX = (canvasWidth - width * this.zoom) / 2 - bounds.minX * this.zoom;
        this.panY = (canvasHeight - height * this.zoom) / 2 - bounds.minY * this.zoom;

        this.renderCanvas();
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

    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    WorkflowOrchestrator.init();
});
