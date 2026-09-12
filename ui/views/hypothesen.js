/* Hypothesen.
 *
 * Eine Hypothese ist eine Vermutung über einen Zusammenhang – keine
 * Feststellung, auch dann nicht, wenn sie gestützt ist. Die Formulierungen
 * kommen aus dem Backend und sind dort bewusst konditional gehalten
 * ("könnte niedriger sein als"); diese Ansicht formuliert nichts um.
 *
 * Konkurrierende Hypothesen stehen nebeneinander, nicht nacheinander. Dass
 * mehrere Erklärungen zu denselben Beobachtungen passen, ist der Normalzustand
 * und wird hier auch so gezeigt: keine Rangliste, keine "wahrscheinlichste"
 * Hypothese, keine Prozentangabe zur Sicherheit.
 *
 * Jede Hypothese führt die Aufgabe mit, die sie widerlegen würde. Eine
 * Hypothese ohne solche Aufgabe wäre nicht prüfbar (§115) und wird als solche
 * ausgewiesen.
 */

import { el, abschnitt, kv, leer, merkzettel, tabelle, hypotheseMarke, ergebnisMarke,
         ebene, ebenenTitel, sprung, zeitpunkt, waage, antwortText, optionen }
  from "../dom.js";
import { label, kurzName, vokabularInfo } from "../labels.js";
import { nachId, gruppieren } from "../data.js";

const PRUEFUNG_TEXT = {
  PLANNED: ["geplant", "Diese Aufgabe ist vorgemerkt, aber noch nicht bearbeitet."],
  DONE: ["erfolgt", "Diese Aufgabe wurde bearbeitet; das Ergebnis steht unten."],
  NONE: ["keine", "Zu dieser Hypothese ist keine widerlegende Aufgabe hinterlegt."],
};

/* Die Beobachtungen, auf die sich eine Hypothese stützt.
 *
 * Wichtig und leicht zu übersehen: `supporting_evidence` und
 * `contradicting_evidence` führen **Versuchskennungen**, keine Evidenzzeilen –
 * über alle Hypothesen geprüft stehen dort ausschließlich `AT-…`. Die Hypothese
 * hängt also an der Ebene *Beobachtung*, nicht an der Ebene *Evidenz*. Die
 * Spaltenüberschrift sagt das, und die letzte Spalte führt über den
 * Fremdschlüssel `source_attempt` zu den Evidenzzeilen, die aus derselben
 * Beobachtung entstanden sind. Dass diese Zeilen die Hypothese stützen, steht
 * dort nicht und wird hier nicht behauptet.
 */
function beobachtungenZu(profil, attemptIds, aufgabenNachId) {
  const ids = new Set(attemptIds);
  const treffer = profil.observations.filter((b) => ids.has(b.attempt_id));
  if (!treffer.length) return leer("keine");
  return tabelle(["Aufgabe", "Ergebnis", "Antwort", "Zeitpunkt", "Daraus entstandene Evidenz"],
    treffer, (b) => {
      const zeilen = profil.evidence.filter((e) => e.source_attempt === b.attempt_id);
      return [
        el("span", {}, el("span.mono", b.task_id), el("br"),
          el("span.leer", aufgabenNachId.get(b.task_id)?.title || "")),
        ergebnisMarke(b.is_correct),
        el("span.mono", antwortText(b.answer)),
        zeitpunkt(b.started_at),
        zeilen.length
          ? sprung(`${zeilen.length} ${zeilen.length === 1 ? "Eintrag" : "Einträge"}`,
              { ansicht: "evidenz", beobachtung: b.attempt_id },
              "die Evidenzzeilen dieser Beobachtung ansehen")
          : el("span.leer", "keine"),
      ];
    });
}

function hypotheseKarte(h, daten) {
  const { profil, katalog, knotenNachId, aufgabenNachId, hypothesenNachId } = daten;
  const pruefung = h.hypothesis_test;
  const [pruefWort, pruefHinweis] = PRUEFUNG_TEXT[pruefung.state];
  const kontrolle = pruefung.task_id ? aufgabenNachId.get(pruefung.task_id) : null;
  const ergebnisDerPruefung = pruefung.state === "DONE"
    ? profil.observations.filter((b) => b.task_id === pruefung.task_id)
    : [];

  return el("div.karte", {},
    el("div.karte-kopf", {},
      el("h3", {}, ebene("hypothese"), " ", label("HYPOTHESIS_TYPE", h.hypothesis_type)),
      hypotheseMarke(h.status)),
    el("p.mono.leer", { style: "margin:.1rem 0 .5rem" },
      `${h.hypothesis_id}  ·  ${h.target_construct}`),

    el("p", { style: "font-size:.95rem" }, h.description),
    merkzettel("Formulierung aus dem Backend, bedingt gehalten. Auch eine "
      + "gestützte Hypothese bleibt eine Vermutung."),

    kv([
      ["Betroffener Knoten", sprung(
        kurzName(knotenNachId.get(h.competency_id)?.name || h.competency_id),
        { ansicht: "karte", knoten: h.competency_id })],
      ["Status", `${label("HYPOTHESIS_STATUS", h.status)}`],
      ["Evidenzstärke", waage(h.evidence_balance.supporting, h.evidence_balance.contradicting,
        "stützende Beobachtungen", "widersprechende")],
      // "Prioritaet 2" liest sich wie eine Dringlichkeit ("zweitwichtigste
      // Erkenntnis"). Es ist ein Rang in der Warteschlange der Pruefungen und
      // sagt nichts darueber, wie wahrscheinlich die Hypothese zutrifft.
      ["Rang in der Prüfwarteschlange", el("span", {
        title: "Reihenfolge, in der das Routing die offenen Hypothesen abarbeitet "
          + "(kleinere Zahl zuerst). Keine Aussage darüber, wie wahrscheinlich "
          + "die Hypothese zutrifft.",
      }, `${h.priority}`, el("span.leer", " – Reihenfolge der Prüfung, kein Gewicht"))],
      ["Angelegt", zeitpunkt(h.created_at)],
      ["Zuletzt geändert", zeitpunkt(h.last_updated)],
    ]),

    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("beobachtung"), " Unterstützende Beobachtungen"),
      merkzettel("Das Backend verknüpft eine Hypothese mit Beobachtungen, nicht "
        + "mit Evidenzzeilen. Die letzte Spalte führt zu den Evidenzzeilen, die "
        + "aus derselben Beobachtung entstanden sind – dass sie diese Hypothese "
        + "stützen, steht damit nicht fest."),
      beobachtungenZu(profil, h.supporting_evidence, aufgabenNachId)),

    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("beobachtung"), " Widersprechende Beobachtungen"),
      beobachtungenZu(profil, h.contradicting_evidence, aufgabenNachId)),

    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("pruefung"), " Hypothesenprüfung", el("span.quelle", " §115")),
      kv([
        ["Stand", el("span.wichtig", pruefWort)],
        ["Kontrollaufgabe", pruefung.task_id
          ? el("span", {}, el("span.mono", pruefung.task_id),
              kontrolle ? ` – ${kontrolle.title}` : "")
          : el("span.leer", "keine hinterlegt")],
        ["Bedingung der Aufgabe", kontrolle
          ? el("span", {}, label("REPRESENTATION_MODE", kontrolle.representation_mode),
              " · ", label("INTERNAL_DIFFICULTY", kontrolle.internal_difficulty),
              " · ", label("QUESTION_FORM", kontrolle.question_form))
          : null],
        ["Noch fehlende Evidenz", h.missing_evidence
          ? el("span.wichtig", h.missing_evidence)
          : el("span.leer", pruefung.state === "DONE"
              ? "Die Kontrollaufgabe ist bearbeitet."
              : "–")],
      ]),
      el("p.leer", { style: "margin-top:.3rem" }, pruefHinweis),
      ergebnisDerPruefung.length
        ? el("div", { style: "margin-top:.4rem" },
            el("h4", "Ergebnis der Kontrollaufgabe"),
            beobachtungenZu(profil, ergebnisDerPruefung.map((b) => b.attempt_id), aufgabenNachId))
        : null),

    el("div", { style: "margin-top:.8rem" },
      el("h4", "Konkurrierende Hypothesen"),
      h.competing_hypotheses.length
        ? el("div.chips", {}, h.competing_hypotheses.map((id) => {
          const andere = hypothesenNachId.get(id);
          return sprung(andere ? `${id} – ${label("HYPOTHESIS_TYPE", andere.hypothesis_type)}` : id,
            { ansicht: "hypothesen", hypothese: id });
        }))
        : leer("keine weitere Hypothese zu diesem Knoten")));
}

export default {
  zahl: (z) => ({ wert: z.profil.hypotheses.length || null, ebene: "hypothese",
                  was: "Hypothesen" }),

  render(zustand) {
    const { profil, katalog, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const hypothesenNachId = nachId(profil.hypotheses, "hypothesis_id");

    const gewaehlt = parameter.get("hypothese");
    const knotenFilter = parameter.get("knoten");
    const nurOffen = parameter.get("nuroffen") === "1";

    const setze = (schluessel, wert) => {
      const p = new URLSearchParams(parameter);
      if (wert === null || wert === "") p.delete(schluessel); else p.set(schluessel, wert);
      location.hash = `#hypothesen?${p}`;
    };

    let liste = profil.hypotheses;
    if (knotenFilter) liste = liste.filter((h) => h.competency_id === knotenFilter);
    if (nurOffen) liste = liste.filter((h) => ["OPEN", "SUPPORTED", "WEAKENED"].includes(h.status));
    if (gewaehlt) liste = liste.filter((h) => h.hypothesis_id === gewaehlt);

    const knotenMitHypothesen = [...new Set(profil.hypotheses.map((h) => h.competency_id))];

    const filter = el("div.filterleiste", {},
      el("label", {}, "Kompetenzknoten",
        el("select", { "data-fokus": "knoten", onchange: (e) => setze("knoten", e.target.value) },
          optionen(knotenFilter, knotenMitHypothesen, (k) =>
            kurzName(knotenNachId.get(k)?.name || k)))),
      el("label", {},
        el("input", {
          type: "checkbox", checked: nurOffen, "data-fokus": "nuroffen",
          onchange: (e) => setze("nuroffen", e.target.checked ? "1" : null),
        }), "nur noch nicht abgeschlossene"),
      (gewaehlt || knotenFilter || nurOffen)
        ? el("button", { type: "button", onclick: () => { location.hash = "#hypothesen"; } },
            "Filter zurücksetzen")
        : null);

    const wurzel = el("div");

    // Konkurrenzgruppen zuerst: wo mehrere Hypothesen denselben Knoten
    // betreffen, ist das die eigentliche diagnostische Lage.
    const gruppen = [...gruppieren(profil.hypotheses, (h) => h.competency_id).entries()]
      .filter(([, g]) => g.length > 1);

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("hypothese", "Hypothesen", "§64, §115"),
      merkzettel("Eine Hypothese ist eine Vermutung über einen Zusammenhang. Sie "
        + "wird nicht zur Tatsache, indem sie gestützt wird – sie bleibt an die "
        + "Aufgabe gebunden, die sie widerlegen würde."),
      gruppen.length
        ? el("div", {},
          el("h4", "Knoten mit konkurrierenden Hypothesen"),
          el("div.chips", {}, gruppen.map(([knoten, g]) =>
            sprung(`${kurzName(knotenNachId.get(knoten)?.name || knoten)} (${g.length})`,
              { ansicht: "hypothesen", knoten }))),
          el("p.leer", { style: "margin-top:.3rem" },
            "Mehrere Erklärungen passen zu denselben Beobachtungen. Welche zutrifft, "
            + "entscheidet erst die Prüfung."))
        : null,
      filter,
      liste.length
        ? el("div.karten", {}, liste.map((h) => hypotheseKarte(h,
            { profil, katalog, knotenNachId, aufgabenNachId, hypothesenNachId })))
        : leer(profil.hypotheses.length
            ? "Keine Hypothese passt zu dieser Auswahl."
            : "Es liegt keine Hypothese vor. Das heißt nicht, dass alles geklärt ist – "
              + "es heißt, dass die Beobachtungen bisher keine Vermutung ausgelöst haben."),
      el("p.leer", { style: "margin-top:1rem" },
        vokabularInfo("HYPOTHESIS_TYPE")?.beschreibung || "")));

    return wurzel;
  },
};
