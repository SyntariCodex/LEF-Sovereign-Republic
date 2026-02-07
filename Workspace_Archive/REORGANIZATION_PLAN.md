# Workspace Reorganization Plan

## Current Structure
```
LEF Ai/
├── fulcrum/          (Fulcrum trading system)
├── snw/              (SNW RFR system - minimal)
├── docs/             (Shared documentation)
├── [various .md files] (LEF Ai documentation)
└── [various .docx files] (Original documents)
```

## Proposed Structure
```
LEF Ai/
├── fulcrum/          (Fulcrum trading system - stays as is)
│   └── [all fulcrum files]
│
├── lef-ai/           (LEF Ai project files - NEW)
│   ├── docs/
│   │   ├── whitepapers/
│   │   ├── protocols/
│   │   └── github/
│   ├── README.md
│   ├── CLAUDE_INTRODUCTORY_MESSAGE.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── [other LEF Ai specific files]
│
├── snw/              (SNW project - expand)
│   ├── rfr_synapse.py
│   ├── docs/
│   │   └── SOUTHERN_NEVADA_WILDLANDS.md (move from docs/whitepapers)
│   └── [SNW specific files]
│
└── shared/           (Shared resources - NEW)
    └── [files used by multiple projects]
```

## Files to Move

### To `lef-ai/`:
- `CLAUDE_INTRODUCTORY_MESSAGE.md`
- `COMPLETION_SUMMARY.md`
- `EXECUTION_ANALYSIS.md`
- `IMPLEMENTATION_PLAN.md`
- `SETUP_STATUS.md`
- `SIMPLE_SETUP_GUIDE.md`
- `SUMMARY.md`
- `TASKS.md`
- `README.md` (if LEF Ai specific)
- `docs/` folder (whitepapers, protocols, github)
- `dashboard_index.html` (if LEF Ai specific)
- `.docx` files (original documents)

### To `snw/`:
- `docs/whitepapers/SOUTHERN_NEVADA_WILDLANDS.md`
- `Southern Nevada Wildlands (SNW) - White Paper.docx`
- Expand `snw/` folder structure

### Keep in Root:
- `fulcrum/` (stays as is - self-contained)
- `snw/` (stays as is)

## Path Updates Needed

### Python Files:
- `fulcrum/advanced_backtest.py`: Uses relative paths (should be fine)
- `fulcrum/main.py`: Uses `Path(__file__).parent` (should be fine)
- All fulcrum agents use relative imports (should be fine)

### Database Paths:
- `fulcrum.db` is in `fulcrum/` folder (stays)
- All references use relative paths (should be fine)

### Config Files:
- `fulcrum/config/` stays in fulcrum folder (should be fine)

## Action Plan

1. Create `lef-ai/` folder
2. Move LEF Ai specific files
3. Move `docs/` to `lef-ai/docs/`
4. Expand `snw/` structure
5. Move SNW specific files
6. Test that all paths still work
7. Update any broken references

## Risk Assessment

**Low Risk:**
- Fulcrum is self-contained with relative paths
- Python imports use `Path(__file__).parent` (works regardless of location)
- Database paths are relative

**Medium Risk:**
- Documentation references may need updating
- Some scripts might reference old paths

**Mitigation:**
- Test after moving
- Update any broken references
- Keep backups
