# Architekturentscheidungen

## ADR-001: Zwei Ausführungsmodi

**Entscheidung:** Demo und echter MAF-Modus bleiben getrennt und sichtbar gekennzeichnet.

**Begründung:** Die Plattform muss ohne API-Key vollständig bedienbar sein, darf eine Simulation aber nicht als echten Agentenlauf darstellen.

## ADR-002: Sprachmodell nur im Draft-Schritt

**Entscheidung:** Risikoklassifikation, Statuswechsel und Human Approval bleiben deterministisch.

**Begründung:** Ein Modell darf keine finanzwirksame Zustandsänderung allein auslösen.

## ADR-003: Fachzustand und Workflowzustand trennen

**Entscheidung:** SQLite speichert Runs und Audit-Events; FileCheckpointStorage speichert MAF-Ausführungszustand.

**Begründung:** Die Wiederaufnahme eines Workflows und die Wahrheit über einen Geschäftsvorgang sind unterschiedliche Verantwortlichkeiten.

## ADR-004: Kein Frontend-Buildsystem

**Entscheidung:** Die Oberfläche verwendet HTML, CSS und JavaScript ohne Node-Abhängigkeit.

**Begründung:** Der Lerngegenstand ist MAF. Installation und Fehlersuche sollen nicht durch ein zweites Toolchain-Ökosystem verdeckt werden.

## ADR-005: Provider über OpenAI-kompatible Konfiguration

**Entscheidung:** API-Key, Modell und optionale Base URL werden ausschließlich über Umgebungsvariablen gesetzt.

**Begründung:** Standard-OpenAI, lokale Ollama-Endpunkte und kompatible Gateways lassen sich untersuchen, ohne Providerdaten in Git zu speichern.
