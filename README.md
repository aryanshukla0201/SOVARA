# Multimodal AI Workbench MVP

## Overview

This project is a modular, evidence-first multimodal AI workbench built around deterministic routing, tool control, and traceable execution. It is intentionally not designed as an unrestricted autonomous agent. Instead, the workflow follows a strict pattern:

1. Input detection
2. Task classification by Qwen3
3. Structured task-state validation
4. Deterministic Python routing
5. Tool execution only through approved routes
6. Evidence aggregation
7. Complexity gating
8. Synthesis only when justified
9. Verification and repair
10. Deliverable generation
11. Full traceability output

## Architecture at a glance

```text
USER
  |
  v
INPUT LAYER
  |
  v
TASK ANALYZER (Qwen3 8B)
  |
  v
TASK STATE
  |
  v
POLICY ROUTER (Python / LangGraph)
  |----------------------------------
  |        |                         |
  v        v                         v
DOCUMENT  DATA                    VISION
TOOL      TOOL                   TOOL
(PyMuPDF) (Pandas)             (Gemma 3)
  |        |                         |
  +--------+-------------------------+
           |
           v
       RESULT STATE
           |
           v
      COMPLEXITY GATE
           |---------------------------
           |                           |
           v                           v
      DIRECT OUTPUT               SYNTHESIS
                                      |
                                      v
                                   Qwen3 8B
                                      |
                                      v
                                  VERIFIER
                                      |
                             PASS / FAIL
                                      |
                                      v
                                   REPAIR
                                      |
                                      v
                              DELIVERABLE TOOL
                                      |
                                      v
                                DOCX / XLSX / PPTX
```

## Core workflow principles

- The LLM classifies and interprets the user task.
- Python and LangGraph decide routing, tool permissions, execution, and verification.
- Tools execute only through deterministic policy decisions.
- Evidence is preserved with source metadata and trace IDs.
- Synthesis is skipped when deterministic results already satisfy the request.
- All important outputs are verified before delivery.

## Project structure

```text
project_root/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── logging.py
│   ├── models/
│   │   ├── base.py
│   │   ├── qwen_adapter.py
│   │   ├── gemma_adapter.py
│   │   └── model_factory.py
│   ├── state/
│   │   ├── evidence.py
│   │   ├── result_state.py
│   │   ├── task_state.py
│   │   └── workflow_state.py
│   ├── workflow/
│   │   ├── graph.py
│   │   └── nodes/
│   │       ├── input_processor.py
│   │       ├── task_analyzer.py
│   │       ├── policy_router.py
│   │       ├── document_node.py
│   │       ├── data_node.py
│   │       ├── vision_node.py
│   │       ├── reasoning_node.py
│   │       ├── complexity_gate.py
│   │       ├── synthesis.py
│   │       ├── verifier.py
│   │       ├── repair.py
│   │       └── deliverable.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── data/
│   │   │   ├── csv_analyzer.py
│   │   │   ├── excel_analyzer.py
│   │   │   └── python_executor.py
│   │   ├── documents/
│   │   │   ├── pdf_parser.py
│   │   │   ├── document_loader.py
│   │   │   └── retriever.py
│   │   └── vision/
│   │       └── image_analyzer.py
│   ├── verification/
│   │   ├── json_validator.py
│   │   ├── citation_validator.py
│   │   ├── numeric_validator.py
│   │   ├── report_validator.py
│   │   └── claim_validator.py
│   ├── deliverables/
│   │   ├── docx_generator.py
│   │   ├── xlsx_generator.py
│   │   └── pptx_generator.py
│   ├── services/
│   │   ├── traceability_service.py
│   │   └── evidence_service.py
│   ├── prompts/
│   │   ├── task_analyzer.py
│   │   ├── synthesis.py
│   │   └── verifier.py
│   ├── tests/
│   │   ├── test_input_processor.py
│   │   ├── test_router.py
│   │   ├── test_data_analysis.py
│   │   ├── test_document_analysis.py
│   │   └── test_verification.py
│   └── ui/
│       └── app.py
├── data/
│   ├── uploads/
│   └── processed/
├── outputs/
├── .env.example
├── requirements.txt
├── README.md
└── venv/
```

## Installation

1. Create or activate the project virtual environment.
2. Install requirements:

```bash
python -m pip install -r requirements.txt
```

3. Copy the environment template:

```bash
copy .env.example .env
```

## Environment configuration

Set the following values as needed:

```env
MODEL_PROVIDER=ollama
QWEN_MODEL=qwen3:8b
GEMMA_MODEL=gemma3:latest
OLLAMA_BASE_URL=http://localhost:11434
UPLOAD_DIRECTORY=data/uploads
OUTPUT_DIRECTORY=outputs
MAX_REPAIR_ATTEMPTS=3
```

## Running local models

This MVP is provider-independent, but Ollama is the default implementation.

Start Ollama locally and pull the required models:

```bash
ollama pull qwen3:4b
ollama pull gemma3:latest
```

Then set `OLLAMA_BASE_URL` to the local server if needed.

## Running backend

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running frontend

```bash
streamlit run app/ui/app.py
```

## Example API requests

### Analyze a document plus CSV

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "user_query=Analyze this maintenance report and sensor dataset. Tell me if there is evidence of equipment failure and generate a report." \
  -F "requested_deliverable=report" \
  -F "files=@maintenance_report.pdf" \
  -F "files=@sensor_data.csv"
```

### Check status

```bash
curl "http://localhost:8000/analysis/req_123"
```

### Download a generated file

```bash
curl -OJ "http://localhost:8000/download/req_123/Maintenance_Report.docx"
```

## Demo scenario

The MVP is designed to support the example workflow:

- User says: "Analyze this maintenance report and sensor dataset. Tell me if there is evidence of equipment failure and generate a report."
- Inputs: maintenance report PDF, sensor CSV
- Task analyzer identifies equipment analysis, document analysis, data analysis, and report generation
- Deterministic router triggers document and data routes
- Evidence is aggregated and passed to the complexity gate
- Synthesis is triggered only if multiple evidence sources require interpretation
- Verification checks evidence support and workflow constraints
- A DOCX report is generated with traceability

## How to add new tools

1. Implement the tool in a module under the relevant `app/tools` subpackage.
2. Keep the tool deterministic and evidence-producing.
3. Register its metadata in `app/tools/registry.py`.
4. Add routing permission logic in the policy router.
5. Add tests covering success and failure conditions.

## How to add new models

1. Create a new adapter implementing the interface in `app/models/base.py`.
2. Register it in `app/models/model_factory.py`.
3. Use the adapter through the workflow nodes rather than calling a provider directly.
4. Keep provider-specific logic isolated from routing and state management.

## Known MVP limitations

- Ollama is the primary supported provider, but the adapter layer is provider-agnostic.
- Vision support is scaffolded but not yet fully extended beyond the MVP pattern.
- PDF and CSV support is robust for the first phase; DOCX/XLSX/PPTX deliverables are generated but may need additional schema tuning for large enterprise reports.
- The synthesis path uses heuristic gating and deterministic evidence-first design rather than an unrestricted autonomous loop.

## Verification and testing

The project includes reusable validation checks for:

- input modality detection
- task-state validation
- routing decisions
- CSV calculations
- evidence metadata preservation
- complexity gate logic
- JSON verification
- numeric verification
- repair attempt limits

Run tests with:

```bash
python -m pytest app/tests -q
```
