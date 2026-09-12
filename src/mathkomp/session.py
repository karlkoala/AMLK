"""Ablaufsteuerung. Setzt §119 und §120 zusammen.

§120  function processAttempt(attempt):
          storeRawAttempt(attempt)
          result = score(attempt)
          errors = classifyObservableErrors(result)
          evidence = createEvidence(result, errors)
          updateStudentState(evidence)
          updateHypotheses(evidence)
          checkParkConditions()
          checkReactivationConditions()
          return nextTask(student)

Die Reihenfolge ist bindend und wird hier eingehalten. Sie ist auch die
Reihenfolge der drei Ebenen aus §66: erst Rohbeobachtung, dann Evidenz, dann
Hypothese. Wer Hypothesen vor der Evidenz aktualisiert, vermischt die Ebenen.

§3 ist bindend: das System trifft keine endgueltigen Entscheidungen. Diese
Klasse liefert Beobachtungen, Evidenz, Muster, offene Hypothesen und einen
Vorschlag fuer den naechsten Schritt. Die Lehrkraft kann jeden davon
uebersteuern (parking.set_blocked, task_routes.enabled, system_config).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import attempts, evidence, hypotheses, parking, renderer, routing, state
from .attempts import Submission
from .clock import Clock
from .config import Config
from .hypotheses import HypothesisAction
from .parking import Transition
from .routing import Decision


@dataclass
class Turn:
    """Ein vollstaendiger Durchlauf: Antwort rein, naechste Aufgabe raus."""
    attempt_id: str
    task_id: str
    is_correct: bool
    error_codes: list[str]
    evidence_created: list[str] = field(default_factory=list)
    state_changes: list[tuple[str, str | None, str]] = field(default_factory=list)
    hypothesis_actions: list[HypothesisAction] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    next_decision: Decision | None = None


class Session:
    def __init__(self, conn: sqlite3.Connection, student_id: str, clock: Clock,
                 cfg: Config | None = None, grade_reference: int | None = None,
                 focus: set[str] | None = None) -> None:
        self.conn = conn
        self.student_id = student_id
        self.clock = clock
        self.cfg = cfg or Config(conn)
        #: Einschraenkung des aktiven Teilgraphen durch die Lehrkraft (§3).
        self.focus = focus
        attempts.ensure_student(conn, student_id, clock, grade_reference)
        self._last: dict | None = None

    # ------------------------------------------------------------- Auswahl

    def next_task(self) -> Decision:
        """§119."""
        return routing.next_task(self.conn, self.student_id, self.cfg, self.clock,
                                 self._last, self.focus)

    def render_next(self) -> tuple[Decision, dict | None]:
        decision = self.next_task()
        if decision.selected_task is None:
            return decision, None
        task = attempts.load_task(self.conn, decision.selected_task)
        return decision, renderer.render(task)

    # ------------------------------------------------------------ Abgabe

    def submit(self, submission: Submission) -> Turn:
        """§120, in der dort vorgegebenen Reihenfolge."""
        # 1. Rohdaten und Beobachtung (Ebene 1 von §66).
        recorded = attempts.record(self.conn, self.student_id, submission, self.clock)
        turn = Turn(attempt_id=recorded.attempt_id, task_id=recorded.task_id,
                    is_correct=recorded.is_correct, error_codes=recorded.error_codes)

        # 2. Evidenz (Ebene 2 von §66).
        created = evidence.create(self.conn, self.student_id, recorded, self.clock, self.cfg)
        turn.evidence_created = [e.evidence_id for e in created]

        # 3. Zustand fortschreiben - fuer jede beruehrte Kompetenz.
        touched = state.touched_competencies(self.conn, self.student_id, recorded.attempt_id)
        for competency in touched:
            result = state.recompute(self.conn, self.student_id, competency, self.cfg, self.clock)
            if result.previous_status != result.status:
                turn.state_changes.append(
                    (competency, result.previous_status, result.status))

        # 4. Hypothesen (Ebene 3 von §66) - erst NACH der Evidenz.
        for competency in touched:
            turn.hypothesis_actions.extend(
                hypotheses.detect(self.conn, self.student_id, competency, self.cfg, self.clock))

        # 5. Parken (§38) und Reaktivieren (§39).
        for competency in touched:
            parked = parking.check_park(self.conn, self.student_id, competency,
                                        self.cfg, self.clock)
            if parked:
                turn.transitions.append(parked)
            reactivated = parking.check_reactivation(self.conn, self.student_id, competency,
                                                    self.cfg, self.clock)
            if reactivated:
                turn.transitions.append(reactivated)

        # 6. Kontext fuer die naechste Auswahl (§30: Fehlerreplikation).
        task = attempts.load_task(self.conn, recorded.task_id)
        self._last = {
            "task_id": recorded.task_id,
            "competency_id": task["primary_competency"],
            "difficulty": task["internal_difficulty"],
            "representation": task["representation_mode"],
            "is_correct": recorded.is_correct,
            "error_codes": recorded.error_codes,
            "repeated": self._is_repeated_pattern(task, recorded),
        }

        # 7. return nextTask(student)
        turn.next_decision = self.next_task()
        return turn

    def _is_repeated_pattern(self, task: dict, recorded) -> bool:
        """§30: erst wenn ein Fehler mit aehnlichem Fehlermuster wiederholt
        auftritt, liegt ein reproduzierbares Muster vor.

        Aehnlich heisst hier: derselbe Fehlercode, in derselben Aufgabenfamilie
        oder an derselben Aufgabe. Die Aufgabenfamilie ist der richtige Rahmen,
        weil §25 das Parallelitem genau dafuer definiert - "Ziel: Fehler
        replizieren".
        """
        if recorded.is_correct or not recorded.error_codes:
            return False
        codes = set(recorded.error_codes) - {"ERR_SELF_CORRECTED"}
        if not codes:
            return False

        rows = self.conn.execute(
            "SELECT a.attempt_id, t.task_family_id, a.task_id FROM task_attempts a"
            " JOIN tasks t ON t.task_id = a.task_id"
            " WHERE a.student_id = ? AND a.is_correct = 0 AND a.attempt_id <> ?"
            " AND (t.task_family_id IS NOT NULL AND t.task_family_id = ?"
            "      OR a.task_id = ?)",
            (self.student_id, recorded.attempt_id, task["task_family_id"], task["task_id"]),
        ).fetchall()
        for row in rows:
            earlier = {
                r["error_code"] for r in self.conn.execute(
                    "SELECT error_code FROM attempt_error_codes WHERE attempt_id = ?",
                    (row["attempt_id"],))
            }
            if codes & earlier:
                return True
        return False

    # ------------------------------------------------------------- Auskunft

    def last_context(self) -> dict | None:
        return self._last

    def state_snapshot(self) -> dict[str, dict]:
        return state.load(self.conn, self.student_id)

    def open_hypotheses(self) -> list[dict]:
        return hypotheses.open_hypotheses(self.conn, self.student_id)
