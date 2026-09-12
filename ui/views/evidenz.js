/* Evidenz.
 *
 * Die mittlere der drei Ebenen: aus Beobachtungen abgeleitete Belege für oder
 * gegen eine Kompetenz. Sie ist weder die Beobachtung selbst noch der Zustand,
 * der aus ihr folgt – beides ist von hier aus verlinkt, aber nicht vermischt.
 *
 * Zwei Eigenheiten des Backends werden hier sichtbar gemacht, weil sie sonst
 * als Ungereimtheit erschienen:
 *
 * 1. Nicht jede Evidenz bewegt den Status. Darstellungs-, Strategie- und
 *    Transferevidenz tragen Facetten und Hypothesen, nicht die Statusrechnung.
 *    Die Spalte "statuswirksam" zeigt das.
 * 2. Eine richtige Antwort erzeugt indirekte positive Evidenz auf die
 *    Voraussetzungen. Eine falsche erzeugt KEINE indirekte negative – aus
 *    einem Fehlversuch folgt nicht, dass eine Voraussetzung fehlt (§29, §121).
 *    Deshalb steht INDIRECT_NEGATIVE in der Übersicht bei null, und das ist
 *    kein Datenmangel, sondern die Regel.
 */

import { el, abschnitt, leer, merkzettel, tabelle, richtungsMarke, ergebnisMarke,
         ebenenTitel, ebene, sprung, zeitpunkt, waage, antwortText, optionen }
  from "../dom.js";
import { label, kurzName, vokabularInfo } from "../labels.js";
import { nachId, gruppieren } from "../data.js";

export default {
  zahl: (z) => ({ wert: z.profil.evidence.length || null, ebene: "evidenz",
                  was: "Evidenzeinträge" }),

  render(zustand) {
    const { profil, katalog, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const beobachtungNachId = nachId(profil.observations, "attempt_id");

    const knotenFilter = parameter.get("knoten");
    const typFilter = parameter.get("typ");
    const richtungFilter = parameter.get("richtung");
    // Die Hypothesenansicht verweist hierher: sie kennt Versuchskennungen, denn
    // `supporting_evidence` fuehrt Beobachtungen, keine Evidenzzeilen. Der Weg
    // von der Beobachtung zu ihren Evidenzzeilen ist ein Fremdschluessel
    // (`source_attempt`), keine Deutung.
    const beobachtungFilter = parameter.get("beobachtung");

    const setze = (schluessel, wert) => {
      const p = new URLSearchParams(parameter);
      if (wert === null || wert === "") p.delete(schluessel); else p.set(schluessel, wert);
      location.hash = `#evidenz?${p}`;
    };

    let liste = profil.evidence;
    if (knotenFilter) liste = liste.filter((e) => e.competency_id === knotenFilter);
    if (typFilter) liste = liste.filter((e) => e.evidence_type === typFilter);
    if (richtungFilter) liste = liste.filter((e) => e.direction === richtungFilter);
    if (beobachtungFilter) liste = liste.filter((e) => e.source_attempt === beobachtungFilter);

    const typen = [...new Set(profil.evidence.map((e) => e.evidence_type))].sort();
    const knoten = [...new Set(profil.evidence.map((e) => e.competency_id))].sort();

    const wurzel = el("div");

    /* --- Verteilung ---------------------------------------------------- */

    const nachTyp = gruppieren(profil.evidence, (e) => e.evidence_type);
    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("evidenz", "Evidenz nach Art", "§28, §65"),
      tabelle(["Evidenzart", "Anzahl", "Richtung", "statuswirksam"],
        [...nachTyp.entries()].sort(),
        ([typ, eintraege]) => [
          el("span", {}, label("EVIDENCE_TYPE", typ), el("br"), el("span.mono.leer", typ)),
          el("button.chip", { type: "button", onclick: () => setze("typ", typ) },
            `${eintraege.length} anzeigen`),
          el("div.chips", {}, [...new Set(eintraege.map((e) => e.direction))]
            .map((r) => richtungsMarke(r))),
          eintraege[0].is_scored
            ? el("span", {}, "ja – geht in die Statusrechnung ein")
            : el("span.leer", "nein – trägt Facetten und Hypothesen"),
        ]),
      merkzettel("Aus einer richtigen Antwort folgt indirekte positive Evidenz auf "
        + "die Voraussetzungen. Aus einer falschen folgt keine indirekte negative: "
        + "ein Fehlversuch belegt nicht, dass eine Voraussetzung fehlt (§29, §121).")));

    /* --- Bilanz je Knoten ---------------------------------------------- */

    wurzel.append(abschnitt("Evidenz und Gegen-Evidenz je Kompetenz", "§66",
      tabelle(["Kompetenz", "Bilanz", "Zustand daraus", "Einträge"],
        [...gruppieren(profil.evidence, (e) => e.competency_id).entries()].sort(),
        ([id, eintraege]) => {
          const zustandDesKnotens = profil.competency_states.find((z) => z.competency_id === id);
          return [
            sprung(kurzName(knotenNachId.get(id)?.name || id), { ansicht: "karte", knoten: id }),
            waage(eintraege.filter((e) => e.direction === "POSITIVE").length,
              eintraege.filter((e) => e.direction === "NEGATIVE").length,
              "stützend", "gegenläufig"),
            zustandDesKnotens
              ? el("span", {}, ebene("zustand"), " ", zustandDesKnotens.status_label)
              : el("span.leer", "kein Zustand"),
            el("button.chip", { type: "button", onclick: () => setze("knoten", id) },
              `${eintraege.length} anzeigen`),
          ];
        }),
      merkzettel("Die Bilanz ist eine Zählung, kein Maß. Aus ihr folgt der Status "
        + "nicht durch Mehrheit – die Regel dafür steht im Backend (§28, §41).")));

    /* --- Einzeleinträge ------------------------------------------------ */

    const filter = el("div.filterleiste", {},
      el("label", {}, "Kompetenz",
        el("select", { "data-fokus": "knoten", onchange: (e) => setze("knoten", e.target.value) },
          optionen(knotenFilter, knoten, (k) =>
            kurzName(knotenNachId.get(k)?.name || k)))),
      el("label", {}, "Evidenzart",
        el("select", { "data-fokus": "typ", onchange: (e) => setze("typ", e.target.value) },
          optionen(typFilter, typen, (t) => label("EVIDENCE_TYPE", t)))),
      el("label", {}, "Richtung",
        el("select", { "data-fokus": "richtung", onchange: (e) => setze("richtung", e.target.value) },
          optionen(richtungFilter, ["POSITIVE", "NEGATIVE", "NEUTRAL"],
            (r) => label("EVIDENCE_DIRECTION", r)))),
      beobachtungFilter
        ? el("span.chip", {}, `nur zur Beobachtung ${beobachtungFilter}`)
        : null,
      (knotenFilter || typFilter || richtungFilter || beobachtungFilter)
        ? el("button", { type: "button", onclick: () => { location.hash = "#evidenz"; } },
            "Filter zurücksetzen")
        : null);

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("evidenz", "Einzelne Evidenzeinträge", "§65"),
      filter,
      el("p.leer", `${liste.length} von ${profil.evidence.length} Einträgen`),
      tabelle(
        ["Zeitpunkt", "Kompetenz", "Art", "Richtung", "Stärke", "Auslösende Beobachtung"],
        liste,
        (e) => {
          const beobachtung = beobachtungNachId.get(e.source_attempt);
          return [
            zeitpunkt(e.created_at),
            el("span", {}, kurzName(knotenNachId.get(e.competency_id)?.name || e.competency_id),
              el("br"), el("span.mono.leer", e.competency_id)),
            el("span", {}, label("EVIDENCE_TYPE", e.evidence_type),
              e.is_scored ? null : el("span.leer", " (nicht statuswirksam)")),
            richtungsMarke(e.direction),
            // Wie bei der Konsistenz in karte.js: der Wert stammt aus der Engine,
            // die Skala nicht aus dem Nichts. Ohne Hinweis liest sich "0.4" wie
            // ein Anteil.
            e.strength === null || e.strength === undefined
              ? el("span.leer", "–")
              : el("span", { title: "Gewicht dieses Eintrags nach "
                  + "evidence.strength_formula (§65) – abhängig von der Evidenzart "
                  + "und davon, ob Hilfe benutzt wurde. Kein Anteil." },
                String(e.strength)),
            e.source_task
              ? el("span", {},
                sprung(e.source_task, { ansicht: "verlauf", aufgabe: e.source_task }),
                beobachtung
                  ? el("span", {}, " ", ergebnisMarke(beobachtung.is_correct), el("br"),
                      el("span.mono.leer", antwortText(beobachtung.answer)))
                  : el("span.leer", " (indirekt: aus einer Aufgabe zu einer anderen Kompetenz)"))
              : el("span.leer", "ohne Aufgabenbezug"),
          ];
        })));

    return wurzel;
  },
};
