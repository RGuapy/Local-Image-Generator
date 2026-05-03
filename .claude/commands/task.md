Read IMPLEMENTATION_TASKS.md and PROJECT_PLAN.md.

The argument passed to this command is: $ARGUMENTS

## Behavior

**If no argument is given:**
- List all uncompleted tasks (`- [ ]`) grouped by section, with their section number and description.
- Ask the user which task or section to execute next.

**If an argument is given** (e.g. "1", "2.3", "setup", a keyword, or "next"):
- Find the matching uncompleted task(s) in IMPLEMENTATION_TASKS.md.
  - A number like "1" means section 1, all its uncompleted tasks.
  - A number like "2.3" means section 2, third bullet.
  - A keyword matches by description substring.
  - "next" means the first uncompleted task in the file.
- Implement every matched task, following PROJECT_PLAN.md strictly.
- After each individual sub-task is done, mark it `- [x]` in IMPLEMENTATION_TASKS.md immediately.
- When the section is complete, confirm to the user and show what was marked done.

## Constraints (always apply)
- Never implement anything not in IMPLEMENTATION_TASKS.md.
- Keep all code consistent with the design in PROJECT_PLAN.md.
- Respect the machine profile: CPU-first, GTX 650 Ti has limited VRAM.
- Match the file structure exactly: `app/main.py`, `app/generator.py`, `app/models.py`, `app/config.py`, `outputs/`.
