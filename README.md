# Smart Life Planner

An intelligent multi-agent system for automated life planning, aligned with Kaggle "Agents Intensive – Capstone Project" criteria.

## Features

### Multi-Agent Architecture
- **IntentAgent**: Extracts goals, constraints, and priorities from user input
- **TaskAgent**: Proposes weekly tasks using TaskDB
- **MealAgent**: Generates meal plans using RecipeTool
- **BudgetAgent**: Builds shopping lists and estimates budgets using GroceryTool
- **SchedulerAgent**: Combines outputs and resolves time conflicts using CalendarTool
- **CoordinatorAgent**: Merges proposals and scores plan options
- **VerifierAgent**: Final validation with reproducibility signatures

### Tools
- **TaskDB**: SQLite-based task database
- **RecipeTool**: Recipe search with dietary constraints
- **GroceryTool**: Price lookup and shopping list management
- **CalendarTool**: Scheduling and conflict detection

### Memory
- **Session Memory**: In-memory session service for user preferences and queries
- **Long-term Memory**: JSON-based persistent storage

### Observability
- Structured logging with JSONL output
- Execution tracing
- Evaluation metrics

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Usage

### Run the Streamlit App

```bash
uv run streamlit run src/app.py
```

Or with pip:

```bash
streamlit run src/app.py
```

### Example Input

```
Plan my week with exercise, healthy meals, and grocery shopping. 
Budget is $100. I'm vegetarian.
```

## Architecture

The system uses an ADK-compatible multi-agent pipeline:

1. **IntentAgent** → Extracts user intent
2. **Parallel Execution**:
   - **TaskAgent** → Generates tasks
   - **MealAgent** → Generates meal plan
3. **BudgetAgent** → Estimates budget (runs after MealAgent)
4. **SchedulerAgent** → Creates schedule and resolves conflicts
5. **CoordinatorAgent** → Optimizes and scores plan
6. **VerifierAgent** → Validates final plan

## Project Structure

```
smart-life-planner/
├── src/
│   ├── app.py                 # Streamlit web app
│   ├── orchestrator.py        # Multi-agent pipeline
│   ├── agents/                # All agent implementations
│   ├── tools/                 # Tool implementations
│   ├── memory/                # Memory modules
│   └── utils/                 # Logger and evaluator
├── notebooks/
│   └── demo.ipynb            # Demo notebook
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.8+
- streamlit>=1.28.0
- pydantic>=2.0.0

## Development

The codebase is designed to be:
- **Modular**: Each agent and tool is independently testable
- **Traceable**: Full execution trace and logging
- **Deterministic**: Keyword-based fallbacks when LLM not available
- **Observable**: Comprehensive metrics and evaluation

## Next Steps

To add LLM intelligence, integrate with:
- OpenAI API
- Anthropic Claude API
- Or other LLM providers

The current implementation uses deterministic keyword matching as a fallback, making it fully functional without LLM dependencies.
