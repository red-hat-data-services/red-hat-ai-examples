# Red Hat AI Examples Style Guide

Standards for creating consistent, discoverable examples in the red-hat-ai-examples repository.

---

## File Naming

### Directories

- Use lowercase with hyphens: `knowledge-tuning`, `model-compression`
- For multi-module examples, use numbered prefixes: `00_Setup`, `01_Processing`

### Files

| Type | Convention | Example |
|------|------------|---------|
| Notebooks | Descriptive with underscores | `Base_Model_Evaluation.ipynb` |
| Python scripts | snake_case | `knowledge_generation_pipeline.py` |
| Module READMEs | `{Module_Name}_README.md` | `01_Base_Model_Evaluation_README.md` |
| Metadata | Always `example.yaml` | `example.yaml` |

### Forbidden

- Spaces in filenames
- Generic names (`test.ipynb`, `example.py`, `temp.py`)
- camelCase for Python files

---

## Directory Structure

### Required Files

Every example MUST have:

- `example.yaml` - Metadata file
- `README.md` - Documentation
- `pyproject.toml` - Dependencies (if required)
- `.env.example` - Environment template (if env vars needed)

### Patterns

**Simple Example:**

```text
examples/llmcompressor/
├── example.yaml
├── README.md
├── workbench_example.ipynb
├── pyproject.toml
└── .env.example
```

**Multi-Module Example:**

```text
examples/knowledge-tuning/
├── example.yaml
├── README.md
├── .env.example
├── 00_Setup/
│   ├── 00_Setup_README.md
│   ├── Setup.ipynb
│   └── pyproject.toml
├── 01_Base_Model_Evaluation/
│   └── ...
```

---

## README Structure

### Required Sections

1. **Title** - Clear, descriptive (matches `metadata.title`)
2. **Overview** - What, why, and key technologies (2-3 paragraphs)
3. **Prerequisites** - RHOAI version, hardware, credentials, prior knowledge
4. **Setup** - Step-by-step environment preparation
5. **Usage** - How to run the example
6. **Expected Outcomes** - What success looks like
7. **Hardware Requirements** - Minimum and recommended specs

### Optional Sections

- Troubleshooting
- References

### Module READMEs (Multi-Module)

Required sections:

1. Title
2. Navigation (previous/next links)
3. Overview
4. Prerequisites
5. Procedure
6. Verification
7. Next Steps

---

## Jupyter Notebooks

### Required First Cells

1. **Title and Description** (Markdown) - Name, purpose, prerequisites
2. **Imports** (Code) - All imports in one cell with `load_dotenv()`

### Organization

- Group code into logical sections with Markdown headers
- Keep cells focused on single tasks
- Add explanatory text before complex code
- Clear outputs before committing (handled by `nbstripout`)

### Preserving Output

Add `keep_output` tag only for:

- Final evaluation metrics
- Important visualizations
- Summary tables

---

## Environment Variables

### .env.example Format

```bash
# Model Configuration
STUDENT_MODEL_NAME=RedHatAI/Llama-3.1-8B-Instruct

# API Configuration (required)
# HF_TOKEN=your_token_here

# Training Configuration
NUM_EPOCHS=3
BATCH_SIZE=8
```

### Best Practices

- Group related variables with comments
- Comment out sensitive variables (tokens, keys)
- Provide safe defaults where possible
- Never commit actual `.env` files
