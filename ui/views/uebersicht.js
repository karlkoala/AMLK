/* Übersicht.
 *
 * Drei getrennte Gruppen: Ressourcen, offene Bereiche, noch nicht Geprüftes.
 * Die Gruppierung stammt aus dem Backend (`resource_class`), nicht von hier.
 *
 * Bewusst als erste Ansicht und bewusst in dieser Reihenfolge: die Oberfläche
 * darf nicht defizitorientiert sein, und `UNKNOWN` ist ein gültiger Zustand,
 * kein Mangel. Deshalb steht Ungeprüftes als eigene Gruppe neben den anderen
 * und nicht als Rest.
 *
 * Was hier fehlt, fehlt absichtlich: kein Gesamtwert, kein Prozentwert, kein
 * Klassenstufenäquivalent. Die Aufgabenbank ist nicht kalibriert; eine
 * zusammenfassende Zahl würde eine Genauigkeit behaupten, die es nicht gibt.
 */

import { el, abschnitt, kv, leer, chips, merkzettel, klassenMarke, statusMarke,
         ebene, sprung, zeitpunkt } from "../dom.js";
import { label, kurzName, niveauBereich } from "../labels.js";
import { nachId } from "../data.js";

const REIHENFOLGE = ["RESOURCE", "OPEN", "UNCHECKED"];

const TITEL = {
  RESOURCE: "Ressourcen und Suffizienzen",
  OPEN: "Offene und schwierige Bereiche",
  UNCHECKED: "Noch nicht ausreichend geprüft",
};

const ERLAEUTERUNG = {
  RESOURCE: "Durch Evidenz stabil gezeigt. Ein Status gilt für den aktuellen "
    + "Stand der Evidenz, nicht dauerhaft (§27).",
  OPEN: "Hier liegen Schwierigkeiten oder widersprüchliche Evidenz. Was die "
    + "Schwierigkeit verursacht, steht damit nicht fest – dafür sind Hypothesen da.",
  UNCHECKED: "Kein Mangel, sondern fehlende Information: zu diesen Knoten gibt "
    + "es noch keine ausreichende Evidenz.",
};

function knotenKarte(zustand, knoten) {
  const name = knoten ? knoten.name : zustand.competency_id;
  const beobachtungen = zustand.observation_counts;
  return el("button.karte.wahl", {
    type: "button",
    onclick: () => window.dispatchEvent(new CustomEvent("navigiere", {
      detail: { ansicht: "karte", knoten: zustand.competency_id } })),
  },
    el("div.karte-kopf", {},
      el("h3", kurzName(name)),
      statusMarke(zustand)),
    el("p.mono.leer", { style: "margin:.1rem 0 .4rem" }, zustand.competency_id),
    kv([
      ["Beobachtungen", `${beobachtungen.correct} richtig, ${beobachtungen.incorrect} abweichend`],
      ["Niveaubereich", niveauBereich(zustand.current_floor, zustand.current_ceiling)],
      ["Profilmarker", zustand.profile_markers.length
        ? chips(zustand.profile_markers, "PROFILE_MARKER") : null],
    ]));
}

function naechsteAufgabe(profil, aufgabenNachId) {
  const entscheidung = profil.next_decision;
  if (!entscheidung) {
    return leer("Es liegt noch keine Entscheidung des Systems vor.");
  }
  if (!entscheidung.selected_task) {
    // §73: die Entscheidung, nicht weiter zu testen, ist selbst eine
    // Entscheidung und wird als solche angezeigt – nicht als leere Liste.
    return el("div", {},
      el("p", {}, el("span.wichtig", "Das System hat entschieden, nicht weiter zu testen."),
        " Grund: ", el("span.mono", entscheidung.rule_triggered || "–")),
      merkzettel(entscheidung.termination?.diagnostically_complete
        ? "Alle Ziele im angegebenen Prüfumfang sind gesichert oder geparkt. Dies ist keine empirische Gütegarantie."
        : "Technischer Abschluss: Es ist keine geeignete Folgeaufgabe verfügbar. Offene Kompetenzbereiche bleiben bestehen."),
      ...(entscheidung.termination?.open_areas || []).map((a) => el("p", {},
        el("span.mono", a.competency_id), ` · ${a.status} · ${Object.keys(a.exclusion_reasons).join(", ")}`)),
      ...(entscheidung.termination?.blocked_areas || []).map((a) => el("p", {},
        el("span.mono", a.competency_id), " · gesperrt")),
      sprung("Begründung im Debug ansehen", { ansicht: "debug" }));
  }
  const aufgabe = aufgabenNachId.get(entscheidung.selected_task);
  return el("div", {},
    !entscheidung.is_pending
      ? merkzettel("Diese Auswahl ist bereits bearbeitet. Die nächste Entscheidung "
        + "entsteht erst im nächsten Durchlauf.")
      : null,
    kv([
      ["Aufgabe", el("span", {}, el("span.mono", entscheidung.selected_task),
        aufgabe ? ` – ${aufgabe.title}` : "")],
      ["Kompetenz", aufgabe ? aufgabe.primary_competency : null],
      ["Niveaubereich", aufgabe ? label("INTERNAL_DIFFICULTY", aufgabe.internal_difficulty) : null],
      ["Darstellung", aufgabe ? label("REPRESENTATION_MODE", aufgabe.representation_mode) : null],
      ["Auslösende Regel", el("span.mono", entscheidung.rule_triggered || "–")],
      ["Konfidenz der Auswahl", label("CONFIDENCE_LEVEL", entscheidung.confidence)],
      ["Zeitpunkt", zeitpunkt(entscheidung.timestamp)],
    ]),
    el("p", { style: "margin-top:.6rem" },
      sprung("Vollständige Begründung", { ansicht: "debug" })));
}

export default {
  zahl: () => null,

  render(zustand) {
    const { profil, katalog } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const wurzel = el("div");

    wurzel.append(abschnitt("Profil", "§86 pseudonym",
      kv([
        ["Kennung", el("span.mono", profil.student.student_id)],
        ["Angelegt", zeitpunkt(profil.student.created_at)],
        ["Klassenstufe als Bezug", profil.student.grade_reference
          ? `${profil.student.grade_reference} (§94: Bezugsrahmen, keine Schranke)`
          : "nicht angegeben"],
      ]),
      merkzettel("Gespeichert werden ausschließlich die drei oben genannten Felder. "
        + "Kein Klarname, keine medizinischen oder psychologischen Angaben (§86, §87).")));

    // Die drei Gruppen, immer alle drei – auch wenn eine leer ist. Eine
    // ausgeblendete leere Gruppe würde den Eindruck erwecken, es gäbe dort
    // nichts zu wissen; tatsächlich heißt leer hier: nichts erhoben.
    for (const klasse of REIHENFOLGE) {
      const ids = profil.resource_overview[klasse].competencies;
      const zustaende = profil.competency_states.filter((z) => ids.includes(z.competency_id));
      wurzel.append(abschnitt(
        el("span", {}, klassenMarke(klasse, TITEL[klasse]),
          el("span.quelle", ` ${ids.length} Knoten`)),
        null,
        el("p.leer", ERLAEUTERUNG[klasse]),
        zustaende.length
          ? el("div.karten", {}, zustaende.map((z) => knotenKarte(z, knotenNachId.get(z.competency_id))))
          : leer("Kein Knoten in dieser Gruppe.")));
    }

    wurzel.append(abschnitt(
      el("span", {}, ebene("zustand"), " Nächste diagnostisch sinnvolle Aufgabe"),
      "§119, §89",
      naechsteAufgabe(profil, aufgabenNachId)));

    // Ein kurzer Bestand: was liegt zu dieser Schüler:in überhaupt vor?
    // Getrennt nach den Ebenen der Grundregel, damit die Zahlen nicht
    // verschmelzen.
    wurzel.append(abschnitt("Datenbestand", "Grundregel: die Ebenen bleiben getrennt",
      el("div.karten", {},
        bestand("beobachtung", "Beobachtungen", profil.observations.length,
          "Rohe Versuche, unbewertet (§60).", { ansicht: "verlauf" }),
        bestand("fehler", "Fehlerbeobachtungen", profil.error_observations.length,
          `davon ${profil.error_patterns.filter((m) => m.reproduced).length} als Muster reproduziert (§30).`,
          { ansicht: "fehleranalyse" }),
        bestand("evidenz", "Evidenzeinträge", profil.evidence.length,
          `davon ${profil.evidence.filter((e) => e.is_scored).length} statuswirksam (§28).`,
          { ansicht: "evidenz" }),
        bestand("hypothese", "Hypothesen", profil.hypotheses.length,
          `davon ${profil.hypotheses.filter((h) => h.hypothesis_test.is_active).length} `
          + "mit laufender Prüfung (§115).",
          { ansicht: "hypothesen" }))));

    return wurzel;
  },
};

function bestand(art, titel, anzahl, hinweis, ziel) {
  return el("div.karte", {},
    el("div.karte-kopf", {},
      el("h3", {}, ebene(art), " ", titel),
      el("span.wichtig", { style: "font-size:1.3rem" }, String(anzahl))),
    el("p.leer", hinweis),
    sprung("ansehen", ziel));
}
