"""Kommandozeile fuer Sprint 1-3.

    python -m mathkomp build            Schema anlegen und Content importieren
    python -m mathkomp validate         Pruefregeln ausfuehren
    python -m mathkomp report           Uebersicht ueber den Content
    python -m mathkomp routes ZO06-D2-S-A   Ausgehende Routen einer Aufgabe
    python -m mathkomp session KIND-01  Interaktiver Durchlauf (§105)
    python -m mathkomp student KIND-01  Lehrkraftansicht (§106)
    python -m mathkomp ui               Analyseoberflaeche im Browser
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import db, importer, validate

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "mathkomp.sqlite3"
DEFAULT_CONTENT = ROOT / "content"


def cmd_build(args: argparse.Namespace) -> int:
    dbpath = Path(args.db)
    if dbpath.exists():
        if not args.force:
            print(f"{dbpath} existiert bereits. Mit --force neu aufbauen.", file=sys.stderr)
            return 2
        dbpath.unlink()

    conn = db.connect(dbpath)
    db.init_schema(conn)

    missing = set(db.REQUIRED_TABLES_SPEC_78) - db.table_names(conn)
    if missing:
        print(f"Schema unvollstaendig, §78 verlangt: {sorted(missing)}", file=sys.stderr)
        return 1

    try:
        with db.transaction(conn):
            report = importer.import_all(conn, Path(args.content))
    except importer.ImportError_ as exc:
        print(f"Import abgebrochen: {exc}", file=sys.stderr)
        return 1

    print(f"Datenbank: {dbpath}")
    print(f"Tabellen:  {len(db.table_names(conn))} (§78 verlangt {len(db.REQUIRED_TABLES_SPEC_78)})")
    print()
    for table, n in sorted(report.counts.items()):
        print(f"  {table:<22} {n:>5}")
    print(f"  {'SUMME':<22} {report.total():>5}")

    if report.warnings:
        print(f"\nUNDEFINED-Felder ({len(report.warnings)}), siehe OFFENE_FRAGEN.md:")
        for w in report.warnings:
            print(f"  - {w}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    findings = validate.run_all(conn)

    errs = [f for f in findings if f.severity == validate.ERROR]
    notes = [f for f in findings if f.severity == validate.NOTICE]

    if errs:
        print(f"FEHLER ({len(errs)}) - Verstoss gegen eine Vorgabe der Spezifikation:")
        for f in errs:
            print(f"  {f}")
        print()
    else:
        print("Keine Regelverstoesse.\n")

    if notes:
        print(f"HINWEISE ({len(notes)}) - fachliche Luecken der Spezifikation, keine Bugs:")
        for f in notes:
            print(f"  {f}")

    return 1 if errs else 0


def cmd_report(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    q = lambda sql: conn.execute(sql).fetchall()  # noqa: E731

    print("KOMPETENZEN JE LEITIDEE")
    for r in q("SELECT leitidee, COUNT(*) n, SUM(is_mvp) mvp FROM competencies"
               " GROUP BY leitidee ORDER BY leitidee"):
        print(f"  {r['leitidee']:<20} {r['n']:>3} Knoten, davon {r['mvp']} im MVP")

    print("\nAUFGABEN JE KOMPETENZ")
    for r in q("SELECT primary_competency c, COUNT(*) n FROM tasks"
               " GROUP BY primary_competency ORDER BY primary_competency"):
        print(f"  {r['c']:<32} {r['n']:>3}")

    print("\nAUFGABEN JE SCHWIERIGKEIT")
    for r in q("SELECT internal_difficulty d, COUNT(*) n FROM tasks"
               " GROUP BY internal_difficulty ORDER BY internal_difficulty"):
        print(f"  {r['d']:<6} {r['n']:>3}")

    print("\nAUFGABEN JE DARSTELLUNG (§16)")
    for r in q("SELECT representation_mode m, COUNT(*) n FROM tasks"
               " GROUP BY representation_mode ORDER BY n DESC"):
        print(f"  {r['m']:<22} {r['n']:>3}")

    print("\nAUFGABEN JE BEDIENFORM (§17)")
    for r in q("SELECT interaction_mode m, COUNT(*) n FROM tasks"
               " GROUP BY interaction_mode ORDER BY n DESC"):
        print(f"  {r['m']:<22} {r['n']:>3}")

    print("\nAUFGABEN JE ZWECK (§90)")
    for r in q("SELECT task_purpose p, COUNT(*) n FROM tasks"
               " GROUP BY task_purpose ORDER BY n DESC"):
        print(f"  {r['p']:<12} {r['n']:>3}")

    print("\nRELATIONEN JE TYP UND EVIDENZGRAD (§12, §13)")
    for r in q("SELECT relation_type t, evidence_status e, COUNT(*) n FROM relations"
               " GROUP BY relation_type, evidence_status ORDER BY relation_type"):
        print(f"  {r['t']:<24} {r['e']}  {r['n']:>3}")

    print("\nAUFGABENFAMILIEN JE TYP (§25)")
    for r in q("SELECT family_type t, COUNT(*) n FROM task_families"
               " GROUP BY family_type ORDER BY n DESC"):
        print(f"  {r['t']:<26} {r['n']:>3}")

    print("\nMERKMALE JE KLASSE (§20-23, §15)")
    for r in q("SELECT feature_kind k, COUNT(*) n, COUNT(DISTINCT feature_value) v"
               " FROM task_features GROUP BY feature_kind ORDER BY n DESC"):
        print(f"  {r['k']:<22} {r['n']:>4} Zuordnungen, {r['v']} verschiedene Werte")

    print("\nROUTEN JE BEGRUENDUNG (§67)")
    for r in q("SELECT reason, COUNT(*) n FROM task_routes GROUP BY reason ORDER BY n DESC"):
        print(f"  {r['reason']:<28} {r['n']:>3}")
    return 0


def cmd_routes(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    task = conn.execute(
        "SELECT task_id, title, internal_difficulty, representation_mode, task_purpose,"
        " parallel_item_id FROM tasks WHERE task_id = ?", (args.task_id,)
    ).fetchone()
    if task is None:
        print(f"Unbekannte Aufgabe: {args.task_id}", file=sys.stderr)
        return 2

    print(f"{task['task_id']}  {task['title']}")
    print(f"  {task['internal_difficulty']} | {task['representation_mode']}"
          f" | {task['task_purpose']}")
    if task["parallel_item_id"]:
        print(f"  Parallelitem: {task['parallel_item_id']}  (§30: falsch -> Parallelitem)")

    rows = conn.execute(
        "SELECT route_id, condition, target_task, target_competency, reason, priority,"
        " enabled, spec_section FROM task_routes WHERE source_task = ?"
        " ORDER BY priority DESC", (args.task_id,)
    ).fetchall()
    if not rows:
        print("  Keine ausgehenden Routen in task_routes.")
        return 0
    print("\n  Ausgehende Routen:")
    for r in rows:
        target = r["target_task"] or f"[Knoten] {r['target_competency']}"
        flag = "" if r["enabled"] else "  (deaktiviert)"
        print(f"    {r['route_id']}  {r['condition']:<24} -> {target}")
        print(f"           {r['reason']}, Prioritaet {r['priority']}, {r['spec_section']}{flag}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Sprint 12: die sechs Testfaelle aus §98 bis §103."""
    from . import simulation
    from .config import Config

    conn = db.connect(args.db)
    cfg = Config(conn)
    namen = {"A": "§98 hohe Kompetenz", "B": "§99 grundlegende Schwierigkeit",
             "C": "§100 Repraesentation", "D": "§101 Zahlenabhaengigkeit",
             "E1": "§102 gleiche Antwort, Darstellungsroute",
             "E2": "§102 gleiche Antwort, Grundvorstellungsroute",
             "F1": "§103 Phase 1: sichern und parken",
             "F2": "§103 Phase 2: nach Reaktivierung"}

    traces = simulation.run_all(conn, cfg)
    auswahl = [args.case] if args.case else list(traces)
    for key in auswahl:
        if key not in traces:
            print(f"Unbekannter Testfall: {key}. Verfuegbar: {', '.join(traces)}",
                  file=sys.stderr)
            return 2
        print("=" * 78)
        print(f"TESTFALL {key} - {namen.get(key, '')}")
        print("=" * 78)
        print(simulation.render_trace(traces[key]))
        print()

    pfade = {k: tuple(t.task_ids) for k, t in traces.items() if k != "F2"}
    verschieden = len(set(pfade.values())) == len(pfade)
    print(f"§123 Kriterium 20 - unterschiedliche Pfade: "
          f"{'erfuellt' if verschieden else 'NICHT erfuellt'}")
    if not args.no_conn_commit:
        conn.commit()
    return 0


def cmd_student(args: argparse.Namespace) -> int:
    """§106 Lehrkraftansicht, §117/§118 Facetten, §89 Entscheidungsprotokoll."""
    from . import teacher
    from .clock import Clock
    from .config import Config

    conn = db.connect(args.db)
    exists = conn.execute(
        "SELECT 1 FROM students WHERE student_id = ?", (args.student_id,)).fetchone()
    if not exists:
        vorhanden = [r["student_id"] for r in conn.execute(
            "SELECT student_id FROM students ORDER BY student_id")]
        print(f"Unbekannte Schueler:in: {args.student_id}."
              f" Vorhanden: {', '.join(vorhanden) or 'keine'}", file=sys.stderr)
        return 2

    cfg, clock = Config(conn), Clock()
    if args.trail:
        print(teacher.decision_trail(conn, args.student_id))
    elif args.profile:
        print(teacher.profile_summary(conn, args.student_id))
    else:
        print(teacher.render(teacher.report(conn, args.student_id, cfg, clock)))
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    """§105 Schueler:innenansicht: Aufgabe, Interaktion, Antwort, Feedback."""
    from . import interactive

    conn = db.connect(args.db)
    if not db.table_names(conn):
        print("Keine Datenbank. Zuerst: python -m mathkomp build", file=sys.stderr)
        return 2

    focus = set(args.focus) if args.focus else None
    if focus:
        known = {r["competency_id"] for r in conn.execute(
            "SELECT competency_id FROM competencies")}
        unknown = focus - known
        if unknown:
            print(f"Unbekannte Kompetenz: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2

    return interactive.run(conn, args.student_id, grade=args.grade, focus=focus,
                           diagnose=args.diagnose, show_solution=args.loesung,
                           max_tasks=args.max_tasks)


def cmd_ui(args: argparse.Namespace) -> int:
    """Analyseoberflaeche im Browser (§106, §116)."""
    from . import server

    dbpath = Path(args.db)
    if not dbpath.exists():
        print(f"Keine Datenbank unter {dbpath}. Zuerst: py -m mathkomp build",
              file=sys.stderr)
        return 2
    try:
        server.serve(dbpath, host=args.host, port=args.port)
    except (FileNotFoundError, OSError) as exc:
        print(f"Server nicht gestartet: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathkomp", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Pfad zur SQLite-Datei")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="Schema anlegen und Content importieren")
    p.add_argument("--content", default=str(DEFAULT_CONTENT))
    p.add_argument("--force", action="store_true", help="bestehende Datenbank ersetzen")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("validate", help="Pruefregeln ausfuehren")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("report", help="Uebersicht ueber den Content")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("routes", help="Routen einer Aufgabe anzeigen")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_routes)

    p = sub.add_parser("simulate", help="die sechs Testfaelle aus §98-§103 durchspielen")
    p.add_argument("--case", help="nur ein Testfall: A B C D E1 E2 F1 F2")
    p.add_argument("--no-conn-commit", action="store_true",
                   help="Simulationsdaten nicht in die Datenbank schreiben")
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("session", help="interaktiver Durchlauf mit einer Schueler:in (§105)")
    p.add_argument("student_id", help="pseudonyme ID, frei waehlbar (§86: kein Klarname)")
    p.add_argument("--grade", type=int, help="Klassenstufe als Bezugsrahmen (§87)")
    p.add_argument("--focus", nargs="+", metavar="COMPETENCY",
                   help="aktiven Teilgraphen einschraenken (§3/§74)")
    p.add_argument("--diagnose", action="store_true",
                   help="Fehlercodes, Status, Hypothesen mitschreiben (§106, nicht fuer die Schueler:innenansicht)")
    p.add_argument("--loesung", action="store_true",
                   help="bei falscher Antwort die richtige nennen")
    p.add_argument("--max-tasks", type=int, dest="max_tasks",
                   help="nach n Aufgaben beenden")
    p.set_defaults(func=cmd_session)

    p = sub.add_parser("student", help="Lehrkraftansicht einer Schueler:in (§106)")
    p.add_argument("student_id")
    p.add_argument("--profile", action="store_true", help="Zielbild nach §118")
    p.add_argument("--trail", action="store_true", help="Entscheidungsprotokoll nach §89")
    p.set_defaults(func=cmd_student)

    p = sub.add_parser("ui", help="Analyseoberflaeche im Browser")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1",
                   help="Voreinstellung bewusst nur lokal (§86)")
    p.set_defaults(func=cmd_ui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
