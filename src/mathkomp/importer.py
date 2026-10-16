"""Import der Content-Dateien aus content/*.json in die Datenbank.

Reihenfolge folgt den Abhaengigkeiten:
    vocabularies -> sources -> competencies -> relations
    -> task_families -> tasks -> task_features -> task_routes
    -> error_codes -> system_config

Vorwaertsreferenzen (competencies.parent_id, tasks.parallel_item_id) werden
in einem zweiten Durchgang nachgetragen, damit die Reihenfolge innerhalb
einer Datei keine Rolle spielt.

Nach den Dateien in content/ laufen die Zusatzpakete aus EXTENSIONS. Sie
liegen in eigenen Unterverzeichnissen, weil content/*.json die Inhalte
traegt, die §42-57 der Spezifikation nennt. Ein Zusatzpaket beruft sich auf
keine Fundstelle; beides im selben Verzeichnis zu mischen wuerde diese
Unterscheidung unsichtbar machen (§1). Ein Paket laesst sich weglassen,
indem sein Verzeichnis geloescht oder aus EXTENSIONS entfernt wird.

Der Importer validiert vor dem Schreiben. §1: fehlt eine fachliche Angabe,
wird sie nicht ergaenzt - der Import bricht ab oder traegt den in der
Content-Datei hinterlegten UNDEFINED-Wert ein.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FEATURE_KINDS = (
    "numeric_features",
    "structural_features",
    "surface_features",
    "strategy_affordances",
    "additional_demands",
)

#: Zusatzpakete unterhalb von content/, in Importreihenfolge.
EXTENSIONS = ("klassen5bis10",)

#: Abbildung Feldname in tasks.json -> Vokabularname in der Datenbank.
FEATURE_KIND_VOCABULARY = {
    "numeric_features": "NUMERIC_FEATURE",
    "structural_features": "STRUCTURAL_FEATURE",
    "surface_features": "SURFACE_FEATURE",
    "strategy_affordances": "STRATEGY_AFFORDANCE",
    "additional_demands": "ADDITIONAL_DEMAND",
}


class ImportError_(Exception):
    """Inhaltlicher Fehler in einer Content-Datei."""


@dataclass
class ImportReport:
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add(self, table: str, n: int) -> None:
        self.counts[table] = self.counts.get(table, 0) + n

    def total(self) -> int:
        return sum(self.counts.values())


def _load(content_dir: Path, name: str) -> dict[str, Any]:
    path = content_dir / name
    if not path.exists():
        raise ImportError_(f"Content-Datei fehlt: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _j(value: Any) -> str:
    """JSON-Spalten immer als kompakten Text schreiben."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- vocabularies


def import_vocabularies(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for voc in data["vocabularies"]:
        conn.execute(
            "INSERT INTO vocabularies (vocabulary, vocabulary_kind, spec_section, description)"
            " VALUES (?, ?, ?, ?)",
            (voc["vocabulary"], voc["vocabulary_kind"], voc.get("spec_section"), voc["description"]),
        )
        rep.add("vocabularies", 1)
        for term in voc["terms"]:
            conn.execute(
                "INSERT INTO vocabulary_terms (vocabulary, term, label_de, notes)"
                " VALUES (?, ?, ?, ?)",
                (voc["vocabulary"], term["term"], term.get("label_de"), term.get("notes")),
            )
            rep.add("vocabulary_terms", 1)


def import_vocabulary_terms(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    """Zusaetzliche Terme in bereits angelegte Vokabulare eintragen.

    Ein Zusatzpaket darf kein neues Vokabular anlegen. Die Liste der
    Vokabulare stammt aus §79ff.; sie zu erweitern waere eine fachliche
    Entscheidung, die nicht nebenbei beim Import eines Aufgabenpakets
    fallen soll (§1).
    """
    bekannt = {r["vocabulary"] for r in conn.execute("SELECT vocabulary FROM vocabularies")}
    for term in data["vocabulary_terms"]:
        if term["vocabulary"] not in bekannt:
            raise ImportError_(
                f"vocabulary_terms: '{term['vocabulary']}' ist kein bestehendes"
                " Vokabular. Zusatzpakete erweitern Vokabulare, sie legen keine an."
            )
        conn.execute(
            "INSERT INTO vocabulary_terms (vocabulary, term, label_de, notes)"
            " VALUES (?, ?, ?, ?)",
            (term["vocabulary"], term["term"], term.get("label_de"), term.get("notes")),
        )
        rep.add("vocabulary_terms", 1)


# --------------------------------------------------------------------- sources


def import_sources(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for src in data["sources"]:
        conn.execute(
            "INSERT INTO sources (source_id, author_or_org, title, year, source_type,"
            " url_or_doi, access_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                src["source_id"], src["author_or_org"], src["title"], src.get("year"),
                src["source_type"], src.get("url_or_doi"), src.get("access_date"),
                src.get("notes"),
            ),
        )
        rep.add("sources", 1)


# ---------------------------------------------------------------- competencies


def import_competencies(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    rows = data["competencies"]
    # Durchgang 1: ohne parent_id, damit die Reihenfolge in der Datei frei ist.
    for c in rows:
        conn.execute(
            "INSERT INTO competencies (competency_id, name, description, domain, leitidee,"
            " parent_id, grade_reference_min, grade_reference_max, is_mvp, source_id,"
            " evidence_status, spec_section) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
            (
                c["competency_id"], c["name"], c.get("description"), c["domain"], c["leitidee"],
                c.get("grade_reference_min"), c.get("grade_reference_max"),
                int(c.get("is_mvp", 0)), c.get("source_id"), c["evidence_status"],
                c.get("spec_section"),
            ),
        )
        rep.add("competencies", 1)
    # Durchgang 2: Hierarchie nachtragen.
    for c in rows:
        if c.get("parent_id"):
            conn.execute(
                "UPDATE competencies SET parent_id = ? WHERE competency_id = ?",
                (c["parent_id"], c["competency_id"]),
            )
    _assert_no_parent_cycle(conn)


def _assert_no_parent_cycle(conn: sqlite3.Connection) -> None:
    parents = {
        r["competency_id"]: r["parent_id"]
        for r in conn.execute("SELECT competency_id, parent_id FROM competencies")
    }
    for start in parents:
        seen, node = set(), start
        while node is not None:
            if node in seen:
                raise ImportError_(f"Zyklus in competencies.parent_id bei {start}")
            seen.add(node)
            node = parents.get(node)


# ------------------------------------------------------------------- relations


def import_relations(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for r in data["relations"]:
        # §114: ohne relation_type und evidence_status kein Import.
        if not r.get("relation_type") or not r.get("evidence_status"):
            raise ImportError_(
                f"§114 verletzt: Relation {r.get('relation_id')} ohne relation_type"
                " oder evidence_status"
            )
        conn.execute(
            "INSERT INTO relations (relation_id, source_competency, target_competency,"
            " relation_type, strength, evidence_status, source_id, bidirectional, notes,"
            " spec_section) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["relation_id"], r["source_competency"], r["target_competency"],
                r["relation_type"], r.get("strength"), r["evidence_status"],
                r.get("source_id"), int(r.get("bidirectional", 0)), r.get("notes"),
                r.get("spec_section"),
            ),
        )
        rep.add("relations", 1)


# ---------------------------------------------------------------- task_families


def import_task_families(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for f in data["task_families"]:
        conn.execute(
            "INSERT INTO task_families (task_family_id, name, family_type,"
            " primary_competency, diagnostic_purpose, notes, spec_section)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f["task_family_id"], f["name"], f["family_type"], f.get("primary_competency"),
                f["diagnostic_purpose"], f.get("notes"), f.get("spec_section"),
            ),
        )
        rep.add("task_families", 1)


# ----------------------------------------------------------------------- tasks


def import_tasks(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    defaults = data.get("defaults", {})
    rows = data["tasks"]

    def get(task: dict, key: str) -> Any:
        return task.get(key, defaults.get(key))

    for t in rows:
        conn.execute(
            "INSERT INTO tasks (task_id, task_family_id, title, primary_competency,"
            " secondary_competencies, primary_leitidee, secondary_leitideen,"
            " process_competencies, prerequisites, internal_difficulty, calibration_status,"
            " representation_mode, interaction_mode, question_form, language_demand, task_prompt,"
            " task_payload, correct_answer, scoring_rule, estimated_time_seconds,"
            " source_type, source_reference, task_purpose, parallel_item_id,"
            " grade_reference_min, grade_reference_max, spec_section)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
            " NULL, ?, ?, ?)",
            (
                t["task_id"], t.get("task_family_id"), t["title"], t["primary_competency"],
                _j(get(t, "secondary_competencies")), get(t, "primary_leitidee"),
                _j(get(t, "secondary_leitideen")), _j(get(t, "process_competencies")),
                _j(get(t, "prerequisites")), t["internal_difficulty"],
                get(t, "calibration_status"), t["representation_mode"], t["interaction_mode"],
                t["question_form"],
                get(t, "language_demand"), t["task_prompt"], _j(t.get("task_payload", {})),
                _j(t["correct_answer"]), t["scoring_rule"], get(t, "estimated_time_seconds"),
                get(t, "source_type"),
                f"MVP V1.0 {t['spec_section']}" if t.get("spec_section") else None,
                t["task_purpose"],
                get(t, "grade_reference_min"), get(t, "grade_reference_max"),
                t.get("spec_section"),
            ),
        )
        rep.add("tasks", 1)

        for field_name in FEATURE_KINDS:
            values = t.get(field_name, defaults.get(field_name, []))
            for value in values:
                conn.execute(
                    "INSERT INTO task_features (task_id, feature_kind, feature_value)"
                    " VALUES (?, ?, ?)",
                    (t["task_id"], FEATURE_KIND_VOCABULARY[field_name], value),
                )
                rep.add("task_features", 1)

    # Durchgang 2: Parallelitems nachtragen (Vorwaertsreferenzen).
    for t in rows:
        if t.get("parallel_item_id"):
            conn.execute(
                "UPDATE tasks SET parallel_item_id = ? WHERE task_id = ?",
                (t["parallel_item_id"], t["task_id"]),
            )

    # Sekundaerkompetenzen und Voraussetzungen gegen competencies pruefen -
    # das Schema kann JSON-Arrays nicht per Fremdschluessel absichern.
    known = {r["competency_id"] for r in conn.execute("SELECT competency_id FROM competencies")}
    for t in rows:
        for key in ("secondary_competencies", "prerequisites"):
            for cid in t.get(key, defaults.get(key, [])):
                if cid not in known:
                    raise ImportError_(
                        f"{t['task_id']}.{key} verweist auf unbekannte Kompetenz {cid}"
                    )
    _check_json_array_vocabulary(conn, rows, defaults)


def _check_json_array_vocabulary(conn: sqlite3.Connection, rows: list[dict], defaults: dict) -> None:
    """process_competencies und secondary_leitideen gegen die Vokabulare pruefen."""
    for column, vocabulary in (
        ("process_competencies", "PROCESS_COMPETENCY"),
        ("secondary_leitideen", "LEITIDEE"),
    ):
        allowed = {
            r["term"]
            for r in conn.execute(
                "SELECT term FROM vocabulary_terms WHERE vocabulary = ?", (vocabulary,)
            )
        }
        for t in rows:
            for value in t.get(column, defaults.get(column, [])):
                if value not in allowed:
                    raise ImportError_(
                        f"{t['task_id']}.{column}: '{value}' ist kein Term in {vocabulary}"
                    )


# ----------------------------------------------------------------- task_routes


def import_task_routes(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for r in data["task_routes"]:
        conn.execute(
            "INSERT INTO task_routes (route_id, source_task, condition, target_task,"
            " target_competency, reason, priority, enabled, requires_status,"
            " requires_hypothesis, notes, spec_section)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["route_id"], r["source_task"], r["condition"], r.get("target_task"),
                r.get("target_competency"), r["reason"], r["priority"],
                int(r.get("enabled", 1)), r.get("requires_status"),
                r.get("requires_hypothesis"), r.get("notes"), r.get("spec_section"),
            ),
        )
        rep.add("task_routes", 1)


# ----------------------------------------------------------------- error_codes


def import_error_codes(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for e in data["error_codes"]:
        note = e.get("note")
        description = e.get("description")
        conn.execute(
            "INSERT INTO error_codes (error_code, label_de, description,"
            " is_observation_only, spec_section) VALUES (?, ?, ?, 1, ?)",
            (e["error_code"], e["label_de"], description, e.get("spec_section")),
        )
        rep.add("error_codes", 1)
        if description is None:
            rep.warnings.append(
                f"error_codes.{e['error_code']}: description UNDEFINED - {note or 'ohne Hinweis'}"
            )


# --------------------------------------------------------------- system_config


def import_config(conn: sqlite3.Connection, data: dict, rep: ImportReport) -> None:
    for c in data["config"]:
        conn.execute(
            "INSERT INTO system_config (config_key, value, value_type, status,"
            " spec_section, description) VALUES (?, ?, ?, ?, ?, ?)",
            (
                c["config_key"], c.get("value"), c["value_type"], c["status"],
                c.get("spec_section"), c["description"],
            ),
        )
        rep.add("system_config", 1)
        if c.get("value") is None:
            rep.warnings.append(f"system_config.{c['config_key']}: value UNDEFINED (§1)")


# ---------------------------------------------------------------- Zusatzpakete


#: Dateien eines Zusatzpakets. Jede ist optional - ein Paket, das nur Knoten
#: beitraegt, braucht keine Aufgaben, und umgekehrt.
EXTENSION_STEPS = (
    ("vocabulary_terms.json", import_vocabulary_terms),
    ("sources.json", import_sources),
    ("competencies.json", import_competencies),
    ("relations.json", import_relations),
    ("task_families.json", import_task_families),
    ("tasks.json", import_tasks),
    ("task_routes.json", import_task_routes),
)


def import_extension(conn: sqlite3.Connection, pack_dir: Path, rep: ImportReport) -> None:
    """Ein Zusatzpaket aus einem Unterverzeichnis von content/ importieren.

    Fehlt das Verzeichnis, passiert nichts: das Paket ist dann schlicht nicht
    installiert. Fehlt dagegen eine einzelne Datei innerhalb eines
    vorhandenen Verzeichnisses, ist das kein Fehler, sondern bedeutet, dass
    das Paket zu dieser Tabelle nichts beitraegt.
    """
    if not pack_dir.is_dir():
        return
    for filename, fn in EXTENSION_STEPS:
        path = pack_dir / filename
        if not path.exists():
            continue
        fn(conn, json.loads(path.read_text(encoding="utf-8")), rep)


# ------------------------------------------------------------------ Gesamtlauf


def import_all(conn: sqlite3.Connection, content_dir: Path) -> ImportReport:
    rep = ImportReport()
    steps = (
        ("vocabularies.json", import_vocabularies),
        ("sources.json", import_sources),
        ("competencies.json", import_competencies),
        ("relations.json", import_relations),
        ("task_families.json", import_task_families),
        ("tasks.json", import_tasks),
        ("task_routes.json", import_task_routes),
        ("error_codes.json", import_error_codes),
        ("config.json", import_config),
    )
    for filename, fn in steps:
        fn(conn, _load(content_dir, filename), rep)

    for name in EXTENSIONS:
        import_extension(conn, content_dir / name, rep)

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise ImportError_(
            f"{len(violations)} Fremdschluesselverletzung(en) nach dem Import: "
            + ", ".join(f"{v[0]}/{v[3]}" for v in violations[:10])
        )
    return rep
