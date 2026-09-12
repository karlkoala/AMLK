/* Darstellung / EIS.
 *
 * Unter welcher Darstellung wurde was beobachtet? Das erweiterte EIS-Modell
 * kennt fünf Formen; das Backend führt sie als Facetten je Kompetenz.
 *
 * Eine Grenze, die diese Ansicht durchgängig hält: Darstellung und Bedienform
 * sind zwei verschiedene Variablen (§17). Wer eine Aufgabe per Klickfolge
 * bearbeitet, bearbeitet damit noch keine ikonische Aufgabe. Beide werden
 * getrennt gezeigt und nicht zusammengezogen.
 *
 * Und eine zweite: ein Unterschied zwischen zwei Darstellungen ist ein
 * beobachteter Unterschied. Ob er an der Darstellung liegt, ist eine
 * Hypothese – sie steht in der Hypothesenansicht, nicht hier.
 */

import { el, abschnitt, leer, chips, merkzettel, tabelle, klassenMarke, waage,
         ebenenTitel, sprung, zeitpunkt } from "../dom.js";
import { label, kurzName, vokabularInfo, vokabularTitel } from "../labels.js";
import { nachId, gruppieren } from "../data.js";

const FACETTEN_ARTEN = [
  ["REPRESENTATION_MODE", "§16"],
  ["INTERACTION_MODE", "§17"],
  ["INTERNAL_DIFFICULTY", "§18"],
  ["STRUCTURAL_FEATURE", "§21"],
  ["SURFACE_FEATURE", "§22"],
  ["STRATEGY_AFFORDANCE", "§23"],
  ["NUMERIC_FEATURE", "§20"],
  ["TASK_PURPOSE", "§90"],
];

function facettenTabelle(zustaende, art, knotenNachId) {
  const zeilen = [];
  for (const zustand of zustaende) {
    for (const facette of zustand.facets[art] || []) {
      zeilen.push({ zustand, facette });
    }
  }
  if (!zeilen.length) {
    return leer("Zu dieser Merkmalsart liegt noch keine Facette vor. "
      + "Das ist fehlende Information, kein Befund.");
  }
  return tabelle(
    ["Kompetenz", "Ausprägung", "Beobachtungen", "Facettenstatus", "zuletzt"],
    zeilen,
    ({ zustand, facette }) => [
      sprung(kurzName(knotenNachId.get(zustand.competency_id)?.name || zustand.competency_id),
        { ansicht: "karte", knoten: zustand.competency_id }),
      el("span", {}, label(art, facette.value), el("br"),
        el("span.mono.leer", facette.value)),
      waage(facette.positive_count, facette.negative_count, "richtig", "abweichend"),
      klassenMarke(facette.resource_class, facette.status_label),
      zeitpunkt(facette.last_evidence),
    ]);
}

/** Die gelieferten RepresentationEvidence-Zeilen, unveraendert dargestellt. */
function darstellungsTabelle(zeilen, knotenNachId) {
  if (!zeilen.length) {
    return leer("Zu keiner Kompetenz liegt eine Darstellungsfacette vor. "
      + "Das ist fehlende Information, kein Befund.");
  }
  return tabelle(
    ["Kompetenz", "Darstellung", "Beobachtungen", "Facettenstatus", "zuletzt"],
    zeilen,
    (z) => [
      sprung(kurzName(knotenNachId.get(z.competency_id)?.name || z.name || z.competency_id),
        { ansicht: "karte", knoten: z.competency_id }),
      el("span", {}, label("REPRESENTATION_MODE", z.facet_value), el("br"),
        el("span.mono.leer", z.facet_value)),
      waage(z.positive_count, z.negative_count, "richtig", "abweichend"),
      klassenMarke(z.resource_class, z.status_label),
      zeitpunkt(z.last_evidence),
    ]);
}

export default {
  zahl: (z) => ({ wert: z.profil.representation_evidence.length || null, ebene: "evidenz",
                  was: "Darstellungsfacetten" }),

  render(zustand) {
    const { profil, katalog } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const wurzel = el("div");

    /* --- Darstellung im engeren Sinn ---------------------------------- */

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("evidenz", "Darstellungsevidenz (EIS)", "§16"),
      el("p.leer", vokabularInfo("REPRESENTATION_MODE")?.beschreibung || ""),
      // Das gelieferte Objekt, nicht die eigene Herleitung. Vorher stand hier
      // dieselbe Tabelle, aus `competency_states` zusammengesucht: die
      // Navigationszahl zaehlte `representation_evidence`, die Ansicht zeigte
      // etwas anderes - inhaltlich gleich, aber aus zwei Quellen. Dass die
      // EIS-Sicht genau diese Facetten sind, entscheidet api.py (§16).
      darstellungsTabelle(profil.representation_evidence, knotenNachId),
      merkzettel("Ein Unterschied zwischen zwei Darstellungen ist hier eine "
        + "Beobachtung. Ob er an der Darstellung liegt, prüft eine Hypothese – "
        + "ein Vergleich muss dafür Niveau, Antwortformat und Frageform "
        + "konstant halten (§116)."),
      sprung("Darstellungsbezogene Hypothesen ansehen", { ansicht: "hypothesen" })));

    /* --- Bedienform, ausdrücklich getrennt ----------------------------- */

    wurzel.append(abschnitt("Bedienform", "§17 – getrennt von der Darstellung",
      el("p.leer", vokabularInfo("INTERACTION_MODE")?.beschreibung || ""),
      facettenTabelle(profil.competency_states, "INTERACTION_MODE", knotenNachId)));

    /* --- Beobachtungen nach Darstellung ------------------------------- */

    const nachDarstellung = gruppieren(profil.observations, (b) => b.representation_mode);
    wurzel.append(abschnitt("Beobachtungen je Darstellung", "§60",
      el("p.leer", "Die rohe Zählung, ohne Verdichtung."),
      tabelle(["Darstellung", "Beobachtungen", "Aufgaben"],
        [...nachDarstellung.entries()].sort(),
        ([modus, liste]) => [
          el("span", {}, label("REPRESENTATION_MODE", modus), el("br"),
            el("span.mono.leer", modus)),
          waage(liste.filter((b) => b.is_correct).length,
            liste.filter((b) => !b.is_correct).length, "richtig", "abweichend"),
          el("div.chips", {}, liste.map((b) =>
            sprung(b.task_id, { ansicht: "verlauf", aufgabe: b.task_id }))),
        ])));

    /* --- Aufgabenmerkmale insgesamt ----------------------------------- */

    wurzel.append(abschnitt("Weitere Aufgabenmerkmale", "§15, §20–§23, §112",
      el("p.leer", "Merkmale beschreiben die Aufgabe, nicht die Schüler:in. "
        + "Sie stehen hier, weil ein Unterschied zwischen zwei Aufgaben nur dann "
        + "interpretierbar ist, wenn bekannt ist, worin sie sich unterscheiden."),
      el("div", {}, FACETTEN_ARTEN.filter(([art]) =>
        art !== "REPRESENTATION_MODE" && art !== "INTERACTION_MODE")
        .map(([art, fundstelle]) => el("details", { style: "margin-bottom:.4rem" },
          el("summary", { style: "cursor:pointer;padding:.25rem 0" },
            el("span.wichtig", vokabularTitel(art)),
            el("span.quelle", ` · ${fundstelle}`)),
          facettenTabelle(profil.competency_states, art, knotenNachId))))));

    /* --- Prozesskompetenzen ------------------------------------------- */

    wurzel.append(abschnitt("Prozesskompetenzen", "§8",
      profil.process_competency_evidence.length
        ? el("div", {},
          tabelle(["Prozesskompetenz", "Beobachtungen", "Aufgaben"],
            profil.process_competency_evidence,
            (p) => [
              label("PROCESS_COMPETENCY", p.process_competency),
              waage(p.observed_correct, p.observed_incorrect, "richtig", "abweichend"),
              el("div.chips", {}, p.tasks.map((t) =>
                sprung(t, { ansicht: "verlauf", aufgabe: t }))),
            ]),
          merkzettel(profil.process_competency_evidence[0].note))
        : leer("Keine der bearbeiteten Aufgaben trägt eine Prozesskompetenz.")));

    return wurzel;
  },
};
