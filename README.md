# MAF Learning Platform

Eine vollständige lokale Lernplattform für das **Microsoft Agent Framework (MAF)**. Das Repository enthält nicht nur Notizen oder lose Samples, sondern eine zusammenhängende Anwendung mit Browser-Oberfläche, API, SQLite-Persistenz, echtem MAF-Workflow, File-Checkpoints, Human-in-the-Loop, Demo-Modus, Tests, Docker und Continuous Integration (CI).

## Was die Plattform konkret zeigt

- Expliziter Workflow: `Case Intake → Risk Policy → Agent Draft → Human Review → Output`
- Deterministische Regeln außerhalb des Sprachmodells
- Echter MAF-Agent über `OpenAIChatClient`
- `request_info` und `response_handler` für Human-in-the-Loop
- `FileCheckpointStorage` für Pause und Wiederaufnahme
- Revision Loop zurück zum Agenten
- SQLite-basierter Run- und Event-Inspector
- API-key-freier Demo-Modus, der Simulationen klar als Simulation kennzeichnet
- OpenAI-kompatible Provider (OpenRouter, Ollama, kompatible Gateways)

## Voraussetzungen

- Windows 10/11, Linux oder macOS
- Python 3.12 oder 3.13
- Git
- Optional: Docker Desktop
- Nur für echten MAF-Modus: API-Key und ein unterstütztes OpenAI-kompatibles Modell

## Bestehenden lokalen Ordner aktualisieren

Der vorgesehene Windows-Pfad lautet:

`C:\Users\user\Documents\GitHub\MAF_Microsoft_Agent_Framework`

Öffnen Sie PowerShell in diesem Ordner und führen Sie aus:

```powershell
git fetch --all --prune
git checkout main
git pull --ff-only
```

## Schnellstart unter Windows

```powershell
cd C:\Users\user\Documents\GitHub\MAF_Microsoft_Agent_Framework
.\scripts\setup.ps1
.\scripts\run.ps1
```

Danach im Browser öffnen:

`http://127.0.0.1:8000`

Der Demo-Modus funktioniert ohne API-Key. Das Setup verwendet `requirements-lock.txt` mit vollständig aufgelösten Versionen.

## Echter Microsoft-Agent-Framework-Modus

1. Kopieren Sie `.env.example` nach `.env`, falls das Setup dies noch nicht erledigt hat.
2. Empfohlene Konfiguration für **OpenRouter**:

```dotenv
OPENAI_API_KEY=sk-or-v1-...
OPENAI_MODEL=deepseek/deepseek-v4-flash
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

3. Alternativ für einen OpenAI-kompatiblen Gateway oder **Ollama** (lokal):

```dotenv
OPENAI_BASE_URL=http://localhost:11434/v1/
OPENAI_MODEL=llama3.2
OPENAI_API_KEY=ollama
```

4. Starten Sie die Anwendung neu und wählen Sie im Formular den Modus `maf`.

API-Keys und lokale Daten werden durch `.gitignore` vom Repository ausgeschlossen.

## Tests

```powershell
.\scripts\test.ps1
```

Die Tests prüfen:

- deterministische Risikoklassifikation
- SQLite-Persistenz
- vollständigen Demo-Lebenszyklus bis zur Freigabe
- Revision mit neuem Checkpoint
- HTTP-API und Systemstatus

Der echte Modellaufruf ist bewusst kein automatischer CI-Test, da er Kosten, Zugangsdaten und Providerverfügbarkeit voraussetzt.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Die Daten werden im Docker-Volume `maf-lab-data` gespeichert.

## API

Nach dem Start stehen bereit:

- `GET /api/health`
- `GET /api/system`
- `GET /api/concepts`
- `GET /api/runs`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/decision`
- interaktive OpenAPI-Dokumentation unter `/docs`

## Repository-Struktur

```text
.github/workflows/ci.yml       CI für Python 3.12 und 3.13
docs/                          Architektur, Lernpfad und Entscheidungen
scripts/                       Windows- und Unix-Setup, Start und Tests
src/maf_lab/api.py             FastAPI-Anwendung
src/maf_lab/service.py         Anwendungsorchestrierung
src/maf_lab/maf_engine.py      Echter Microsoft-Agent-Framework-Workflow
src/maf_lab/demo_engine.py     API-key-freier, klar gekennzeichneter Simulator
src/maf_lab/repository.py      SQLite Run-, Event- und Checkpoint-Metadaten
src/maf_lab/static/            Browser-Oberfläche ohne Buildsystem
tests/                         Automatisierte Tests
```

## Empfohlene Lernreihenfolge

1. Demo-Lauf starten und Event-Timeline lesen.
2. Revision anfordern und den zweiten Checkpoint prüfen.
3. Lauf freigeben und finalen Output untersuchen.
4. `docs/MAF_CONCEPTS.md` parallel zum Code öffnen.
5. Echten MAF-Modus konfigurieren.
6. Anwendung während einer Human-in-the-Loop-Pause beenden und danach fortsetzen.
7. Die Architekturfragen in `docs/LEARNING_PATH.md` beantworten.

## Technische Einordnung

Diese Plattform ist ein Lern- und Architektur-Labor, kein produktives Mahnwesen. Sie zeigt gezielt, wie MAF als Workflow- und Agentenschicht eingesetzt wird, ohne fachlichen Systemzustand, Audit und menschliche Kontrolle an ein Sprachmodell abzugeben.

## Dokumentation

- [Architektur](docs/ARCHITECTURE.md)
- [Lernpfad](docs/LEARNING_PATH.md)
- [MAF-Konzepte](docs/MAF_CONCEPTS.md)
- [Architekturentscheidungen](docs/DECISIONS.md)

## Lizenz

MIT
