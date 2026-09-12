/* Gerüst und Wegführung.
 *
 * Lädt die Daten über die Datenzugriffsschicht, hält die aktuelle Auswahl im
 * Adressfragment und übergibt beides an die jeweilige Ansicht. Mehr tut diese
 * Datei nicht – insbesondere rechnet sie nichts aus.
 */

import * as daten from "./data.js";
import { vokabularSetzen } from "./labels.js";
import { el, leeren, ebene } from "./dom.js";

import uebersicht from "./views/uebersicht.js";
import karte from "./views/karte.js";
import fehleranalyse from "./views/fehleranalyse.js";
import darstellung from "./views/darstellung.js";
import hypothesen from "./views/hypothesen.js";
import evidenz from "./views/evidenz.js";
import verlauf from "./views/verlauf.js";
import debug from "./views/debug.js";

/** Die Hauptnavigation. Die Reihenfolge folgt dem Implementierungsauftrag. */
const ANSICHTEN = [
  ["uebersicht",    "Übersicht",        uebersicht],
  ["karte",         "Kompetenzkarte",   karte],
  ["fehleranalyse", "Fehleranalyse",    fehleranalyse],
  ["darstellung",   "Darstellung / EIS", darstellung],
  ["hypothesen",    "Hypothesen",       hypothesen],
  ["evidenz",       "Evidenz",          evidenz],
  ["verlauf",       "Aufgabenverlauf",  verlauf],
  ["debug",         "Debug",            debug],
];

const zustand = {
  schuelerId: null,
  katalog: null,
  profil: null,
  ansicht: "uebersicht",
  parameter: new URLSearchParams(),
};

const inhalt = document.getElementById("inhalt");
const navigation = document.getElementById("navigation");
const auswahl = document.getElementById("schueler");

/* ------------------------------------------------------------ Adressfragment */

function fragmentLesen() {
  const roh = location.hash.replace(/^#\/?/, "");
  const [ansicht, abfrage = ""] = roh.split("?");
  return {
    ansicht: ANSICHTEN.some(([k]) => k === ansicht) ? ansicht : "uebersicht",
    parameter: new URLSearchParams(abfrage),
  };
}

function fragmentSchreiben(ansicht, parameter) {
  const abfrage = parameter && [...parameter.keys()].length ? `?${parameter}` : "";
  const neu = `#${ansicht}${abfrage}`;
  if (location.hash !== neu) location.hash = neu;
}

/** Wegführung aus einer Ansicht heraus: `sprung()` in dom.js löst dies aus. */
window.addEventListener("navigiere", (ereignis) => {
  const { ansicht, ...rest } = ereignis.detail || {};
  const parameter = new URLSearchParams();
  for (const [k, v] of Object.entries(rest)) if (v != null) parameter.set(k, v);
  fragmentSchreiben(ansicht || zustand.ansicht, parameter);
});

window.addEventListener("hashchange", () => {
  Object.assign(zustand, fragmentLesen());
  zeichnen();
});

/* ------------------------------------------------------------------ Aufbau */

/* Die Zahl neben einem Navigationspunkt.
 *
 * Sie zählt in jeder Ansicht etwas anderes – Beobachtungen, Fehler, Evidenz,
 * Kompetenzzustände, Hypothesen, Entscheidungen. Als nackte Ziffer stünden in
 * der einzigen immer sichtbaren Leiste sieben Zahlen aus fünf Ebenen
 * nebeneinander, und der Vorlesename der Schaltfläche lautete "Fehleranalyse6".
 * Die Grundregel gilt aber jederzeit, nicht nur innerhalb einer Ansicht.
 * Deshalb trägt jede Zahl das Kürzel ihrer Ebene und einen ausgeschriebenen
 * Namen für Vorlese- und Zeigegeräte. */
function navigationZahl(modul) {
  const angabe = zustand.profil && modul.zahl ? modul.zahl(zustand) : null;
  if (angabe === null || angabe === undefined) return null;
  const { wert, ebene: art, was } = angabe;
  if (wert === null || wert === undefined) return null;
  return {
    marke: el("span.nav-zahl", { title: `${wert} ${was}` },
      art ? ebene(art) : null, String(wert)),
    name: `${wert} ${was}`,
  };
}

function navigationZeichnen() {
  leeren(navigation);
  for (const [schluessel, titel, modul] of ANSICHTEN) {
    const zahl = navigationZahl(modul);
    navigation.append(el("button", {
      type: "button",
      "aria-current": schluessel === zustand.ansicht ? "page" : null,
      "aria-label": zahl ? `${titel}: ${zahl.name}` : null,
      onclick: () => fragmentSchreiben(schluessel, new URLSearchParams()),
    }, titel, zahl ? zahl.marke : null));
  }
}

/* Der fachliche Geltungsbereich im Seitenkopf.
 *
 * Er stand fest verdrahtet im Gerüst ("Leitidee 1 · Zahl und Operation") –
 * derselbe Katalogwert, den die Oberfläche sonst nirgends selbst behauptet.
 * Enthielte der Katalog eines Tages inhaltliche Knoten in einer zweiten
 * Leitidee, versprächen Kopfzeile und Kompetenzkarte Verschiedenes.
 * Aufgeführt werden die Wurzeln, unter denen tatsächlich Knoten hängen; die
 * übrigen sind nach §7 im MVP leer und stehen im Graphen als einzelner Punkt.
 */
function bereichSchreiben(katalog) {
  const ziel = document.getElementById("kopf-bereich");
  if (!ziel) return;
  const mitKindern = new Set(katalog.competency_nodes
    .filter((k) => k.parent_id).map((k) => k.parent_id));
  const namen = katalog.competency_nodes
    .filter((k) => !k.parent_id && mitKindern.has(k.competency_id))
    .map((k) => k.name);
  ziel.textContent = namen.length ? namen.join(" · ") : "Katalog ohne Unterknoten";
}

/* Der Fokus überlebt den Neuaufbau.
 *
 * Jede Filteränderung schreibt ins Adressfragment und baut #inhalt neu auf –
 * das Bedienelement, das gerade benutzt wurde, existiert danach nicht mehr.
 * Ohne Wiederherstellung beginnt die Tastaturbedienung nach jedem einzelnen
 * Filterschritt wieder am Seitenanfang, und "vollständig navigierbar" wäre
 * nur mit der Maus wahr. Elemente melden sich dafür mit data-fokus an. */
function fokusMerken() {
  const aktiv = document.activeElement;
  return aktiv && inhalt.contains(aktiv) ? aktiv.dataset?.fokus || null : null;
}

function fokusSetzen(schluessel) {
  if (!schluessel) return;
  const ziel = inhalt.querySelector(`[data-fokus="${CSS.escape(schluessel)}"]`);
  ziel?.focus({ preventScroll: true });
}

function zeichnen() {
  navigationZeichnen();
  const fokus = fokusMerken();
  leeren(inhalt);
  const eintrag = ANSICHTEN.find(([k]) => k === zustand.ansicht);
  if (!eintrag || !zustand.profil) return;
  try {
    inhalt.append(eintrag[2].render(zustand));
  } catch (fehler) {
    inhalt.append(el("div.fehlermeldung", {},
      el("h2", "Diese Ansicht konnte nicht dargestellt werden."),
      el("p", String(fehler && fehler.message ? fehler.message : fehler)),
      el("p.leer", "Die zugrundeliegenden Daten sind davon nicht betroffen.")));
    console.error(fehler);
  }
  fokusSetzen(fokus);
  if (!fokus) inhalt.scrollTo?.(0, 0);
}

async function schuelerLaden(id) {
  const wechsel = zustand.schuelerId !== null && zustand.schuelerId !== id;
  zustand.schuelerId = id;
  leeren(inhalt).append(el("p.laedt", `Profil ${id} wird geladen …`));
  try {
    zustand.profil = await daten.profil(id);
  } catch (fehler) {
    leeren(inhalt).append(el("div.fehlermeldung", {},
      el("h2", "Profil nicht geladen"), el("p", String(fehler.message || fehler))));
    return;
  }
  try { localStorage.setItem("mathkomp.schueler", id); } catch { /* private Fenster */ }

  // Die Filter des vorigen Kindes werden verworfen. Sie tragen Kennungen –
  // einen Fehlercode, einen Knoten, eine Hypothese –, die zum nächsten Kind
  // nicht gehören. Blieben sie stehen, zeigte die Fehleranalyse für ein Kind
  // mit sechs Fehlerbeobachtungen eine leere Liste, während die Auswahlfelder
  // "alle" behaupten. Eine Oberfläche, die fehlende Information benennt, darf
  // vorhandene nicht verschweigen.
  if (wechsel) {
    zustand.parameter = new URLSearchParams();
    fragmentSchreiben(zustand.ansicht, zustand.parameter);
  }
  zeichnen();
}

async function start() {
  try {
    const [kat, liste] = await Promise.all([daten.katalog(), daten.schuelerListe()]);
    zustand.katalog = kat;
    vokabularSetzen(kat.vocabulary);
    bereichSchreiben(kat);

    if (!liste.length) {
      leeren(inhalt).append(el("div.fehlermeldung", {},
        el("h2", "Keine Schüler:innen in der Datenbank"),
        el("p", "Ein Durchlauf entsteht mit "),
        el("p.mono", "mathkomp session KIND-01 --grade 3"),
        el("p", "oder, für die sechs Testfälle aus §98–§103: "),
        el("p.mono", "mathkomp simulate")));
      return;
    }

    let gemerkt = null;
    try { gemerkt = localStorage.getItem("mathkomp.schueler"); } catch { /* egal */ }
    const start = liste.some((s) => s.student_id === gemerkt) ? gemerkt : liste[0].student_id;

    leeren(auswahl);
    for (const s of liste) {
      auswahl.append(el("option", { value: s.student_id, selected: s.student_id === start },
        `${s.student_id} (${s.attempt_count} ${s.attempt_count === 1 ? "Aufgabe" : "Aufgaben"})`));
    }
    auswahl.addEventListener("change", () => schuelerLaden(auswahl.value));

    Object.assign(zustand, fragmentLesen());
    await schuelerLaden(start);
  } catch (fehler) {
    leeren(inhalt).append(el("div.fehlermeldung", {},
      el("h2", "Das Backend antwortet nicht"),
      el("p", String(fehler.message || fehler)),
      el("p", "Die Oberfläche erfindet keine Ersatzdaten. Server starten mit:"),
      el("p.mono", "mathkomp ui")));
  }
}

const schalter = document.getElementById("begriffe-schalter");
const liste = document.getElementById("begriffe-liste");
schalter.addEventListener("click", () => {
  const offen = schalter.getAttribute("aria-expanded") === "true";
  schalter.setAttribute("aria-expanded", String(!offen));
  liste.hidden = offen;
  schalter.textContent = offen
    ? "Sechs unterschiedene Ebenen – Erläuterung einblenden"
    : "Sechs unterschiedene Ebenen – Erläuterung ausblenden";
});

start();
