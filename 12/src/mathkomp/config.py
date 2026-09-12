"""Zugriff auf system_config.

§41 ist bindend: Schwellen sind Defaults mit dem Status CONFIGURABLE, keine
Behauptungen. §35 ist bindend: die Skip-Level-Logik ist eine
CONFIGURABLE_HEURISTIC. §39 ist bindend: Zeitgrenzen werden nicht hardcodiert.

Deshalb liest die Engine jeden Schwellwert, jedes Gewicht und jede Zeitgrenze
hier - kein Literal im Code. Der Test test_config_enthaelt_keine_hardcodierten_
schwellen sichert das ab.

Ein Schluessel mit value = NULL ist UNDEFINED (§1). require() bricht dann ab,
statt einen Ersatzwert anzunehmen. Das ist Absicht: ein stillschweigend
geratener Schwellwert waere genau die eigenstaendige fachliche Ergaenzung, die
§1 verbietet.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class UndefinedConfig(Exception):
    """Der Schluessel ist fachlich nicht festgelegt (§1)."""


class Config:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._rows = {
            r["config_key"]: dict(r)
            for r in conn.execute("SELECT * FROM system_config")
        }

    def __contains__(self, key: str) -> bool:
        return key in self._rows

    def status(self, key: str) -> str:
        return self._rows[key]["status"]

    def spec_section(self, key: str) -> str | None:
        return self._rows[key]["spec_section"]

    def require(self, key: str) -> Any:
        """Wert oder Abbruch. Fuer alles, ohne das die Engine nicht rechnen darf."""
        if key not in self._rows:
            raise KeyError(f"Konfigurationsschluessel fehlt: {key}")
        row = self._rows[key]
        if row["value"] is None:
            raise UndefinedConfig(
                f"{key} ist UNDEFINED ({row['spec_section']}). Die Engine nimmt keinen"
                " Ersatzwert an (§1). Siehe OFFENE_FRAGEN.md.")
        return _cast(row["value"], row["value_type"])

    def optional(self, key: str, default: Any = None) -> Any:
        """Wert, oder default wenn UNDEFINED. Nur fuer Mechanismen, die ohne
        den Wert abgeschaltet bleiben duerfen - etwa EVIDENCE_TOO_OLD (§39)."""
        if key not in self._rows or self._rows[key]["value"] is None:
            return default
        row = self._rows[key]
        return _cast(row["value"], row["value_type"])

    def override(self, key: str, value: object) -> None:
        """Setzt einen Wert zur Laufzeit. §3: "Die Lehrkraft kann
        Systementscheidungen uebersteuern." Auch die Simulation nutzt das, um
        einen Testfall auf einer anderen Startstufe zu fahren (§96).

        Der Ueberschreibungsstatus bleibt erhalten; ein STRUCTURAL-Wert wie
        routing.llm_in_decision_path laesst sich damit nicht heimlich kippen -
        die Pruefregeln lesen die Datenbank, nicht dieses Objekt.
        """
        if key not in self._rows:
            raise KeyError(f"Unbekannter Konfigurationsschluessel: {key}")
        self._rows[key] = {**self._rows[key], "value": None if value is None else str(value)}

    def undefined_keys(self) -> list[str]:
        return sorted(k for k, r in self._rows.items() if r["value"] is None)


def _cast(value: str, value_type: str) -> Any:
    if value_type == "INTEGER":
        return int(value)
    if value_type == "REAL":
        return float(value)
    if value_type == "BOOLEAN":
        return value.strip().lower() in ("true", "1", "yes")
    if value_type == "JSON":
        return json.loads(value)
    return value
