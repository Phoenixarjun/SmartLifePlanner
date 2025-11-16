# 🚀 **Smart Life Planner**

### *Your Autonomous Multi-Agent Chief of Staff — Built for Kaggle “Agents Intensive – Capstone Project”*

<p align="center">
  <img src="https://img.shields.io/badge/Category-Enterprise%20Agents-0078FF?style=for-the-badge&logo=kaggle" />
  <img src="https://img.shields.io/badge/Architecture-ADK%20Multi--Agent%20Pipeline-8A2BE2?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/Status-Fully%20Working-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Notebook-Demonstration%20Included-orange?style=for-the-badge&logo=jupyter" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/badges/shields?style=flat-square" />
  <img src="https://img.shields.io/badge/LLM-Optional-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Deterministic-Fallback%20Mode-critical?style=flat-square" />
</p>

---

## 🌟 **Overview**

**Smart Life Planner** is a fully working, end-to-end **multi-agent life planning system** built entirely around **Autonomous Design Kit (ADK)** principles.

From a *single natural-language request*, it generates a:

* Weekly schedule
* Task plan
* Meal plan
* Grocery list
* Budget breakdown
* Final validation
* Reproducibility signature

All with complete traceability, deterministic fallbacks, and full tool-agent integration.

This project follows the **Enterprise Agents** track:
multi-step pipelines, tool-augmented reasoning, and orchestrated agent collaboration.

---

# 🧠 **Why This Project Exists**

Most productivity apps only solve *one* thing: tasks, meals, groceries, scheduling…
Smart Life Planner unifies them.

It acts like a **personal Chief of Staff**, coordinating multiple AI agents that reason and negotiate to deliver a coherent weekly life strategy.

---

# 🔥 **Key Features**

## 🧩 **Multi-Agent Architecture (ADK-Aligned)**

| Agent                | Responsibility                                     |
| -------------------- | -------------------------------------------------- |
| **IntentAgent**      | Extracts goals, constraints, priorities            |
| **TaskAgent**        | Creates tasks using TaskDB (LLM optional)          |
| **MealAgent**        | Builds meal plans via RecipeTool & diet filtering  |
| **BudgetAgent**      | Computes grocery budget using GroceryTool          |
| **SchedulerAgent**   | Resolves conflicts, schedules events intelligently |
| **CoordinatorAgent** | Merges outputs, scores & optimizes plan            |
| **VerifierAgent**    | Final validation with reproducibility signature    |

All agents implement a **clean process() interface**, making the pipeline plug-and-play.

---

# 🛠️ **Tools**

Fully ADK-style tools:

* **TaskDB Tool** — SQLite-backed task storage
* **RecipeTool** — Recipe search with diet filters
* **GroceryTool** — Smart price estimation + fallback
* **CalendarTool** — Scheduling support & conflict detection

Each tool supports:

```
tool.execute(action_name, **kwargs)
```

---

# 🧠 Memory System

### 🟦 Session Memory

Tracks:

* queries
* plan states
* intermediate agent outputs

### 🟧 Long-Term Memory

Stores:

* past goals
* plan scores
* user patterns

Used for future personalization.

---

# 👁️ Observability & Traceability

* Structured JSONL logging
* Agent-level event tracing
* Plan evaluation metrics
* Deterministic fallback modes
* SHA-256 plan signature for reproducibility

---

# 📦 Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

---

# ▶️ Run the App (Streamlit UI)

```bash
uv run streamlit run src/app.py
```

or

```bash
streamlit run src/app.py
```

---

# 💡 Example Input

```
Plan my week with exercise, healthy meals, and grocery shopping. 
Budget is $100. I’m vegetarian.
```

---

# 🏗️ Architecture

```
IntentAgent 
   ↓
[TaskAgent, MealAgent]  (Parallel)
   ↓
BudgetAgent
   ↓
SchedulerAgent
   ↓
CoordinatorAgent
   ↓
VerifierAgent
```

Each step logs its output and stores structured results.

---

# 📁 Project Structure

```
smart-life-planner/
├── src/
│   ├── app.py                 
│   ├── orchestrator.py        
│   ├── agents/                
│   ├── tools/                 
│   ├── memory/                
│   └── utils/                 
├── notebooks/
│   └── demo.ipynb            
├── requirements.txt
└── README.md
```

---

# 🧪 Notebook Experiments (Competition Requirement)

The included notebook shows:

* Step-by-step tool/agent testing
* Agent pipeline execution
* Structured outputs
* Deterministic fallback behaviors
* Full experimental trace

Judges can replicate *every* result.

---

# 🎯 Core Design Principles

| Principle           | Implementation                           |
| ------------------- | ---------------------------------------- |
| **Determinism**     | Fallback logic without LLM               |
| **Reproducibility** | SHA-256 signature                        |
| **ADK Alignment**   | Tools, memory, agents, orchestrator      |
| **Parallelization** | Tasks + Meals generated simultaneously   |
| **Scoring System**  | Budget, constraint, goals, overall score |

---

# 🧩 Development & Extensibility

The system is engineered to be:

* **Modular** – Each agent is independently testable
* **Transparent** – Full logs and traces
* **LLM-Optional** – Works offline or with Gemini/OpenAI
* **Composable** – Add new agents without modifying others

---

# 🚀 Next Improvements

* Multi-user profiles
* Automatic grocery ordering
* Reinforcement-learning task optimization
* Multi-week planning
* Voice input + TTS output
* Fine-tuned LLM integration

---

# ⭐ Final Words

Smart Life Planner shows how a **multi-agent ecosystem**, when designed with ADK principles, can automate complex planning workflows that normally take hours of human effort.

It’s not a chatbot — it’s an **autonomous planning system**.

