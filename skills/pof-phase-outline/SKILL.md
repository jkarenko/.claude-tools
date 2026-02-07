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
├── 0.2 Git init + requirements gathering
├── 0.3 Context setup + initial commit
└── 0.4 Phase outline presentation → **CHECKPOINT**

### PHASE 1: ARCHITECTURE
├── 1.1 Stack validation
├── 1.2 Infrastructure discussion
├── 1.3 Architecture proposal
└── 1.5 Architecture approval → **CHECKPOINT** + ADR + COMMIT

### PHASE 2: DESIGN
├── 2.1 UX/accessibility patterns
├── 2.2 Component & data flow design
└── 2.4 Design approval → **CHECKPOINT** + ADR + COMMIT

### PHASE 3: SCAFFOLDING (if green-field)
├── 3.1 Project initialization
├── 3.2 Dependencies & configuration
└── 3.4 Scaffold verification → COMMIT

### PHASE 4: IMPLEMENTATION
├── 4.1 Implementation planning → **CHECKPOINT**
├── 4.2 Development cycles (TDD)
│   └── Per feature: write test → implement → run test → COMMIT
├── 4.2.5 Integration tests (optional, separate concern)
├── 4.3 Security review
└── 4.4 Implementation approval → **CHECKPOINT**

### PHASE 5: DEPLOYMENT
├── 5.1 Environment configuration
├── 5.2 Deployment plan review → **CHECKPOINT**
├── 5.3 Deployment execution
├── 5.4 Verification
└── 5.5 Rollback documentation → ADR + COMMIT

### PHASE 6: HANDOFF
├── 6.1 Documentation finalization
├── 6.2 ADR index generation
└── 6.3 Summary presentation → final COMMIT

---

**Legend:**
- **CHECKPOINT**: Requires user approval to proceed
- **ADR**: Architecture Decision Record written
- **COMMIT**: Conventional commit created (feature-level granularity)
```

## With Current Position

If an active session exists (`.claude/context/.active-session`), read the session file and show current position:

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
