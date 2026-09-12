/* Debug und Dateneffizienz.
 *
 * Der Zweck dieser Ansicht ist nicht Vollständigkeit, sondern das Gegenteil:
 * sichtbar zu machen, dass NICHT alle vorhandenen Daten in jede Entscheidung
 * eingehen. Deshalb steht neben "verwendete Daten" ausdrücklich die Liste der
 * nicht herangezogenen – eine Entscheidung, die alles benutzt, erklärt nichts.
 *
 * Die Mengendifferenz dafür wird hier gebildet, nicht im Backend: welche
 * Evidenz eine Regel benutzt hat, protokolliert das Backend (§89); was davon
 * übrigbleibt, ist reine Ablesung.
 */

import { el, abschnitt, kv, leer, chips, merkzettel, tabelle, hypotheseMarke,
         ebene, ebenenTitel, sprung, zeitpunkt } from "../dom.js";
import { label, kurzName } from "../labels.js";
import { nachId } from "../data.js";
import * as daten from "../data.js";

/** Die elf Summanden des Aufgabenscores tragen im Protokoll technische Namen.
 *  Die Zuordnung zu einer deutschen Bezeichnung ist Beschriftung, keine
 *  Gewichtung – die Gewichte stehen in der Konfiguration und werden unten
 *  vollständig angezeigt. */
const SUMMAND = {
  information_need: "Informationsbedarf am Knoten",
  facet_novelty: "neue Merkmalskombination",
  hypothesis_discrimination: "trennt konkurrierende Hypothesen",
  boundary_value: "liegt an der beobachteten Grenze",
  confirmation: "bestätigt einen vorläufigen Befund",
  family_completion: "vervollständigt eine Aufgabenfamilie",
  transfer_value: "Transferwert",
  redundancy: "Redundanzabzug",
  estimated_cost: "Aufwandsabzug",
  route: "durch eine Route erzwungen",
  replication: "wiederholt einen Fehler zur Musterprüfung",
};

/* Ein Score, so genau wie er geliefert wurde.
 *
 * `toFixed(1)` hat aus 2.9375 und 2.8750 zweimal "2.9" gemacht. In dreizehn der
 * protokollierten Entscheidungen stand danach der Hoechstwert mehrfach da, und
 * die Ansicht, die genau erklaeren soll, warum diese Aufgabe gewaehlt wurde,
 * konnte es nicht mehr. Gerundet wird deshalb erst dort, wo die Zahl ohnehin
 * endet - hoechstens vier Stellen, nachlaufende Nullen weg.
 */
/** Wie viele Kandidaten den Hoechstwert teilen - 0, wenn der Gewinner allein steht. */
function gleichstand(entscheidung) {
  const werte = entscheidung.alternatives_considered
    .map((a) => a.score).filter((w) => typeof w === "number");
  if (werte.length < 2) return 0;
  const hoechster = Math.max(...werte);
  const anzahl = werte.filter((w) => w === hoechster).length;
  return anzahl > 1 ? anzahl : 0;
}

function score(wert) {
  if (typeof wert !== "number" || !Number.isFinite(wert)) return String(wert ?? "–");
  return String(Number(wert.toFixed(4)));
}

function entscheidungKarte(entscheidung, daten_, offen) {
  const { profil, aufgabenNachId, knotenNachId, hypothesenNachId, istDoppelt } = daten_;
  const alleEvidenz = profil.evidence.map((e) => e.evidence_id);
  const benutzt = new Set(entscheidung.evidence_used);
  const nichtBenutzt = alleEvidenz.filter((id) => !benutzt.has(id));
  // Zu welchen Knoten die benutzten Eintraege gehoeren. Das ist ein Nachschlagen
  // in `profil.evidence`, keine Deutung: die Zuordnung Evidenz -> Knoten steht
  // in den Daten. Sie beantwortet die Frage, die der Auftrag unter
  // "Dateneffizienz" stellt - welche Daten waren fuer diese Entscheidung
  // ueberhaupt im Blick -, ohne dass die Oberflaeche die Auswahlregel errät.
  const knotenDerBenutzten = [...new Set(profil.evidence
    .filter((e) => benutzt.has(e.evidence_id))
    .map((e) => e.competency_id))];
  const geprueft = new Set(entscheidung.hypothesis_used);
  const nichtGeprueft = profil.hypotheses
    .filter((h) => !geprueft.has(h.hypothesis_id));
  const aufgabe = entscheidung.selected_task
    ? aufgabenNachId.get(entscheidung.selected_task) : null;
  const summanden = Object.entries(entscheidung.score_breakdown || {})
    .filter(([, wert]) => wert !== 0)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  return el("details.karte", { open: offen || null, id: `entscheidung-${entscheidung.decision_id}` },
    el("summary", { style: "cursor:pointer" },
      el("span.wichtig", entscheidung.selected_task
        ? `→ ${entscheidung.selected_task}`
        : "→ keine weitere Aufgabe"),
      el("span.quelle", `  ${zeitpunkt(entscheidung.timestamp)}`
        + `  ·  ${entscheidung.decision_id}`
        + `  ·  Konfidenz ${label("CONFIDENCE_LEVEL", entscheidung.confidence)}`),
      istDoppelt
        ? el("span.chip.chip-leer", { title: "In allen gelieferten Feldern identisch "
            + "mit der vorangehenden Zeile." }, "feldgleich mit der Vorgängerin")
        : null),

    el("div", { style: "margin-top:.6rem" }, kv([
      ["Vorherige Aufgabe", entscheidung.previous_task
        ? el("span.mono", entscheidung.previous_task) : el("span.leer", "Beginn des Durchlaufs")],
      ["Gewählte Aufgabe", entscheidung.selected_task
        ? el("span", {}, sprung(entscheidung.selected_task,
            { ansicht: "verlauf", aufgabe: entscheidung.selected_task }),
            aufgabe ? ` – ${aufgabe.title}` : "")
        : el("span.leer", "keine")],
      ["Auslösende Regel", el("span.mono", entscheidung.rule_triggered || "–")],
      ["Kompetenz der Aufgabe", aufgabe
        ? sprung(kurzName(knotenNachId.get(aufgabe.primary_competency)?.name
            || aufgabe.primary_competency), { ansicht: "karte", knoten: aufgabe.primary_competency })
        : null],
      ["Bedingung der Aufgabe", aufgabe
        ? el("span", {}, label("INTERNAL_DIFFICULTY", aufgabe.internal_difficulty), " · ",
            label("REPRESENTATION_MODE", aufgabe.representation_mode), " · ",
            label("QUESTION_FORM", aufgabe.question_form))
        : null],
    ])),

    el("div", { style: "margin-top:.8rem" },
      el("h4", "Warum diese Aufgabe – die Summanden des Scores"),
      summanden.length
        ? tabelle(["Summand", "Beitrag"], summanden, ([name, wert]) => [
          el("span", {}, SUMMAND[name] || name, el("br"), el("span.mono.leer", name)),
          el("span", { class: wert < 0 ? "leer" : "wichtig" },
            `${wert > 0 ? "+" : ""}${score(wert)}`),
        ])
        : leer("Diese Entscheidung stammt nicht aus dem Score, sondern aus einer "
          + "Regel oder einem Abbruch.")),

    el("div", { style: "margin-top:.8rem" },
      el("h4", "Betrachtete Kandidatenaufgaben"),
      entscheidung.alternatives_considered.length
        ? tabelle(["Aufgabe", "Score", "Grund", "Route"],
          entscheidung.alternatives_considered,
          (a) => [
            el("span", { class: a.task_id === entscheidung.selected_task ? "wichtig" : "" },
              el("span.mono", a.task_id),
              a.task_id === entscheidung.selected_task ? " ← gewählt" : ""),
            score(a.score),
            a.reason ? label("ROUTE_REASON", a.reason) : el("span.leer", "–"),
            a.route_id ? el("span.mono", a.route_id) : el("span.leer", "–"),
          ])
        : leer("Es standen keine Kandidaten zur Auswahl."),
      // Bei Gleichstand ist die Wahl aus dem Protokoll nicht erklaerbar: der
      // Abstand zum Zweitplatzierten (`margin`) wird berechnet, aber nicht
      // gespeichert. Das zu verschweigen waere schlimmer als es zu sagen.
      gleichstand(entscheidung)
        ? merkzettel(`${gleichstand(entscheidung)} Kandidaten haben denselben `
          + "höchsten Score. Warum die Wahl auf diese Aufgabe fiel, hält das "
          + "Protokoll nicht fest.")
        : null),

    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("evidenz"), " Verwendete Daten"),
      entscheidung.evidence_used.length
        ? chips(entscheidung.evidence_used)
        : leer("keine Evidenz herangezogen"),
      benutzt.size
        ? el("p.leer", { style: "margin-top:.2rem" },
            knotenDerBenutzten.length === 1
              ? "Alle aufgeführten Einträge gehören zum Knoten "
                + `${kurzName(knotenNachId.get(knotenDerBenutzten[0])?.name
                    || knotenDerBenutzten[0])}.`
              : `Die aufgeführten Einträge verteilen sich auf ${knotenDerBenutzten.length} `
                + "Kompetenzknoten.")
        : null,
      el("h4", { style: "margin-top:.6rem" }, "Nicht herangezogen"),
      // Der Auftrag verlangt, sichtbar zu machen, dass nicht alle vorhandenen
      // Daten in jede Entscheidung eingehen. Er verlangt nicht, dass die
      // Oberflaeche das bewertet. Vorher stand hier der Satz "Eine Entscheidung,
      // die alles benutzt, erklaert nichts" - eine eigene fachliche Behauptung,
      // und noch dazu eine, die die Zahl ueberdeutet: das Protokoll haelt fest,
      // WELCHE Eintraege benutzt wurden, aber nicht, WARUM die uebrigen fehlen.
      // Der Unterschied zwischen "nicht relevant" und "nicht nachgeschlagen"
      // ist aus den Daten nicht zu erkennen, also behauptet die Oberflaeche ihn
      // auch nicht.
      nichtBenutzt.length
        ? el("div", {}, chips(nichtBenutzt),
            el("p.leer", { style: "margin-top:.2rem" },
              `${nichtBenutzt.length} von ${alleEvidenz.length} Evidenzeinträgen stehen `
              + "nicht in der Liste oben. Das Protokoll hält fest, welche Einträge in "
              + "die Auswahl eingegangen sind – nicht, aus welchem Grund die übrigen "
              + "fehlen."))
        : el("p.leer", "Alle vorhandenen Evidenzeinträge stehen in der Liste oben.")),

    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("hypothese"), " Geprüfte Hypothesen"),
      entscheidung.hypothesis_used.length
        ? el("div", {}, entscheidung.hypothesis_used.map((id) => {
          const h = hypothesenNachId.get(id);
          return el("p", { style: "margin:.15rem 0" },
            h ? hypotheseMarke(h.status) : null, " ",
            sprung(id, { ansicht: "hypothesen", hypothese: id }),
            h ? el("span.leer", `  ${h.description}`) : null);
        }))
        : leer("Diese Entscheidung prüft keine Hypothese."),
      nichtGeprueft.length
        ? el("p.leer", { style: "margin-top:.3rem" },
          `Nicht geprüft: ${nichtGeprueft.map((h) => h.hypothesis_id).join(", ")}`)
        : null));
}

export default {
  zahl: (z) => ({ wert: z.profil.routing_decisions.length || null, ebene: null,
                  was: "protokollierte Entscheidungen" }),

  render(zustand) {
    const { profil, katalog, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const hypothesenNachId = nachId(profil.hypotheses, "hypothesis_id");
    const gewaehlt = parameter.get("entscheidung");

    const wurzel = el("div");
    const aktuell = profil.next_decision;

    /* --- Die aktive diagnostische Frage -------------------------------- */

    // `is_active` statt `state === "PLANNED"`: ob eine Hypothese gerade
    // geprueft wird, haengt auch an ihrem Status, und diese Bedingung gehoert
    // nicht ins Frontend. api.py liefert sie fertig (§115).
    const offeneHypothesen = profil.hypotheses.filter(
      (h) => h.hypothesis_test.is_active);

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("zustand", "Aktive diagnostische Frage", "§119, §89"),
      aktuell
        ? kv([
          ["Stand", aktuell.is_pending
            ? el("span.wichtig", "Eine Aufgabe ist ausgewählt und noch nicht bearbeitet.")
            : aktuell.selected_task
              ? el("span.leer", "Die zuletzt gewählte Aufgabe ist bereits bearbeitet.")
              : el("span.wichtig", "Das System hat entschieden, nicht weiter zu testen (§73).")],
          ["Frage", aktuell.selected_task
            ? el("span", {}, "Wie verhält sich die Bearbeitung bei ",
                el("span.mono", aktuell.selected_task), "?")
            : null],
          ["Auslösende Regel", el("span.mono", aktuell.rule_triggered || "–")],
          ["Konfidenz der Auswahl", el("span", {},
            label("CONFIDENCE_LEVEL", aktuell.confidence),
            el("span.leer", " – Sicherheit der Auswahl, nicht der Diagnose (§88)"))],
        ])
        : leer("Noch keine Entscheidung protokolliert."),
      el("div", { style: "margin-top:.7rem" },
        el("h4", {}, ebene("pruefung"), " Derzeit geprüfte Hypothesen"),
        offeneHypothesen.length
          ? el("div", {}, offeneHypothesen.map((h) => el("p", { style: "margin:.15rem 0" },
            hypotheseMarke(h.status), " ",
            sprung(h.hypothesis_id, { ansicht: "hypothesen", hypothese: h.hypothesis_id }),
            " — Kontrollaufgabe ", el("span.mono", h.hypothesis_test.task_id))))
          : leer("Derzeit ist keine Hypothesenprüfung vorgemerkt."))));

    /* --- Das vollständige Protokoll ------------------------------------ */

    // Feldgleiche Nachbarn. Bis zu einer Korrektur im Backend hat ein Zug zwei
    // Zeilen geschrieben - eine beim Ausliefern der Aufgabe, eine beim
    // Auswerten. In den bereits erzeugten Profilen stehen sie weiterhin. Der
    // Vergleich ist ein Zeichenkettenvergleich ueber die gelieferten Felder,
    // keine Deutung; behauptet wird nur, dass zwei Zeilen gleich aussehen.
    const doppelte = new Set();
    for (let i = 1; i < profil.routing_decisions.length; i++) {
      const vorher = { ...profil.routing_decisions[i - 1], decision_id: "", timestamp: "" };
      const jetzt = { ...profil.routing_decisions[i], decision_id: "", timestamp: "" };
      if (JSON.stringify(vorher) === JSON.stringify(jetzt)) {
        doppelte.add(profil.routing_decisions[i].decision_id);
      }
    }

    wurzel.append(el("section.abschnitt", {},
      el("h2", {}, "Entscheidungsprotokoll",
        el("span.quelle", " · §89 Explainability Logging")),
      merkzettel("Das Protokoll entsteht beim Entscheiden, nicht beim Betrachten – "
        + "diese Oberfläche greift nur lesend zu und erzeugt keine Einträge."),
      doppelte.size
        ? merkzettel(`${doppelte.size} von ${profil.routing_decisions.length} Zeilen sind `
          + "in allen Feldern mit ihrer Vorgängerin identisch und unten als solche "
          + "gekennzeichnet. Sie stammen aus Durchläufen vor einer Korrektur im "
          + "Backend, die je Zug zwei Zeilen geschrieben hat. Eine Zeile hier ist "
          + "deshalb nicht in jedem Fall eine eigene Entscheidung.")
        : null,
      profil.routing_decisions.length
        ? el("div.karten", { style: "grid-template-columns:1fr" },
          [...profil.routing_decisions].reverse().map((d) => entscheidungKarte(d,
            { profil, aufgabenNachId, knotenNachId, hypothesenNachId,
              istDoppelt: doppelte.has(d.decision_id) },
            gewaehlt ? d.decision_id === gewaehlt : d === profil.routing_decisions.at(-1))))
        : leer("Kein Protokolleintrag vorhanden.")));

    /* --- Schwellenwerte ------------------------------------------------ */

    const konfigBlock = el("div", {}, el("p.laedt", "Konfiguration wird geladen …"));
    wurzel.append(abschnitt("Schwellenwerte und Regelparameter", "§35, §41",
      el("p.leer", "Alle Werte, nach denen die Engine entscheidet, stehen als Daten in "
        + "der Datenbank – nicht im Code und erst recht nicht in dieser Oberfläche. "
        + "UNDEFINED heißt: fachlich noch nicht festgelegt; die Engine nimmt dann "
        + "keinen Ersatzwert an (§1)."),
      konfigBlock));

    daten.konfiguration().then((eintraege) => {
      konfigBlock.replaceChildren(tabelle(
        ["Schlüssel", "Wert", "Verbindlichkeit", "Fundstelle"],
        eintraege,
        (k) => [
          el("span.mono", k.config_key),
          k.value === null
            ? el("span.leer", "UNDEFINED")
            : el("span.mono.wichtig", String(k.value)),
          el("span", {}, label("CONFIG_STATUS", k.status), el("br"),
            el("span.mono.leer", k.status)),
          el("span.leer", k.spec_section || "–"),
        ]));
    }).catch((fehler) => {
      konfigBlock.replaceChildren(el("p.leer", `Nicht geladen: ${fehler.message || fehler}`));
    });

    if (gewaehlt) {
      queueMicrotask(() => document
        .getElementById(`entscheidung-${gewaehlt}`)
        ?.scrollIntoView({ block: "center" }));
    }

    return wurzel;
  },
};
