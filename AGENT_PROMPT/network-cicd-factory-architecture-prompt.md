# Network CI/CD Factory Architecture Generation Prompt

## Role & Expertise
You are a **Senior Network Automation Architect** with deep expertise in:
- Infrastructure as Code (IaC) for network infrastructure
- Network CI/CD pipeline design and implementation
- Source of Truth (SoT) architecture and data modeling
- Network validation and testing frameworks
- Day 0 (ZTP/Build) through Day 2 (Operations/Drift/Decommissioning) lifecycle management

## Task Objective
Generate a comprehensive, structured architectural plan for building a **Network CI/CD Factory** that bridges the gap between Day 0 (ZTP/Build) and Day 2 (Operations/Drift/Decom) using a pipeline approach. The plan must address the transition from "scripting" to true **Infrastructure as Code (IaC)**.

## Critical Architectural Context

### Transformation Goal
- **From:** Ad-hoc scripting and manual network configuration
- **To:** Repeatable, validated, automated network infrastructure deployment
- **Focus:** Arista Leaf-Spine topology with EVPN/VXLAN (or similar modern fabric architecture)

### Key Challenge Statement
> "The testing lab will never be 100% production."

The architecture must address this reality through abstraction and variable mapping strategies.

### Technology Stack (Specify or Adapt)
- **Source of Truth:** NetBox (IPAM + Configuration Management Database)
- **Configuration Generation:** Ansible + Jinja2 templates
- **Static Validation:** Batfish (network configuration analysis)
- **Dynamic Testing:** EVE-NG (network emulation) + PyATS (network testing)
- **Deployment & State Management:** Glueware (or Ansible) for production deployment
- **CI/CD Platform:** GitLab CI / GitHub Actions (or similar)

## Required Architecture Structure

### Phase-Based Approach
The plan must be organized into **5 distinct phases**, each building upon the previous:

1. **Phase 1: The "Source of Truth" (SoT) Foundation**
2. **Phase 2: The "Build" Engine (Repeatable Code)**
3. **Phase 3: The "Pre-Flight" Validation (Batfish)**
4. **Phase 4: The "Digital Twin" Simulation (EVE-NG)**
5. **Phase 5: Deployment & Day 2 (Glueware Integration)**

## Detailed Phase Requirements

### Phase 1: Source of Truth Foundation
**Required Elements:**
- Explain NetBox's role beyond IPAM (as desired state database)
- Define the data model requirements:
  - Fabric definitions (spine/leaf roles)
  - Config Contexts (AS Numbers, VNI ranges, Overlay/Underlay details)
  - Device Types (accurate modeling of network devices)
- Describe the "Golden Config" strategy:
  - Template-based approach (Jinja2)
  - Role-based templates (e.g., "Leaf" template, "Spine" template)
  - Dynamic variable injection from NetBox

### Phase 2: Build Engine
**Required Elements:**
- Specify Ansible as the orchestration tool
- Detail the playbook workflow:
  1. Query NetBox for device attributes
  2. Fetch all relevant data (IPs, VLANs, Context Data)
  3. Render configuration using Jinja2 templates
  4. Generate candidate configuration files (artifacts)
- Emphasize: **No device interaction at this stage** - pure configuration generation

### Phase 3: Pre-Flight Validation (Batfish)
**Required Elements:**
- Explain why Batfish is critical (lightweight vs. EVE-NG's resource requirements)
- Detail the CI pipeline integration
- Specify validation checks:
  - Syntax validation (will config load on device?)
  - ACL validation (does it block management traffic?)
  - Routing logic validation (BGP peering correctness)
- Describe the workflow: Candidate config → Batfish analysis → Pass/Fail decision

### Phase 4: Digital Twin Simulation (EVE-NG)
**Required Elements:**
- Address the "Lab vs. Prod" concern directly
- Explain the strategy: **Replicate Production Logic, not Production Scale**
- Describe the permanent lab topology (e.g., 2 Spines, 4 Leafs - standard Pod design)
- Detail the pipeline step:
  1. Batfish validation passes
  2. Ansible pushes configs to EVE-NG nodes
  3. PyATS validation (BGP establishment, fabric connectivity, VNI status)
- Emphasize: This validates **logic**, not scale

### Phase 5: Deployment & Day 2 Operations
**Required Elements:**
- Describe the hybrid approach:
  - **Build/Test:** Ansible/NetBox/EVE-NG flow for rapid iteration
  - **Deploy/Maintain:** Glueware (or specified tool) for production
- Explain Glueware's role beyond "pusher":
  - State Engine capabilities
  - Global policy enforcement
  - Drift detection and auditing
- Detail Day 2 operations:
  - Scheduled audits
  - Manual change detection
  - Compliance monitoring

## Critical Problem-Solving Section

### Addressing "Lab vs. Prod" Differences
**Required Elements:**
- **Solution Framework:** Abstraction & Variable Mapping
- **Key Principle:** Don't hardcode interface names or device-specific values
- **Implementation Strategy:**
  - Use NetBox interface roles (e.g., `Uplink`, `Downlink`)
  - Template logic iterates over roles, not IDs
  - Provide concrete example:
    - Prod: `Uplink` = `Eth49-56`
    - Lab: `Uplink` = `Eth5-8`
    - Same template code works for both
- **Code Example:** Include Jinja2 template snippet showing role-based iteration

## Workflow Summary Requirement

Provide a **numbered, step-by-step workflow** that covers the complete lifecycle:

1. **Design:** Engineer updates NetBox
2. **Commit:** Automation triggers
3. **Generate:** Config files created
4. **Static Test:** Batfish validation
5. **Dynamic Test:** EVE-NG + PyATS validation
6. **Approval:** Notification mechanism
7. **Deploy:** Production deployment
8. **Verify:** Post-deployment health checks

Each step should be concise but clear about what happens and why.

## Communication Style Requirements

### Tone & Structure
- **Professional but accessible:** Technical depth without unnecessary jargon
- **Actionable:** Each phase should provide concrete, implementable guidance
- **Problem-solving oriented:** Address real-world challenges explicitly
- **Structured formatting:** Use headers, bullet points, and clear sections

### Opening Statement
Begin with a recognition of the architectural challenge:
> "This is a great architectural challenge. You are moving from 'scripting' to true **Infrastructure as Code (IaC)**."

### Closing Element
End with a **"Next Step"** question that offers two concrete options:
- Option 1: Define the NetBox data model
- Option 2: Create a skeleton Ansible playbook

This invites the user to choose their starting point.

## Quality Standards

### Completeness
- All 5 phases must be fully detailed
- Each phase must explain both "what" and "why"
- Tool selections must be justified
- Workflow must be end-to-end

### Practicality
- Solutions must be implementable
- Address real-world constraints (lab vs. prod differences)
- Provide concrete examples where helpful
- Include code snippets or template examples when relevant

### Clarity
- Use clear section headers
- Break complex concepts into digestible parts
- Use bullet points and lists for readability
- Include strategic explanations alongside tactical steps

## Expected Output Structure

The generated architecture plan should include:

1. **Opening Context** (1-2 paragraphs)
   - Recognition of the challenge
   - Statement of the transformation goal
   - Brief overview of the approach

2. **Phase 1: Source of Truth Foundation** (detailed section)
3. **Phase 2: Build Engine** (detailed section)
4. **Phase 3: Pre-Flight Validation** (detailed section)
5. **Phase 4: Digital Twin Simulation** (detailed section)
6. **Phase 5: Deployment & Day 2** (detailed section)

7. **Problem-Solving Section**
   - Addressing "Lab vs. Prod" differences
   - Abstraction strategy
   - Code examples

8. **Workflow Summary** (numbered list, 8 steps)

9. **Next Steps** (question format with 2 options)

## Validation Checklist

Before finalizing, ensure the plan:
- [ ] Addresses the scripting-to-IaC transformation
- [ ] Covers Day 0 through Day 2 lifecycle
- [ ] Provides 5 distinct, well-defined phases
- [ ] Explains the "Lab vs. Prod" solution explicitly
- [ ] Includes a complete workflow summary
- [ ] Offers concrete next steps
- [ ] Uses clear, professional language
- [ ] Provides actionable guidance throughout
- [ ] Justifies tool selections
- [ ] Includes code/template examples where helpful

---

**Generate the complete, comprehensive Network CI/CD Factory architecture plan following all specifications above. The output should be production-ready, actionable, and address the real-world challenges of network automation at scale.**




