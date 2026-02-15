# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **Speckit**, a specification-driven development framework for Claude Code. It provides a structured workflow that emphasizes creating detailed specifications before coding, planning implementations with technical details, and systematically executing development work.

## Core Architecture

### Workflow Phases

Speckit follows a linear, gated workflow where each phase produces artifacts for the next:

1. **Specify** (`/speckit.specify`) → Creates `spec.md`
   - Converts natural language feature requests into structured specifications
   - Focuses on WHAT users need and WHY (not HOW to implement)
   - Organizes requirements into prioritized user stories (P1, P2, P3)
   - Each user story must be independently testable
   - Written for business stakeholders, technology-agnostic

2. **Clarify** (`/speckit.clarify`) → Updates `spec.md`
   - Optional: Identifies underspecified areas in specifications
   - Asks targeted clarification questions (max 5)
   - Updates spec with resolved clarifications

3. **Plan** (`/speckit.plan`) → Creates `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
   - Translates specification into technical implementation plan
   - Performs research to resolve technical unknowns (Phase 0)
   - Generates data models and API contracts (Phase 1)
   - Checks against project constitution for compliance

4. **Tasks** (`/speckit.tasks`) → Creates `tasks.md`
   - Generates dependency-ordered, actionable task lists
   - Organizes tasks by user story to enable independent delivery
   - Marks parallelizable tasks with [P]
   - Links each task to specific file paths

5. **Analyze** (`/speckit.analyze`) → Creates analysis reports
   - Validates consistency across spec.md, plan.md, and tasks.md
   - Non-destructive quality checks

6. **Implement** (`/speckit.implement`) → Executes `tasks.md`
   - Systematically executes all tasks in dependency order
   - Validates checklist completion before starting
   - Follows phase-by-phase execution (Setup → Foundational → User Stories → Polish)

7. **Constitution** (`/speckit.constitution`) → Manages `.specify/memory/constitution.md`
   - Defines project principles and governance rules
   - Used as gates during planning phase

8. **Checklist** (`/speckit.checklist`) → Creates custom checklists
   - Generates domain-specific quality checklists
   - Stored in `specs/###-feature-name/checklists/`

9. **Tasks to Issues** (`/speckit.taskstoissues`) → Creates GitHub issues
   - Converts tasks.md into actionable GitHub issues
   - Preserves dependencies and ordering

### Feature Organization

Features are developed in isolated branches and directories:

- **Branch naming**: `###-short-name` (e.g., `001-user-auth`, `002-analytics-dashboard`)
  - Number auto-increments based on highest existing feature number
  - Short name is 2-4 words, action-noun format

- **Specs directory**: `specs/###-feature-name/`
  ```
  specs/001-user-auth/
  ├── spec.md              # Feature specification (Phase: Specify)
  ├── plan.md              # Implementation plan (Phase: Plan)
  ├── research.md          # Technical research (Phase: Plan, Phase 0)
  ├── data-model.md        # Entity definitions (Phase: Plan, Phase 1)
  ├── quickstart.md        # Integration scenarios (Phase: Plan, Phase 1)
  ├── contracts/           # API specifications (Phase: Plan, Phase 1)
  │   └── *.yaml
  ├── tasks.md             # Task breakdown (Phase: Tasks)
  └── checklists/          # Quality checklists (Phase: Checklist)
      ├── requirements.md  # Auto-generated during specify
      └── *.md             # Domain-specific checklists
  ```

## Key Scripts

All scripts are in `.specify/scripts/powershell/` and output JSON when called with `-Json` flag:

- **`create-new-feature.ps1`**: Initialize new feature branch and directory structure
  - Usage: `./create-new-feature.ps1 -Json [-ShortName "name"] [-Number N] "feature description"`
  - Auto-detects next available feature number across remote branches, local branches, and specs directories
  - Creates feature branch and initializes spec file

- **`setup-plan.ps1`**: Set up planning phase context
  - Usage: `./.specify/scripts/powershell/setup-plan.ps1 -Json`
  - Returns: FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH paths

- **`check-prerequisites.ps1`**: Validate prerequisites and return context
  - Usage: `./.specify/scripts/powershell/check-prerequisites.ps1 -Json [-RequireTasks] [-IncludeTasks]`
  - Returns: FEATURE_DIR, AVAILABLE_DOCS list

- **`update-agent-context.ps1`**: Update AI agent context files with project tech stack
  - Usage: `./.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
  - Detects agent type and updates appropriate context file
  - Preserves manual additions between markers

## Architecture Principles

1. **Specification-First**: Define WHAT before HOW. Specifications are technology-agnostic and focus on user needs.

2. **User Story Driven**: All work is organized by user stories, not technical layers. This enables:
   - Independent implementation of stories
   - Independent testing of stories
   - Incremental delivery (MVP = User Story 1)

3. **Independent Testability**: Each user story must be testable on its own, without depending on other stories.

4. **Constitution-Based**: Project principles (defined in `.specify/memory/constitution.md`) act as gates during planning.

5. **Quality Gates**: Validation checkpoints at each phase:
   - Specify: Specification quality checklist (requirements.md)
   - Plan: Constitution check gates
   - Implement: Pre-execution checklist validation

6. **Dependency Awareness**: Tasks explicitly declare dependencies and parallelizability:
   - Sequential tasks run in order
   - Parallel tasks [P] can run together
   - Phase completion required before next phase

## Task Format Conventions

All tasks in `tasks.md` follow strict format:

```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

Components:
- `- [ ]`: Markdown checkbox (required)
- `[TaskID]`: Sequential ID (T001, T002...)
- `[P]`: Optional marker for parallelizable tasks
- `[Story]`: User story label (US1, US2...) - required for story phase tasks only
- Description: Clear action with exact file path

## Project Structure Patterns

Source code organization depends on project type (detected from plan.md):

- **Single project** (default): `src/`, `tests/` at repository root
- **Web application**: `backend/src/`, `frontend/src/`, separate test directories
- **Mobile + API**: `api/src/`, `ios/` or `android/` with platform-specific structure

## Working with Speckit

### Starting a new feature:
```bash
# Option 1: Use the skill directly
/speckit.specify Add user authentication with email/password

# Option 2: Run script manually (rarely needed)
./.specify/scripts/powershell/create-new-feature.ps1 -Json "Add user authentication"
```

### Following the workflow:
1. Create spec: `/speckit.specify <feature description>`
2. (Optional) Clarify: `/speckit.clarify`
3. Create plan: `/speckit.plan`
4. Generate tasks: `/speckit.tasks`
5. (Optional) Analyze: `/speckit.analyze`
6. Execute: `/speckit.implement`

### Handling quotes in PowerShell scripts:
- Prefer double quotes: `"I'm building a feature"`
- For single quotes in bash: `'I'\''m building'` (escape syntax)

## Important Notes

- **Always use `-Json` flag** when calling PowerShell scripts programmatically
- **Parse JSON output** from scripts for paths and context (don't hardcode paths)
- **Read artifacts in order**: spec.md → plan.md → tasks.md → implement
- **Respect phase boundaries**: Don't skip ahead in the workflow
- **Check prerequisites**: Use `check-prerequisites.ps1` before starting phases
- **Validate checklists**: Implementation checks all checklists before executing tasks
- **Mark completed tasks**: Update tasks.md checkboxes `[X]` as work completes
- **Constitution gates**: Planning phase must pass constitution checks to proceed
- **Tests are optional**: Only generate test tasks if explicitly requested in spec or by user

## Skills Available

All Speckit commands are invoked via the Skill tool (referenced as `/speckit.<command>`):
- `/speckit.specify` - Create/update feature specification
- `/speckit.clarify` - Clarify specification requirements
- `/speckit.plan` - Create implementation plan
- `/speckit.tasks` - Generate task breakdown
- `/speckit.implement` - Execute implementation
- `/speckit.analyze` - Analyze cross-artifact consistency
- `/speckit.constitution` - Manage project principles
- `/speckit.checklist` - Generate custom checklists
- `/speckit.taskstoissues` - Convert tasks to GitHub issues

## TremoAI Project Context

This Speckit instance is configured for the **TremoAI Web Platform** - a graduation project providing doctors with real-time monitoring for patients using smart wearable gloves for Parkinson's tremor suppression.

### Constitutional Tech Stack (Non-Negotiable)

**Architecture**: Monorepo with `backend/` (Django) and `frontend/` (React)

**Backend**:
- Django 5.x + Django REST Framework + Django Channels
- Python with pytest for testing
- Django Channels WebSocket for real-time data streaming
  - channels-redis (Redis channel layer backend)
  - Redis server (localhost:6379) for inter-process communication
- MQTT client for glove sensor data ingestion
  - paho-mqtt library for MQTT protocol
  - MQTT broker (Mosquitto or equivalent)
- AI/ML models: scikit-learn (.pkl) and TensorFlow/Keras (.h5)

**Frontend**:
- React 18+ with Vite build tool
- Tailwind CSS for styling
- Recharts for data visualization
- Jest/Vitest for testing

**Database**: Supabase PostgreSQL (remote only, no local SQLite)

**Authentication**: JWT tokens via Django SimpleJWT with two roles:
- `patient` - Patient users
- `doctor` - Medical professional users

**API Standards**:
- RESTful endpoints (e.g., `/api/patients/`, `/api/tremor-data/`)
- JSON request/response bodies only
- Standard HTTP status codes
- snake_case for JSON keys
- Error format: `{ "error": "message" }`

**Configuration**: All secrets via `.env` files (never hardcoded)

**Development Scope**: Local development ONLY
- No Docker containerization
- No CI/CD pipelines
- No production deployment configurations
- Development servers: `python manage.py runserver`, `npm run dev`

### When Planning Features

Always validate against `.specify/memory/constitution.md`:
- Features must fit within the monorepo structure
- No new frameworks outside the constitutional stack
- Must use Supabase PostgreSQL (no other databases)
- Authentication via JWT with patient/doctor roles
- Real-time features use Django Channels WebSocket
- Sensor data integration uses MQTT
- All secrets in `.env` files

See the constitution file for complete principles and rationale.
