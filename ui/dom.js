/* Bausteine für die Darstellung.
 *
 * Kleine, dumme Hilfsfunktionen. Keine davon kennt die Fachlogik; sie bauen
 * Elemente. Durchgängig über textContent statt innerHTML – Aufgabentexte und
 * Schülerantworten sind Fremdtext und gehören nicht als Markup interpretiert.
 */

import { KLASSE, HYPOTHESE_ZEICHEN, RICHTUNG_ZEICHEN, ERGEBNIS, EBENE, label }
  from "./labels.js";

/** el("div.karte", {id: "x"}, kind1, kind2, "Text") */
export function el(auswahl, attribute, ...kinder) {
  const [tag, ...klassen] = String(auswahl).split(".");
  const knoten = document.createElement(tag || "div");
  if (klassen.length) knoten.className = klassen.join(" ");
  if (attribute && attribute.nodeType === undefined && typeof attribute !== "string") {
    for (const [name, wert] of Object.entries(attribute)) {
      if (wert === null || wert === undefined || wert === false) continue;
      if (name === "onclick") knoten.addEventListener("click", wert);
      else if (name === "oninput") knoten.addEventListener("input", wert);
      else if (name === "onchange") knoten.addEventListener("change", wert);
      else if (name === "text") knoten.textContent = wert;
      // Stil über das CSSOM, nicht über das style-Attribut: die Seite läuft
      // unter einer Content-Security-Policy ohne 'unsafe-inline'. Das ist die
      // vorgesehene Schnittstelle dafür, kein Umweg um die Richtlinie.
      else if (name === "style") stilSetzen(knoten, wert);
      else knoten.setAttribute(name, wert === true ? "" : String(wert));
    }
  } else if (attribute !== undefined && attribute !== null) {
    kinder.unshift(attribute);
  }
  anhaengen(knoten, kinder);
  return knoten;
}

function stilSetzen(knoten, regeln) {
  for (const regel of String(regeln).split(";")) {
    const trenner = regel.indexOf(":");
    if (trenner < 0) continue;
    knoten.style.setProperty(regel.slice(0, trenner).trim(), regel.slice(trenner + 1).trim());
  }
}

function anhaengen(knoten, kinder) {
  for (const kind of kinder.flat(4)) {
    if (kind === null || kind === undefined || kind === false) continue;
    knoten.append(kind.nodeType ? kind : document.createTextNode(String(kind)));
  }
}

export function leeren(knoten) {
  while (knoten.firstChild) knoten.removeChild(knoten.firstChild);
  return knoten;
}

/* ------------------------------------------------------------- Textbausteine */

export const leer = (text = "keine Angaben") => el("p.leer", text);

export function abschnitt(titel, fundstelle, ...inhalt) {
  return el("section.abschnitt", {},
    el("h2", {}, titel, fundstelle ? el("span.quelle", ` · ${fundstelle}`) : null),
    ...inhalt);
}

/** Ein hervorgehobener Hinweis, der eine Aussage begrenzt. Wird durchgängig
 *  dort eingesetzt, wo eine Zahl sonst mehr verspricht, als sie hält. */
export const merkzettel = (...inhalt) => el("p.merkzettel", {}, ...inhalt);

export function kv(paare) {
  const liste = el("dl.kv");
  for (const [begriff, wert] of paare) {
    if (wert === null || wert === undefined) continue;
    liste.append(el("dt", begriff), el("dd", {}, wert));
  }
  return liste;
}

export function chips(werte, vokabular, leerText = "keine") {
  const behaelter = el("div.chips");
  const liste = werte || [];
  if (!liste.length) { behaelter.append(el("span.chip.chip-leer", leerText)); return behaelter; }
  for (const wert of liste) {
    const text = vokabular ? label(vokabular, wert) : String(wert);
    behaelter.append(el("span.chip", { title: vokabular ? wert : null }, text));
  }
  return behaelter;
}

/** Tabelle aus Kopfzeilen und Zeilenlieferant. */
export function tabelle(kopf, zeilen, zellen) {
  if (!zeilen.length) return leer("keine Einträge");
  const t = el("table");
  t.append(el("thead", {}, el("tr", {}, kopf.map((h) => el("th", h)))));
  const koerper = el("tbody");
  for (const zeile of zeilen) {
    koerper.append(el("tr", {}, zellen(zeile).map((z) => el("td", {}, z))));
  }
  t.append(koerper);
  return el("div.tabelle-rahmen", {}, t);
}

/* ------------------------------------------------------------------ Marken */

/** Ressourcenklasse als Marke: Zeichen, Text und Farbe – in dieser Reihenfolge
 *  der Wichtigkeit. Die Farbe ist die dritte Codierung, nie die erste. */
export function klassenMarke(klasse, beschriftung) {
  const k = KLASSE[klasse] || KLASSE.UNCHECKED;
  return el(`span.marke.marke-${k.stil}`, { title: klasse },
    el("span.marke-zeichen", { "aria-hidden": "true" }, k.zeichen),
    beschriftung || k.wort);
}

/** Kompetenzstatus mit seiner Klasse. `zustand` ist ein CompetencyState. */
export function statusMarke(zustand) {
  if (!zustand) return klassenMarke("UNCHECKED", "kein Zustand erfasst");
  return klassenMarke(zustand.resource_class, zustand.status_label || zustand.status);
}

export function hypotheseMarke(status) {
  // Der Stil kam vorher aus einem Ternaer, dessen beide letzten Zweige denselben
  // Wert lieferten - die Unterscheidung REJECTED/CLOSED gegen den Rest war
  // wirkungslos. Zu unterscheiden ist hier ohnehin nichts: eine gestuetzte
  // Hypothese ist keine "offenere" als eine verworfene, sie ist eine andere.
  // Welche, sagen das Zeichen und das ausgeschriebene Wort - beide aus dem
  // Vokabular, beide durch Tests gedeckt.
  return el("span.marke.marke-ungeprueft", { title: status },
    el("span.marke-zeichen", { "aria-hidden": "true" }, HYPOTHESE_ZEICHEN[status] || "◇"),
    label("HYPOTHESIS_STATUS", status));
}

export function richtungsMarke(richtung) {
  const stil = richtung === "POSITIVE" ? "ressource" : richtung === "NEGATIVE" ? "offen" : "ungeprueft";
  return el(`span.marke.marke-${stil}`, { title: richtung },
    el("span.marke-zeichen", { "aria-hidden": "true" }, RICHTUNG_ZEICHEN[richtung] || "·"),
    label("EVIDENCE_DIRECTION", richtung));
}

export function ergebnisMarke(istRichtig) {
  const e = istRichtig ? ERGEBNIS.richtig : ERGEBNIS.falsch;
  const stil = istRichtig ? "ressource" : "offen";
  return el(`span.marke.marke-${stil}`, {},
    el("span.marke-zeichen", { "aria-hidden": "true" }, e.zeichen), e.wort);
}

/** Ebenenkennzeichnung nach der Grundregel. */
export function ebene(art) {
  const [zeichen, wort] = EBENE[art];
  return el(`span.ebene.ebene-${zeichen.toLowerCase()}`, { title: wort }, zeichen);
}

/** Überschrift mit Ebenenkennzeichnung davor. */
export const ebenenTitel = (art, text, fundstelle) =>
  el("h2", {}, ebene(art), " ", text,
     fundstelle ? el("span.quelle", ` · ${fundstelle}`) : null);

/* ------------------------------------------------------------------ Zahlen */

/** Gegenüberstellung dafür/dagegen. Bewusst als Anzahl, nicht als Anteil:
 *  ein Prozentwert würde eine Messgenauigkeit behaupten, die nicht besteht. */
export function waage(dafuer, dagegen, beschriftungDafuer = "dafür", beschriftungDagegen = "dagegen") {
  const summe = dafuer + dagegen;
  const spur = el("span.balken-spur", { "aria-hidden": "true" });
  if (summe > 0) {
    if (dafuer) spur.append(el("span.balken-dafuer", { style: `width:${(dafuer / summe) * 100}%` }));
    if (dagegen) spur.append(el("span.balken-dagegen", { style: `width:${(dagegen / summe) * 100}%` }));
  } else {
    spur.append(el("span", { style: "width:100%" }));
  }
  return el("span.balken", {}, spur,
    el("span", `${dafuer} ${beschriftungDafuer}, ${dagegen} ${beschriftungDagegen}`));
}

export function zeitpunkt(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
}

/** Antworten sind Fremdtext beliebiger Form. Kompakt, aber unverändert. */
export function antwortText(wert) {
  if (wert === null || wert === undefined) return "–";
  if (typeof wert === "object") return JSON.stringify(wert);
  return String(wert);
}

/* Die Optionen eines Filterfeldes.
 *
 * Der Sonderfall, um den es hier geht: das Adressfragment traegt einen Wert,
 * den die Liste dieses Kindes nicht enthaelt - ein Lesezeichen aus einem
 * anderen Profil, ein geteilter Verweis. Ohne passende Option waehlt der
 * Browser die erste, also "alle". Das Bedienelement behauptet dann, es sei
 * nicht gefiltert, waehrend die Ansicht darunter leer bleibt: ein Kind mit
 * sechs Fehlerbeobachtungen sieht aus wie ein Kind ohne Fehler.
 *
 * Stattdessen bekommt der fremde Wert eine eigene, benannte Option. Fehlende
 * Information wird als fehlende Information ausgewiesen - dieselbe Regel, die
 * die Ansichten sonst ueberall befolgen.
 */
export function optionen(aktiv, werte, text, allesText = "alle") {
  const vorhanden = werte.includes(aktiv);
  return [
    el("option", { value: "", selected: !aktiv }, allesText),
    ...werte.map((w) => el("option", { value: w, selected: w === aktiv }, text(w))),
    aktiv && !vorhanden
      ? el("option", { value: aktiv, selected: true },
          `${text(aktiv)} – für dieses Kind nicht vorhanden`)
      : null,
  ];
}

/** Knopf, der eine andere Ansicht öffnet. */
export function sprung(text, ziel, titel) {
  return el("button.chip", {
    type: "button", title: titel || "",
    onclick: () => window.dispatchEvent(new CustomEvent("navigiere", { detail: ziel })),
  }, text);
}
