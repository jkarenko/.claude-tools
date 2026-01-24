---
name: pof-phase-outline
description: Display the POF phase structure. Shows all phases and their sub-steps.
---

# POF Phase Outline

Display the complete POF phase structure for reference.

## Output

```markdown
## POF Phase Structure

### PHASE 0: INITIALIZATION
├── 0.1 Project state detection (green-field/existing/integration)
├── 0.2 Requirements gathering
├── 0.3 Source priority setup
└── 0.4 Phase outline presentation → **CHECKPOINT**

### PHASE 1: ARCHITECTURE
├── 1.1 Stack validation
├── 1.2 Infrastructure discussion
├── 1.3 Architecture proposal
├── 1.4 Alternatives presentation (if concerns)
└── 1.5 Architecture approval → **CHECKPOINT** + ADR

### PHASE 2: DESIGN
├── 2.1 UX/accessibility patterns
├── 2.2 Component structure
├── 2.3 Data flow design
└── 2.4 Design approval → **CHECKPOINT** + ADR

### PHASE 3: SCAFFOLDING (if needed)
├── 3.1 Project initialization
├── 3.2 Dependency installation
├── 3.3 Configuration setup
└── 3.4 Scaffold verification → ADR + COMMIT

### PHASE 4: IMPLEMENTATION
├── 4.1 Implementation planning
├── 4.2 Iterative development cycles
│   ├── Code generation
│   ├── Test running (parallel)
│   ├── Git commits (parallel)
│   └── Progress reporting
├── 4.3 Security review
└── 4.4 Implementation approval → **CHECKPOINT**

### PHASE 5: DEPLOYMENT
├── 5.1 Environment configuration
├── 5.2 Deployment plan review → **CHECKPOINT**
├── 5.3 Deployment execution
├── 5.4 Verification
└── 5.5 Rollback documentation → ADR

### PHASE 6: HANDOFF
├── 6.1 Documentation finalization
├── 6.2 ADR index generation
└── 6.3 Summary presentation

---

**Legend:**
- **CHECKPOINT**: Requires user approval to proceed
- **ADR**: Architecture Decision Record written
- **COMMIT**: Git commit created
```

## With Current Position

If `.claude/context/state.json` exists, show current position:

```markdown
## POF Phase Structure

### PHASE 0: INITIALIZATION ✓
...

### PHASE 1: ARCHITECTURE ✓
...

### PHASE 2: DESIGN ◀ CURRENT
├── 2.1 UX/accessibility patterns ✓
├── 2.2 Component structure ✓
├── 2.3 Data flow design ← In progress
└── 2.4 Design approval

### PHASE 3: SCAFFOLDING
...
```

Use ✓ for completed, ◀ for current phase, ← for current step.
