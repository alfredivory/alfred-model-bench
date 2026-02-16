# Alfred Model Bench

Benchmark LLMs across real-world scenarios — email triage, tool orchestration, structured output, and more.

## Setup

```bash
pip install -r requirements.txt
```

Set your OpenRouter API key:
```bash
mkdir -p ~/.config/openrouter
echo "sk-or-..." > ~/.config/openrouter/api_key
```

## Usage

```bash
# Run all models × all scenarios
python run.py run --all

# Run a specific model
python run.py run --model claude-sonnet

# Run a specific scenario
python run.py run --scenario email_triage

# Open the dashboard
python run.py report --open
```

## Dashboard

After running benchmarks, open `dashboard/index.html` in a browser. It loads results from `results/latest.json` and shows:

- **Model comparison table** — sortable by any column
- **Radar chart** — all models overlaid on scenario axes
- **Recommendation matrix** — color-coded model × scenario grid
- **Cost per run** — total API cost for each model

## Configuration

Edit `config.yaml` to add/remove models and adjust the evaluator model. Scenarios live in `scenarios/*.yaml`.

## Project Structure

```
├── run.py              # CLI entry point
├── config.yaml         # Models + settings
├── src/                # Core logic (runner, evaluator, providers)
├── scenarios/          # Benchmark scenarios (YAML)
├── results/            # Output JSON files
└── dashboard/          # Static HTML dashboard
```
