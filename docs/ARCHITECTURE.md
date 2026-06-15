# Architektur

## Ziel

Die Plattform zeigt die Grenze zwischen deterministischer Geschäftslogik, modellgestützter Formulierung, Human-in-the-Loop und dauerhaftem Anwendungszustand. Sie ist absichtlich kein Chatbot.

## Komponenten

| Komponente | Verantwortung | Persistenz |
|---|---|---|
| FastAPI | HTTP-API und Auslieferung der Benutzeroberfläche | Keine eigene |
| RunService | Anwendungsfall koordinieren, Engine auswählen, Fehler abgrenzen | Über Repository |
| RiskPolicy | Deterministische Risikoklassifikation | Ergebnis im Run |
| DemoWorkflowEngine | API-key-freie Simulation des MAF-Lebenszyklus | SQLite |
| MicrosoftAgentFrameworkEngine | Echter MAF-Workflow mit Agent, request_info und FileCheckpointStorage | MAF-Dateicheckpoints |
| SQLiteRepository | Runs, Ereignisse und Checkpoint-Metadaten | SQLite |
| Browser-UI | Workflow ausführen und Ereignisse untersuchen | Keine eigene |

## Kontrollfluss

1. `CaseIntakeExecutor` übernimmt einen typisierten Rechnungsfall.
2. Die Anwendung berechnet die Risikostufe deterministisch, bevor ein Modell beteiligt wird.
3. `DraftExecutor` ruft im MAF-Modus einen `Agent` über `OpenAIChatClient` auf.
4. `HumanReviewGateway` erzeugt mit `request_info` eine persistierbare menschliche Entscheidung.
5. `FileCheckpointStorage` speichert den Workflowzustand zwischen Supersteps.
6. Ein späterer HTTP-Aufruf rekonstruiert eine neue Workflow-Instanz und setzt sie mit Checkpoint und Antwort fort.
7. `yield_output` beendet den Lauf oder die Revision führt über eine explizite Kante zurück zum Drafter.

## Bewusste Grenzen

- SQLite ist hier Anwendungs- und Lernpersistenz, nicht verteilte Produktionsinfrastruktur.
- FileCheckpointStorage demonstriert Wiederaufnahme, ersetzt aber keinen organisationsweiten Durable-Task-Backbone.
- Das Sprachmodell erzeugt nur einen internen Vorschlag. Es versendet keine Nachricht und verändert keinen externen Geschäftszustand.
- Die UI zeigt Framework-Ereignisse und Anwendungsereignisse gemeinsam, kennzeichnet aber ihre Quelle.
- Der Demo-Modus ist eine Simulation und wird in Events ausdrücklich so bezeichnet.

## Erweiterungspfad

- OpenTelemetry-Exporter an die vorhandene MAF-Telemetrie anbinden.
- Durable Task für langlaufende, verteilte Workflows untersuchen.
- MCP-Werkzeuge nur mit Freigabepolitik ergänzen.
- Provider-spezifische Adapter hinter einer klaren Konfigurationsgrenze halten.
- Business State und Workflow State weiterhin getrennt behandeln.
