# Skeleton

`skeleton` `fun` `shell scripting with python`

---
A quick project skeleton for easily starting new Python Application projects.

---
## To make a new project
```
python skeleton.py foo [--post-action=pipenv]
```

What does skeleton script do?
This copies the contents of the skeleton to a sibling directory `foo`, substitutes some templates, and might do one, all, or none of the optional actions:
- init git repo there
- create a virtual environment via the pipenv module
- setup git commit hooks via the pre-commit package if git was inited
---
