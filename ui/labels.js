/* Beschriftung.
 *
 * Alle deutschen Bezeichnungen kommen aus dem Vokabular des Backends. Diese
 * Datei enthält deshalb keine Übersetzungstabelle für Fachbegriffe – sie
 * enthält nur die Zuordnung von Zeichen zu Zuständen, damit Farbe nie die
 * einzige Information ist.
 *
 * Das Zeichen ist bewusst redundant zur Farbe und zum Text. Drei Codierungen
 * für dieselbe Angabe; zwei davon funktionieren in Graustufen.
 */

let VOKABULAR = {};

export function vokabularSetzen(v) { VOKABULAR = v || {}; }

/** Deutsche Beschriftung eines Begriffs. Fällt auf den Rohwert zurück –
 *  sichtbar als Großbuchstabenkennung, nicht stillschweigend erfunden. */
export function label(vokabular, term) {
  if (term === null || term === undefined || term === "") return "–";
  return VOKABULAR[vokabular]?.terms?.[term]?.label ?? term;
}

export function anmerkung(vokabular, term) {
  return VOKABULAR[vokabular]?.terms?.[term]?.notes ?? null;
}

/** Beschreibung eines ganzen Vokabulars, mit Fundstelle. Trägt an mehreren
 *  Stellen die entscheidende Einschränkung – etwa dass D1–D5 nicht die
 *  IQB-Kompetenzstufen sind. */
export function vokabularInfo(vokabular) {
  const v = VOKABULAR[vokabular];
  if (!v) return null;
  return { beschreibung: v.description, fundstelle: v.spec_section, art: v.kind };
}


/** Überschrift für eine Merkmalsart: der erste Satz ihrer Beschreibung aus dem
 *  Vokabelregister. Damit steht auch über einer Merkmalsliste ein deutscher
 *  Begriff, ohne dass diese Datei einen erfindet. */
export function vokabularTitel(vokabular) {
  const beschreibung = VOKABULAR[vokabular]?.description;
  if (!beschreibung) return vokabular;
  const satz = beschreibung.split(/(?<=\.)\s/)[0];
  return satz.replace(/\.$/, "");
}

/* ------------------------------------------------------------ Zeichen */

/** Ressourcenklasse: Ressource / offener Bereich / noch nicht geprüft.
 *  Die Zuordnung selbst trifft das Backend (api.py `resource_class`). */
export const KLASSE = {
  RESOURCE:  { zeichen: "■", wort: "Ressource",     stil: "ressource" },
  OPEN:      { zeichen: "▲", wort: "offen",         stil: "offen" },
  UNCHECKED: { zeichen: "○", wort: "nicht geprüft", stil: "ungeprueft" },
};

/** Hypothesenstatus. Die Bedeutung steht im Vokabular HYPOTHESIS_STATUS. */
export const HYPOTHESE_ZEICHEN = {
  OPEN: "◇", SUPPORTED: "◆", WEAKENED: "◨", REJECTED: "✕", CLOSED: "●",
};

/** Evidenzrichtung. */
export const RICHTUNG_ZEICHEN = { POSITIVE: "+", NEGATIVE: "−", NEUTRAL: "·" };

/** Ergebnis einer Beobachtung. Kein Werturteil, eine Beschreibung. */
export const ERGEBNIS = {
  richtig: { zeichen: "✓", wort: "richtig" },
  falsch:  { zeichen: "✗", wort: "abweichend" },
};

/** Die sechs Ebenen der Grundregel. */
export const EBENE = {
  beobachtung: ["B", "Beobachtung"],
  fehler: ["F", "Fehler"],
  evidenz: ["E", "Evidenz"],
  zustand: ["K", "Kompetenzzustand"],
  hypothese: ["H", "Hypothese"],
  pruefung: ["P", "Hypothesenprüfung"],
};

/** Beobachteter Niveaubereich als Text. Der Bereich kann einseitig offen sein –
 *  etwa wenn nur eine Obergrenze beobachtet wurde. Dann steht nur diese da und
 *  nicht ein Gedankenstrich, der wie eine fehlende Angabe aussieht. */
export function niveauBereich(unten, oben) {
  const u = unten ? label("INTERNAL_DIFFICULTY", unten) : null;
  const o = oben ? label("INTERNAL_DIFFICULTY", oben) : null;
  if (u && o) return u === o ? u : `${u} bis ${o}`;
  if (o) return `bis ${o}`;
  if (u) return `ab ${u}`;
  return null;
}

/** Kurzname einer Kompetenz ohne den vorangestellten Code.
 *  "ZO06.5 Stellenwertzerlegung" -> "Stellenwertzerlegung" */
export function kurzName(name) {
  if (!name) return "";
  return name.replace(/^(?:[A-Z]{1,3}\d*(?:\.\d+)?|L\d)\s+/, "");
}
