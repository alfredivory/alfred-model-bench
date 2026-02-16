# Alfred Model Bench — Specification

## Overview
Custom AI model benchmark tailored to OpenClaw/Alfred workflows. Tests models via OpenRouter (cloud) and Ollama (local) against real-world scenarios, scores them, and produces a web dashboard with results.

## Architecture

```
alfred-model-bench/
├── README.md
├── requirements.txt
├── config.yaml              # Models to test, API keys, settings
├── scenarios/               # Test scenario definitions (YAML)
│   ├── tool_orchestration.yaml
│   ├── instruction_following.yaml
│   ├── email_triage.yaml
│   ├── judgment_calls.yaml
│   ├── structured_output.yaml
│   └── long_context.yaml
├── src/
│   ├── runner.py            # Main benchmark runner
│   ├── providers/
│   │   ├── openrouter.py    # OpenRouter API client
│   │   └── ollama.py        # Ollama local client
│   ├── evaluator.py         # Scoring engine (automated checks)
│   ├── external.py          # External benchmark data fetcher
│   └── report.py            # Generate results JSON for dashboard
├── results/                 # Benchmark run outputs (JSON)
├── dashboard/               # Static web dashboard
│   ├── index.html
│   ├── app.js
│   └── style.css
└── run.py                   # CLI entry point
```

## Test Scenarios (6 categories)

### 1. Tool Orchestration
- Prompt: "Check my calendar for today and create a Things task for each meeting with prep notes"
- Tests: correct multi-step tool call generation, parameter accuracy, sequencing
- Scoring: JSON schema validation of tool calls, correct ordering, no hallucinated tools

### 2. Instruction Following
- Prompt: system prompt (simplified AGENTS.md) + "You receive a heartbeat. What do you do?"
- Tests: compliance with operational docs, correct procedure
- Scoring: checklist of expected behaviors (read HEARTBEAT.md, check items, respond correctly)

### 3. Email Triage
- Prompt: 10 sample emails with varying urgency → "Classify each by alert level (🔴🟡🟢) and draft responses for 🔴"
- Tests: classification accuracy, response quality
- Scoring: accuracy vs ground truth labels, response relevance

### 4. Judgment Calls (when to speak vs stay silent)
- Prompt: 5 group chat scenarios → "Should you respond? If yes, what?"
- Tests: social awareness, appropriate silence
- Scoring: binary correct on speak/silent + quality of response when speaking

### 5. Structured Output
- Prompt: "Create a Notion page with these fields: [spec]. Return the API call JSON."
- Tests: valid JSON, correct Notion API structure, all fields populated
- Scoring: JSON validity, schema compliance, field completeness

### 6. Long Context
- Prompt: 20K+ token context (memory files + conversation) + question about specific detail
- Tests: retrieval accuracy from long context, no hallucination
- Scoring: exact match or semantic similarity to ground truth

## Scoring

Each scenario produces a score 0-100:
- **Automated checks** (tool call validity, JSON schema, exact match) = binary pass/fail per criterion
- **LLM-as-judge** for subjective quality (using Claude as evaluator) = 0-100 rubric score
- Final score = weighted average

## Models to Test (initial set)

Cloud (via OpenRouter):
- claude-sonnet-4-20250514
- claude-opus-4-20250514
- gpt-4o
- gpt-4o-mini
- gpt-o3
- gpt-o4-mini
- gemini-2.5-pro
- gemini-2.5-flash
- deepseek-chat-v3
- deepseek-r1
- llama-4-maverick
- qwen-2.5-72b

Local (via Ollama, optional):
- llama3.2:8b
- qwen2.5:14b
- mistral:7b

## Dashboard
Static HTML/JS/CSS. Reads results JSON. Shows:
- Model comparison table (sortable by category)
- Radar chart per model (category scores)
- Overall ranking
- Cost per run (from OpenRouter pricing)
- Recommendation matrix: model × use case

## CLI Usage

```bash
# Run full benchmark
python run.py --all

# Run specific scenario
python run.py --scenario tool_orchestration

# Run specific model
python run.py --model claude-sonnet-4-20250514

# Generate dashboard
python run.py --report
```

## Config (config.yaml)

```yaml
openrouter_api_key_file: ~/.config/openrouter/api_key
ollama_url: http://localhost:11434
evaluator_model: claude-sonnet-4-20250514  # for LLM-as-judge
models:
  - id: anthropic/claude-sonnet-4-20250514
    provider: openrouter
  # ... etc
```
