# Project Ground Rules

## Source of Truth

These two files are the authoritative sources for this project. Always read and follow them before taking any action:

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** — Architecture, design decisions, API contracts, and constraints. Never deviate from the design described here without explicit user approval.
- **[IMPLEMENTATION_TASKS.md](IMPLEMENTATION_TASKS.md)** — The canonical task list. All implementation work must correspond to a task in this file.

## Rules

1. **Before implementing anything**, check IMPLEMENTATION_TASKS.md. Only implement what is listed there.
2. **After completing a task**, mark it as done in IMPLEMENTATION_TASKS.md by changing `- [ ]` to `- [x]`.
3. **Never add new tasks** to IMPLEMENTATION_TASKS.md without the user explicitly requesting it.
4. **Never change the project design** (API shape, file structure, tech stack) without confirming against PROJECT_PLAN.md first. If a conflict arises, surface it to the user before proceeding.
5. **Respect the machine profile**: AMD Ryzen 5 3600 / 32 GiB RAM / GTX 650 Ti. Default to CPU execution; GPU fallback requires careful VRAM management.
6. **File structure is fixed**: `app/main.py`, `app/generator.py`, `app/models.py`, `app/config.py`, `outputs/` — match exactly what PROJECT_PLAN.md specifies.
7. **Do not create files not listed** in PROJECT_PLAN.md's "Next Files to Create" section unless implementing a task that explicitly requires it.
8. **Never run code locally or install packages on this machine.** This machine is for development only. Do not run `pip install`, `python`, `uvicorn`, or any other execution commands. All runtime testing and dependency loading happens on the server.
