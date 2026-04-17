# PawPal+ (Module 2 Project)

PawPal+ is an AI-powered pet care assistant built with Python and Streamlit. It features a powerful **Hybrid UI**, maintaining standard dashboard controls while introducing a **Floating Conversational Hub**. This allows pet owners to manage tasks across multiple pets using native natural language at their convenience. It harnesses Dynamic Intent Routing and JSON sanitization for resilient actions. The AI layer runs entirely on a local Ollama model, such as `llama3.2:3b`, with no API key required.

## Features

- **Owner setup**: enter your name and daily time budget; fields lock after saving with an Edit button to unlock
- **Multi-pet support**: add any number of pets (name, species, age, and optional special needs); switch between pets to manage their tasks; each pet's special needs are summarized below the task table
- **Task manager**: add tasks with title, duration, priority, category, frequency, and scheduled time (15-minute step picker); tasks are only saved if no time conflict exists
- **Conflict detection**: warns before saving if another task is already scheduled at the same time slot across any pet
- **Sort and filter**: sort tasks by scheduled time, priority, or duration; filter by priority; high-priority badge shows count of outstanding items
- **Complete / uncomplete**: toggle completion per task with strikethrough display; completing a daily or weekly task automatically queues the next occurrence; uncompleting removes it
- **Generate Plan**: filter by pet and status, schedule incomplete tasks within the time budget, display Scheduled / Could not fit / Complete tables
- **Data persistence**: all data saves to `data/pawpal_data.json` automatically on every change; restored on refresh or restart

## AI Features
- **Floating Conversational Hub**: Access the Llama AI instantly through a persistent action button without losing visibility of your manual dashboard.
- **Dynamic Intent Routing**: The `router.py` parses user intent organically and routes it internally with multi-turn "Context Locking".
- **Smart Scheduler & Predictive Alerts**: Proactively scans behavioral history to identify gaps and suggests a 'Smart Plan' based on species-specific guidelines.
- **Contextual Knowledge Base**: Seeded with industry-standard care (Dogs: 30m walk/2x feeding; Cats: play/grooming) to ground AI advice in best practices.
- **JSON Output Sanitization**: Integrated regex-based filtering strictly isolates python dictionaries from LLM conversational filler.

## Demo

### 1. Owner & Pet Setup
![Owner and Pet Setup](assets/screenshots/1-owner-pet.png)

### 2. Task Manager
![Task Manager](assets/screenshots/2-task-manager.png)

### 3. Task List
![Task List](assets/screenshots/3-tasks.png)

### 4. Generate Plan
![Generate Plan](assets/screenshots/4-schedule.png)

## Architecture Overview

PawPal+ uses a lightweight layered architecture wrapped smoothly around a Unified Conversational UI.

![System Architecture](assets/architecture.png)

| Layer | File(s) | Responsibility |
|-------|---------|---------------|
| Configuration | `config.py` | Centralized system instructions, pet care guidelines, and LLM properties |
| View + Controller | `app.py` | Streamlit asynchronous streaming chat interface, batch plan confirmation UI |
| AI Service Layer | `ai/router.py`, `ai/tools.py`, `ai/utils.py` | Intent parsing, zero-temperature grounding, tool interactions, and markdown sanitization |
| Core / Model | `pawpal_system.py` | Data model, scheduler, AnalyticsEngine (anomaly detection), conflict detection, persistence |
| Data Layer | `history.py`, `data/pawpal_data.json` | JSON persistence, completion history, analytics |

The AI Service Layer gracefully restricts itself. When Ollama is disconnected, the system manages raw exceptions to prevent severe UI freezes.

### AI Service Layer

![AI Service Layer](assets/ai_layer.png)

### UML Diagram

![PawPal+ UML Class Diagram](assets/uml.png)

## Setup Instructions

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2:3b
ollama serve
streamlit run app.py
```

AI features require Ollama to be running. The app works without it but NL task creation, chat, alerts, and smart scheduling will fall back to manual/greedy behavior.

## Sample Interactions

| Feature | User Input | AI Output |
|---------|------------|-----------|
| **NL Task Creation** | "Schedule a 20min feeding for Mochi at 8am" | "Please verify this schedule: **Feeding** for **Mochi** at 08:00... Does this look accurate?" |
| **Proactive Planner** | "What should I schedule?" | "Mochi hasn't had a walk today... I suggest adding a 30min walk at 14:00." |
| **Predictive Alert** | "Check alerts" | "Everything looks on track! / I noticed Mochi is missing their daily walk. Should we schedule one?" |
| **Escape Action** | "Nevermind" | *Breaks active intent lock and returns to main menu context.* |

## Design Decisions

| Decision | Choice | Pro | Con |
|----------|--------|-----|-----|
| LLM provider | Ollama local with `llama3.2:3b` | Highly capable, zero data sprawl, extremely flexible | Slower inference hardware demands |
| Central Configuration | `config.py` overrides `.env` | Eliminates extra dependencies/keys | Adjusting core configurations touches runtime variables |
| Missing Data Logic | Conversational AI interception | Prevents guessing or hard error locks | Requires an additional round trip to LLM |
| JSON Sanitization | Regular Expression Strippers | Highly resilient to varied LLM boilerplate | Complex formatting anomalies may occasionally penetrate |
| Testing AI components | Mock Router responses | Fast, repeatable, removes Ollama from standard test runner checks | Cannot emulate pure hallucination boundaries |

## Testing Summary

- **Automated tests**: 26 core tests passing (`pytest tests/test_pawpal.py`).
- **Proactive Anomaly Detection**: `AnalyticsEngine` successfully identifies missed recurring tasks and triggers conversational alerts.
- **Batch Plan Execution**: The AI assistant can process multiple pet requirements simultaneously and apply batch updates to the schedule upon user confirmation.
- **Human evaluation**: Manually verified that "Smart Plan" suggestions respect species guidelines and historical completion patterns.

*Summary: All AI milestones complete. The system now acts as a proactive agent rather than a reactive scheduler.*

## Reflection

### Limitations and biases

- The NL task parser is only as good as the prompt. Unusual phrasing or ambiguous times may produce wrong field values.
- The predictive alert system flags patterns statistically. Special seasonal needs may trigger false missed-task alerts.
- Historical data reflects past owner behavior. The AI learn from user habits to suggest future "ideal" times.
- The system has no veterinary knowledge. It cannot determine if a medication schedule is medically appropriate.

### Misuse and prevention

- Primary risk is over-reliance: owners may treat AI health alerts as medical advice.
- Mitigation: every Proactive Alert instruction includes strict grounding in provided database facts only.

### Collaboration with AI

- **Helpful suggestion**: Using a multi-turn "Intent Lock" in the router significantly improved the reliability of follow-up corrections (e.g., "Change the time to 5pm").
- **Flawed suggestion**: Early attempts at alerts without "Zero-Temperature Grounding" led to hallucinations of fake pets like "Bella". Fixed via strict pet-list filtering and 0.0 temperature.
