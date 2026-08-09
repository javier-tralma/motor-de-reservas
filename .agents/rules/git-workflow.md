<RULE[git_workflow]>
# Reglas de Git Workflow

Estas reglas deben aplicar a partir de ahora en todo el proyecto:

## 1. COMMITS SEMÁNTICOS E INCREMENTALES
- Cada commit debe seguir Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`, `docs:`).
- Cada commit debe representar un cambio atómico y funcional — no mezclar features distintas en un solo commit, ni hacer commits gigantes al final del día.
- El mensaje debe explicar el "por qué", no solo el "qué", cuando el cambio no sea autoevidente.

## 2. VALIDACIÓN PRE-PUSH
- Antes de cualquier `git push`, correr automáticamente: linter, type-check (`tsc --noEmit`), y la suite de tests si existe.
- Si algo falla, NO hacer push — corregir primero y avisar qué falló y por qué antes de continuar.
- Nunca usar `--no-verify` ni saltarse esta validación, incluso si parece un cambio trivial.

## 3. RAMAS
- No trabajar directo sobre `main` para features — usar ramas descriptivas (`feat/nombre-corto`) y avisar antes de mergear a `main`.
</RULE[git_workflow]>
