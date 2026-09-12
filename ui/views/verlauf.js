/* Aufgabenverlauf.
 *
 * Die unterste Ebene: was tatsächlich passiert ist, in zeitlicher Reihenfolge.
 * Rohe Antwort, Aufgabe, Merkmale, Fehlercodes – und was daraus entstanden ist.
 *
 * Die Bearbeitungszeit wird angezeigt, weil sie zu den Rohdaten gehört (§60).
 * Sie ist ausdrücklich kein Kompetenzindikator: langsam heißt nicht schwach
 * (§62). Der Hinweis steht direkt an der Spalte und nicht im Kleingedruckten,
 * weil eine Zeitangabe in einer Diagnostikoberfläche sonst genau so gelesen
 * wird.
 */

import { el, abschnitt, kv, leer, chips, merkzettel, tabelle, ergebnisMarke,
         ebene, ebenenTitel, sprung, zeitpunkt, antwortText, optionen }
  from "../dom.js";
import { label, kurzName, vokabularTitel } from "../labels.js";
import { nachId, gruppieren } from "../data.js";

function versuchKarte(beobachtung, daten) {
  const { katalog, profil, knotenNachId, aufgabenNachId, nummer } = daten;
  const aufgabe = aufgabenNachId.get(beobachtung.task_id);
  const fehler = profil.error_observations.filter((f) => f.attempt_id === beobachtung.attempt_id);
  const evidenz = profil.evidence.filter((e) => e.source_attempt === beobachtung.attempt_id);
  const entscheidung = profil.routing_decisions.find(
    (d) => d.previous_task === beobachtung.task_id);

  return el("div.karte", { id: `aufgabe-${beobachtung.task_id}` },
    el("div.karte-kopf", {},
      el("h3", {}, el("span.mono.leer", `${nummer}. `), aufgabe ? aufgabe.title : beobachtung.task_id),
      ergebnisMarke(beobachtung.is_correct)),
    el("p.mono.leer", { style: "margin:.1rem 0 .5rem" },
      `${beobachtung.task_id}  ·  Versuch ${beobachtung.attempt_number}`
      + `  ·  ${zeitpunkt(beobachtung.started_at)}`),

    aufgabe ? el("p", aufgabe.task_prompt) : null,

    kv([
      ["Kompetenz", sprung(
        kurzName(knotenNachId.get(beobachtung.primary_competency)?.name || beobachtung.primary_competency),
        { ansicht: "karte", knoten: beobachtung.primary_competency })],
      ["Niveaubereich", label("INTERNAL_DIFFICULTY", beobachtung.internal_difficulty)],
      ["Darstellung", label("REPRESENTATION_MODE", beobachtung.representation_mode)],
      ["Bedienform", aufgabe ? label("INTERACTION_MODE", aufgabe.interaction_mode) : null],
      ["Frageform", label("QUESTION_FORM", beobachtung.question_form)],
      ["Zweck der Aufgabe", label("TASK_PURPOSE", beobachtung.task_purpose)],
      ["Antwort", el("span.mono", antwortText(beobachtung.answer))],
      ["Unterstützung genutzt", beobachtung.support_used ? "ja (§33)" : "nein"],
      ["Interaktionsereignisse", beobachtung.interaction_event_count
        ? `${beobachtung.interaction_event_count} aufgezeichnet (§61)` : "keine"],
      ["Bearbeitungszeit", beobachtung.time_seconds !== null && beobachtung.time_seconds !== undefined
        ? el("span", {}, `${beobachtung.time_seconds} s `,
            el("span.leer", "– Rohdatum, kein Kompetenzindikator (§62)"))
        : el("span.leer", "nicht erfasst")],
    ]),

    fehler.length
      ? el("div", { style: "margin-top:.7rem" },
        el("h4", {}, ebene("fehler"), " Beobachtete Fehler"),
        el("div.chips", {}, fehler.map((f) => el("button.chip", {
          type: "button", title: f.description,
          onclick: () => window.dispatchEvent(new CustomEvent("navigiere", {
            detail: { ansicht: "fehleranalyse", fehler: f.error_code } })),
        }, f.label_de))))
      : null,

    evidenz.length
      ? el("div", { style: "margin-top:.7rem" },
        el("h4", {}, ebene("evidenz"), " Daraus entstandene Evidenz"),
        el("div.chips", {}, evidenz.map((e) => el("span.chip", {
          title: `${e.competency_id} · ${e.direction}`,
        }, `${e.direction === "POSITIVE" ? "+" : e.direction === "NEGATIVE" ? "−" : "·"} `
           + `${label("EVIDENCE_TYPE", e.evidence_type)}`))),
        el("p.leer", { style: "margin-top:.2rem" },
          `${evidenz.length} Einträge, davon ${evidenz.filter((e) => e.is_scored).length} statuswirksam`))
      : null,

    entscheidung
      ? el("div", { style: "margin-top:.7rem" },
        el("h4", "Daraufhin gewählt"),
        el("p", { style: "margin:.1rem 0" },
          entscheidung.selected_task
            ? el("span", {}, el("span.mono", entscheidung.selected_task), " – Regel ",
                el("span.mono", entscheidung.rule_triggered || "–"))
            : el("span", {}, "keine weitere Aufgabe: ",
                el("span.mono", entscheidung.rule_triggered || "–"))),
        sprung("Begründung", { ansicht: "debug", entscheidung: entscheidung.decision_id }))
      : null);
}

export default {
  zahl: (z) => ({ wert: z.profil.observations.length || null, ebene: "beobachtung",
                  was: "Aufgabenversuche" }),

  render(zustand) {
    const { profil, katalog, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");

    const aufgabenFilter = parameter.get("aufgabe");
    const knotenFilter = parameter.get("knoten");
    const nurAbweichend = parameter.get("nurfalsch") === "1";

    const setze = (schluessel, wert) => {
      const p = new URLSearchParams(parameter);
      if (wert === null || wert === "") p.delete(schluessel); else p.set(schluessel, wert);
      location.hash = `#verlauf?${p}`;
    };

    let liste = profil.observations;
    if (aufgabenFilter) liste = liste.filter((b) => b.task_id === aufgabenFilter);
    if (knotenFilter) liste = liste.filter((b) => b.primary_competency === knotenFilter);
    if (nurAbweichend) liste = liste.filter((b) => !b.is_correct);

    const knoten = [...new Set(profil.observations.map((b) => b.primary_competency))];

    const filter = el("div.filterleiste", {},
      el("label", {}, "Kompetenz",
        el("select", { "data-fokus": "knoten", onchange: (e) => setze("knoten", e.target.value) },
          optionen(knotenFilter, knoten, (k) =>
            kurzName(knotenNachId.get(k)?.name || k)))),
      el("label", {},
        el("input", {
          type: "checkbox", checked: nurAbweichend, "data-fokus": "nurfalsch",
          onchange: (e) => setze("nurfalsch", e.target.checked ? "1" : null),
        }), "nur abweichende Antworten"),
      aufgabenFilter
        ? el("span.chip", {}, `gefiltert auf ${aufgabenFilter}`)
        : null,
      (aufgabenFilter || knotenFilter || nurAbweichend)
        ? el("button", { type: "button", onclick: () => { location.hash = "#verlauf"; } },
            "Filter zurücksetzen")
        : null);

    const wurzel = el("div");

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("beobachtung", "Aufgabenverlauf", "§60, §66 Ebene 1"),
      merkzettel("Rohdaten: die Antwort steht so, wie sie abgegeben wurde. Auch eine "
        + "unsinnige Antwort ist eine Beobachtung und wird nicht ausgelassen."),
      filter,
      el("p.leer", `${liste.length} von ${profil.observations.length} Versuchen`),
      liste.length
        ? el("div.karten", {}, liste.map((b, i) => versuchKarte(b, {
            katalog, profil, knotenNachId, aufgabenNachId,
            nummer: profil.observations.indexOf(b) + 1,
          })))
        : leer("Kein Versuch passt zu dieser Auswahl.")));

    // Eine kompakte Zeitachse als zweite Lesart derselben Daten - derselben,
    // also auch derselben Auswahl. Vorher stand hier `profil.observations`:
    // oben "6 von 8 Versuchen", darunter kommentarlos alle acht Zeilen.
    wurzel.append(abschnitt("Kompakte Übersicht", null,
      liste.length === profil.observations.length
        ? null
        : el("p.leer", `${liste.length} von ${profil.observations.length} Versuchen, `
            + "dieselbe Auswahl wie oben"),
      tabelle(["#", "Aufgabe", "Kompetenz", "Niveau", "Darstellung", "Ergebnis", "Fehler"],
        liste,
        (b) => {
          const fehler = profil.error_observations.filter((f) => f.attempt_id === b.attempt_id);
          return [
            String(profil.observations.indexOf(b) + 1),
            el("span.mono", b.task_id),
            kurzName(knotenNachId.get(b.primary_competency)?.name || b.primary_competency),
            label("INTERNAL_DIFFICULTY", b.internal_difficulty),
            label("REPRESENTATION_MODE", b.representation_mode),
            ergebnisMarke(b.is_correct),
            fehler.length ? chips(fehler.map((f) => f.label_de)) : el("span.leer", "–"),
          ];
        })));

    if (aufgabenFilter) {
      queueMicrotask(() => document
        .getElementById(`aufgabe-${aufgabenFilter}`)
        ?.scrollIntoView({ block: "center" }));
    }

    return wurzel;
  },
};
