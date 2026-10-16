/* Bedienformen (§17) als Eingabefelder.
 *
 * Diese Datei beantwortet genau eine Frage: wie gibt ein Kind die Antwort?
 * Was es dabei sieht, steht in figuren.js. Die Trennung ist nicht Geschmack,
 * sondern §16/§17 - dieselbe Darstellung kommt mit verschiedenen Bedienformen
 * vor, und nur weil beides getrennt gefuehrt wird, laesst sich ein Unterschied
 * spaeter der einen oder der anderen Variablen zuordnen (§32).
 *
 * §61/§42 verlangen ein Interaktionsprotokoll: Klickreihenfolge, ausgelassene
 * Objekte, doppelte Klicks. Jedes Widget fuehrt es mit. Ohne object_id in der
 * richtigen Reihenfolge entstehen ERR_OMISSION und ERR_DOUBLE_COUNT nie.
 *
 * Was hier bewusst NICHT passiert: mitzaehlen. Wer die angetippten Punkte
 * als Zahl einblendet, hat die Zaehlaufgabe geloest, nicht das Kind - und
 * §43 wollte gerade beobachten, ob nach dem Zaehlen erneut gezaehlt wird.
 * Angetippte Objekte wechseln die Farbe (das tut ein Finger auch), eine Zahl
 * erscheint nirgends.
 */

import { zeichne, streuplaetze } from "./figuren.js";

/** HTML-Knoten bauen. Kein innerHTML - der Server setzt eine enge CSP. */
export function h(tag, attrs = {}, kinder = []) {
  const k = document.createElement(tag);
  for (const [name, wert] of Object.entries(attrs)) {
    if (wert === null || wert === undefined || wert === false) continue;
    if (name === "class") k.className = wert;
    else if (name === "text") k.textContent = String(wert);
    else if (name.startsWith("on")) k.addEventListener(name.slice(2), wert);
    else k.setAttribute(name, wert === true ? "" : String(wert));
  }
  for (const kind of [].concat(kinder)) {
    if (kind === null || kind === undefined) continue;
    k.appendChild(typeof kind === "string" ? document.createTextNode(kind) : kind);
  }
  return k;
}

/** Protokoll nach §61. */
function protokoll() {
  const liste = [];
  return {
    liste,
    merke(event_type, object_id = null, value = null) {
      // §61 wird serverseitig bei 2000 Ereignissen abgeschnitten. Hier vorher
      // aufhoeren ist ehrlicher als eine abgelehnte Abgabe.
      if (liste.length >= 1800) return;
      liste.push({ event_type, object_id, value });
    },
  };
}

/**
 * @param {object} spec        Darstellungsvorschrift aus renderer.render
 * @param {object} antwortform {rule, felder} aus dem Lernserver
 * @returns {{element: HTMLElement, figur: SVGElement|null, lies: Function,
 *            setze: Function, ereignisse: Function, fokus: Function}}
 */
export function baue(spec, antwortform) {
  const log = protokoll();
  const stimulus = spec.representation.stimulus;
  const modus = spec.representation.mode;

  // §116: ein Bild gehoert nur zu einem Item, dessen Darstellung bildlich ist.
  // Bei MATHEMATICAL_SYMBOL oder NATURAL_LANGUAGE eines zu zeichnen - und sei
  // es als Hilfe - macht aus dem symbolischen Item ein ikonisches und
  // zerstoert den Vergleich, fuer den das Paar gebaut wurde.
  const figur = zeichne(stimulus, modus);

  const bauer = BAUER[spec.interaction.mode];
  const widget = bauer
    ? bauer(spec, antwortform, log, figur, stimulus)
    : notfall(spec, log);
  return { figur, ...widget, ereignisse: () => log.liste };
}

function notfall(spec, log) {
  return {
    element: h("p", { class: "fehler",
      text: `Für die Bedienform ${spec.interaction.mode} hat diese Oberfläche`
        + " kein Eingabefeld." }),
    lies: () => undefined,
    setze: () => {},
    fokus: () => {},
  };
}

// ============================================================ ENTER (§17)

function zahlfeld(klasse = "zahlenfeld") {
  return h("input", { type: "text", class: klasse, inputmode: "decimal",
    autocomplete: "off", autocapitalize: "off", spellcheck: "false" });
}

/** Was im Feld steht, so wie es dort steht.
 *
 * Als Zeichenkette - scoring.normalize_number liest "3 000" und "0,4" nach
 * deutscher Schreibweise. Eine Umrechnung hier wuerde diese Regel verdoppeln.
 * Einzige Ausnahme: ein einzelner Punkt zwischen Ziffern ist als Dezimalpunkt
 * gemeint, waehrend normalize_number ihn als Tausenderpunkt streichen wuerde.
 * Diese Antwort als Zahl zu uebergeben nimmt der Oberflaeche einen Fehler ab,
 * den sie sonst dem Kind zuschriebe (§59).
 */
function gelesen(text) {
  const roh = text.trim();
  if (roh === "") return undefined;
  if (/^-?\d+\.\d+$/.test(roh)) return Number(roh);
  return roh;
}

function e_enter(spec, form, log) {
  const art = spec.interaction.input_type;

  if (art === "NUMBER_SEQUENCE") {
    const anzahl = Math.max(1, spec.interaction.fields || form.felder || 1);
    const felder = [];
    const reihe = h("div", { class: "felderreihe" });
    for (let i = 0; i < anzahl; i++) {
      const feld = zahlfeld();
      feld.setAttribute("aria-label", `${i + 1}. Zahl`);
      horche(feld, log, `feld${i + 1}`);
      felder.push(feld);
      reihe.appendChild(feld);
    }
    return {
      element: h("div", { class: "eingabe" }, [
        h("p", { class: "anleitung", text: anzahl === 1
          ? "Trage die Zahl ein." : `Trage ${anzahl} Zahlen der Reihe nach ein.` }),
        reihe,
      ]),
      lies: () => {
        const werte = felder.map((f) => gelesen(f.value));
        return werte.some((w) => w === undefined) ? undefined : werte;
      },
      setze: (antwort) => {
        [].concat(antwort).forEach((w, i) => {
          if (felder[i]) felder[i].value = deutsch(w);
        });
        log.merke("ANSWER_CHANGE", null, "simulation");
      },
      fokus: () => felder[0].focus(),
    };
  }

  const breit = art === "EXPRESSION" || art === "TEXT";
  const feld = zahlfeld("zahlenfeld" + (breit ? " breit" : ""));
  if (breit) feld.inputMode = "text";
  feld.setAttribute("aria-label", "Deine Antwort");
  horche(feld, log, "feld");
  const anleitung = art === "EXPRESSION"
    ? "Schreibe die ganze Rechnung auf."
    : (art === "TEXT" ? "Schreibe deine Antwort auf." : "Trage die Zahl ein.");
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: anleitung }), feld,
    ]),
    lies: () => gelesen(feld.value),
    setze: (antwort) => {
      feld.value = deutsch(antwort);
      log.merke("ANSWER_CHANGE", null, "simulation");
    },
    fokus: () => feld.focus(),
  };
}

/** Zahlen in deutscher Schreibweise anzeigen - auch die der Simulation. */
function deutsch(wert) {
  if (typeof wert === "number" && !Number.isInteger(wert)) {
    return String(wert).replace(".", ",");
  }
  return wert === null || wert === undefined ? "" : String(wert);
}

function horche(feld, log, id) {
  let zuletzt = "";
  feld.addEventListener("input", () => {
    if (feld.value === zuletzt) return;
    zuletzt = feld.value;
    log.merke("ANSWER_CHANGE", id, feld.value);
  });
}

// =========================================================== SELECT (§17)

function e_select(spec, form, log) {
  const mehrfach = spec.interaction.multiple;
  const optionen = spec.interaction.options || [];
  const gewaehlt = new Set();
  const knoepfe = [];
  const kurz = optionen.every((o) => String(o).length <= 14);

  const liste = h("div", {
    class: "auswahl" + (kurz && optionen.length > 2 ? " waagerecht" : ""),
    role: mehrfach ? "group" : "radiogroup",
  });

  optionen.forEach((option, i) => {
    const knopf = h("button", {
      type: "button", class: "option" + (mehrfach ? "" : " rund"),
      "aria-pressed": "false",
    }, [h("span", { class: "haken", text: mehrfach ? "✓" : "●" }),
        h("span", { text: String(option) })]);
    knopf.addEventListener("click", () => {
      if (gewaehlt.has(option)) {
        gewaehlt.delete(option);
        knopf.setAttribute("aria-pressed", "false");
        log.merke("DESELECT", `option${i + 1}`, String(option));
      } else {
        if (!mehrfach) {
          gewaehlt.clear();
          knoepfe.forEach((k) => k.setAttribute("aria-pressed", "false"));
        }
        gewaehlt.add(option);
        knopf.setAttribute("aria-pressed", "true");
        log.merke("SELECT", `option${i + 1}`, String(option));
      }
      log.merke("ANSWER_CHANGE", null, [...gewaehlt].join("|"));
    });
    knoepfe.push(knopf);
    liste.appendChild(knopf);
  });

  const erwartet = spec.interaction.expected_selection_count;
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: mehrfach
        ? `Wähle alle zutreffenden aus${erwartet > 1 ? ` (${erwartet})` : ""}.`
        : "Wähle eine Antwort aus." }),
      liste,
    ]),
    lies: () => {
      if (gewaehlt.size === 0) return undefined;
      return mehrfach ? [...gewaehlt] : [...gewaehlt][0];
    },
    setze: (antwort) => {
      gewaehlt.clear();
      knoepfe.forEach((k) => k.setAttribute("aria-pressed", "false"));
      for (const wert of [].concat(antwort)) {
        const i = optionen.findIndex((o) => String(o) === String(wert));
        if (i >= 0) {
          gewaehlt.add(optionen[i]);
          knoepfe[i].setAttribute("aria-pressed", "true");
          log.merke("SELECT", `option${i + 1}`, String(wert));
        }
      }
      log.merke("ANSWER_CHANGE", null, "simulation");
    },
    fokus: () => knoepfe[0] && knoepfe[0].focus(),
  };
}

// =================================================== CLICK_SEQUENCE (§42)

function e_click_sequence(spec, form, log, figur, stimulus) {
  // Drei Faelle, die der Renderer unterscheidet:
  //   input_type NUMBER   -> Objekte antippen, Anzahl selbst eintragen (§43)
  //   target_object       -> ein Objekt mehrfach antippen
  //   sonst (Figurteile)  -> Teile der Figur antippen, Anzahl ist die Antwort
  if (spec.interaction.target_object) return e_tippen(spec, log);
  if (spec.interaction.input_type === "NUMBER") {
    return e_zaehlen(spec, form, log, figur);
  }
  return e_figurteile(spec, form, log, figur);
}

/** Zaehlen: antippen protokolliert, die Zahl kommt vom Kind (§43). */
function e_zaehlen(spec, form, log, figur) {
  const feld = zahlfeld();
  feld.setAttribute("aria-label", "Wie viele sind es?");
  horche(feld, log, "feld");
  if (figur) aktiviere(figur, "[data-objekt]", (ziel, id) => {
    ziel.classList.toggle("geklickt");
    log.merke("CLICK", `obj${Number(id) + 1}`);
  });
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: figur
        ? "Tippe die Objekte an, während du zählst. Trage dann die Anzahl ein."
        : "Trage die Anzahl ein." }),
      feld,
    ]),
    lies: () => gelesen(feld.value),
    setze: (antwort) => {
      feld.value = deutsch(antwort);
      log.merke("ANSWER_CHANGE", null, "simulation");
    },
    fokus: () => feld.focus(),
  };
}

/** Ein Objekt genau n-mal antippen. Die Anzahl der Tipps ist die Antwort. */
function e_tippen(spec, log) {
  let tipps = 0;
  const stand = h("span", { class: "stand", text: "0" });
  const knopf = h("button", {
    type: "button", class: "stein",
    "aria-label": "Hier tippen",
  });
  knopf.style.width = "92px";
  knopf.style.height = "92px";
  knopf.addEventListener("click", () => {
    tipps += 1;
    stand.textContent = String(tipps);
    log.merke("CLICK", "target", tipps);
  });
  const zurueck = h("button", {
    type: "button", class: "leise klein", text: "Von vorn",
  });
  zurueck.addEventListener("click", () => {
    tipps = 0;
    stand.textContent = "0";
    log.merke("CLICK", "reset", 0);
  });
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: "Tippe auf den Kreis." }),
      h("div", { class: "zaehler" }, [knopf, stand, zurueck]),
    ]),
    // Hier ist das Antippen die Antwort, nicht ihre Vorbereitung: die Aufgabe
    // lautet "tippe genau siebenmal". 0 Tipps ist deshalb keine Antwort.
    lies: () => (tipps === 0 ? undefined : { interactions: tipps }),
    setze: (antwort) => {
      const n = typeof antwort === "object" && antwort ? antwort.interactions : antwort;
      tipps = Number(n) || 0;
      stand.textContent = String(tipps);
      for (let i = 0; i < tipps; i++) log.merke("CLICK", "target", i + 1);
    },
    fokus: () => knopf.focus(),
  };
}

/** Teile einer Figur antippen (Bruchstreifen). Die Zahl der Tipps zaehlt. */
function e_figurteile(spec, form, log, figur) {
  let tipps = 0;
  if (figur) aktiviere(figur, "[data-teil]", (ziel, id) => {
    // Jeder Tipp zaehlt, auch der auf ein schon gefaerbtes Teil: §42 fuehrt
    // doppelte Klicks als Beobachtung, nicht als Bedienfehler, den die
    // Oberflaeche stillschweigend verschluckt.
    ziel.classList.toggle("gewaehlt");
    tipps += 1;
    log.merke("CLICK", `teil${Number(id) + 1}`, tipps);
  });
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: "Tippe die Teile an, die dazugehören." }),
    ]),
    lies: () => (tipps === 0 ? undefined : { interactions: tipps }),
    setze: (antwort) => {
      const n = typeof antwort === "object" && antwort ? antwort.interactions : antwort;
      const ziel = Number(n) || 0;
      const teile = figur ? [...figur.querySelectorAll("[data-teil]")] : [];
      for (let i = 0; i < ziel; i++) {
        if (teile[i]) teile[i].classList.add("gewaehlt");
        tipps += 1;
        log.merke("CLICK", `teil${i + 1}`, tipps);
      }
    },
    fokus: () => {
      const erstes = figur && figur.querySelector("[data-teil]");
      if (erstes) erstes.focus();
    },
  };
}

/** Teile einer SVG-Figur anklickbar machen. Erst hier - §17. */
function aktiviere(figur, auswahl, bei) {
  figur.classList.add("figur-aktiv");
  for (const ziel of figur.querySelectorAll(auswahl)) {
    const id = ziel.getAttribute("data-teil") ?? ziel.getAttribute("data-objekt")
      ?? ziel.getAttribute("data-wert");
    ziel.setAttribute("tabindex", "0");
    ziel.setAttribute("role", "button");
    ziel.addEventListener("click", () => bei(ziel, id));
    ziel.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); bei(ziel, id); }
    });
  }
}

// ============================================================= DRAG (§17)

function e_drag(spec, form, log, figur, stimulus) {
  if (form.rule === "GROUP_PARTITION") return e_verteilen(spec, form, log, stimulus);
  if (spec.interaction.input_type === "NUMBER_LINE_POSITION") {
    return e_marke(spec, log, figur);
  }
  return e_legen(spec, form, log);
}

/** Eine Marke auf dem Zahlenstrahl ablegen. */
function e_marke(spec, log, figur) {
  let wert;
  const anzeige = h("span", { class: "stand", text: "–" });
  if (figur) {
    aktiviere(figur, "[data-wert]", (ziel) => {
      for (const anderes of figur.querySelectorAll("[data-wert]")) {
        anderes.classList.remove("gewaehlt");
      }
      ziel.classList.add("gewaehlt");
      wert = Number(ziel.getAttribute("data-wert"));
      anzeige.textContent = deutsch(wert);
      log.merke("DRAG", "marke");
      log.merke("DROP", "marke", wert);
      log.merke("ANSWER_CHANGE", null, wert);
    });
  }
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung",
        text: "Tippe die Stelle auf dem Zahlenstrahl an, an die die Marke gehört." }),
      h("div", { class: "zaehler" }, [h("span", { text: "Marke steht auf" }), anzeige]),
    ]),
    // Die Zahl kommt aus der Figur, nicht aus einem Textfeld: als Zahl
    // uebergeben, damit normalize_number den Punkt in 0.4 nicht als
    // Tausenderpunkt streicht.
    lies: () => wert,
    setze: (antwort) => {
      const z = Number(antwort);
      const ziel = figur && figur.querySelector(`[data-wert="${z}"]`);
      if (ziel) ziel.dispatchEvent(new Event("click"));
      else {
        wert = z;
        anzeige.textContent = deutsch(z);
        log.merke("DROP", "marke", z);
      }
    },
    fokus: () => {
      const erstes = figur && figur.querySelector("[data-wert]");
      if (erstes) erstes.focus();
    },
  };
}

/** Genau n Objekte aus einem Vorrat in ein Feld legen. */
function e_legen(spec, form, log) {
  const vorhanden = spec.interaction.source_count || 0;
  const vorrat = h("div", { class: "vorrat", "data-ziel": "vorrat" });
  const feld = h("div", { class: "ablage", "data-ziel": "feld" }, [
    h("span", { class: "platzhalter", text: spec.interaction.target_label || "Feld" }),
  ]);
  const zug = schieber(log, (stein, ziel) => {
    ziel.appendChild(stein);
    aufraeumen();
  });
  zug.ziel(feld, spec.interaction.target_label || "Feld");
  zug.ziel(vorrat, "Vorrat");          // zuruecklegen muss auch gehen
  for (let i = 0; i < vorhanden; i++) {
    vorrat.appendChild(zug.stein(`obj${i + 1}`));
  }
  function aufraeumen() {
    const platzhalter = feld.querySelector(".platzhalter");
    if (platzhalter) platzhalter.hidden = feld.querySelectorAll(".stein").length > 0;
    log.merke("ANSWER_CHANGE", null, feld.querySelectorAll(".stein").length);
  }
  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung",
        text: "Ziehe die Objekte in das Feld – oder tippe eines an und dann das Feld." }),
      feld,
      h("p", { class: "anleitung", text: "Vorrat" }),
      vorrat,
    ]),
    lies: () => {
      const n = feld.querySelectorAll(".stein").length;
      return n === 0 ? undefined : { placed: n };
    },
    setze: (antwort) => {
      const ziel = Number(antwort && antwort.placed !== undefined
        ? antwort.placed : antwort) || 0;
      for (const stein of [...feld.querySelectorAll(".stein")]) vorrat.appendChild(stein);
      const steine = [...vorrat.querySelectorAll(".stein")];
      for (let i = 0; i < ziel && i < steine.length; i++) {
        log.merke("DRAG", steine[i].dataset.objekt);
        feld.appendChild(steine[i]);
        log.merke("DROP", steine[i].dataset.objekt, "feld");
      }
      aufraeumen();
    },
    fokus: () => { const s = vorrat.querySelector(".stein"); if (s) s.focus(); },
  };
}

/** Objekte auf Gruppen verteilen (§55). */
function e_verteilen(spec, form, log, stimulus) {
  const gesamt = spec.interaction.source_count || stimulus.objects || 0;
  const feste = Number(spec.interaction.targets);
  const quotativ = !Number.isFinite(feste);   // Gruppengroesse gegeben, Anzahl gesucht
  const vorrat = h("div", { class: "vorrat", "data-ziel": "vorrat" });
  const feld = h("div", { class: "gruppenfeld" });

  const zug = schieber(log, (stein, ziel) => {
    (ziel.classList.contains("gruppe") ? ziel.querySelector(".inhalt") : ziel)
      .appendChild(stein);
    zaehle();
  });

  let naechste = 0;
  function neueGruppe() {
    naechste += 1;
    const titel = quotativ ? `Gruppe ${naechste}` : `Kind ${naechste}`;
    const g = h("div", { class: "gruppe", "data-ziel": `gruppe${naechste}` }, [
      h("div", { class: "titel", text: titel }),
      h("div", { class: "inhalt" }),
    ]);
    zug.ziel(g, titel);
    feld.appendChild(g);
    return g;
  }
  zug.ziel(vorrat, "Vorrat");          // zuruecklegen muss auch gehen
  if (quotativ) neueGruppe();
  else for (let i = 0; i < feste; i++) neueGruppe();

  for (let i = 0; i < gesamt; i++) vorrat.appendChild(zug.stein(`obj${i + 1}`));

  const dazu = h("button", { type: "button", class: "leise klein",
    text: "+ weitere Gruppe" });
  dazu.addEventListener("click", () => { neueGruppe(); log.merke("CLICK", "neue_gruppe"); });

  function gruppen() {
    return [...feld.querySelectorAll(".gruppe")]
      .map((g) => g.querySelectorAll(".stein").length)
      .filter((n) => n > 0);
  }
  function zaehle() { log.merke("ANSWER_CHANGE", null, gruppen().join("+")); }

  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung", text: quotativ
        ? "Ziehe die Objekte in die Gruppen. Lege bei Bedarf eine neue Gruppe an."
        : "Ziehe die Objekte zu den Kindern – oder tippe ein Objekt an und dann ein Feld." }),
      feld,
      quotativ ? h("div", { class: "knopfreihe" }, [dazu]) : null,
      h("p", { class: "anleitung", text: "Vorrat" }),
      vorrat,
    ]),
    lies: () => {
      const g = gruppen();
      if (g.length === 0) return undefined;
      // per_group nur dann, wenn alle Gruppen gleich gross sind - eine
      // ungleiche Verteilung ist eine Antwort, keine Stoerung, und wird als
      // solche bewertet (§59: nicht die Oberflaeche entscheidet das).
      const gleich = g.every((n) => n === g[0]);
      return { groups: g.length, per_group: gleich ? g[0] : null };
    },
    setze: (antwort) => {
      const anzahl = Number(antwort && antwort.groups) || 0;
      const je = Number(antwort && antwort.per_group) || 0;
      for (const stein of [...feld.querySelectorAll(".stein")]) vorrat.appendChild(stein);
      while (quotativ && feld.querySelectorAll(".gruppe").length < anzahl) neueGruppe();
      const boxen = [...feld.querySelectorAll(".gruppe")];
      const steine = [...vorrat.querySelectorAll(".stein")];
      let k = 0;
      for (let g = 0; g < anzahl && g < boxen.length; g++) {
        for (let i = 0; i < je && k < steine.length; i++, k++) {
          log.merke("DRAG", steine[k].dataset.objekt);
          boxen[g].querySelector(".inhalt").appendChild(steine[k]);
          log.merke("DROP", steine[k].dataset.objekt, `gruppe${g + 1}`);
        }
      }
      zaehle();
    },
    fokus: () => { const s = vorrat.querySelector(".stein"); if (s) s.focus(); },
  };
}

/**
 * Objekte bewegen - mit Zeiger oder in zwei Tipps.
 *
 * Beide Wege melden DRAG und DROP, denn beide Male wird ein Objekt genommen
 * und abgelegt; §61 fragt nach dem Vorgang, nicht nach der Handbewegung. Der
 * Zweitippweg ist kein Zugestaendnis an die Bequemlichkeit, sondern die
 * einzige Bedienung, die auch mit der Tastatur funktioniert.
 */
function schieber(log, ablegen) {
  let inDerHand = null;

  function waehle(stein) {
    if (inDerHand === stein) {
      stein.classList.remove("faehrt");
      inDerHand = null;
      return;
    }
    if (inDerHand) inDerHand.classList.remove("faehrt");
    inDerHand = stein;
    stein.classList.add("faehrt");
    log.merke("DRAG", stein.dataset.objekt);
  }

  function lass(stein, ziel) {
    stein.classList.remove("faehrt");
    inDerHand = null;
    // Erst das Ablegen melden, dann bewegen: ablegen() meldet seinerseits
    // ANSWER_CHANGE, und sonst stuende die Folge auf dem Kopf - die Antwort
    // haette sich geaendert, bevor das Objekt abgelegt wurde (§61).
    log.merke("DROP", stein.dataset.objekt, ziel.dataset.ziel || "feld");
    ablegen(stein, ziel);
  }

  function zielUnter(x, y) {
    const unten = document.elementFromPoint(x, y);
    return unten ? unten.closest("[data-ziel]") : null;
  }

  /**
   * Einen Behaelter als Ablage anmelden.
   *
   * Ohne das waere ein leeres Feld nicht antippbar - man koennte nur auf ein
   * Objekt tippen, das dort schon liegt. Beim ersten Objekt liegt dort aber
   * keines. Genau diesen Weg nennt die Anleitung, und mit der Tastatur ist er
   * der einzige.
   */
  function ziel(behaelter, name) {
    // role="group", nicht "button": in der Ablage liegen Schaltflaechen, und
    // eine Schaltflaeche in einer Schaltflaeche meldet die Vorlesesoftware
    // falsch. Erreichbar ist sie trotzdem - tabindex und Enter/Leertaste.
    behaelter.setAttribute("tabindex", "0");
    behaelter.setAttribute("role", "group");
    if (name) behaelter.setAttribute("aria-label", name);
    behaelter.addEventListener("click", (ev) => {
      // Ein Tipp auf ein liegendes Objekt meldet sich selbst.
      if (!inDerHand || ev.target.closest(".stein")) return;
      lass(inDerHand, behaelter);
    });
    behaelter.addEventListener("keydown", (ev) => {
      if (!inDerHand || (ev.key !== "Enter" && ev.key !== " ")) return;
      ev.preventDefault();
      lass(inDerHand, behaelter);
    });
    return behaelter;
  }

  function stein(id) {
    const k = h("button", { type: "button", class: "stein", "data-objekt": id,
      "aria-label": `Objekt ${id}` });

    k.addEventListener("click", () => {
      if (inDerHand === k) { waehle(k); return; }
      if (inDerHand) {                       // in der Hand liegt ein anderes
        const ziel = k.closest("[data-ziel]");
        if (ziel) { lass(inDerHand, ziel); return; }
      }
      waehle(k);
    });

    let zieht = false, start = null;
    k.addEventListener("pointerdown", (ev) => {
      if (ev.pointerType === "mouse" && ev.button !== 0) return;
      start = { x: ev.clientX, y: ev.clientY };
      zieht = false;
      // Der Zeiger muss schon hier gefangen werden. Faengt man ihn erst,
      // wenn die Schwelle ueberschritten ist, laufen die pointermove-
      // Ereignisse laengst an anderen Elementen vorbei - das Objekt bliebe
      // beim ersten Zug liegen, und das Kind haelt die Oberflaeche fuer
      // kaputt, nicht die Aufgabe fuer schwer.
      try { k.setPointerCapture(ev.pointerId); } catch { /* geht auch ohne */ }
    });
    k.addEventListener("pointermove", (ev) => {
      if (!start) return;
      if (!zieht && Math.hypot(ev.clientX - start.x, ev.clientY - start.y) > 6) {
        zieht = true;
        if (inDerHand !== k) waehle(k);
      }
      if (!zieht) return;
      const ziel = zielUnter(ev.clientX, ev.clientY);
      for (const z of document.querySelectorAll("[data-ziel]")) {
        z.classList.toggle("bereit", z === ziel);
      }
    });
    k.addEventListener("pointerup", (ev) => {
      for (const z of document.querySelectorAll("[data-ziel]")) z.classList.remove("bereit");
      if (!zieht) { start = null; return; }
      zieht = false; start = null;
      const ziel = zielUnter(ev.clientX, ev.clientY);
      if (ziel) lass(k, ziel);
      else { k.classList.remove("faehrt"); inDerHand = null; }
      // Der Klick nach dem Ziehen wuerde das Objekt sonst gleich wieder
      // aufnehmen.
      ev.preventDefault();
    });
    k.addEventListener("pointercancel", () => {
      zieht = false; start = null;
      k.classList.remove("faehrt");
      inDerHand = null;
    });
    return k;
  }

  return { stein, ziel, inDerHand: () => inDerHand };
}

// ======================================================= MANIPULATE (§17)

function e_manipulate(spec, form, log, figur, stimulus) {
  if (form.rule === "GROUP_PARTITION") return e_buendeln(spec, form, log);
  return e_bewegen(spec, form, log);
}

/** Buendeln (§69, §92): loses Material zu Einheiten zusammenfassen. */
function e_buendeln(spec, form, log) {
  const gesamt = spec.interaction.objects || 0;
  const groesse = spec.interaction.bundle_size || 10;
  const felder = form.felder || ["bundles", "remaining"];
  const gewaehlt = new Set();
  let buendel = 0;

  const lose = h("div", { class: "vorrat" });
  const buendelreihe = h("div", { class: "vorrat" }, [
    h("span", { class: "platzhalter", text: "noch keine Bündel" }),
  ]);
  const knopf = h("button", { type: "button", class: "klein",
    text: `${groesse} bündeln`, disabled: true });

  function wuerfel(i) {
    const k = h("button", { type: "button", class: "stein", "data-objekt": `obj${i}`,
      "aria-label": `Würfel ${i}` });
    k.style.borderRadius = "7px";
    k.addEventListener("click", () => {
      if (gewaehlt.has(k)) { gewaehlt.delete(k); k.classList.remove("faehrt"); }
      else { gewaehlt.add(k); k.classList.add("faehrt"); }
      log.merke("CLICK", `obj${i}`, gewaehlt.size);
      knopf.disabled = gewaehlt.size !== groesse;
    });
    return k;
  }
  for (let i = 1; i <= gesamt; i++) lose.appendChild(wuerfel(i));

  knopf.addEventListener("click", () => {
    if (gewaehlt.size !== groesse) return;
    for (const w of gewaehlt) {
      log.merke("DRAG", w.dataset.objekt);
      w.remove();
      log.merke("DROP", w.dataset.objekt, "buendel");
    }
    gewaehlt.clear();
    buendel += 1;
    const platzhalter = buendelreihe.querySelector(".platzhalter");
    if (platzhalter) platzhalter.hidden = true;
    const b = h("div", { class: "stein", title: `Bündel zu ${groesse}` });
    b.style.width = "46px";
    b.style.borderRadius = "7px";
    b.style.display = "grid";
    b.style.placeItems = "center";
    b.style.color = "#fff";
    b.style.fontWeight = "700";
    b.textContent = String(groesse);
    buendelreihe.appendChild(b);
    knopf.disabled = true;
  });

  const uebrig = () => lose.querySelectorAll(".stein").length;

  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung",
        text: `Tippe ${groesse} Würfel an und bündle sie. Wiederhole das, solange es geht.` }),
      h("p", { class: "anleitung", text: "Bündel" }),
      buendelreihe,
      h("p", { class: "anleitung", text: "Einzelne Würfel" }),
      lose,
      h("div", { class: "knopfreihe" }, [knopf]),
    ]),
    lies: () => {
      if (buendel === 0 && uebrig() === gesamt) return undefined;
      const antwort = {};
      antwort[felder[0]] = buendel;
      antwort[felder[1]] = uebrig();
      return antwort;
    },
    setze: (antwort) => {
      const ziel = Number(antwort && antwort[felder[0]]) || 0;
      while (buendel < ziel && lose.querySelectorAll(".stein").length >= groesse) {
        const steine = [...lose.querySelectorAll(".stein")].slice(0, groesse);
        gewaehlt.clear();
        for (const s of steine) gewaehlt.add(s);
        knopf.disabled = false;
        knopf.dispatchEvent(new Event("click"));
      }
    },
    fokus: () => { const s = lose.querySelector(".stein"); if (s) s.focus(); },
  };
}

/** Bewegliches Material zaehlen (§47): schieben hilft, zaehlen muss das Kind. */
function e_bewegen(spec, form, log) {
  const gesamt = spec.interaction.objects || 0;
  const feld = h("div", { class: "ablage", "data-ziel": "feld" });
  feld.style.minHeight = "180px";
  feld.style.position = "relative";
  feld.style.display = "block";

  // Die Plaetze werden erst im ersten Layout gesetzt: vorher ist die Breite
  // des Feldes unbekannt, und ohne sie laesst sich kein Mindestabstand
  // einhalten. Ueberlappende Objekte waeren hier besonders misslich, weil
  // gerade gezaehlt werden soll.
  const steine = [];
  requestAnimationFrame(() => {
    const breite = Math.max(200, feld.clientWidth - 48);
    const { hoehe, plaetze } = streuplaetze(gesamt, breite, 44, 36);
    feld.style.minHeight = `${hoehe + 36}px`;
    plaetze.forEach(([x, y], i) => {
      steine[i].style.left = `${Math.round(x)}px`;
      steine[i].style.top = `${Math.round(y)}px`;
    });
  });

  for (let i = 1; i <= gesamt; i++) {
    const k = h("button", { type: "button", class: "stein", "data-objekt": `obj${i}`,
      "aria-label": `Objekt ${i}` });
    steine.push(k);
    k.style.position = "absolute";
    k.style.left = "0px";
    k.style.top = "0px";
    k.addEventListener("click", () => {
      k.classList.toggle("faehrt");
      log.merke("CLICK", `obj${i}`);
    });
    let zieht = false, griff = null;
    k.addEventListener("pointerdown", (ev) => {
      const kasten = feld.getBoundingClientRect(), eigen = k.getBoundingClientRect();
      griff = { dx: ev.clientX - eigen.left, dy: ev.clientY - eigen.top, kasten,
        x: ev.clientX, y: ev.clientY };
      zieht = false;
      try { k.setPointerCapture(ev.pointerId); } catch { /* geht auch ohne */ }
    });
    k.addEventListener("pointermove", (ev) => {
      if (!griff) return;
      if (!zieht) {
        // Erst ab ein paar Pixeln ist es ein Zug. Sonst wird jedes Zittern
        // beim Antippen zum Verschieben, und der Tipp geht verloren.
        if (Math.hypot(ev.clientX - griff.x, ev.clientY - griff.y) <= 6) return;
        zieht = true;
        log.merke("DRAG", `obj${i}`);
      }
      const x = ev.clientX - griff.dx - griff.kasten.left;
      const y = ev.clientY - griff.dy - griff.kasten.top;
      k.style.left = `${Math.max(0, Math.min(griff.kasten.width - 34, x))}px`;
      k.style.top = `${Math.max(0, Math.min(griff.kasten.height - 34, y))}px`;
    });
    k.addEventListener("pointerup", (ev) => {
      if (zieht) { log.merke("DROP", `obj${i}`); ev.preventDefault(); }
      zieht = false; griff = null;
    });
    feld.appendChild(k);
  }

  const zahl = zahlfeld();
  zahl.setAttribute("aria-label", "Wie viele sind es?");
  horche(zahl, log, "feld");

  return {
    element: h("div", { class: "eingabe" }, [
      h("p", { class: "anleitung",
        text: "Du kannst die Objekte verschieben. Trage dann die Anzahl ein." }),
      feld,
      zahl,
    ]),
    lies: () => gelesen(zahl.value),
    setze: (antwort) => {
      zahl.value = deutsch(antwort);
      log.merke("ANSWER_CHANGE", null, "simulation");
    },
    fokus: () => zahl.focus(),
  };
}

const BAUER = {
  ENTER: e_enter,
  SELECT: e_select,
  CLICK_SEQUENCE: e_click_sequence,
  DRAG: e_drag,
  MANIPULATE: e_manipulate,
};
