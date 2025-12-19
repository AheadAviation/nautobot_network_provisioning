# UI/UX Design Strategy: The "Automation Hub" Approach

The current UI approach of using fragmented tables (Tasks, Implementations, Workflows, Forms) is being replaced by a **Hub-based architecture**. This ensures that "clicking on stuff" always provides context, actionable next steps, and a clear path from design to execution.

## 1. Core UX Principles
- **No Dead Ends**: Every object view must answer "What can I do next?".
- **Contextual Connectivity**: Link from physical (DCIM) to logical (Automation) seamlessly.
- **Visual Authoring**: Move away from row-based editing to IDE/Designer views.
- **Status at a Glance**: Don't make the user click to see if a Task is implemented or if a Workflow is failing.

---

## 2. Navigation Structure (The Sidebar)

The sidebar is simplified into three distinct zones:

### **A. SELF-SERVICE (Operational Focus)**
*   **Portal**: The "front door" for non-engineers. Simple service cards.
*   **My Requests**: Track status of your own executions.

### **B. THE CATALOG (Engineering Focus)**
*   **Automation Hub**: The unified workspace for building and managing everything.
*   **Execution History**: Auditable logs of all runs.

### **C. SYSTEM (Administrator Focus)**
*   **Providers**: Driver & credential management.
*   **Git Sync**: Repository health and manual sync.

---

## 3. The "Automation Hub" (Unified Workspace)

Instead of separate menus, the Hub provides a nested, interactive tree/grid view:

- **Task Catalog (The "What")**:
    - Click a Task → Shows description, input variables, and **nested Implementations**.
    - Action: "Add Implementation" or "Run Now" (opens preview).
- **Implementations (The "How")**:
    - Direct link to **Template IDE**.
    - No more standard forms for code.
- **Workflows (The "Orchestration")**:
    - Direct link to **Workflow Designer**.
    - Shows associated Request Forms immediately.

---

## 4. The "Form Designer" (New Standard)

Request Forms are no longer managed via the "Request Form Fields" table. The **Request Form Detail View** is the designer:
- **Live Preview Pane**: See the form change as you edit fields.
- **Smart Helpers**: Dropdowns for "Building", "VLAN by Tag", etc., hide technical complexity.
- **Consolidated Actions**: Reorder, edit, and test in one single screen.

---

## 5. Seamless DCIM Integration (The "Wiring")

To fix the "goes nowhere" feeling, the app injects context into core Nautobot objects:

- **On a Location (Building/Site)**: 
    - Button: "Provision New Service" → Directs to Portal with Location pre-selected.
- **On an Interface/Port**:
    - Button: "Change VLAN/Service" → Directs to Portal with Device/Port pre-selected.
- **On a Device**:
    - Button: "Run Maintenance Task" → Shows only Tasks compatible with this platform.

---

## 6. Execution & Monitoring

The Execution view is upgraded from a static table to a "Live Terminal" experience:
- **Progress Stepper**: Visual breadcrumbs of where the workflow is (Step 1 of 5).
- **Log Stream**: Real-time output from Netmiko/Napalm/Ansible.
- **Rendered Output**: View the actual J2 config sent to the device side-by-side with the live log.
- **Diff View**: Automatic "Before vs After" configuration comparison.

---

## 7. IDE Experience (GraphiQL Style)

The Template IDE remains the primary tool for J2, but is enhanced with:
- **Schema Explorer**: Sidebar showing available variables from the Task definition.
- **Live Device Context**: Select a real device to pull its facts/GraphQL data into the preview pane.
- **One-Click Save**: Instantly updates the Task Implementation without leaving the IDE.
