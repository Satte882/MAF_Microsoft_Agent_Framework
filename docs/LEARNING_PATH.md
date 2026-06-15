# Lernpfad

## Phase A – Ohne Modell

1. Starten Sie einen Demo-Lauf.
2. Prüfen Sie die getrennten Events für Intake, Policy, Entwurf, Human Review und Checkpoint.
3. Fordern Sie eine Überarbeitung an und beobachten Sie den zweiten Checkpoint.
4. Beenden Sie den Lauf per Freigabe oder Ablehnung.

Ziel: Den Lebenszyklus verstehen, ohne Modellqualität mit Orchestrierungsqualität zu verwechseln.

## Phase B – Echter MAF-Lauf

1. Tragen Sie einen OpenAI-kompatiblen API-Key, Modellnamen und optional eine Base URL in `.env` ein.
2. Starten Sie die Anwendung neu.
3. Wählen Sie im Formular den Modus `maf`.
4. Vergleichen Sie die Event-Timeline und das Dateiverzeichnis `data/checkpoints/<run-id>` mit dem Demo-Modus.
5. Stoppen Sie die Anwendung, bevor Sie die menschliche Entscheidung senden.
6. Starten Sie sie erneut und entscheiden Sie dann im Browser.

Ziel: Nachweisen, dass nicht der Python-Prozess, sondern der gespeicherte Checkpoint die Fortsetzung ermöglicht.

## Phase C – Architekturfragen

Beantworten Sie anhand der Anwendung:

- Welche Schritte müssen deterministisch bleiben?
- Welcher Zustand gehört in die Fachanwendung, welcher in die Workflow-Engine?
- Was passiert bei doppelter Zustellung einer menschlichen Entscheidung?
- Welche Werkzeuge dürften ohne separate Freigabe aufgerufen werden?
- Welche Daten würden Sie in OpenTelemetry erfassen und welche wegen personenbezogener Daten auslassen?
- Ab wann reicht FileCheckpointStorage nicht mehr aus?

## Phase D – Consultant-Perspektive

Erstellen Sie für einen Kundenfall eine Entscheidungsmatrix mit:

- Prozessdauer und Zahl der Unterbrechungen
- regulatorischer oder finanzieller Wirkung
- zulässigem Autonomiegrad
- Anforderungen an Recovery und Audit
- bestehendem Microsoft-/Azure-Footprint
- Kosten und Lock-in des Hostingmodells

Ziel: Nicht das Framework verkaufen, sondern den passenden Kontroll- und Betriebsmodus begründen.
