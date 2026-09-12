"""Der Datenvertrag zur Oberflaeche (api.py).

Die Oberflaeche darf keine fachlichen Entscheidungen treffen. Technisch heisst
das: sie darf nichts ableiten muessen. Geprueft wird hier deshalb nicht in
erster Linie, ob ein Feld existiert, sondern ob die Oberflaeche mit dem
Gelieferten ohne eigene Regel auskommt - und ob sie nichts geliefert bekommt,
das sie nach §117 gar nicht zeigen duerfte.

Die eigenen Schuelerkennungen (API-*) statt der Testfaelle aus §98 bis §103
sind Absicht: test_testfaelle.py spielt SIM-A bis SIM-F in derselben
Sitzungsdatenbank durch, und zwei Laeufe unter derselben Kennung wuerden
einander die Beobachtungen verfaelschen.
"""

from __future__ import annotations

import pytest

from mathkomp import api, simulation
from mathkomp.clock import FixedClock
from mathkomp.config import Config

#: Die fuenfzehn Objektarten des Implementierungsauftrags und das Feld, unter
#: dem der Vertrag sie fuehrt. TaskFeature haengt an der Aufgabe,
#: HypothesisEvidence und HypothesisTest haengen an der Hypothese - dafuer
#: stehen die beiden Tests direkt darunter.
OBJEKTE = {
    "StudentProfile": ("profil", "student"),
    "CompetencyNode": ("katalog", "competency_nodes"),
    "CompetencyState": ("profil", "competency_states"),
    "Evidence": ("profil", "evidence"),
    "Observation": ("profil", "observations"),
    "ErrorObservation": ("profil", "error_observations"),
    "ErrorPattern": ("profil", "error_patterns"),
    "Task": ("katalog", "tasks"),
    "RepresentationEvidence": ("profil", "representation_evidence"),
    "ProcessCompetencyEvidence": ("profil", "process_competency_evidence"),
    "Hypothesis": ("profil", "hypotheses"),
    "RoutingDecision": ("profil", "routing_decisions"),
}


@pytest.fixture(scope="module")
def cfg(conn):
    return Config(conn)


@pytest.fixture(scope="module")
def lauf(conn):
    """Ein Darstellungsfall nach dem Muster aus §100.

    Echte Engine-Ausgabe: mehrere Fehlerbeobachtungen zu einem Code, ein daraus
    reproduziertes Muster, konkurrierende Hypothesen und ein
    Entscheidungsprotokoll. Nichts davon ist hier gesetzt.
    """
    lokal = Config(conn)
    lokal.override("routing.start_difficulty", "D2")
    simulation.run(conn, "API-REPR", simulation.policy_representation, FixedClock(),
                   focus={"ZO06_PLACE_VALUE"}, max_turns=16, cfg=lokal,
                   first_task="ZO06-D2-S-A")
    return "API-REPR"


@pytest.fixture(scope="module")
def profil(conn, cfg, lauf):
    return api.student_profile(conn, lauf, cfg, FixedClock())


@pytest.fixture(scope="module")
def katalog(conn):
    return api.catalog(conn)


# ------------------------------------------------------- Vollstaendigkeit


def test_alle_geforderten_objektarten_werden_geliefert(profil, katalog):
    quelle = {"profil": profil, "katalog": katalog}
    fehlend = [name for name, (wo, feld) in OBJEKTE.items() if feld not in quelle[wo]]
    assert not fehlend, f"Objektarten ohne Entsprechung im Vertrag: {fehlend}"


def test_taskfeature_haengt_an_der_aufgabe(katalog):
    """TaskFeature ist keine eigene Liste, sondern gehoert zur Aufgabe - sonst
    muesste die Oberflaeche zwei Listen zusammenfuehren."""
    aufgaben = katalog["tasks"]
    mit_merkmalen = [a for a in aufgaben if a["features"]]
    assert len(mit_merkmalen) > len(aufgaben) // 2, "Die Aufgabenbank ist beschrieben"
    for aufgabe in mit_merkmalen:
        for art, werte in aufgabe["features"].items():
            assert art and isinstance(werte, list) and werte


def test_hypothesenevidenz_und_pruefung_haengen_an_der_hypothese(profil):
    assert profil["hypotheses"], "Der Darstellungsfall eroeffnet Hypothesen"
    for h in profil["hypotheses"]:
        assert set(h["evidence_balance"]) == {"supporting", "contradicting"}
        assert isinstance(h["supporting_evidence"], list)
        assert isinstance(h["contradicting_evidence"], list)
        assert set(h["hypothesis_test"]) == {"task_id", "state", "is_active",
                                             "spec_section"}
        # `is_active` ist die Regel, die die Oberflaeche sonst dreimal
        # nachgebaut haette - und zweimal falsch, weil der Status fehlte.
        assert h["hypothesis_test"]["is_active"] == (
            h["hypothesis_test"]["state"] == "PLANNED"
            and h["status"] in api.ACTIVE_HYPOTHESIS_STATUS)


def test_aktive_pruefung_und_naechste_frage_sagen_dasselbe(profil):
    """Dieselbe Frage - wird diese Hypothese gerade geprueft? - darf nicht von
    zwei Stellen verschieden beantwortet werden. `next_question` und
    `hypothesis_test.is_active` stammen jetzt aus derselben Bedingung."""
    aus_frage = {e["hypothesis_id"] for z in profil["competency_states"]
                 for e in z["next_question"]["from_hypothesis_tests"]}
    aus_pruefung = {h["hypothesis_id"] for h in profil["hypotheses"]
                    if h["hypothesis_test"]["is_active"]}
    assert aus_frage == aus_pruefung


# --------------------------------------------------------- Keine eigenen Regeln


def test_ressourcenklasse_folgt_der_konfiguration(conn):
    """§38 sagt, aus welchem Status heraus geparkt wird; daran haengt, was als
    gezeigtes Koennen gilt. Stuende die Zuordnung fest verdrahtet im Vertrag,
    waere sie eine zweite fachliche Festlegung neben der Konfiguration."""
    original = Config(conn)
    enter = original.require("park.enter_status")
    assert api._resource_class_map(original)[enter] == "RESOURCE"

    anders = Config(conn)
    anders.override("park.enter_status", "UNCERTAIN")
    assert api._resource_class_map(anders)["UNCERTAIN"] == "RESOURCE", \
        "Die Gruppierung liest den Konfigurationswert nicht"


def test_jeder_status_bekommt_eine_gruppe(conn, cfg):
    """Kein Status darf durchfallen. Was keine Gruppe hat, muesste die
    Oberflaeche selbst einsortieren."""
    bekannt = {r["term"] for r in conn.execute(
        "SELECT term FROM vocabulary_terms WHERE vocabulary = 'COMPETENCY_STATUS'")}
    zuordnung = api._resource_class_map(cfg)
    assert not bekannt - set(zuordnung), f"ohne Gruppe: {sorted(bekannt - set(zuordnung))}"
    assert set(zuordnung.values()) <= set(api.RESOURCE_CLASS_LABEL)


def test_unknown_ist_kein_defizit(cfg):
    """"UNKNOWN ist ein gueltiger Zustand und kein Defizit." UNKNOWN und
    SUPPORT_FOCUS duerfen deshalb nicht in dieselbe Gruppe fallen."""
    zuordnung = api._resource_class_map(cfg)
    assert zuordnung["UNKNOWN"] == "UNCHECKED"
    assert zuordnung["SUPPORT_FOCUS"] == "OPEN"


def test_fehlermuster_nutzt_den_schwellenwert_der_engine(profil, cfg):
    """§30/§41: ab wann ein Fehler als reproduziert gilt, steht in der
    Konfiguration. Ein eigener Schwellenwert im Vertrag koennte dazu fuehren,
    dass dieselbe Beobachtung in der Oberflaeche ein Muster ist und im Routing
    keines."""
    schwelle = int(cfg.require("mastery.failure_replication_required"))
    muster = profil["error_patterns"]
    assert muster, "Der Darstellungsfall erzeugt Fehlerbeobachtungen"
    assert any(m["reproduced"] for m in muster)
    for eintrag in muster:
        assert eintrag["replication_threshold"] == schwelle
        assert eintrag["reproduced"] == (len(set(eintrag["attempts"])) >= schwelle)


def test_fehlermuster_nennt_keine_ursache_sondern_hypothesen(profil):
    """Die Grundregel der UI-Spezifikation: ein Fehlermuster wird nicht zur
    Diagnose. Ein wiederholter Zehneruebergangsfehler darf als Muster
    erscheinen - nicht als Stellenwertdefizit."""
    verboten = {"cause", "ursache", "diagnosis", "diagnose", "deficit", "defizit"}
    for eintrag in profil["error_patterns"]:
        benannt = verboten & {k.lower() for k in eintrag}
        assert not benannt, f"Fehlermuster behauptet eine Ursache: {sorted(benannt)}"
        assert "candidate_hypotheses" in eintrag
    reproduziert = [m for m in profil["error_patterns"] if m["reproduced"]]
    assert any(len(m["candidate_hypotheses"]) > 1 for m in reproduziert), \
        "Ein reproduziertes Muster ohne konkurrierende Hypothesen waere eine Ursache"


def test_hypothese_nennt_die_aufgabe_die_sie_widerlegen_wuerde(profil):
    """§115. Ob eine Hypothese pruefbar ist und was ihr dafuer fehlt, steht im
    Vertrag - die Oberflaeche sucht keine Kontrollaufgabe selbst."""
    for h in profil["hypotheses"]:
        pruefung = h["hypothesis_test"]
        assert pruefung["state"] in ("PLANNED", "DONE", "NONE")
        assert (pruefung["state"] == "NONE") == (not pruefung["task_id"])
        if pruefung["state"] == "PLANNED":
            assert pruefung["task_id"] in h["missing_evidence"]
        else:
            assert h["missing_evidence"] is None


def test_konkurrierende_hypothesen_sind_wechselseitig(profil):
    hypothesen = {h["hypothesis_id"]: h for h in profil["hypotheses"]}
    assert any(h["competing_hypotheses"] for h in hypothesen.values()), \
        "§68: zu einer Beobachtung stehen mehrere Erklaerungen nebeneinander"
    for h in hypothesen.values():
        assert h["hypothesis_id"] not in h["competing_hypotheses"]
        for anderer in h["competing_hypotheses"]:
            assert h["hypothesis_id"] in hypothesen[anderer]["competing_hypotheses"]


def test_evidenz_weist_aus_was_den_status_bewegt(profil):
    """Die Debug-Ansicht soll zeigen, welche Daten fuer eine Entscheidung nicht
    gebraucht wurden. Dafuer muss am Eintrag stehen, ob er ueberhaupt in die
    Statusrechnung eingeht (§28) - sonst muesste das Frontend die Regel
    kennen."""
    eintraege = profil["evidence"]
    assert eintraege and any(e["is_scored"] for e in eintraege)
    for e in eintraege:
        assert e["is_scored"] == (e["evidence_type"] in api.SCORED_EVIDENCE_TYPES)


def test_naechste_frage_trennt_routing_und_hypothesenpruefung(profil):
    """Beide Quellen werden benannt und nicht zu einer Empfehlung verrechnet.
    Eine Rangfolge zu bilden waere Routinglogik - die gehoert weder ins
    Frontend noch in den Vertrag zur Oberflaeche."""
    for zustand in profil["competency_states"]:
        frage = zustand["next_question"]
        assert set(frage) == {"from_routing", "routing_reason", "from_hypothesis_tests"}
        for test in frage["from_hypothesis_tests"]:
            assert set(test) == {"hypothesis_id", "task_id", "description"}


def test_offene_entscheidung_wird_als_solche_ausgewiesen(conn, cfg):
    """Die zuletzt protokollierte Entscheidung ist die noch offene, solange
    ihre Aufgabe nicht bearbeitet wurde. Ohne dieses Feld muesste die
    Oberflaeche entweder selbst vergleichen oder - schlimmer - next_task()
    aufrufen und damit beim blossen Ansehen eine Entscheidung protokollieren.
    """
    simulation.run(conn, "API-OFFEN", simulation.policy_high_competence,
                   FixedClock(), max_turns=2, cfg=Config(conn))
    profil = api.student_profile(conn, "API-OFFEN", cfg, FixedClock())
    offen = profil["next_decision"]
    assert offen is not None
    assert offen["decision_id"] == profil["routing_decisions"][-1]["decision_id"]
    bearbeitet = {b["task_id"] for b in profil["observations"]}
    assert offen["is_pending"] == bool(
        offen["selected_task"] and offen["selected_task"] not in bearbeitet)


def test_jede_entscheidung_traegt_ihre_begruendung(profil):
    """§89: das Protokoll muss die benutzten Daten, die verworfenen
    Alternativen und die Gewichtung enthalten. Die Debug-Ansicht zeigt genau
    diese Felder."""
    assert profil["routing_decisions"]
    for d in profil["routing_decisions"]:
        assert isinstance(d["evidence_used"], list)
        assert isinstance(d["hypothesis_used"], list)
        assert isinstance(d["alternatives_considered"], list)
        assert isinstance(d["score_breakdown"], dict)
        assert d["rule_triggered"]


# ---------------------------------------------------------------- §86, §117, §62


def test_profil_gibt_nur_pseudonyme_schuelerdaten_heraus(profil):
    """§86. Was die Schnittstelle nicht herausgibt, kann keine Ansicht zeigen -
    und kein spaeterer Umbau der Oberflaeche versehentlich sichtbar machen."""
    assert set(profil["student"]) <= {"student_id", "created_at", "grade_reference"}


def test_profil_enthaelt_keinen_gesamtwert(profil):
    """§117: keine Prozentwerte, kein Gesamtscore, kein
    Klassenstufenaequivalent. Am wirksamsten verhindert, indem so etwas gar
    nicht erst geliefert wird."""
    verboten = ("percent", "prozent", "overall", "gesamt", "total_score",
                "grade_equivalent", "klassenstufe", "mastery_level", "ability")
    gefunden = []

    def pruefe(knoten, pfad):
        if isinstance(knoten, dict):
            for schluessel, wert in knoten.items():
                treffer = [v for v in verboten if v in schluessel.lower()]
                if treffer:
                    gefunden.append(f"{pfad}.{schluessel} ({', '.join(treffer)})")
                pruefe(wert, f"{pfad}.{schluessel}")
        elif isinstance(knoten, list):
            for eintrag in knoten:
                pruefe(eintrag, f"{pfad}[]")

    pruefe(profil, "profil")
    assert not gefunden, "Felder, die nach einem Gesamtwert aussehen: " + "; ".join(gefunden)


def test_zeit_wird_geliefert_aber_nicht_als_evidenz(cfg, profil):
    """§62: Zeit wird gespeichert und nicht ausgewertet. Die Oberflaeche zeigt
    sie deshalb mit Vorbehalt - die Zusicherung selbst steht in der Datenbank
    und nicht in einem Kommentar im Frontend.

    Die Simulation misst keine Zeiten; geprueft wird deshalb, dass das Feld im
    Vertrag steht und dass kein Evidenzeintrag es verwendet hat."""
    assert profil["observations"]
    assert all("time_seconds" in b for b in profil["observations"])
    assert cfg.require("evidence.time_seconds_used_for_inference") is False


# ------------------------------------------------------------------ Vokabular


def _vokabularspalten(conn) -> list[tuple[str, str, str]]:
    """(Tabelle, Vokabularspalte, Wertspalte) fuer jeden Fremdschluessel auf
    vocabulary_terms.

    Das Schema verknuepft jede Vokabularspalte ueber einen zusammengesetzten
    Fremdschluessel mit ihrem Vokabular (die generierte ``_v_*``-Spalte). Die
    Liste wird daraus gelesen und nicht abgeschrieben: kommt spaeter eine
    Spalte dazu, prueft der Test sie ohne Zutun mit.
    """
    tabellen = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    out = []
    for tabelle in tabellen:
        gruppen: dict[int, dict[str, str]] = {}
        for r in conn.execute(f'PRAGMA foreign_key_list("{tabelle}")'):
            if r["table"] == "vocabulary_terms":
                gruppen.setdefault(r["id"], {})[r["to"]] = r["from"]
        for paar in gruppen.values():
            if "vocabulary" in paar and "term" in paar:
                out.append((tabelle, paar["vocabulary"], paar["term"]))
    return out


def test_jeder_vokabularwert_hat_eine_deutsche_beschriftung(conn, katalog, lauf):
    """Der eigentliche Vertrag mit der Oberflaeche (§108).

    Jeder Wert eines kontrollierten Vokabulars, der irgendwo in der Datenbank
    steht, muss im Katalog eine deutsche Beschriftung haben. Faellt dieser
    Test, muesste das Frontend uebersetzen - und jede Uebersetzung eines
    Fachbegriffs ausserhalb des Contents ist eine fachliche Festlegung an der
    falschen Stelle.
    """
    vokabular = katalog["vocabulary"]
    spalten = _vokabularspalten(conn)
    assert len(spalten) > 20, "Das Schema fuehrt deutlich mehr Vokabularspalten"

    fehlend = []
    geprueft = 0
    for tabelle, vspalte, wspalte in spalten:
        for row in conn.execute(
            f'SELECT DISTINCT "{vspalte}" AS vok, "{wspalte}" AS wert'
            f' FROM "{tabelle}" WHERE "{wspalte}" IS NOT NULL'
        ):
            geprueft += 1
            eintrag = vokabular.get(row["vok"], {}).get("terms", {}).get(row["wert"])
            if not eintrag or not eintrag["label"] or eintrag["label"] == row["wert"]:
                fehlend.append(f"{tabelle}.{wspalte} = {row['wert']} ({row['vok']})")

    assert geprueft > 100, "Zu wenig Daten fuer eine belastbare Pruefung"
    assert not fehlend, "Werte ohne deutsche Beschriftung:\n  " + "\n  ".join(sorted(fehlend))


def test_jedes_vokabular_traegt_beschreibung_und_fundstelle(katalog):
    """Die Oberflaeche schreibt an mehreren Stellen die Einschraenkung dazu -
    dass D1 bis D5 nicht die IQB-Stufen sind (§6), dass ein Profilmarker keine
    Diagnose ist (§26). Diese Saetze stammen aus dem Vokabelregister."""
    ohne = [name for name, v in katalog["vocabulary"].items()
            if not v["description"] or not v["spec_section"] or not v["terms"]]
    assert not ohne, f"Vokabulare ohne Beschreibung, Fundstelle oder Begriffe: {ohne}"


def test_aufgabenmerkmale_sind_beschriftet(katalog):
    """Auch die Merkmalsart selbst - die Oberflaeche ueberschreibt eine
    Merkmalsliste mit dem ersten Satz aus dem Vokabelregister."""
    vokabular = katalog["vocabulary"]
    fehlend = []
    for aufgabe in katalog["tasks"]:
        for art, werte in aufgabe["features"].items():
            if art not in vokabular:
                fehlend.append(f"Merkmalsart ohne Registereintrag: {art}")
                continue
            fehlend += [f"{art} = {w}" for w in werte if w not in vokabular[art]["terms"]]
    assert not fehlend, "\n  ".join(sorted(set(fehlend)))


# ------------------------------------------------------------------ Endpunkte


def test_studentenliste_bleibt_pseudonym(conn, lauf):
    liste = api.students(conn)
    assert any(s["student_id"] == lauf for s in liste)
    for s in liste:
        assert set(s) <= {"student_id", "created_at", "grade_reference", "attempt_count"}


def test_unbekannte_kennung_liefert_ein_leeres_profil(conn, cfg):
    """Kein Absturz und keine erfundene Schueler:in - ein leeres Profil, das
    die Oberflaeche als solches anzeigen kann."""
    profil = api.student_profile(conn, "GIBT-ES-NICHT", cfg, FixedClock())
    assert profil["student"] == {"student_id": "GIBT-ES-NICHT"}
    assert profil["competency_states"] == []
    assert profil["next_decision"] is None
    for klasse in ("RESOURCE", "OPEN", "UNCHECKED"):
        assert profil["resource_overview"][klasse]["competencies"] == []
