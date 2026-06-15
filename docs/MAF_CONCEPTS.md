# Microsoft-Agent-Framework-Konzepte im Repository

| MAF-Konzept | Implementierung | Lernzweck |
|---|---|---|
| `Executor` | `CaseIntakeExecutor`, `DraftExecutor`, `HumanReviewGateway` | Deterministische und modellgestützte Schritte explizit trennen |
| `WorkflowBuilder` | `_build_workflow` | Graph, Kanten, Iterationslimit und Output-Executor sichtbar machen |
| `Agent` | `PaymentFlowAdvisor` | Modell nur für eine klar begrenzte Reasoning-Aufgabe einsetzen |
| `OpenAIChatClient` | `DraftExecutor` | Standard-OpenAI, Ollama oder kompatible Gateways über Base URL nutzen |
| `request_info` | `HumanReviewGateway.request_review` | Persistente menschliche Entscheidung anfordern |
| `response_handler` | `HumanReviewGateway.process_review` | Freigabe, Revision und Ablehnung typisiert verarbeiten |
| `FileCheckpointStorage` | Run-spezifisches Verzeichnis | Pause und Fortsetzung über Prozessgrenzen untersuchen |
| `on_checkpoint_save/restore` | Iterationszähler des Review Gateways | Eigenen Executor-Zustand explizit serialisieren |
| Workflow-Events | `_collect` | Runtime-Ereignisse in einen lesbaren Audit-Trail übersetzen |

## Wichtige Interpretation

Ein Agent Framework ersetzt keine Fachdomäne, keine Datenbank und keine Berechtigungsarchitektur. Es koordiniert Ausführung. Der fachliche Zustand bleibt in dieser Plattform in SQLite, während MAF seinen technischen Workflowzustand in Checkpoint-Dateien hält.
