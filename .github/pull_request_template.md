## Description

<!-- Describe the changes introduced by this PR and link any relevant issue or ADR. -->

## Type of Change

- [ ] `feat`: New feature (on `feature/*` -> `develop`)
- [ ] `fix`: Bug fix
- [ ] `refactor`: Code refactoring without functional changes
- [ ] `docs`: Documentation / ADR update
- [ ] `ci` / `chore`: CI/CD, Docker, or tooling updates

## Checklist

- [ ] Code, comments, and documentation are in English
- [ ] Clean Architecture dependency rules respected (`src/api` and `src/ml` depend only on abstractions)
- [ ] `python -m ruff check .` passes
- [ ] `python -m pylint src/` passes (`>= 8.0`)
- [ ] `python -m pytest -v` passes with tests covering changes
