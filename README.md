# SOVARA

### Sovereign Orchestration for Verified AI Reasoning & Automation

SOVARA is a modular multimodal AI analysis system designed to process different types of inputs, select appropriate analysis capabilities, execute specialized tools, reason over the resulting evidence, verify the generated answer, and produce a structured deliverable.

Instead of treating an LLM as an unrestricted autonomous agent, SOVARA uses a controlled workflow in which **LLMs handle interpretation and reasoning while deterministic application logic controls routing, tools, state, verification, and execution flow.**

---

## Overview

SOVARA is designed around an evidence-first and policy-controlled workflow.

The current MVP supports:

- Natural-language task analysis using Qwen3
- PDF/document analysis
- CSV data analysis
- Deterministic route selection
- Evidence collection and traceability
- Reasoning over extracted results
- Complexity-based synthesis decisions
- Output verification
- Repair/retry handling
- DOCX report generation
- Local LLM execution through Ollama

The architecture is designed to be extended with additional modalities, tools, models, retrieval systems, and deployment infrastructure.

---

## Core Workflow

```text
USER INPUT
     |
     v
INPUT PROCESSOR
     |
     v
TASK ANALYZER
(Qwen3 4B)
     |
     v
STRUCTURED TASK STATE
     |
     v
POLICY ROUTER
(Python / LangGraph)
     |
     +-------------------+-------------------+
     |                   |                   |
     v                   v                   v
 DOCUMENT              DATA              VISION
  ROUTE                ROUTE              ROUTE
     |                   |                   |
     v                   v                   v
 PDF PARSER          CSV ANALYZER       IMAGE ANALYZER
 RETRIEVER           / DATA TOOLS        / VISION
     |                   |                   |
     +-------------------+-------------------+
                         |
                         v
                  RESULT AGGREGATION
                         |
                         v
                  COMPLEXITY GATE
                    /         \
                   /           \
                  v             v
             DIRECT PATH     SYNTHESIS
                               |
                               v
                           Qwen3 4B
                               |
                  +------------+
                  |
                  v
             FINAL ANSWER
                  |
                  v
               VERIFIER
              /        \
           PASS         FAIL
            |             |
            |             v
            |           REPAIR
            |             |
            +-------------+
                  |
                  v
             DELIVERABLE
                  |
                  v
              DOCX REPORT
