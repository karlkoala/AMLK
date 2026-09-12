-- =====================================================================
-- MVP V1.0 - Adaptives Mathematik-Lern- und Kompetenzsystem
-- Datenbankschema (Sprint 1)
--
-- Referenzen in Kommentaren (§NN) verweisen auf Abschnitte der
-- fachlichen Spezifikation "MVP V1.0", Version 1.0.
--
-- Leitprinzipien, die dieses Schema erzwingt:
--   §66  Beobachtung / Evidenz / Hypothese sind getrennte Tabellen.
--   §84  Routing liegt als Daten vor (task_routes), nicht im Code.
--   §85  CONTENT / LOGIC / USER STATE sind strikt getrennt.
--   §108 Vokabulare sind datengetrieben, nicht als CHECK-Listen fixiert.
--   §114 Keine Relation ohne relation_type und evidence_status.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- =====================================================================
-- EBENE 0: VOKABULARE
-- §108 "Keine Tabellenstruktur bauen, die ausschliesslich ZO07, ZO08
--       usw. kennt. Kompetenzen muessen datengetrieben sein."
-- Dasselbe gilt fuer alle kontrollierten Wertelisten: neue
-- task_features, evidence_types oder Rollen muessen ohne Migration
-- ergaenzbar sein. Deshalb keine CHECK (x IN (...))-Listen, sondern
-- Fremdschluessel auf vocabulary_terms.
-- =====================================================================

CREATE TABLE vocabularies (
    vocabulary      TEXT PRIMARY KEY,
    vocabulary_kind TEXT NOT NULL,      -- FEATURE | CLASSIFICATION | STATUS | STRUCTURAL
    spec_section    TEXT,               -- z.B. "§20"
    description     TEXT NOT NULL
);

CREATE TABLE vocabulary_terms (
    vocabulary TEXT NOT NULL REFERENCES vocabularies(vocabulary) ON DELETE CASCADE,
    term       TEXT NOT NULL,
    label_de   TEXT,
    notes      TEXT,
    PRIMARY KEY (vocabulary, term)
);

-- =====================================================================
-- EBENE 1: CONTENT  (§85)
-- =====================================================================

-- §109 Quellenverwaltung / §110 Quellenstatus
CREATE TABLE sources (
    source_id     TEXT PRIMARY KEY,
    author_or_org TEXT NOT NULL,
    title         TEXT NOT NULL,
    year          INTEGER,
    source_type   TEXT NOT NULL,        -- SOURCE_TYPE (§110)
    url_or_doi    TEXT,
    access_date   TEXT,
    notes         TEXT,

    _v_source_type TEXT GENERATED ALWAYS AS ('SOURCE_TYPE') VIRTUAL,
    FOREIGN KEY (_v_source_type, source_type)
        REFERENCES vocabulary_terms(vocabulary, term)
);

-- §79 competencies
CREATE TABLE competencies (
    competency_id       TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    domain              TEXT NOT NULL,  -- DOMAIN
    leitidee            TEXT NOT NULL,  -- LEITIDEE (§7)
    parent_id           TEXT REFERENCES competencies(competency_id),
    grade_reference_min INTEGER,        -- §94 Referenz, keine Schranke
    grade_reference_max INTEGER,
    is_mvp              INTEGER NOT NULL DEFAULT 0 CHECK (is_mvp IN (0, 1)),
    source_id           TEXT REFERENCES sources(source_id),
    evidence_status     TEXT NOT NULL,  -- EVIDENCE_STATUS A-E (§13)
    spec_section        TEXT,

    _v_domain    TEXT GENERATED ALWAYS AS ('DOMAIN')          VIRTUAL,
    _v_leitidee  TEXT GENERATED ALWAYS AS ('LEITIDEE')        VIRTUAL,
    _v_evstatus  TEXT GENERATED ALWAYS AS ('EVIDENCE_STATUS') VIRTUAL,
    FOREIGN KEY (_v_domain,   domain)          REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_leitidee, leitidee)        REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_evstatus, evidence_status) REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_competencies_leitidee ON competencies(leitidee);
CREATE INDEX idx_competencies_parent   ON competencies(parent_id);
CREATE INDEX idx_competencies_mvp      ON competencies(is_mvp);

-- =====================================================================
-- EBENE 2: LOGIC  (§85)
-- =====================================================================

-- §80 relations / §12 Relationstypen / §13 Evidenzgrad
-- §11 Der Kompetenzgraph ist ausdruecklich kein linearer Baum:
--     mehrere Voraussetzungen und mehrere Nachfolger sind zulaessig.
CREATE TABLE relations (
    relation_id       TEXT PRIMARY KEY,
    source_competency TEXT NOT NULL REFERENCES competencies(competency_id),
    target_competency TEXT NOT NULL REFERENCES competencies(competency_id),
    relation_type     TEXT NOT NULL,   -- RELATION_TYPE (§12)   §114: NOT NULL
    strength          REAL,            -- 0..1, NULL = UNDEFINED
    evidence_status   TEXT NOT NULL,   -- EVIDENCE_STATUS (§13) §114: NOT NULL
    source_id         TEXT REFERENCES sources(source_id),
    bidirectional     INTEGER NOT NULL DEFAULT 0 CHECK (bidirectional IN (0, 1)),
    notes             TEXT,
    spec_section      TEXT,

    _v_reltype  TEXT GENERATED ALWAYS AS ('RELATION_TYPE')   VIRTUAL,
    _v_evstatus TEXT GENERATED ALWAYS AS ('EVIDENCE_STATUS') VIRTUAL,

    CHECK (source_competency <> target_competency),
    CHECK (strength IS NULL OR (strength >= 0.0 AND strength <= 1.0)),
    UNIQUE (source_competency, target_competency, relation_type),
    FOREIGN KEY (_v_reltype,  relation_type)   REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_evstatus, evidence_status) REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_relations_source ON relations(source_competency);
CREATE INDEX idx_relations_target ON relations(target_competency);
CREATE INDEX idx_relations_type   ON relations(relation_type);

-- §58 Aufgabenfamilien / §52 Contrast Family / §25 Variantentypen
CREATE TABLE task_families (
    task_family_id     TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    family_type        TEXT NOT NULL,   -- TASK_FAMILY_TYPE (§25)
    primary_competency TEXT REFERENCES competencies(competency_id),
    diagnostic_purpose TEXT NOT NULL,   -- §58: nur wenn der Vergleich Informationswert hat
    notes              TEXT,
    spec_section       TEXT,

    _v_famtype TEXT GENERATED ALWAYS AS ('TASK_FAMILY_TYPE') VIRTUAL,
    FOREIGN KEY (_v_famtype, family_type) REFERENCES vocabulary_terms(vocabulary, term)
);

-- §81 tasks / §90 task_purpose / §113 Qualitaetsregel
-- Mehrwertige Felder (secondary_competencies, process_competencies,
-- prerequisites, secondary_leitideen) liegen als JSON-Arrays vor und
-- werden vom Importer gegen competencies bzw. Vokabulare validiert.
-- Begruendung: die Feldnamen bleiben 1:1 wie in §81 lesbar.
CREATE TABLE tasks (
    task_id                TEXT PRIMARY KEY,
    task_family_id         TEXT REFERENCES task_families(task_family_id),
    title                  TEXT NOT NULL,
    primary_competency     TEXT NOT NULL REFERENCES competencies(competency_id),
    secondary_competencies TEXT NOT NULL DEFAULT '[]',
    primary_leitidee       TEXT NOT NULL,  -- LEITIDEE
    secondary_leitideen    TEXT NOT NULL DEFAULT '[]',
    process_competencies   TEXT NOT NULL DEFAULT '[]',  -- PROCESS_COMPETENCY (§8)
    prerequisites          TEXT NOT NULL DEFAULT '[]',
    internal_difficulty    TEXT NOT NULL,  -- INTERNAL_DIFFICULTY D1-D5 (§18)
    calibration_status     TEXT NOT NULL,  -- CALIBRATION_STATUS (§6)
    representation_mode    TEXT NOT NULL,  -- REPRESENTATION_MODE (§16)
    interaction_mode       TEXT NOT NULL,  -- INTERACTION_MODE (§17)
    -- question_form ist eine Erweiterung gegenueber §81. Begruendung: §116
    -- verlangt, dass ein diagnostischer Vergleich nur EINE Variable aendert.
    -- Darstellung (§16) und Bedienform (§17) fuehrt die Spezifikation getrennt,
    -- die Frageform nicht - "Welchen Wert hat die Ziffer 6 in 364?" und "Welchen
    -- Wert haben die Zehnerstangen zusammen?" fragen aber Verschiedenes. Ohne
    -- dieses Feld waere die Frageform eine unbeobachtete zweite Variable und
    -- §116 nicht pruefbar. Siehe ENTSCHEIDUNGEN.md D-28.
    question_form          TEXT NOT NULL,  -- QUESTION_FORM (§116)
    language_demand        TEXT NOT NULL,  -- LANGUAGE_DEMAND
    task_prompt            TEXT NOT NULL,
    task_payload           TEXT NOT NULL DEFAULT '{}',  -- JSON, renderer-spezifisch
    correct_answer         TEXT NOT NULL,               -- JSON (§49: mehrere Loesungen moeglich)
    scoring_rule           TEXT NOT NULL,  -- SCORING_RULE
    estimated_time_seconds INTEGER,
    source_type            TEXT NOT NULL,  -- TASK_SOURCE_TYPE
    source_reference       TEXT,
    task_purpose           TEXT NOT NULL,  -- TASK_PURPOSE (§90)
    parallel_item_id       TEXT REFERENCES tasks(task_id),  -- §113
    grade_reference_min    INTEGER,        -- §94
    grade_reference_max    INTEGER,
    spec_section           TEXT,

    _v_leitidee  TEXT GENERATED ALWAYS AS ('LEITIDEE')            VIRTUAL,
    _v_diff      TEXT GENERATED ALWAYS AS ('INTERNAL_DIFFICULTY') VIRTUAL,
    _v_calib     TEXT GENERATED ALWAYS AS ('CALIBRATION_STATUS')  VIRTUAL,
    _v_repr      TEXT GENERATED ALWAYS AS ('REPRESENTATION_MODE') VIRTUAL,
    _v_inter     TEXT GENERATED ALWAYS AS ('INTERACTION_MODE')    VIRTUAL,
    _v_qform     TEXT GENERATED ALWAYS AS ('QUESTION_FORM')       VIRTUAL,
    _v_langdem   TEXT GENERATED ALWAYS AS ('LANGUAGE_DEMAND')     VIRTUAL,
    _v_scoring   TEXT GENERATED ALWAYS AS ('SCORING_RULE')        VIRTUAL,
    _v_srctype   TEXT GENERATED ALWAYS AS ('TASK_SOURCE_TYPE')    VIRTUAL,
    _v_purpose   TEXT GENERATED ALWAYS AS ('TASK_PURPOSE')        VIRTUAL,
    FOREIGN KEY (_v_leitidee, primary_leitidee)    REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_diff,     internal_difficulty) REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_calib,    calibration_status)  REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_repr,     representation_mode) REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_inter,    interaction_mode)    REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_qform,    question_form)       REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_langdem,  language_demand)     REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_scoring,  scoring_rule)        REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_srctype,  source_type)         REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_purpose,  task_purpose)        REFERENCES vocabulary_terms(vocabulary, term),

    CHECK (json_valid(secondary_competencies)),
    CHECK (json_valid(secondary_leitideen)),
    CHECK (json_valid(process_competencies)),
    CHECK (json_valid(prerequisites)),
    CHECK (json_valid(task_payload)),
    CHECK (json_valid(correct_answer))
);

CREATE INDEX idx_tasks_primary_competency ON tasks(primary_competency);
CREATE INDEX idx_tasks_difficulty         ON tasks(internal_difficulty);
CREATE INDEX idx_tasks_representation     ON tasks(representation_mode);
CREATE INDEX idx_tasks_family             ON tasks(task_family_id);
CREATE INDEX idx_tasks_purpose            ON tasks(task_purpose);

-- §82 task_features
-- Normalisierte Form der vier Arrays aus §20-23 plus additional_demands
-- aus §15. feature_kind ist selbst ein Vokabularname; damit ist eine
-- neue Merkmalsklasse ohne Migration ergaenzbar (§108).
CREATE TABLE task_features (
    task_id       TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    feature_kind  TEXT NOT NULL REFERENCES vocabularies(vocabulary),
    feature_value TEXT NOT NULL,
    PRIMARY KEY (task_id, feature_kind, feature_value),
    FOREIGN KEY (feature_kind, feature_value)
        REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_task_features_value ON task_features(feature_kind, feature_value);

-- §59 Fehlercodes. Beschreiben Beobachtungen, keine Diagnosen.
-- description ist nullable: §59 listet die Codes ohne Definition. Wo die
-- Spezifikation keine Bedeutung angibt, bleibt das Feld leer (§1).
CREATE TABLE error_codes (
    error_code          TEXT PRIMARY KEY,
    label_de            TEXT NOT NULL,
    description         TEXT,
    is_observation_only INTEGER NOT NULL DEFAULT 1 CHECK (is_observation_only = 1),
    spec_section        TEXT
);

-- §83 task_routes / §84 Routing nicht hardcoden
-- target_task ODER target_competency: §69 endet in "Buendelung /
-- Stellenwert-Voraussetzungen pruefen", also in einem Knoten, nicht in
-- einem konkreten Item.
-- requires_status und requires_hypothesis sind eine Erweiterung gegenueber §83.
-- Begruendung: §83 sieht als Bedingung nur das Ergebnis der Vorgaengeraufgabe
-- vor. Die Foerderrouten aus §92 und §93 duerfen aber nur greifen, wenn fuer
-- die Kompetenz SUPPORT_FOCUS gesetzt ist - sonst lenkt eine richtig geloeste
-- Screening-Aufgabe in eine Foerderkette. Ohne diese Felder muesste die
-- Bedingung im Code stehen, was §84 verbietet. Siehe ENTSCHEIDUNGEN.md D-08.
CREATE TABLE task_routes (
    route_id            TEXT PRIMARY KEY,
    source_task         TEXT NOT NULL REFERENCES tasks(task_id),
    condition           TEXT NOT NULL,   -- ROUTE_CONDITION
    target_task         TEXT REFERENCES tasks(task_id),
    target_competency   TEXT REFERENCES competencies(competency_id),
    reason              TEXT NOT NULL,   -- ROUTE_REASON (§67 Priorisierung)
    priority            INTEGER NOT NULL,
    enabled             INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    requires_status     TEXT,            -- COMPETENCY_STATUS oder NULL
    requires_hypothesis TEXT,            -- HYPOTHESIS_TYPE oder NULL
    notes               TEXT,
    spec_section        TEXT,

    _v_cond   TEXT GENERATED ALWAYS AS ('ROUTE_CONDITION')    VIRTUAL,
    _v_reason TEXT GENERATED ALWAYS AS ('ROUTE_REASON')       VIRTUAL,
    _v_rstat  TEXT GENERATED ALWAYS AS ('COMPETENCY_STATUS')  VIRTUAL,
    _v_rhyp   TEXT GENERATED ALWAYS AS ('HYPOTHESIS_TYPE')    VIRTUAL,

    CHECK (target_task IS NOT NULL OR target_competency IS NOT NULL),
    FOREIGN KEY (_v_cond,   condition)           REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_reason, reason)              REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_rstat,  requires_status)     REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_rhyp,   requires_hypothesis) REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_task_routes_source ON task_routes(source_task, enabled, priority DESC);

-- §41 Mastery-Schwellen, §68 Score-Gewichte, §95 ALLOW_ABOVE_GRADE,
-- §96 Startschwierigkeit, §35 Skip-Level als CONFIGURABLE_HEURISTIC.
-- Kein Wert dieser Art darf im Code stehen.
CREATE TABLE system_config (
    config_key   TEXT PRIMARY KEY,
    value        TEXT,              -- NULL = UNDEFINED (§1)
    value_type   TEXT NOT NULL,     -- INTEGER | REAL | BOOLEAN | STRING | JSON
    status       TEXT NOT NULL,     -- CONFIG_STATUS
    spec_section TEXT,
    description  TEXT NOT NULL,

    _v_cfgstatus TEXT GENERATED ALWAYS AS ('CONFIG_STATUS') VIRTUAL,
    FOREIGN KEY (_v_cfgstatus, status) REFERENCES vocabulary_terms(vocabulary, term)
);

-- =====================================================================
-- EBENE 3: USER STATE  (§85)
-- Ab Sprint 5 gefuellt. Das Schema steht bereits, damit Sprint 6-9
-- nicht migrieren muessen.
-- =====================================================================

-- §86 Datenschutzprinzip: student_id ist ein pseudonymes UUID.
-- Bewusst keine Spalten fuer Namen, Geburtsdatum, Schule, Diagnosen.
CREATE TABLE students (
    student_id       TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,
    grade_reference  INTEGER,          -- §94 Referenz, keine Schranke
    notes            TEXT
);

-- §60 Rohdaten speichern
CREATE TABLE task_attempts (
    attempt_id     TEXT PRIMARY KEY,
    student_id     TEXT NOT NULL REFERENCES students(student_id),
    task_id        TEXT NOT NULL REFERENCES tasks(task_id),
    started_at     TEXT NOT NULL,
    completed_at   TEXT,
    answer         TEXT,              -- JSON, Rohantwort unveraendert (§66)
    is_correct     INTEGER CHECK (is_correct IN (0, 1)),
    score          REAL,
    time_seconds   REAL,              -- §62 zunaechst nur Kontextinformation
    support_used   INTEGER NOT NULL DEFAULT 0 CHECK (support_used IN (0, 1)),
    attempt_number INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_attempts_student ON task_attempts(student_id, started_at);
CREATE INDEX idx_attempts_task    ON task_attempts(task_id);

-- §61 Interaktionsdaten
CREATE TABLE interaction_events (
    event_id        TEXT PRIMARY KEY,
    attempt_id      TEXT NOT NULL REFERENCES task_attempts(attempt_id) ON DELETE CASCADE,
    timestamp       TEXT NOT NULL,
    event_type      TEXT NOT NULL,    -- EVENT_TYPE (§61)
    object_id       TEXT,
    value           TEXT,
    sequence_number INTEGER NOT NULL,

    _v_evtype TEXT GENERATED ALWAYS AS ('EVENT_TYPE') VIRTUAL,
    FOREIGN KEY (_v_evtype, event_type) REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_events_attempt ON interaction_events(attempt_id, sequence_number);

-- §66 Ebene 1 von 3: Rohbeobachtung -> Fehlercode.
-- Bewusst eine eigene Tabelle: ein Fehlercode ist eine Beobachtung und
-- darf nicht mit Evidenz oder Hypothese in einer Zeile stehen.
CREATE TABLE attempt_error_codes (
    attempt_id TEXT NOT NULL REFERENCES task_attempts(attempt_id) ON DELETE CASCADE,
    error_code TEXT NOT NULL REFERENCES error_codes(error_code),
    detail     TEXT,
    PRIMARY KEY (attempt_id, error_code)
);

-- §65 Evidence Events / §28 Evidenzarten
-- §66 Ebene 2 von 3.
CREATE TABLE evidence_events (
    evidence_id   TEXT PRIMARY KEY,
    student_id    TEXT NOT NULL REFERENCES students(student_id),
    competency_id TEXT NOT NULL REFERENCES competencies(competency_id),
    source_task   TEXT REFERENCES tasks(task_id),
    source_attempt TEXT REFERENCES task_attempts(attempt_id),
    evidence_type TEXT NOT NULL,      -- EVIDENCE_TYPE (§28)
    direction     TEXT NOT NULL,      -- EVIDENCE_DIRECTION
    strength      REAL,               -- NULL = UNDEFINED (Berechnung offen)
    created_at    TEXT NOT NULL,
    review_at     TEXT,

    _v_evtype TEXT GENERATED ALWAYS AS ('EVIDENCE_TYPE')      VIRTUAL,
    _v_dir    TEXT GENERATED ALWAYS AS ('EVIDENCE_DIRECTION') VIRTUAL,

    CHECK (strength IS NULL OR (strength >= 0.0 AND strength <= 1.0)),
    FOREIGN KEY (_v_evtype, evidence_type) REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_dir,    direction)     REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_evidence_student ON evidence_events(student_id, competency_id, created_at);

-- §63 Student State / §26 Kompetenzprofilmarker / §40 Zeitliche Stabilitaet
CREATE TABLE student_competency_state (
    student_id             TEXT NOT NULL REFERENCES students(student_id),
    competency_id          TEXT NOT NULL REFERENCES competencies(competency_id),
    status                 TEXT NOT NULL,  -- COMPETENCY_STATUS (§27)
    direct_evidence_score  REAL,
    indirect_evidence_score REAL,
    evidence_consistency   REAL,
    current_floor          TEXT,           -- INTERNAL_DIFFICULTY oder NULL
    current_ceiling        TEXT,           -- INTERNAL_DIFFICULTY oder NULL
    profile_markers        TEXT NOT NULL DEFAULT '[]',  -- JSON, PROFILE_MARKER (§26)
    first_evidence         TEXT,           -- §40
    last_direct_evidence   TEXT,
    last_indirect_evidence TEXT,
    last_review            TEXT,
    next_review            TEXT,
    parked_at              TEXT,           -- §38
    reactivation_reason    TEXT,           -- REACTIVATION_REASON (§39)
    updated_at             TEXT NOT NULL,

    _v_status TEXT GENERATED ALWAYS AS ('COMPETENCY_STATUS') VIRTUAL,

    PRIMARY KEY (student_id, competency_id),
    CHECK (json_valid(profile_markers)),
    FOREIGN KEY (_v_status, status) REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_state_status ON student_competency_state(student_id, status);

-- §117 verbietet, Kompetenz als Prozentwert zu bilden: "73 % richtig -> ZO07 = 73 %
-- verliert Informationen." Stattdessen verlangt §117 eine Aufschluesselung nach
-- Facetten ("basic concept = secure, two-digit symbolic = secure, decomposition =
-- uncertain, compensation = secure, transfer = unknown, representation = stable"),
-- und §118 zeigt dasselbe fuer ZO09. Diese Facetten sind keine Kompetenzknoten,
-- sondern Aufgabenmerkmale (§16, §18, §20-23, §90). Deshalb eine eigene Tabelle,
-- die je Kompetenz und Merkmalswert einen Status fuehrt.
-- facet_kind ist ein Vokabularname; damit ist eine neue Facettenklasse ohne
-- Migration moeglich (§108). Siehe ENTSCHEIDUNGEN.md D-04.
CREATE TABLE student_competency_facets (
    student_id     TEXT NOT NULL REFERENCES students(student_id),
    competency_id  TEXT NOT NULL REFERENCES competencies(competency_id),
    facet_kind     TEXT NOT NULL REFERENCES vocabularies(vocabulary),
    facet_value    TEXT NOT NULL,
    status         TEXT NOT NULL,   -- COMPETENCY_STATUS
    positive_count INTEGER NOT NULL DEFAULT 0,
    negative_count INTEGER NOT NULL DEFAULT 0,
    consistency    REAL,
    last_evidence  TEXT,
    updated_at     TEXT NOT NULL,

    _v_status TEXT GENERATED ALWAYS AS ('COMPETENCY_STATUS') VIRTUAL,

    PRIMARY KEY (student_id, competency_id, facet_kind, facet_value),
    FOREIGN KEY (_v_status,  status)                   REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (facet_kind, facet_value)              REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_facets_lookup ON student_competency_facets(student_id, competency_id, facet_kind);

-- §64 Hypothesen / §115 Grundsatz der Widerlegbarkeit
-- §66 Ebene 3 von 3. Entsteht erst nach Replikation (§30).
CREATE TABLE student_hypotheses (
    hypothesis_id         TEXT PRIMARY KEY,
    student_id            TEXT NOT NULL REFERENCES students(student_id),
    hypothesis_type       TEXT NOT NULL,   -- HYPOTHESIS_TYPE
    target_construct      TEXT NOT NULL,
    status                TEXT NOT NULL,   -- HYPOTHESIS_STATUS (§64)
    supporting_evidence   TEXT NOT NULL DEFAULT '[]',  -- JSON: evidence_id[]
    contradicting_evidence TEXT NOT NULL DEFAULT '[]',
    falsifying_task       TEXT REFERENCES tasks(task_id),  -- §115: muss widerlegbar sein
    priority              INTEGER,
    created_at            TEXT NOT NULL,
    last_updated          TEXT NOT NULL,

    _v_htype  TEXT GENERATED ALWAYS AS ('HYPOTHESIS_TYPE')   VIRTUAL,
    _v_hstat  TEXT GENERATED ALWAYS AS ('HYPOTHESIS_STATUS') VIRTUAL,

    CHECK (json_valid(supporting_evidence)),
    CHECK (json_valid(contradicting_evidence)),
    FOREIGN KEY (_v_htype, hypothesis_type) REFERENCES vocabulary_terms(vocabulary, term),
    FOREIGN KEY (_v_hstat, status)          REFERENCES vocabulary_terms(vocabulary, term)
);

CREATE INDEX idx_hypotheses_student ON student_hypotheses(student_id, status);

-- §88 Lehrkraft-Supervision / §89 Explainability Logging
-- Jede Routingentscheidung muss nachvollziehbar sein.
CREATE TABLE routing_decisions (
    decision_id            TEXT PRIMARY KEY,
    student_id             TEXT NOT NULL REFERENCES students(student_id),
    timestamp              TEXT NOT NULL,
    previous_task          TEXT REFERENCES tasks(task_id),
    selected_task          TEXT REFERENCES tasks(task_id),
    rule_triggered         TEXT,          -- route_id oder Regelname
    evidence_used          TEXT NOT NULL DEFAULT '[]',  -- JSON: evidence_id[]
    hypothesis_used        TEXT NOT NULL DEFAULT '[]',  -- JSON: hypothesis_id[]
    alternatives_considered TEXT NOT NULL DEFAULT '[]', -- JSON: [{task_id, score}]
    score_breakdown        TEXT NOT NULL DEFAULT '{}',  -- JSON, §68 Summanden einzeln
    confidence             TEXT,          -- CONFIDENCE_LEVEL (§88)

    CHECK (json_valid(evidence_used)),
    CHECK (json_valid(hypothesis_used)),
    CHECK (json_valid(alternatives_considered)),
    CHECK (json_valid(score_breakdown))
);

CREATE INDEX idx_decisions_student ON routing_decisions(student_id, timestamp);

-- =====================================================================
-- VIEWS
-- =====================================================================

-- Rekonstruiert die vier Merkmalsarrays aus §20-23 in der Lesart von §82.
CREATE VIEW v_task_features_arrays AS
SELECT
    t.task_id,
    (SELECT json_group_array(feature_value) FROM task_features f
      WHERE f.task_id = t.task_id AND f.feature_kind = 'NUMERIC_FEATURE')     AS numeric_features,
    (SELECT json_group_array(feature_value) FROM task_features f
      WHERE f.task_id = t.task_id AND f.feature_kind = 'STRUCTURAL_FEATURE')  AS structural_features,
    (SELECT json_group_array(feature_value) FROM task_features f
      WHERE f.task_id = t.task_id AND f.feature_kind = 'SURFACE_FEATURE')     AS surface_features,
    (SELECT json_group_array(feature_value) FROM task_features f
      WHERE f.task_id = t.task_id AND f.feature_kind = 'STRATEGY_AFFORDANCE') AS strategy_affordances,
    (SELECT json_group_array(feature_value) FROM task_features f
      WHERE f.task_id = t.task_id AND f.feature_kind = 'ADDITIONAL_DEMAND')   AS additional_demands
FROM tasks t;

-- Lesbare Relationsliste fuer die fachliche Durchsicht (§114).
CREATE VIEW v_relations_readable AS
SELECT
    r.relation_id,
    r.source_competency, cs.name AS source_name,
    r.relation_type,
    r.target_competency, ct.name AS target_name,
    r.evidence_status,
    r.spec_section,
    r.notes
FROM relations r
JOIN competencies cs ON cs.competency_id = r.source_competency
JOIN competencies ct ON ct.competency_id = r.target_competency;
