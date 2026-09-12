/* Fehleranalyse.
 *
 * Die heikelste Ansicht. Ein Fehlercode beschreibt, WAS von der erwarteten
 * Antwort abweicht – nicht, WARUM. Ein wiederholter Fehler beim Zehnerübergang
 * erscheint hier als Fehlermuster und wird nicht zu einem "Stellenwertdefizit".
 * Was die Abweichung verursacht, steht offen; deshalb führt jedes Muster die
 * konkurrierenden Hypothesen mit, statt eine Ursache zu nennen.
 *
 * Dieses Modul leitet keine Ursache ab. Es gibt hier keine Zeile, die aus
 * einem Fehlercode auf eine Kompetenz schließt – das ist Absicht und der Kern
 * des Auftrags.
 */

import { el, abschnitt, kv, leer, chips, merkzettel, tabelle, ergebnisMarke,
         hypotheseMarke, ebene, ebenenTitel, sprung, zeitpunkt, antwortText, waage,
         optionen }
  from "../dom.js";
import { label, kurzName, vokabularTitel } from "../labels.js";
import { nachId } from "../data.js";

/** Fehlerfamilie: der Teil des Codes vor dem spezifischen Namen. Das ist eine
 *  Ablesung der Kennung, keine fachliche Gruppierung – ERR_PLACE_VALUE und
 *  ERR_PLACE_VALUE_SWAP gehören erkennbar zusammen. Eine eigene Taxonomie
 *  führt diese Oberfläche nicht ein. */
function familie(code, alleCodes) {
  const kandidaten = alleCodes
    .filter((c) => c !== code && code.startsWith(`${c}_`))
    .sort((a, b) => b.length - a.length);
  return kandidaten[0] || code;
}

/* Die konkrete Abweichung einer Beobachtung.
 *
 * `detail` ist das, was der Fehlercode gerade NICHT sagt: nicht "Stellenwert",
 * sondern "erwartet 60, gegeben 6". Genau dieses Paar ist das Beispiel aus §66,
 * und es ist der einzige Weg, auf dem die tatsächliche Antwort die Oberfläche
 * erreicht - die Aufgabenbank gibt `correct_answer` nicht heraus.
 *
 * Ein Fehlercode allein ist nicht interpretierbar. Weil er nur das Was benennt
 * und nicht das Warum, muss die Rohbeobachtung daneben lesbar bleiben; sonst
 * bleibt von der verbotenen Deutung nur die Abkürzung übrig. */
function abweichung(detail) {
  if (!detail) return null;
  let werte = detail;
  if (typeof detail === "string") {
    try { werte = JSON.parse(detail); } catch { return el("span.mono", detail); }
  }
  if (!werte || typeof werte !== "object") return el("span.mono", String(detail));
  const erwartet = werte.expected && typeof werte.expected === "object"
    ? werte.expected.value : werte.expected;
  const gegeben = werte.given;
  if (erwartet === undefined && gegeben === undefined) {
    return el("span.mono", JSON.stringify(werte));
  }
  return el("span", {},
    "erwartet ", el("span.mono.wichtig", antwortText(erwartet)),
    ", gegeben ", el("span.mono.wichtig", antwortText(gegeben)));
}

function musterKarte(muster, daten, gewaehlt) {
  const { knotenNachId, hypothesenNachId, alleCodes, setze } = daten;
  const offen = muster.error_code === gewaehlt;
  return el("div.karte", {},
    el("div.karte-kopf", {},
      el("h3", {}, ebene("fehler"), " ", muster.label),
      el("span.marke", { class: `marke marke-${muster.reproduced ? "offen" : "ungeprueft"}` },
        el("span.marke-zeichen", { "aria-hidden": "true" }, muster.reproduced ? "▣" : "▢"),
        muster.reproduced ? "reproduziert" : "einmalig beobachtet")),
    el("p.mono.leer", { style: "margin:.1rem 0 .5rem" },
      `${muster.error_code}  ·  Familie ${familie(muster.error_code, alleCodes)}`
      + `  ·  ${muster.spec_section || ""}`),
    el("p", muster.description),
    kv([
      ["Anzahl Beobachtungen", `${muster.observation_count}`],
      ["Reproduziert", muster.reproduced
        ? `ja – ab ${muster.replication_threshold} Beobachtungen gilt ein Muster als `
          + "reproduziert (§30, Schwellenwert aus der Konfiguration)"
        : `nein – ${muster.observation_count} von ${muster.replication_threshold} `
          + "nötigen Beobachtungen"],
      ["Betroffener Kompetenzknoten", el("span", {},
        sprung(kurzName(knotenNachId.get(muster.competency_id)?.name || muster.competency_id),
          { ansicht: "karte", knoten: muster.competency_id }))],
      ["Betroffene Aufgaben", el("div.chips", {}, muster.tasks.map((t) =>
        sprung(t, { ansicht: "verlauf", aufgabe: t }, "im Aufgabenverlauf zeigen")))],
      ["Repräsentation", chips(muster.representations, "REPRESENTATION_MODE")],
      ["Niveaubereiche", chips(muster.difficulties, "INTERNAL_DIFFICULTY")],
      ["Frageformen", chips(muster.question_forms, "QUESTION_FORM")],
      ["Zusätzliche Aufgabenanforderungen",
        chips(muster.additional_demands, "ADDITIONAL_DEMAND", "keine hinterlegt")],
      // Der Rückweg von der Verdichtung zur Beobachtung. Ein Muster ist eine
      // Zusammenfassung; wer ihm nicht glauben will, muss die Zeilen sehen
      // können, aus denen es entstanden ist.
      ["Zugrundeliegende Beobachtungen", el("button.chip", {
        type: "button",
        onclick: () => setze({ fehler: muster.error_code, knoten: muster.competency_id }),
      }, `${muster.attempts.length} Einzelbeobachtungen unten zeigen`)],
    ]),
    el("details", { open: offen || null },
      el("summary", { style: "cursor:pointer;margin:.6rem 0 .3rem" },
        "Aufgabenmerkmale der betroffenen Aufgaben"),
      merkmale(muster.features)),
    el("div", { style: "margin-top:.8rem" },
      el("h4", {}, ebene("hypothese"), " Mögliche Hypothesen"),
      muster.candidate_hypotheses.length
        ? el("div", {}, muster.candidate_hypotheses.map((id) => {
          const h = hypothesenNachId.get(id);
          if (!h) return null;
          return el("div", { style: "margin-bottom:.5rem" },
            el("p", { style: "margin:0" }, hypotheseMarke(h.status), " ",
              el("span.mono", h.hypothesis_id)),
            el("p", { style: "margin:.1rem 0" }, h.description),
            el("p", { style: "margin:.1rem 0" },
              waage(h.evidence_balance.supporting, h.evidence_balance.contradicting,
                "Belege dafür", "dagegen")),
            sprung("Hypothese im Detail", { ansicht: "hypothesen", hypothese: h.hypothesis_id }));
        }))
        : leer("Zu diesem Muster ist derzeit keine Hypothese offen."),
      merkzettel("Mehrere Hypothesen nebeneinander sind der Normalfall, nicht ein "
        + "ungelöster Zwischenstand. Welche zutrifft, entscheidet die Prüfung – "
        + "nicht die Häufigkeit des Fehlers.")));
}

function merkmale(features) {
  const arten = Object.keys(features || {});
  if (!arten.length) return leer("keine Merkmale hinterlegt");
  return el("div", {}, arten.sort().map((art) => el("div", { style: "margin-bottom:.4rem" },
    el("h4", { style: "margin:0 0 .15rem", title: art }, vokabularTitel(art)),
    chips(features[art], art))));
}

export default {
  zahl: (z) => ({ wert: z.profil.error_observations.length || null, ebene: "fehler",
                  was: "Fehlerbeobachtungen" }),

  render(zustand) {
    const { profil, katalog, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const aufgabenNachId = nachId(katalog.tasks, "task_id");
    const hypothesenNachId = nachId(profil.hypotheses, "hypothesis_id");
    const alleCodes = katalog.error_codes.map((c) => c.error_code);

    const gewaehlt = parameter.get("fehler");
    const knotenFilter = parameter.get("knoten");
    const nurReproduziert = parameter.get("nurmuster") === "1";

    const setze = (schluessel, wert) => {
      const p = new URLSearchParams(parameter);
      const paare = typeof schluessel === "object" ? Object.entries(schluessel)
                                                   : [[schluessel, wert]];
      for (const [k, v] of paare) {
        if (v === null || v === "") p.delete(k); else p.set(k, v);
      }
      location.hash = `#fehleranalyse?${p}`;
    };

    let muster = profil.error_patterns;
    if (knotenFilter) muster = muster.filter((m) => m.competency_id === knotenFilter);
    if (nurReproduziert) muster = muster.filter((m) => m.reproduced);
    if (gewaehlt) muster = muster.filter((m) => m.error_code === gewaehlt);

    const knotenMitFehlern = [...new Set(profil.error_patterns.map((m) => m.competency_id))];
    const codesMitFehlern = [...new Set(profil.error_patterns.map((m) => m.error_code))];

    const filter = el("div.filterleiste", {},
      el("label", {}, "Fehlercode",
        el("select", { "data-fokus": "fehler", onchange: (e) => setze("fehler", e.target.value) },
          optionen(gewaehlt, codesMitFehlern, (c) =>
            `${katalog.error_codes.find((e) => e.error_code === c)?.label_de || c} (${c})`))),
      el("label", {}, "Kompetenzknoten",
        el("select", { "data-fokus": "knoten", onchange: (e) => setze("knoten", e.target.value) },
          optionen(knotenFilter, knotenMitFehlern, (k) =>
            kurzName(knotenNachId.get(k)?.name || k)))),
      el("label", {},
        el("input", {
          type: "checkbox", checked: nurReproduziert, "data-fokus": "nurmuster",
          onchange: (e) => setze("nurmuster", e.target.checked ? "1" : null),
        }), "nur reproduzierte Muster"),
      (gewaehlt || knotenFilter || nurReproduziert)
        ? el("button", { type: "button", onclick: () => { location.hash = "#fehleranalyse"; } },
            "Filter zurücksetzen")
        : null);

    const wurzel = el("div");

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("fehler", "Fehlermuster", "§30, §59"),
      merkzettel("Ein Fehlercode ist eine Beobachtung. Er benennt die Abweichung, "
        + "nicht ihre Ursache. Auch ein oft wiederholter Fehler bleibt ein Muster – "
        + "eine Ursache entsteht daraus nicht."),
      filter,
      muster.length
        ? el("div.karten", {}, muster.map((m) => musterKarte(m,
            { knotenNachId, hypothesenNachId, alleCodes, setze }, gewaehlt)))
        : leer(profil.error_patterns.length
            ? "Kein Muster passt zu dieser Auswahl."
            : "Es liegt keine Fehlerbeobachtung vor.")));

    // Die Einzelbeobachtungen, ungebündelt. Das Muster ist eine Verdichtung;
    // die Beobachtung bleibt daneben einsehbar (§60, §66 Ebene 1).
    const beobachtungen = profil.error_observations.filter((b) =>
      (!gewaehlt || b.error_code === gewaehlt)
      && (!knotenFilter || b.primary_competency === knotenFilter));

    wurzel.append(el("section.abschnitt", {},
      ebenenTitel("beobachtung", "Einzelne Fehlerbeobachtungen", "§60, §66 Ebene 1"),
      el("p.leer", "Unverdichtet, in zeitlicher Reihenfolge."),
      tabelle(
        ["Zeitpunkt", "Aufgabe", "Fehlercode", "Abweichung", "Kompetenz",
         "Darstellung", "Niveau", "Vermerk"],
        beobachtungen,
        (b) => [
          zeitpunkt(b.started_at),
          // Anklickbar, wie der Auftrag es fuer Fehler verlangt: von der
          // einzelnen Beobachtung zurueck in den Versuch, aus dem sie stammt.
          // Erst dort stehen Antwort, Hilfe und Dauer beieinander.
          el("span", {},
            sprung(b.task_id, { ansicht: "verlauf", aufgabe: b.task_id },
              "diesen Versuch im Aufgabenverlauf zeigen"),
            el("br"), el("span.leer", aufgabenNachId.get(b.task_id)?.title || "")),
          el("span", {}, b.label_de, el("br"), el("span.mono.leer", b.error_code)),
          // Abweichung und Vermerk sind zwei verschiedene Angaben und stehen
          // deshalb in zwei Spalten. Sie vorher in einer Zelle zu vermischen
          // hiess: weil ein Code nicht gewertet wird, bleibt auch verborgen,
          // was die Schueler:in geschrieben hat.
          abweichung(b.detail) || el("span.leer", "nicht erfasst"),
          kurzName(knotenNachId.get(b.primary_competency)?.name || b.primary_competency),
          label("REPRESENTATION_MODE", b.representation_mode),
          label("INTERNAL_DIFFICULTY", b.internal_difficulty),
          b.is_observation_only
            ? el("span.leer", "nur Beobachtung, keine Wertung")
            : el("span.leer", "geht in die Wertung ein"),
        ])));

    return wurzel;
  },
};
