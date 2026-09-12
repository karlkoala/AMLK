/* Kompetenzkarte.
 *
 * Graphbasiert: Kompetenzen sind Knoten, Relationen sind Kanten. Ein Klick auf
 * einen Knoten öffnet die Detailansicht rechts.
 *
 * Das Layout ist eine reine Darstellungsentscheidung und deshalb hier richtig
 * aufgehoben: Knoten werden nach der Länge ihrer Voraussetzungskette in
 * Spalten gelegt. Das ist eine Eigenschaft des Graphen, keine Aussage über die
 * Schüler:in – eine spätere Spalte ist nicht "höheres Niveau", sondern nur
 * "steht weiter hinten in der Voraussetzungskette".
 *
 * Farbe codiert die Ressourcenklasse, zusätzlich zu Zeichen und Text im
 * Knoten. In Graustufen bleibt die Karte vollständig lesbar.
 */

import { el, abschnitt, kv, leer, chips, merkzettel, klassenMarke, statusMarke,
         hypotheseMarke, richtungsMarke, ebene, sprung, waage } from "../dom.js";
import { label, kurzName, KLASSE, vokabularInfo, niveauBereich } from "../labels.js";
import { nachId, gruppieren } from "../data.js";

const BREITE = 208;
const HOEHE = 42;
const SPALTE = 316;
const ZEILE = 56;
const RAND = 24;

const VORAUSSETZUNG = ["STRONG_PREREQUISITE", "HARD_PREREQUISITE"];

/* --------------------------------------------------------------- Anordnung */

/** Spalte je Knoten: 1 + längste Voraussetzungskette. Zyklenfest durch die
 *  begrenzte Zahl der Durchläufe – der Graph ist fachlich azyklisch, aber die
 *  Darstellung darf an einer fehlerhaften Kante nicht hängenbleiben. */
function spalten(knoten, kanten) {
  const vorhanden = new Set(knoten.map((k) => k.competency_id));
  const eingehend = new Map(knoten.map((k) => [k.competency_id, []]));
  for (const kante of kanten) {
    if (!VORAUSSETZUNG.includes(kante.relation_type)) continue;
    if (!vorhanden.has(kante.source_competency) || !vorhanden.has(kante.target_competency)) continue;
    eingehend.get(kante.target_competency).push(kante.source_competency);
  }
  const stufe = new Map(knoten.map((k) => [k.competency_id, 0]));
  for (let durchlauf = 0; durchlauf < knoten.length; durchlauf++) {
    let geaendert = false;
    for (const k of knoten) {
      const quellen = eingehend.get(k.competency_id);
      const gewuenscht = quellen.length ? Math.max(...quellen.map((q) => stufe.get(q) + 1)) : 0;
      if (gewuenscht > stufe.get(k.competency_id)) { stufe.set(k.competency_id, gewuenscht); geaendert = true; }
    }
    if (!geaendert) break;
  }
  return stufe;
}

function anordnen(knoten, kanten) {
  const stufe = spalten(knoten, kanten);
  const nachStufe = gruppieren(knoten, (k) => stufe.get(k.competency_id));
  const punkte = new Map();
  let maxZeilen = 0;
  for (const [nummer, gruppe] of [...nachStufe.entries()].sort((a, b) => a[0] - b[0])) {
    gruppe.sort((a, b) => (a.parent_id || "").localeCompare(b.parent_id || "")
      || a.competency_id.localeCompare(b.competency_id));
    gruppe.forEach((k, i) => punkte.set(k.competency_id, {
      x: RAND + nummer * SPALTE, y: RAND + 18 + i * ZEILE, stufe: nummer,
    }));
    maxZeilen = Math.max(maxZeilen, gruppe.length);
  }
  const stufenZahl = Math.max(...[...nachStufe.keys()], 0) + 1;
  return {
    punkte,
    breite: RAND * 2 + (stufenZahl - 1) * SPALTE + BREITE,
    hoehe: RAND * 2 + 18 + maxZeilen * ZEILE,
    stufenZahl,
  };
}

/* ---------------------------------------------------------------- Zeichnen */

const svgEl = (tag, attribute = {}) => {
  const k = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [name, wert] of Object.entries(attribute)) {
    if (wert !== null && wert !== undefined) k.setAttribute(name, String(wert));
  }
  return k;
};

function kurven(von, nach) {
  const x1 = von.x + BREITE, y1 = von.y + HOEHE / 2;
  const x2 = nach.x, y2 = nach.y + HOEHE / 2;
  const spanne = Math.max(40, Math.abs(x2 - x1) * 0.45);
  return `M ${x1} ${y1} C ${x1 + spanne} ${y1}, ${x2 - spanne} ${y2}, ${x2} ${y2}`;
}

function graphZeichnen(knoten, kanten, zustandNachId, gewaehlt, beiKlick) {
  const { punkte, breite, hoehe, stufenZahl } = anordnen(knoten, kanten);
  const svg = svgEl("svg", {
    width: breite, height: hoehe, viewBox: `0 0 ${breite} ${hoehe}`,
    role: "group", "aria-label": "Kompetenzgraph",
  });

  const pfeil = svgEl("marker", {
    id: "pfeil", viewBox: "0 0 8 8", refX: 7, refY: 4,
    markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse",
  });
  pfeil.append(svgEl("path", { d: "M 0 1 L 8 4 L 0 7 z", fill: "var(--linie-stark)" }));
  const defs = svgEl("defs");
  defs.append(pfeil);
  svg.append(defs);

  for (let i = 0; i < stufenZahl; i++) {
    const t = svgEl("text", { x: RAND + i * SPALTE, y: RAND, class: "schicht-titel" });
    // "ohne harte Voraussetzung", nicht "ohne Voraussetzung": das Layout zählt
    // nur STRONG_ und HARD_PREREQUISITE. Ein Knoten der ersten Spalte kann im
    // Detailblock "Basiskompetenzen" sehr wohl Voraussetzungen führen – über
    // eine unterstützende oder darstellungsbezogene Relation.
    t.textContent = i === 0 ? "ohne harte Voraussetzung" : `Kette ${i}`;
    svg.append(t);
  }

  const kantenGruppe = svgEl("g", {});
  for (const kante of kanten) {
    const von = punkte.get(kante.source_competency);
    const nach = punkte.get(kante.target_competency);
    if (!von || !nach) continue;
    const beruehrt = gewaehlt
      && (kante.source_competency === gewaehlt || kante.target_competency === gewaehlt);
    const pfad = svgEl("path", {
      d: kurven(von, nach),
      class: `kante kante-${kante.relation_type}${beruehrt ? " kante-hervor" : ""}`,
      // Eine beidseitige Relation als einseitigen Pfeil zu zeichnen ist eine
      // falsche Richtungsbehauptung. Sie bekommt an beiden Enden eine Spitze.
      "marker-end": "url(#pfeil)",
      // `orient: "auto-start-reverse"` dreht denselben Marker am Startpunkt
      // von selbst um; ein zweites Symbol ist nicht noetig.
      "marker-start": kante.bidirectional ? "url(#pfeil)" : null,
    });
    const titel = svgEl("title");
    titel.textContent = `${kante.source_competency} ${kante.bidirectional ? "↔" : "→"}`
      + ` ${kante.target_competency}`
      + ` (${label("RELATION_TYPE", kante.relation_type)}, Evidenzgrad `
      + `${kante.evidence_status})`
      // `notes` steht in allen 85 Relationen und erklaert, warum die Kante
      // ueberhaupt existiert. Es ist der Text aus der Fachspezifikation und
      // gehoert an die Kante, nicht in die Datenbank allein.
      + (kante.notes ? `
${kante.notes}` : "");
    pfad.append(titel);
    kantenGruppe.append(pfad);
  }
  svg.append(kantenGruppe);

  for (const k of knoten) {
    const punkt = punkte.get(k.competency_id);
    const zustand = zustandNachId.get(k.competency_id);
    const klasse = zustand ? zustand.resource_class : null;
    const marke = klasse ? KLASSE[klasse] : null;

    const gruppe = svgEl("g", {
      class: `knoten ${klasse ? `knoten-${marke.stil}` : "knoten-ohne"}`,
      transform: `translate(${punkt.x} ${punkt.y})`,
      role: "button", tabindex: "0",
      "data-gewaehlt": k.competency_id === gewaehlt ? "ja" : null,
      // Nach dem Klick wird die Ansicht neu aufgebaut; app.js setzt den Fokus
      // hierüber auf denselben Knoten zurück, damit die Tastaturbedienung
      // nicht bei jedem Schritt an den Seitenanfang springt.
      "data-fokus": `knoten:${k.competency_id}`,
      "aria-label": `${k.name}, ${zustand ? zustand.status_label : "kein Zustand erfasst"}`,
    });
    gruppe.append(svgEl("rect", { width: BREITE, height: HOEHE, rx: 3 }));

    const kopf = svgEl("text", { x: 9, y: 17 });
    kopf.textContent = `${marke ? marke.zeichen : "·"} ${kuerzen(kurzName(k.name), 26)}`;
    gruppe.append(kopf);

    const fuss = svgEl("text", { x: 9, y: 31, class: "knoten-id" });
    fuss.textContent = zustand
      ? `${k.competency_id} · ${kuerzen(zustand.status_label, 22)}`
      : `${k.competency_id} · ohne Zustand`;
    gruppe.append(fuss);

    const titel = svgEl("title");
    titel.textContent = `${k.name}\n${zustand ? zustand.status_label : "kein Zustand erfasst"}`;
    gruppe.append(titel);

    gruppe.addEventListener("click", () => beiKlick(k.competency_id));
    gruppe.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); beiKlick(k.competency_id); }
    });
    svg.append(gruppe);
  }
  return svg;
}

const kuerzen = (text, n) => (text && text.length > n ? `${text.slice(0, n - 1)}…` : text || "");

/* ------------------------------------------------------------ Detailansicht */

function detail(id, daten) {
  const { katalog, profil, knotenNachId, zustandNachId, imGraphen } = daten;
  const knoten = knotenNachId.get(id);
  if (!knoten) return el("div.detail", {}, leer("Unbekannter Knoten."));

  const zustand = zustandNachId.get(id);
  const evidenz = profil.evidence.filter((e) => e.competency_id === id);
  const dafuer = evidenz.filter((e) => e.direction === "POSITIVE");
  const dagegen = evidenz.filter((e) => e.direction === "NEGATIVE");
  const muster = profil.error_patterns.filter((m) => m.competency_id === id);
  const hypothesen = profil.hypotheses.filter((h) => h.competency_id === id);
  const aufgaben = katalog.tasks.filter((t) => t.primary_competency === id);

  const prozess = [...new Set(aufgaben.flatMap((t) => t.process_competencies))];
  const anforderungen = [...new Set(aufgaben.flatMap(
    (t) => t.features.ADDITIONAL_DEMAND || []))];
  const niveaus = [...new Set(aufgaben.map((t) => t.internal_difficulty))].sort();

  const facetten = zustand ? zustand.facets : {};
  const alleFacetten = Object.entries(facetten).flatMap(
    ([art, werte]) => werte.map((w) => ({ ...w, art })));
  const ressourcen = alleFacetten.filter((f) => f.resource_class === "RESOURCE");
  const offene = alleFacetten.filter((f) => f.resource_class === "OPEN");

  const wurzel = el("div.detail", {},
    el("h3", kurzName(knoten.name)),
    el("p.detail-id", id),
    el("p", { style: "margin:.5rem 0" }, statusMarke(zustand)));

  // Der gewählte Knoten kann durch einen Filter aus dem Graphen gefallen sein.
  // Dann beschreibt diese Spalte eine Kompetenz, die links nicht zu sehen ist –
  // das muss dastehen, sonst verortet die Ansicht sie stillschweigend falsch.
  if (imGraphen === false) {
    wurzel.append(merkzettel("Dieser Knoten liegt außerhalb der aktuellen Auswahl "
      + "und ist im Graphen links deshalb nicht eingezeichnet."));
  }

  if (knoten.description) wurzel.append(el("p.leer", knoten.description));

  const block = (art, titel, fundstelle, ...inhalt) => wurzel.append(
    el("div.detail-block", {},
      el("h4", {}, art ? ebene(art) : null, art ? " " : null, titel,
        fundstelle ? el("span.quelle", ` ${fundstelle}`) : null),
      ...inhalt));

  block("zustand", "Zustand", "§27, §63", zustand
    ? kv([
      ["Status", zustand.status_label],
      ["Gruppe", klassenMarke(zustand.resource_class, zustand.resource_class_label)],
      ["Beobachtungen", `${zustand.observation_counts.correct} richtig, `
        + `${zustand.observation_counts.incorrect} abweichend`],
      // Eine einheitenlose Kennzahl ohne Skala ist eine Einladung, sie fuer
      // eine Quote zu halten - die §117 gerade verbietet. Sie bleibt stehen,
      // weil die Engine sie liefert, bekommt aber ihren Wertebereich und den
      // Namen der Formel, unter dem sie in der Debug-Ansicht nachzulesen ist.
      ["Konsistenz", zustand.evidence_consistency === null
        || zustand.evidence_consistency === undefined
        ? leer("nicht berechnet")
        : el("span", { title: "Einheitlichkeit der bisherigen Belege, berechnet von "
            + "der Engine nach evidence.consistency_formula (§63). Kein Anteil "
            + "richtiger Aufgaben." },
          String(zustand.evidence_consistency),
          el("span.leer", " von höchstens 1 – Einheitlichkeit der Belege"))],
      ["Profilmarker", zustand.profile_markers.length
        ? chips(zustand.profile_markers, "PROFILE_MARKER") : "keine"],
      ["Variierte Bedingungen", variationen(zustand.variation_dimensions)],
    ])
    : leer("Zu diesem Knoten liegt kein Zustand vor. Das heißt: nicht geprüft – "
      + "es ist keine Aussage über Können."));

  block(null, "Anforderungs- und Niveaubereiche", "§18",
    el("div", {},
      zustand && niveauBereich(zustand.current_floor, zustand.current_ceiling)
        ? el("p", {}, "Beobachteter Bereich: ",
            el("span.wichtig", niveauBereich(zustand.current_floor, zustand.current_ceiling)))
        : leer("noch kein Bereich beobachtet"),
      el("p.leer", { style: "margin:.2rem 0 .3rem" }, "in der Aufgabenbank vorhanden:"),
      chips(niveaus, "INTERNAL_DIFFICULTY"),
      merkzettel(vokabularInfo("INTERNAL_DIFFICULTY")?.beschreibung
        || "D1–D5 sind interne Schwierigkeitsstufen.")));

  block(null, "Basiskompetenzen", "§12, §13",
    knoten.prerequisites.length
      ? el("div.chips", {}, knoten.prerequisites.map((v) => {
        const z = zustandNachId.get(v);
        return el("button.chip", {
          type: "button", title: knotenNachId.get(v)?.name || v,
          onclick: () => window.dispatchEvent(new CustomEvent("navigiere", {
            detail: { ansicht: "karte", knoten: v } })),
        }, `${z ? KLASSE[z.resource_class].zeichen : "·"} ${kurzName(knotenNachId.get(v)?.name || v)}`);
      }))
      : leer("keine Voraussetzung im Graphen hinterlegt"));

  block("evidenz", "Evidenz und Gegen-Evidenz", "§28, §66",
    evidenz.length
      ? el("div", {},
        waage(dafuer.length, dagegen.length, "stützend", "gegenläufig"),
        el("div.chips", { style: "margin-top:.4rem" },
          [...new Set(evidenz.map((e) => e.evidence_type))].map((t) =>
            el("span.chip", {}, `${label("EVIDENCE_TYPE", t)} `
              + `(${evidenz.filter((e) => e.evidence_type === t).length})`))),
        el("p", { style: "margin-top:.5rem" },
          sprung("Einzelne Einträge", { ansicht: "evidenz", knoten: id })))
      : leer("keine Evidenz zu diesem Knoten"));

  block(null, "EIS-/Darstellungsmuster", "§16",
    facettenListe(facetten.REPRESENTATION_MODE, "REPRESENTATION_MODE",
      "keine darstellungsbezogene Facette erfasst"));

  block(null, "Prozesskompetenzen", "§8",
    el("div", {}, chips(prozess, "PROCESS_COMPETENCY",
      "keine Prozesskompetenz an den Aufgaben dieses Knotens hinterlegt"),
      el("p.leer", { style: "margin-top:.3rem" },
        "Eigenschaft der Aufgaben, kein eigener Kompetenzstatus.")));

  block(null, "Zusätzliche Aufgabenanforderungen", "§15",
    el("div", {}, chips(anforderungen, "ADDITIONAL_DEMAND",
      "keine zusätzlichen Anforderungen hinterlegt"),
      el("p.leer", { style: "margin-top:.3rem" },
        "Diese Merkmale beschreiben die Aufgabe, nicht die Schüler:in.")));

  block("fehler", "Fehlermuster", "§30, §59",
    muster.length
      ? el("div", {}, muster.map((m) => el("p", { style: "margin:.2rem 0" },
        el("button.chip", {
          type: "button",
          onclick: () => window.dispatchEvent(new CustomEvent("navigiere", {
            detail: { ansicht: "fehleranalyse", fehler: m.error_code, knoten: id } })),
        }, `${m.reproduced ? "▣" : "▢"} ${m.label} · ${m.observation_count}×`
           + `${m.reproduced ? " reproduziert" : " einmalig"}`))))
      : leer("keine Fehlerbeobachtung zu diesem Knoten"));

  block(null, "Ressourcen und offene Bereiche innerhalb des Knotens", "§117",
    el("div", {},
      el("p", { style: "margin:.1rem 0" }, klassenMarke("RESOURCE", "Ressourcen"), " "),
      ressourcen.length
        ? el("div.chips", {}, ressourcen.map((f) =>
          el("span.chip", { title: f.art }, `${label(f.art, f.value)}`)))
        : leer("keine Facette stabil gezeigt"),
      el("p", { style: "margin:.6rem 0 .1rem" }, klassenMarke("OPEN", "offene Bereiche"), " "),
      offene.length
        ? el("div.chips", {}, offene.map((f) =>
          el("span.chip", { title: f.art }, `${label(f.art, f.value)}`)))
        : leer("keine Facette als schwierig ausgewiesen"),
      alleFacetten.length
        ? null
        : merkzettel("Keine Facetten erfasst. Das ist kein Defizit, sondern "
          + "fehlende Information.")));

  block("hypothese", "Hypothesen", "§64, §115",
    hypothesen.length
      ? el("div", {}, hypothesen.map((h) => el("div", { style: "margin-bottom:.5rem" },
        el("p", { style: "margin:0" }, hypotheseMarke(h.status), " ",
          el("span.mono", h.hypothesis_id)),
        el("p", { style: "margin:.1rem 0" }, h.description),
        h.competing_hypotheses.length
          ? el("p.leer", { style: "margin:0" },
            `konkurriert mit ${h.competing_hypotheses.join(", ")}`)
          : null)),
        el("p", {}, sprung("Hypothesen im Detail", { ansicht: "hypothesen", knoten: id })))
      : leer("keine Hypothese zu diesem Knoten"));

  block("pruefung", "Nächste diagnostische Frage", "§119, §115",
    naechsteFrage(zustand, katalog));

  return wurzel;
}

/* Die fünf Variationsdimensionen aus §72.
 *
 * Die Schlüssel sind die Namen, die §72 selbst benutzt; eine deutsche
 * Entsprechung gibt es im Content nicht, und eine hier zu erfinden wäre eine
 * fachliche Festlegung. Sie bekommen stattdessen den Satz, der beschreibt,
 * worin variiert wurde - das steht in §72 und wird nicht ausgedacht.
 *
 * Gezeigt werden alle fünf, nicht nur die belegten. Welche Bedingung NICHT
 * variiert wurde, ist die eigentlich interessante Angabe: sie sagt, worüber
 * die bisherige Evidenz nichts aussagt.
 */
const VARIATION = {
  numbers: "verschiedene Zahlen",
  representation: "verschiedene Darstellungsformen",
  surface: "verschiedene Oberflächenmerkmale",
  strategy: "verschiedene Strategieangebote",
  context: "mit und ohne Sachkontext",
};

function variationen(dimensionen) {
  if (!dimensionen) return el("span.leer", "nicht erfasst");
  const eintraege = Object.entries(dimensionen);
  if (!eintraege.length) return el("span.leer", "nicht erfasst");
  return el("div.chips", {}, eintraege.map(([schluessel, belegt]) =>
    el("span.chip", { class: belegt ? "chip" : "chip chip-leer", title: schluessel },
      el("span", { "aria-hidden": "true" }, belegt ? "▣ " : "▢ "),
      VARIATION[schluessel] || schluessel,
      el("span.vh", belegt ? " – belegt" : " – nicht variiert"))));
}

function facettenListe(facetten, vokabular, leerText) {
  if (!facetten || !facetten.length) return leer(leerText);
  return el("div", {}, facetten.map((f) => el("p", { style: "margin:.15rem 0" },
    klassenMarke(f.resource_class, label(vokabular, f.value)), " ",
    el("span.leer", `${f.positive_count} richtig, ${f.negative_count} abweichend`
      + ` · ${f.status_label}`))));
}

function naechsteFrage(zustand, katalog) {
  if (!zustand) return leer("Ohne erfassten Zustand liegt keine Auswahl vor.");
  const frage = zustand.next_question;
  const behaelter = el("div");
  if (frage.from_routing) {
    const aufgabe = katalog.tasks.find((t) => t.task_id === frage.from_routing);
    behaelter.append(el("p", {}, el("span.wichtig", "Vom Routing gewählt: "),
      el("span.mono", frage.from_routing), aufgabe ? ` – ${aufgabe.title}` : "",
      el("span.quelle", ` · Regel ${frage.routing_reason || "–"}`)));
  }
  if (frage.from_hypothesis_tests.length) {
    behaelter.append(el("p", { style: "margin-bottom:.2rem" },
      el("span.wichtig", "Geplante Hypothesenprüfungen:")));
    for (const t of frage.from_hypothesis_tests) {
      behaelter.append(el("p", { style: "margin:.15rem 0" },
        el("span.mono", t.task_id), " – widerlegt ", el("span.mono", t.hypothesis_id),
        el("br"), el("span.leer", t.description)));
    }
  }
  if (!behaelter.children.length) {
    behaelter.append(leer("Derzeit ist für diesen Knoten keine Aufgabe vorgemerkt."));
  }
  return behaelter;
}

/* ------------------------------------------------------------------ Ansicht */

export default {
  zahl: (z) => ({ wert: z.profil.competency_states.length, ebene: "zustand",
                  was: "erfasste Kompetenzzustände" }),

  render(zustand) {
    const { katalog, profil, parameter } = zustand;
    const knotenNachId = nachId(katalog.competency_nodes, "competency_id");
    const zustandNachId = nachId(profil.competency_states, "competency_id");

    const gewaehlt = parameter.get("knoten")
      || profil.competency_states[0]?.competency_id
      || null;
    const wurzeln = katalog.competency_nodes.filter((k) => !k.parent_id);
    const nurMitZustand = parameter.get("nurzustand") === "1";

    const wurzelVon = (id) => {
      let aktuell = knotenNachId.get(id);
      const gesehen = new Set();
      while (aktuell && aktuell.parent_id && !gesehen.has(aktuell.competency_id)) {
        gesehen.add(aktuell.competency_id);
        aktuell = knotenNachId.get(aktuell.parent_id);
      }
      return aktuell ? aktuell.competency_id : id;
    };

    // Ohne ausdrücklich gesetzten Filter richtet sich die Leitidee nach dem
    // ausgewählten Knoten. Sonst beschriebe die Detailspalte beim Einstieg und
    // nach jedem Sprung aus einer anderen Ansicht eine Kompetenz, die im
    // Graphen daneben nicht vorkommt – eine falsche Verortung, kein Layoutfehler.
    const gewaehlteWurzel = parameter.get("leitidee")
      || (gewaehlt ? wurzelVon(gewaehlt) : "L1_NUMBER_OPERATION");

    let sichtbar = katalog.competency_nodes.filter(
      (k) => gewaehlteWurzel === "ALLE" || wurzelVon(k.competency_id) === gewaehlteWurzel);
    if (nurMitZustand) sichtbar = sichtbar.filter((k) => zustandNachId.has(k.competency_id));
    const sichtbareIds = new Set(sichtbar.map((k) => k.competency_id));
    const kanten = katalog.relations.filter(
      (r) => sichtbareIds.has(r.source_competency) && sichtbareIds.has(r.target_competency));

    const setze = (schluessel, wert) => {
      const p = new URLSearchParams(parameter);
      if (wert === null) p.delete(schluessel); else p.set(schluessel, wert);
      location.hash = `#karte?${p}`;
    };

    const filter = el("div.filterleiste", {},
      el("label", {}, "Leitidee",
        el("select", { "data-fokus": "leitidee", onchange: (e) => setze("leitidee", e.target.value) },
          el("option", { value: "ALLE", selected: gewaehlteWurzel === "ALLE" }, "alle"),
          wurzeln.map((w) => el("option",
            { value: w.competency_id, selected: w.competency_id === gewaehlteWurzel }, w.name)),
          // Dieselbe Vorsorge wie `optionen()` in dom.js: ein Wert aus dem
          // Adressfragment, den der Katalog nicht kennt, bekommt eine eigene
          // Option. Sonst waehlte der Browser "alle", waehrend der Graph leer
          // bliebe.
          gewaehlteWurzel !== "ALLE" && !wurzeln.some((w) => w.competency_id === gewaehlteWurzel)
            ? el("option", { value: gewaehlteWurzel, selected: true },
                `${gewaehlteWurzel} – im Katalog nicht vorhanden`)
            : null)),
      el("label", {},
        el("input", {
          type: "checkbox", checked: nurMitZustand, "data-fokus": "nurzustand",
          onchange: (e) => setze("nurzustand", e.target.checked ? "1" : null),
        }), "nur Knoten mit erfasstem Zustand"),
      el("span.leer", `${sichtbar.length} Knoten, ${kanten.length} Relationen`));

    const graph = sichtbar.length
      ? graphZeichnen(sichtbar, kanten, zustandNachId, gewaehlt,
          (id) => setze("knoten", id))
      : leer("Kein Knoten in dieser Auswahl.");

    const flaeche = el("div.karte-flaeche", {}, graph);

    const wurzel = el("div", {},
      abschnitt("Kompetenzkarte", "§7, §9, §12",
        el("p.leer", "Spalten zeigen die Länge der Voraussetzungskette im Graphen. "
          + "Das ist eine Eigenschaft des Fachaufbaus, keine Aussage über die Schüler:in."),
        filter,
        el("div.zweispaltig", {},
          el("div", {}, flaeche, legende(kanten, katalog.relations)),
          gewaehlt
            ? detail(gewaehlt, { katalog, profil, knotenNachId, zustandNachId,
                                 imGraphen: sichtbareIds.has(gewaehlt) })
            : el("div.detail", {}, leer("Einen Knoten anklicken.")))));

    // Den gewählten Knoten sichtbar machen, ohne die Seite zu verschieben.
    queueMicrotask(() => {
      const treffer = flaeche.querySelector('[data-gewaehlt="ja"]');
      if (!treffer) return;
      const rahmen = flaeche.getBoundingClientRect();
      const ziel = treffer.getBoundingClientRect();
      flaeche.scrollLeft += ziel.left - rahmen.left - rahmen.width / 2 + BREITE / 2;
      flaeche.scrollTop += ziel.top - rahmen.top - rahmen.height / 2 + HOEHE / 2;
    });

    return wurzel;
  },
};

/* Die Legende beschreibt den Graphen, der danebensteht - nicht den Katalog.
 *
 * Vorher zaehlte sie sechs Kantenarten fest auf, darunter CROSS_DOMAIN_RELATION.
 * In der Voreinstellung ist davon keine einzige gezeichnet: alle zehn verbinden
 * L1-Knoten mit den Wurzeln von L2 bis L5, und der Graph behaelt nur Kanten,
 * deren beide Enden sichtbar sind. Eine Legende, die Striche erklaert, die es
 * nicht gibt, erklaert nichts - sie behauptet Struktur.
 *
 * Gezeichnete Arten stehen mit ihrem Strich, vorhandene aber ungezeichnete
 * werden benannt. Auch das folgt der Regel, fehlende Information als fehlend
 * auszuweisen, statt sie zu verschweigen.
 */
function legende(kanten, alleRelationen) {
  const strich = (klasse) => {
    const s = svgEl("svg", { width: 34, height: 10, "aria-hidden": "true" });
    s.append(svgEl("path", { d: "M 1 5 L 33 5", class: `kante kante-${klasse}` }));
    return s;
  };
  const gezeichnet = [...new Set(kanten.map((k) => k.relation_type))].sort();
  const ausgeblendet = [...new Set(alleRelationen.map((r) => r.relation_type))]
    .filter((t) => !gezeichnet.includes(t)).sort();
  return el("div.legende", {},
    el("span", {}, "Knoten: "),
    Object.entries(KLASSE).map(([schluessel, k]) =>
      el("span", {}, klassenMarke(schluessel, k.wort))),
    el("span", {}, el("span.marke.marke-ungeprueft", {},
      el("span.marke-zeichen", "·"), "ohne Zustand")),
    el("span", { style: "flex-basis:100%" },
      gezeichnet.length ? "Gezeichnete Kanten: " : "Keine Kante in dieser Auswahl."),
    gezeichnet.map((t) => el("span", {}, strich(t), " ", label("RELATION_TYPE", t))),
    ausgeblendet.length
      ? el("span.leer", { style: "flex-basis:100%" },
          "In dieser Auswahl nicht gezeichnet, weil ein Ende außerhalb liegt: "
          + ausgeblendet.map((t) => label("RELATION_TYPE", t)).join(", ") + ".")
      : null);
}
