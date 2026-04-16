# Logging System Architecture Graphs

This directory contains all architecture diagrams for the Logging System in both Graphviz (`.dot`) and Mermaid (`.mmd`) formats.

## Directory Structure

```
graphs/
├── README.md                          # This file
├── 02_SystemOverview.dot              # High-level architecture
├── 02_SystemOverview.mmd
├── L1_Models_ClassDiagram.dot         # Layer 1: Models
├── L1_Models_ClassDiagram.mmd
├── L2_Ports_Hierarchy.dot             # Layer 2: Ports
├── L2_Ports_Hierarchy.mmd
├── L3_Services_Dependencies.dot        # Layer 3: Services
├── L3_Services_Dependencies.mmd
├── L4_Composables_Interactions.dot    # Layer 4: Composables
├── L4_Composables_Interactions.mmd
├── Flow_LogSubmission.dot             # Sequence: Log submission
├── Flow_LogSubmission.mmd
├── Flow_ProfileActivation.dot          # Sequence: Profile activation
├── Flow_ProfileActivation.mmd
├── Flow_DispatchRound.dot             # Sequence: Dispatch round
├── Flow_DispatchRound.mmd
├── DataFlow_Pipeline.dot               # Input → Storage → Output
├── DataFlow_Pipeline.mmd
├── Catalog_Architecture.dot           # Provider catalog system
├── Catalog_Architecture.mmd
├── Threading_Model.dot                # Thread safety modes
├── Threading_Model.mmd
├── CLI_Architecture.dot               # CLI command structure
├── CLI_Architecture.mmd
└── Port_Hierarchy_Complete.dot         # Complete port interfaces
├── Port_Hierarchy_Complete.mmd
```

## Rendering Instructions

### Graphviz (DOT files)

**Prerequisites:**
```bash
# Install Graphviz (if not already installed)
# macOS
brew install graphviz
# Linux (Ubuntu/Debian)
sudo apt-get install graphviz
# Windows
# Download from https://graphviz.org/download/
```

**Render to SVG:**
```bash
# Single file
dot -Tsvg 02_SystemOverview.dot -o 02_SystemOverview.svg

# Batch convert all .dot files
for f in *.dot; do dot -Tsvg "$f" -o "${f%.dot}.svg"; done
```

**Render to PNG:**
```bash
dot -Tpng 02_SystemOverview.dot -o 02_SystemOverview.png
```

**Other formats:**
```bash
dot -Tpdf 02_SystemOverview.dot -o 02_SystemOverview.pdf
dot -Teps 02_SystemOverview.dot -o 02_SystemOverview.eps
dot -Tsvg:cairo 02_SystemOverview.dot -o 02_SystemOverview.svg
```

### Mermaid (MMD files)

**Option 1: Mermaid CLI**
```bash
# Install
npm install -g @mermaid-js/mermaid-cli

# Render single file
mmdc -i 02_SystemOverview.mmd -o 02_SystemOverview.svg
mmdc -i 02_SystemOverview.mmd -o 02_SystemOverview.png

# Batch convert
for f in *.mmd; do mmdc -i "$f" -o "${f%.mmd}.svg"; done
```

**Option 2: GitHub/GitLab**
- Upload `.mmd` files directly to GitHub/GitLab
- They will be automatically rendered in markdown files

**Option 3: Mermaid Live Editor**
- Visit https://mermaid.live
- Paste contents of `.mmd` file
- Export to SVG/PNG

**Option 4: VS Code Extension**
- Install "Mermaid Markdown Syntax Highlighting" or similar extension
- Preview markdown files containing mermaid blocks

## Graph Categories

| Category | Files | Description |
|----------|-------|-------------|
| **System Overview** | `02_SystemOverview.*` | High-level 4-layer architecture |
| **Layer 1: Models** | `L1_Models_ClassDiagram.*` | LogRecord, LogEnvelope, Schema |
| **Layer 2: Ports** | `L2_Ports_Hierarchy.*`, `Port_Hierarchy_Complete.*` | Interface contracts |
| **Layer 3: Services** | `L3_Services_Dependencies.*` | Service orchestration |
| **Layer 4: Composables** | `L4_Composables_Interactions.*` | Adapters, handlers, resolvers |
| **Sequence Flows** | `Flow_*.*` | Interaction sequences |
| **Data Flow** | `DataFlow_Pipeline.*` | Input → Output pipeline |
| **Catalogs** | `Catalog_Architecture.*` | Provider catalog system |
| **Threading** | `Threading_Model.*` | Concurrency model |
| **CLI** | `CLI_Architecture.*` | Command structure |

## Color Legend

| Color | Layer/Category |
|-------|---------------|
| `#E3F2FD` (Blue) | User/API Layer, Models |
| `#E8F5E9` (Green) | Services Layer |
| `#FFF3E0` (Orange) | Ports Layer, Configuration |
| `#FCE4EC` (Pink) | Data Models, Catalogs |
| `#E1F5FE` (Light Blue) | Containers, Storage |
| `#F3E5F5` (Purple) | Adapters, Composables |
| `#E0F2F1` (Teal) | Utilities, State Store |
| `#FFCCBC` (Peach) | Special components |

## Maintenance

When updating architecture:

1. Update the `.dot` files for precise Graphviz rendering
2. Update the corresponding `.mmd` files for GitHub/GitLab compatibility
3. Update the main documentation to reference the new files
4. Regenerate SVG/PNG assets if needed

## License

These graph files are part of the Logging System architecture documentation and are subject to the same license as the parent project.
