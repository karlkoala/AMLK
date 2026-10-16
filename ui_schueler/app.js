/* Ablauf der Schueler:innensitzung.
 *
 * §105 gibt die vier Schritte vor: Aufgabe, Interaktion, Antwort,
 * Rueckmeldung. Diese Datei haelt sich daran und zeigt sonst nichts.
 *
 * Was der Server mitliefert und hier absichtlich liegen bleibt, ist das Feld
 * "warum" - die Begruendung der Auswahl nach §88/§89. Einem Kind "Fehler
 * wiederholen" anzuzeigen, waere eine Zuschreibung (§32) und eine Diagnose
 * als Rueckmeldung (§59). Beantwortbar muss die Frage sein, nicht an dieser
 * Stelle beantwortet: die Lehrkraftansicht zeigt sie. Im Simulationsmodus
 * sitzt kein Kind vor dem Bildschirm, deshalb steht sie dort.
 */

import { baue, h } from "./eingabe.js";

const Z = {
  katalog: null,
  student_id: null,
  klassenstufe: null,
  spec: null,
  antwortform: null,
  widget: null,
  simulation: false,
  lauf: null,             // {gesamt, gemacht, richtig, art} waehrend der Automatik
};

const buehne = document.getElementById("buehne");
const wer = document.getElementById("wer");
const fussnote = document.getElementById("fussnote");

const KENNUNG = /^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$/;   // §86, wie im Server

// ------------------------------------------------------------------- Netz

async function ruf(pfad, koerper) {
  const antwort = await fetch(pfad, {
    method: koerper === undefined ? "GET" : "POST",
    headers: koerper === undefined ? {} : { "Content-Type": "application/json" },
    body: koerper === undefined ? undefined : JSON.stringify(koerper),
  });
  let daten = null;
  try { daten = await antwort.json(); } catch { daten = null; }
  if (!antwort.ok) {
    throw new Error((daten && daten.error) || `Serverfehler ${antwort.status}`);
  }
  return daten;
}

function zeige(...knoten) {
  buehne.replaceChildren(...knoten.filter(Boolean));
}

function fehlerkasten(meldung) {
  return h("p", { class: "fehler", text: meldung });
}

// -------------------------------------------------------------- Startseite

async function start() {
  try {
    Z.katalog = await ruf("/api/katalog");
  } catch (e) {
    zeige(h("div", { class: "karte" }, [fehlerkasten(e.message)]));
    return;
  }
  fussnote.textContent = Z.katalog.hinweis;
  startseite();
}

function startseite() {
  let stufe = Z.klassenstufe;
  wer.hidden = true;

  const kennung = h("input", { type: "text", id: "kennung", maxlength: "32",
    autocomplete: "off", spellcheck: "false", placeholder: "z. B. kind-07" });
  if (Z.student_id) kennung.value = Z.student_id;

  const bekannt = Z.katalog.schueler || [];
  const schnellwahl = h("div", { class: "knopfreihe" },
    bekannt.slice(0, 8).map((s) => {
      const k = h("button", { type: "button", class: "klein",
        text: `${s.student_id} (${s.bearbeitet})` });
      k.addEventListener("click", () => {
        kennung.value = s.student_id;
        if (s.grade_reference) waehleStufe(s.grade_reference);
      });
      return k;
    }));

  const stufenfeld = h("div", { class: "stufen" });
  const hinweisStufe = h("small", { text: "Wähle, bis wohin gerechnet wird." });
  const knoepfe = [];
  for (let i = 1; i <= 10; i++) {
    const k = h("button", { type: "button", class: "stufe", text: String(i),
      "aria-pressed": "false", "aria-label": `Klasse ${i}` });
    k.addEventListener("click", () => waehleStufe(i));
    knoepfe.push(k);
    stufenfeld.appendChild(k);
  }
  function waehleStufe(i) {
    stufe = i;
    knoepfe.forEach((k, j) => k.setAttribute("aria-pressed", String(j + 1 === i)));
    const je = Z.katalog.aufgaben_je_stufe || [];
    const offen = je.filter((r) => r.stufe <= i).reduce((s, r) => s + r.aufgaben, 0);
    // §94: die Klassenstufe ist Referenz, keine Schranke. Nach unten bleibt
    // alles erreichbar, nach oben wird nichts von sich aus vorgelegt.
    hinweisStufe.textContent =
      `${offen} Aufgaben bis Klasse ${i}. Leichtere bleiben erreichbar.`;
  }
  if (stufe) waehleStufe(stufe);

  const simulation = h("input", { type: "checkbox", id: "sim" });
  simulation.checked = Z.simulation;

  const los = h("button", { type: "button", class: "haupt", text: "Losgehen" });
  const meldeplatz = h("div");

  const kasten = h("div", { class: "karte" }, [
    h("h2", { text: "Wer rechnet?" }),
    h("p", { class: "leise",
      text: "Du brauchst nur ein Kürzel – keinen echten Namen." }),
    h("div", { class: "feldgruppe" }, [
      h("label", { class: "feld", for: "kennung" }, [
        h("span", { text: "Kürzel" }),
        kennung,
        h("small", { text: "2 bis 32 Zeichen: Buchstaben, Ziffern, - und _" }),
      ]),
      bekannt.length ? h("div", { class: "feld" }, [
        h("span", { text: "Schon einmal hier gewesen?" }), schnellwahl,
      ]) : null,
      h("div", { class: "feld" }, [
        h("span", { text: "Klassenstufe" }), stufenfeld, hinweisStufe,
      ]),
      h("label", { class: "schalter", for: "sim" }, [
        simulation, h("span", { text: "Simulation: Antworten vorschlagen lassen" }),
      ]),
    ]),
    h("div", { class: "knopfreihe" }, [los]),
    meldeplatz,
  ]);

  los.addEventListener("click", async () => {
    const id = kennung.value.trim();
    if (!KENNUNG.test(id)) {
      meldeplatz.replaceChildren(fehlerkasten(
        "Das Kürzel passt noch nicht: 2 bis 32 Zeichen, Beginn mit Buchstabe"
        + " oder Ziffer, danach auch - und _."));
      kennung.focus();
      return;
    }
    los.disabled = true;
    try {
      const antwort = await ruf("/api/sitzung",
        { student_id: id, klassenstufe: stufe });
      Z.student_id = antwort.student_id;
      Z.klassenstufe = antwort.klassenstufe;
      Z.simulation = simulation.checked;
      kopfzeile(antwort.bearbeitet);
      await naechsteAufgabe();
    } catch (e) {
      los.disabled = false;
      meldeplatz.replaceChildren(fehlerkasten(e.message));
    }
  });

  zeige(kasten);
  kennung.focus();
}

function kopfzeile(bearbeitet) {
  wer.hidden = false;
  wer.replaceChildren(
    h("span", { class: "marke" }, [h("b", { text: Z.student_id })]),
    h("span", { class: "marke" }, [
      "Klasse ", h("b", { text: String(Z.klassenstufe ?? "–") })]),
    h("span", { class: "marke" }, [
      h("b", { text: String(bearbeitet ?? 0) }), " bearbeitet"]),
  );
}

// ---------------------------------------------------------------- Aufgabe

async function naechsteAufgabe() {
  Z.spec = null;
  let antwort;
  try {
    antwort = await ruf("/api/aufgabe", { student_id: Z.student_id });
  } catch (e) {
    zeige(h("div", { class: "karte" }, [
      fehlerkasten(e.message),
      h("div", { class: "knopfreihe" }, [zurueckKnopf()]),
    ]));
    return;
  }
  if (antwort.ende) {
    endseite(antwort.ende);
    return;
  }
  Z.spec = antwort.aufgabe;
  Z.antwortform = antwort.antwortform;
  kopfzeile(antwort.bearbeitet);
  aufgabenseite(antwort);
}

function aufgabenseite(daten) {
  const spec = Z.spec;
  Z.widget = baue(spec, Z.antwortform);

  const platz = h("div", { id: "rueckmeldung" });

  const pruefen = h("button", { type: "button", class: "haupt", id: "pruefen",
    text: "Antwort prüfen" });
  pruefen.addEventListener("click", () => abgeben());

  const stuetze = h("input", { type: "checkbox", id: "stuetze" });
  stuetze.checked = Boolean(daten.stuetze);
  stuetze.addEventListener("change", () => {
    // §33: eine mit Unterstuetzung geloeste Aufgabe wird als solche erfasst.
    ruf("/api/stuetze", { student_id: Z.student_id, an: stuetze.checked })
      .catch(() => { stuetze.checked = !stuetze.checked; });
  });

  const uebergehen = h("button", { type: "button", class: "leise",
    text: "Andere Aufgabe" });
  uebergehen.addEventListener("click", async () => {
    // §3: der Vorschlag ist ein Vorschlag.
    uebergehen.disabled = true;
    try {
      await ruf("/api/weiter", { student_id: Z.student_id });
      await naechsteAufgabe();
    } catch (e) {
      uebergehen.disabled = false;
      platz.replaceChildren(fehlerkasten(e.message));
    }
  });

  const fertig = h("button", { type: "button", class: "leise", text: "Schluss" });
  fertig.addEventListener("click", beenden);

  const karte = h("div", { class: "karte" }, [
    h("div", { class: "fortschritt" }, [
      h("span", { text: `Aufgabe ${(daten.bearbeitet || 0) + 1}` }),
      h("span", { class: "balken" }, [fortschrittsbalken(daten.bearbeitet || 0)]),
    ]),
    h("p", { class: "frage", text: spec.prompt }),
    Z.widget.figur ? h("div", { class: "bild" }, [Z.widget.figur]) : null,
    Z.widget.element,
    platz,
    h("div", { class: "knopfreihe" }, [
      pruefen,
      h("label", { class: "schalter", for: "stuetze" }, [
        stuetze, h("span", { text: "Ich hatte Hilfe" }),
      ]),
      h("span", { class: "rechts" }),
      uebergehen, fertig,
    ]),
  ]);

  zeige(karte, simulationskasten(daten));

  // Enter gibt ab, solange der Fokus in einem Textfeld steht.
  karte.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.tagName === "INPUT"
        && ev.target.type === "text" && !pruefen.disabled) {
      ev.preventDefault();
      pruefen.click();
    }
  });
  if (!Z.lauf) Z.widget.fokus();
}

function fortschrittsbalken(bearbeitet) {
  const i = h("i");
  // Kein Ziel, nur Bewegung: eine Prozentzahl waere eine Aussage ueber den
  // Stand des Kindes, und die trifft diese Oberflaeche nicht (§32).
  i.style.width = `${Math.min(100, (bearbeitet % 10) * 10 + 10)}%`;
  return i;
}

/** Antwort abgeben. Liefert true/false/null (null = nicht abgegeben). */
async function abgeben() {
  const platz = document.getElementById("rueckmeldung");
  const knopf = document.getElementById("pruefen");
  const antwort = Z.widget.lies();
  if (antwort === undefined) {
    platz.replaceChildren(fehlerkasten("Da fehlt noch eine Antwort."));
    Z.widget.fokus();
    return null;
  }
  knopf.disabled = true;
  const ereignisse = [...Z.widget.ereignisse(), { event_type: "SUBMIT" }];
  let ergebnis;
  try {
    ergebnis = await ruf("/api/antwort",
      { student_id: Z.student_id, answer: antwort, events: ereignisse });
  } catch (e) {
    knopf.disabled = false;
    platz.replaceChildren(fehlerkasten(e.message));
    return null;
  }
  kopfzeile(ergebnis.bearbeitet);
  zeigeRueckmeldung(platz, ergebnis);
  return ergebnis.richtig;
}

/** §105 Schritt 4. Richtig oder noch nicht - mehr sagt diese Seite nicht. */
function zeigeRueckmeldung(platz, ergebnis) {
  const weiter = h("button", { type: "button", class: "haupt", text: "Weiter" });
  weiter.addEventListener("click", naechsteAufgabe);

  platz.replaceChildren(h("div", {
    class: "rueckmeldung " + (ergebnis.richtig ? "ja" : "nein"),
    role: "status",
  }, [
    h("span", { class: "zeichen", text: ergebnis.richtig ? "✓" : "!" }),
    h("span", {}, [
      h("span", { text: ergebnis.richtig ? "Richtig." : "Noch nicht." }),
      ergebnis.loesung !== undefined
        ? h("span", { class: "nachtrag", text: `Richtig wäre: ${ergebnis.loesung}` })
        : null,
    ]),
  ]));

  // Die Aufgabe bleibt stehen, die Eingabe wird stillgelegt: was das Kind
  // geantwortet hat, soll neben der Rueckmeldung sichtbar bleiben.
  for (const feld of document.querySelectorAll(".eingabe input, .eingabe button")) {
    feld.disabled = true;
  }
  for (const figur of document.querySelectorAll(".figur-aktiv")) {
    figur.style.pointerEvents = "none";
  }
  platz.appendChild(h("div", { class: "knopfreihe" }, [weiter]));
  if (!Z.lauf) weiter.focus();
}

function zurueckKnopf() {
  const k = h("button", { type: "button", text: "Von vorn" });
  k.addEventListener("click", () => startseite());
  return k;
}

// ------------------------------------------------------------- Simulation

/**
 * §123: der Simulationsmodus prueft die Engine, indem er sie benutzt.
 *
 * Deshalb geht die vorgeschlagene Antwort denselben Weg wie jede andere -
 * sie landet im Eingabefeld und wird abgeschickt. Eine Abkuerzung am
 * Scoring vorbei pruefte eine zweite Engine, nicht diese.
 */
function simulationskasten(daten) {
  if (!Z.simulation) return null;

  const meta = Z.spec.meta || {};
  const zeile = `${Z.spec.task_id} · ${meta.difficulty}`
    + ` · ${Z.spec.representation.mode} · ${Z.spec.interaction.mode}`
    + ` · ${Z.antwortform.rule}`;

  const einzeln = (art) => {
    const k = h("button", { type: "button", class: "klein",
      text: art === "richtig" ? "Richtig antworten" : "Falsch antworten" });
    k.addEventListener("click", async () => {
      try {
        await vorschlagen(art);
        await abgeben();
      } catch (e) {
        document.getElementById("rueckmeldung")
          .replaceChildren(fehlerkasten(e.message));
      }
    });
    return k;
  };

  const anzahl = h("select", { "aria-label": "Wie viele Aufgaben" });
  for (const n of [5, 10, 25, 50]) {
    anzahl.appendChild(h("option", { value: String(n), text: `${n} Aufgaben` }));
  }
  anzahl.value = String((Z.lauf && Z.lauf.gesamt) || 10);
  anzahl.style.width = "auto";

  const art = h("select", { "aria-label": "Wie geantwortet wird" });
  for (const [wert, text] of [["richtig", "alles richtig"],
                              ["falsch", "alles falsch"],
                              ["gemischt", "gemischt"]]) {
    art.appendChild(h("option", { value: wert, text }));
  }
  art.value = (Z.lauf && Z.lauf.art) || "richtig";
  art.style.width = "auto";

  const starten = h("button", { type: "button", class: "klein", id: "simstart",
    text: "Durchlaufen" });
  const anhalten = h("button", { type: "button", class: "klein leise", id: "simstop",
    text: "Anhalten" });
  const stand = h("span", { id: "simstand", text: Z.lauf ? standtext() : "" });

  starten.addEventListener("click", () => {
    Z.lauf = { gesamt: Number(anzahl.value), art: art.value,
               gemacht: 0, richtig: 0, abbruch: false };
    durchlaufen();
  });
  anhalten.addEventListener("click", () => { if (Z.lauf) Z.lauf.abbruch = true; });

  if (Z.lauf) starten.hidden = true; else anhalten.hidden = true;

  return h("div", { class: "simulation" }, [
    h("div", { class: "kopfzeile" }, [
      h("span", { text: "Simulation" }),
      h("span", { class: "rechts", text: zeile }),
    ]),
    h("div", { class: "koerper" }, [
      // §88/§89 - hier beantwortet, weil hier kein Kind sitzt.
      h("p", { text: `Warum diese Aufgabe: ${daten.warum.grund}`
        + (daten.warum.erklaerung ? ` – ${daten.warum.erklaerung}` : "") }),
      h("div", { class: "knopfreihe" }, [
        einzeln("richtig"), einzeln("falsch"),
        h("span", { class: "rechts" }), anzahl, art, starten, anhalten, stand,
      ]),
    ]),
  ]);
}

function standtext() {
  return `${Z.lauf.gemacht}/${Z.lauf.gesamt} · ${Z.lauf.richtig} richtig`;
}

async function durchlaufen() {
  while (Z.lauf && !Z.lauf.abbruch && Z.lauf.gemacht < Z.lauf.gesamt && Z.spec) {
    const wie = Z.lauf.art === "gemischt"
      ? (Z.lauf.gemacht % 3 === 2 ? "falsch" : "richtig")
      : Z.lauf.art;
    let war;
    try {
      await vorschlagen(wie);
      war = await abgeben();
    } catch (e) {
      document.getElementById("rueckmeldung")
        .replaceChildren(fehlerkasten(e.message));
      break;
    }
    if (war === null) break;             // nicht abgegeben, sonst Endlosschleife
    Z.lauf.gemacht += 1;
    if (war) Z.lauf.richtig += 1;
    const stand = document.getElementById("simstand");
    if (stand) stand.textContent = standtext();
    if (Z.lauf.gemacht >= Z.lauf.gesamt || Z.lauf.abbruch) break;
    await naechsteAufgabe();
  }
  const fertig = Z.lauf ? standtext() : "";
  Z.lauf = null;
  const stand = document.getElementById("simstand");
  if (stand) stand.textContent = fertig;
  const anfangen = document.getElementById("simstart");
  const anhalten = document.getElementById("simstop");
  if (anfangen) anfangen.hidden = false;
  if (anhalten) anhalten.hidden = true;
}

async function vorschlagen(art) {
  const vorschlag = await ruf("/api/vorschlag", { student_id: Z.student_id, art });
  Z.widget.setze(vorschlag.answer);
  return vorschlag;
}

// -------------------------------------------------------------------- Ende

function endseite(ende) {
  Z.lauf = null;
  const nochmal = h("button", { type: "button", class: "haupt",
    text: "Weitermachen" });
  nochmal.addEventListener("click", naechsteAufgabe);
  zeige(h("div", { class: "karte" }, [
    h("div", { class: "abschluss" }, [
      h("div", { class: "zahl" }, [
        String(ende.bearbeitet), h("small", { text: " Aufgaben" })]),
      h("h2", { text: "Das war's für jetzt." }),
      h("p", { class: "leise", text: ende.erklaerung || ende.grund || "" }),
    ]),
    h("div", { class: "knopfreihe" }, [nochmal, zurueckKnopf()]),
  ]));
}

async function beenden() {
  Z.lauf = null;
  let ergebnis = null;
  try {
    ergebnis = await ruf("/api/ende", { student_id: Z.student_id });
  } catch { /* Die Sitzung endet auch ohne Quittung. */ }
  zeige(h("div", { class: "karte" }, [
    h("div", { class: "abschluss" }, [
      h("div", { class: "zahl" }, [
        String((ergebnis && ergebnis.bearbeitet) ?? 0),
        h("small", { text: " Aufgaben" })]),
      h("h2", { text: "Bis zum nächsten Mal." }),
    ]),
    h("div", { class: "knopfreihe" }, [zurueckKnopf()]),
  ]));
}

start();
