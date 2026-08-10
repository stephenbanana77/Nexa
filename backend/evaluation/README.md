# Nexa Evaluation

This folder contains an offline evaluation harness for the AI data analysis agent.

The first suite, `cases/superstore_core.json`, uses the bundled Superstore dataset and checks whether generated SQL:

- passes the AST SQL safety policy,
- executes successfully,
- returns the expected semantic result,
- records per-case latency.

Run it from the repository root:

```powershell
Push-Location backend
.\venv\Scripts\python.exe -m evaluation.runner --format markdown
Pop-Location
```

You can compare generated SQL by passing a predictions file:

```powershell
Push-Location backend
.\venv\Scripts\python.exe -m evaluation.runner --predictions path\to\predictions.json --format json
Pop-Location
```

`predictions.json` may either be an object mapping case id to SQL, or a list of `{ "id": "...", "sql": "..." }` objects.
