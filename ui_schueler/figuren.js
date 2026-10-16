/* Bildliche Darstellungen als SVG.
 *
 * Gezeichnet wird ausschliesslich aus `representation.stimulus` - also aus
 * dem, was der Renderer durchreicht. Zwei Grundsaetze halten diese Datei
 * zusammen:
 *
 * §16/§17: Darstellung und Bedienform sind zwei Variablen. Hier steht nur
 * die Darstellung. Ob man die Teile eines Bruchstreifens anklicken kann,
 * entscheidet nicht diese Datei, sondern die Bedienform - deshalb markiert
 * `zeichne` nur, WAS anklickbar waere (data-teil, data-wert), und eingabe.js
 * entscheidet, OB.
 *
 * §116/§32: ein Vergleich darf nur eine Variable aendern. Ein symbolisches
 * Item bekommt deshalb KEIN Bild, auch kein hilfreiches. Wuerde die
 * Oberflaeche zu "Berechne 3/4 von 20" einen Bruchstreifen zeichnen, waere
 * das Item ikonisch - und der Vergleich mit seinem ikonischen Partner
 * verglichezwei gleiche Dinge. `zeichne` prueft das zuerst.
 *
 * §1: Was die Daten nicht sagen, wird nicht erfunden. Eine Anordnung
 * "UNDEFINED" wird als schlichtes Zeilenraster gezeichnet - weder in
 * Fuenfergruppen (das waere eine Struktur, die §9 als eigenes Merkmal
 * fuehrt) noch zufaellig gestreut (das waere UNORDERED).
 */

const NS = "http://www.w3.org/2000/svg";

/** Darstellungsmodi, in denen ein Bild zur Aufgabe gehoert.
 *
 * ACTION fehlt hier mit Absicht. Bei einer Handlungsaufgabe IST das Material
 * die Bedienung: "Lege genau 9 in das Feld" bringt seinen Vorrat mit, und
 * "Buendle so viele Fuenfer, wie du kannst" seine Wuerfel. Zeichnete diese
 * Datei daneben noch ein Bild derselben Dinge, laegen dreizehn Wuerfel
 * zweimal auf dem Schirm - einmal zum Ansehen, einmal zum Anfassen. Welche
 * das Kind zaehlt, waere dann nicht mehr erkennbar, und bei "Tippe genau
 * siebenmal auf den Kreis" waeren die sieben gemalten Punkte schlicht falsch.
 */
const BILDLICH = new Set(["IMAGE", "MIXED"]);

export function el(tag, attrs = {}, kinder = []) {
  const k = document.createElementNS(NS, tag);
  for (const [name, wert] of Object.entries(attrs)) {
    if (wert === null || wert === undefined) continue;
    k.setAttribute(name, String(wert));
  }
  for (const kind of [].concat(kinder)) {
    if (kind === null || kind === undefined) continue;
    k.appendChild(typeof kind === "string" ? document.createTextNode(kind) : kind);
  }
  return k;
}

function svg(breite, hoehe, kinder, klasse = "") {
  const s = el("svg", {
    viewBox: `0 0 ${breite} ${hoehe}`,
    class: ("figur " + klasse).trim(),
    role: "img",
    preserveAspectRatio: "xMidYMid meet",
  }, kinder);
  s.style.maxHeight = `${Math.min(hoehe, 320)}px`;
  return s;
}

function txt(x, y, inhalt, attrs = {}) {
  return el("text", {
    x, y, class: "fig-text", "text-anchor": "middle",
    "dominant-baseline": "middle", ...attrs,
  }, String(inhalt));
}

function zahl(wert) {
  if (typeof wert !== "number") return String(wert);
  return Number.isInteger(wert) ? String(wert)
    : String(wert).replace(".", ",");
}

/** Klassenname fuer ein benanntes Farbwort aus den Daten.
 *
 * Nennt eine Aufgabe eine Farbe ("Welche Farbe kommt wahrscheinlicher?"),
 * muss das Bild sie auch zeigen - ein rotes Feld in Blau zu zeichnen macht
 * die Frage unbeantwortbar. Umlaute werden umschrieben, damit "gruen" und
 * "grün" dieselbe Klasse treffen.
 */
function farbklasse(name) {
  const rein = String(name).toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue")
    .replace(/ß/g, "ss").replace(/[^a-z0-9]/g, "");
  return rein ? ` fig-kugel-${rein}` : "";
}

/** Deterministischer Zufall: dasselbe Item sieht immer gleich aus.
 *  Zwei Versuche an derselben Aufgabe duerfen sich nicht im Bild
 *  unterscheiden - das waere eine Variable, die niemand erfasst hat. */
function streuung(saat) {
  let s = saat * 9301 + 49297;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

/**
 * Ungeordnete, aber garantiert ueberlappungsfreie Plaetze.
 *
 * §9 fuehrt die Anordnung als Aufgabenmerkmal: ungeordnet ist schwerer zu
 * zaehlen als in einer Reihe, und genau das soll beobachtbar sein. Frei
 * gewuerfelte Punkte ueberlappen aber irgendwann, und zwei Punkte, die wie
 * einer aussehen, machen die Aufgabe unloesbar - der Fehler waere dann
 * einer der Oberflaeche und keine Beobachtung am Kind (§59).
 *
 * Deshalb ein verwackeltes Raster: die Plaetze liegen in gemischter
 * Reihenfolge auf einem groesseren Gitter und werden innerhalb ihrer Zelle
 * nur so weit verschoben, dass der Mindestabstand erhalten bleibt. Das
 * Ergebnis ist ungeordnet, ohne je zu verschmelzen.
 */
function streuplaetze(n, breite, abstand, durchmesser) {
  const spalten = Math.max(1, Math.floor(breite / abstand));
  const zeilen = Math.max(1, Math.ceil((n * 1.7) / spalten));
  const zellen = [];
  for (let r = 0; r < zeilen; r++) {
    for (let c = 0; c < spalten; c++) zellen.push([c, r]);
  }
  const wuerfel = streuung(n * 31 + 7);
  for (let i = zellen.length - 1; i > 0; i--) {
    const j = Math.floor(wuerfel() * (i + 1));
    [zellen[i], zellen[j]] = [zellen[j], zellen[i]];
  }
  const spiel = Math.max(0, abstand - durchmesser);
  return {
    hoehe: zeilen * abstand,
    plaetze: zellen.slice(0, n).map(([c, r]) => [
      c * abstand + abstand / 2 + (wuerfel() - 0.5) * spiel,
      r * abstand + abstand / 2 + (wuerfel() - 0.5) * spiel,
    ]),
  };
}

export { streuplaetze };

// ----------------------------------------------------------------- Einstieg

/**
 * @param {object} stimulus  representation.stimulus aus dem Renderer
 * @param {string} modus     representation.mode
 * @returns {SVGElement|null}
 */
export function zeichne(stimulus, modus) {
  if (!stimulus || !BILDLICH.has(modus)) return null;
  if (stimulus.figure) {
    const bauer = FIGUREN[stimulus.figure.type];
    return bauer ? bauer(stimulus.figure, stimulus) : unbekannt(stimulus.figure.type);
  }
  for (const [passt, bauer] of ALTFORMEN) {
    if (passt(stimulus)) return bauer(stimulus);
  }
  return null;
}

function unbekannt(typ) {
  return svg(320, 60, [
    el("rect", { x: 1, y: 1, width: 318, height: 58, rx: 6, class: "fig-rahmen" }),
    txt(160, 30, `Darstellung ${typ} ist nicht gezeichnet`, { class: "fig-text fig-leise" }),
  ]);
}

// =========================================================== Neue Figuren

const FIGUREN = {};

// --------------------------------------------------------------- Brueche

FIGUREN.FRACTION_BAR = (f) => {
  const n = f.parts, b = 360, h = 56, tb = b / n;
  const teile = [];
  for (let i = 0; i < n; i++) {
    teile.push(el("rect", {
      x: 20 + i * tb, y: 30, width: tb, height: h, rx: 2,
      class: "fig-teil" + (i < (f.shaded || 0) ? " fig-gefuellt" : ""),
      "data-teil": i, tabindex: f.selectable ? 0 : null,
      role: f.selectable ? "button" : null,
      "aria-label": f.selectable ? `Teil ${i + 1} von ${n}` : null,
    }));
  }
  const kinder = [...teile];
  if (f.whole_label) {
    kinder.push(el("line", { x1: 20, y1: 98, x2: 20 + b, y2: 98, class: "fig-mass" }));
    kinder.push(el("line", { x1: 20, y1: 92, x2: 20, y2: 104, class: "fig-mass" }));
    kinder.push(el("line", { x1: 20 + b, y1: 92, x2: 20 + b, y2: 104, class: "fig-mass" }));
    kinder.push(txt(20 + b / 2, 116, `das Ganze: ${f.whole_label}`));
  }
  return svg(400, f.whole_label ? 132 : 100, kinder,
    f.selectable ? "figur-klickbar" : "");
};

FIGUREN.FRACTION_BARS = (f) => {
  const kinder = [];
  f.bars.forEach((bar, reihe) => {
    const y = 16 + reihe * 56, tb = 340 / bar.parts;
    for (let i = 0; i < bar.parts; i++) {
      kinder.push(el("rect", {
        x: 30 + i * tb, y, width: tb, height: 40, rx: 2,
        class: "fig-teil" + (i < bar.shaded ? " fig-gefuellt" : ""),
      }));
    }
    kinder.push(txt(16, y + 20, `${bar.shaded}/${bar.parts}`,
      { "text-anchor": "end", x: 24 }));
  });
  return svg(400, 16 + f.bars.length * 56, kinder);
};

/** Flaechenmodell der Bruchmultiplikation: zwei Faerbungen, der Schnitt zaehlt. */
FIGUREN.FRACTION_GRID = (f) => {
  const b = 300, h = 220, sb = b / f.cols, sh = h / f.rows, kinder = [];
  for (let c = 0; c < f.cols; c++) {
    for (let r = 0; r < f.rows; r++) {
      const inSpalte = c < f.cols_shaded, inZeile = r < f.rows_shaded;
      kinder.push(el("rect", {
        x: 50 + c * sb, y: 10 + r * sh, width: sb, height: sh,
        class: "fig-teil" + (inSpalte && inZeile ? " fig-gefuellt"
          : (inSpalte || inZeile ? " fig-halb" : "")),
      }));
    }
  }
  kinder.push(txt(50 + (f.cols_shaded * sb) / 2, h + 26,
    `${f.cols_shaded}/${f.cols}`));
  kinder.push(el("text", {
    x: 34, y: 10 + (f.rows_shaded * sh) / 2, class: "fig-text",
    "text-anchor": "end", "dominant-baseline": "middle",
  }, `${f.rows_shaded}/${f.rows}`));
  return svg(400, h + 40, kinder);
};

// --------------------------------------------------------- Zahlenstrahl

FIGUREN.NUMBER_LINE = (f) => {
  const links = 36, rechts = 376, y = 70;
  const von = f.from, bis = f.to, schritt = f.step || 1;
  const px = (w) => links + ((w - von) / (bis - von)) * (rechts - links);
  const kinder = [
    el("line", { x1: links - 10, y1: y, x2: rechts + 10, y2: y, class: "fig-achse" }),
    el("polygon", {
      points: `${rechts + 10},${y} ${rechts + 2},${y - 5} ${rechts + 2},${y + 5}`,
      class: "fig-achse-spitze",
    }),
  ];
  const anzahl = Math.round((bis - von) / schritt);
  const jedes = f.labels_every || (anzahl > 16 ? Math.ceil(anzahl / 10) : 1);
  for (let i = 0; i <= anzahl; i++) {
    const wert = Math.round((von + i * schritt) * 1e6) / 1e6;
    const gross = i % jedes === 0;
    kinder.push(el("line", {
      x1: px(wert), y1: y - (gross ? 9 : 5), x2: px(wert), y2: y + (gross ? 9 : 5),
      class: "fig-teilstrich",
    }));
    if (gross) kinder.push(txt(px(wert), y + 24, zahl(wert)));
    if (f.place) {
      kinder.push(el("circle", {
        cx: px(wert), cy: y, r: 11, class: "fig-ziel", "data-wert": wert,
        tabindex: 0, role: "button", "aria-label": `Marke auf ${zahl(wert)}`,
      }));
    }
  }
  for (const m of f.marks || []) {
    const wert = typeof m === "object" ? m.at : m;
    kinder.push(el("polygon", {
      points: `${px(wert)},${y - 3} ${px(wert) - 7},${y - 18} ${px(wert) + 7},${y - 18}`,
      class: "fig-marke",
    }));
    if (m && m.label) kinder.push(txt(px(wert), y - 28, m.label));
  }
  if (f.jump) {
    const a = px(f.jump.start), e = px(f.jump.start + f.jump.delta);
    kinder.push(el("path", {
      d: `M ${a} ${y - 6} Q ${(a + e) / 2} ${y - 48} ${e} ${y - 6}`,
      class: "fig-pfeil",
    }));
    kinder.push(el("polygon", {
      points: `${e},${y - 4} ${e - (e > a ? 9 : -9)},${y - 14} ${e - (e > a ? 1 : -1)},${y - 16}`,
      class: "fig-marke",
    }));
    kinder.push(txt((a + e) / 2, y - 52,
      `${f.jump.delta > 0 ? "+" : ""}${zahl(f.jump.delta)}`));
    kinder.push(el("circle", { cx: a, cy: y, r: 5, class: "fig-punkt" }));
  }
  return svg(400, 112, kinder, f.place ? "figur-klickbar" : "");
};

// ------------------------------------------------------- Stellenwerttafel

function stellenwerttafel(spalten, ziffern, hervor) {
  const n = spalten.length, sb = Math.min(76, 320 / n), x0 = 200 - (n * sb) / 2;
  const kinder = [];
  spalten.forEach((label, i) => {
    kinder.push(el("rect", {
      x: x0 + i * sb, y: 14, width: sb, height: 34, class: "fig-kopfzelle",
    }));
    kinder.push(txt(x0 + i * sb + sb / 2, 31, label, { class: "fig-text fig-leise" }));
    kinder.push(el("rect", {
      x: x0 + i * sb, y: 48, width: sb, height: 46,
      class: "fig-zelle" + (i === hervor ? " fig-hervor" : ""),
    }));
    const z = ziffern[i];
    kinder.push(txt(x0 + i * sb + sb / 2, 72,
      z === null || z === undefined ? "" : z,
      { class: "fig-zahl" }));
  });
  return svg(400, 108, kinder);
}

FIGUREN.PLACE_VALUE_CHART = (f) => {
  const spalten = [...f.columns];
  const ziffern = [...f.digits];
  // Das Komma steht zwischen zwei Spalten, nicht in einer. Es wird als
  // eigene, schmale Spalte eingezogen, damit die Stellen ihre Breite behalten.
  if (f.decimal_after !== undefined && f.decimal_after !== null) {
    spalten.splice(f.decimal_after + 1, 0, "");
    ziffern.splice(f.decimal_after + 1, 0, ",");
  }
  let hervor = f.highlight;
  if (hervor !== undefined && f.decimal_after !== undefined
      && hervor > f.decimal_after) hervor += 1;
  return stellenwerttafel(spalten, ziffern, hervor);
};

// ----------------------------------------------------------------- Prozent

FIGUREN.PERCENT_BAR = (f) => {
  const links = 30, breite = 340, y = 34, h = 44;
  const anteil = (f.percent / 100) * breite;
  const kinder = [
    el("rect", { x: links, y, width: breite, height: h, rx: 3, class: "fig-teil" }),
    el("rect", { x: links, y, width: anteil, height: h, rx: 3, class: "fig-gefuellt" }),
    el("rect", { x: links, y, width: breite, height: h, rx: 3, class: "fig-rahmen" }),
  ];
  if (f.show_scale !== false) {
    for (let p = 0; p <= 100; p += 10) {
      const x = links + (p / 100) * breite;
      kinder.push(el("line", { x1: x, y1: y + h, x2: x, y2: y + h + (p % 50 ? 5 : 9),
        class: "fig-teilstrich" }));
      if (p % 50 === 0) kinder.push(txt(x, y + h + 22, `${p} %`));
    }
  }
  if (f.whole_label) {
    kinder.push(txt(links + breite / 2, 16, `das Ganze: ${f.whole_label}`));
  }
  return svg(400, 112, kinder);
};

// ------------------------------------------------------------ Quadratgitter

FIGUREN.SQUARE_GRID = (f) => {
  const seite = f.side || Math.round(Math.sqrt(f.area));
  const zelle = Math.min(26, 220 / seite), gesamt = seite * zelle;
  const x0 = 200 - gesamt / 2, y0 = 14, kinder = [];
  for (let r = 0; r < seite; r++) {
    for (let c = 0; c < seite; c++) {
      kinder.push(el("rect", {
        x: x0 + c * zelle, y: y0 + r * zelle, width: zelle, height: zelle,
        class: "fig-zelle-klein",
      }));
    }
  }
  if (f.ask === "SIDE") {
    kinder.push(el("line", { x1: x0, y1: y0 + gesamt + 12, x2: x0 + gesamt,
      y2: y0 + gesamt + 12, class: "fig-mass" }));
    kinder.push(txt(x0 + gesamt / 2, y0 + gesamt + 26, "?"));
  }
  return svg(400, y0 + gesamt + 36, kinder);
};

FIGUREN.GRID_RECTANGLE = (f) => {
  const zelle = Math.min(30, 300 / f.w, 160 / f.h);
  const b = f.w * zelle, h = f.h * zelle, x0 = 200 - b / 2, y0 = 18, kinder = [];
  for (let r = 0; r < f.h; r++) {
    for (let c = 0; c < f.w; c++) {
      kinder.push(el("rect", {
        x: x0 + c * zelle, y: y0 + r * zelle, width: zelle, height: zelle,
        class: "fig-zelle-klein",
      }));
    }
  }
  kinder.push(el("rect", { x: x0, y: y0, width: b, height: h, class: "fig-rahmen" }));
  if (f.label_sides) {
    kinder.push(txt(x0 + b / 2, y0 + h + 18, `${f.w} ${f.unit || ""}`.trim()));
    kinder.push(txt(x0 - 20, y0 + h / 2, `${f.h} ${f.unit || ""}`.trim()));
  }
  return svg(400, y0 + h + 32, kinder);
};

// ------------------------------------------------------------- Wertetabelle

FIGUREN.VALUE_TABLE = (f) => {
  const spalten = f.head.length, zeilen = f.rows.length;
  const sb = Math.min(150, 340 / spalten), zh = 34;
  const x0 = 200 - (spalten * sb) / 2, y0 = 12, kinder = [];
  f.head.forEach((kopf, c) => {
    kinder.push(el("rect", { x: x0 + c * sb, y: y0, width: sb, height: zh,
      class: "fig-kopfzelle" }));
    kinder.push(txt(x0 + c * sb + sb / 2, y0 + zh / 2, kopf,
      { class: "fig-text fig-leise" }));
  });
  f.rows.forEach((zeile, r) => {
    zeile.forEach((wert, c) => {
      const gefragt = r === f.ask_row && c === f.ask_col;
      kinder.push(el("rect", {
        x: x0 + c * sb, y: y0 + zh * (r + 1), width: sb, height: zh,
        class: "fig-zelle" + (gefragt ? " fig-hervor" : ""),
      }));
      kinder.push(txt(x0 + c * sb + sb / 2, y0 + zh * (r + 1) + zh / 2,
        wert === null || wert === undefined ? "?" : zahl(wert)));
    });
  });
  return svg(400, y0 + zh * (zeilen + 1) + 12, kinder);
};

// ------------------------------------------------------------------ Algebra

FIGUREN.ALGEBRA_RECT = (f) => {
  const b = 220, h = 90, x0 = 200 - b / 2, y0 = 24;
  return svg(400, 150, [
    el("rect", { x: x0, y: y0, width: b, height: h, rx: 3, class: "fig-teil" }),
    el("rect", { x: x0, y: y0, width: b, height: h, rx: 3, class: "fig-rahmen" }),
    txt(x0 + b / 2, y0 + h + 20, String(f.width)),
    el("text", { x: x0 - 16, y: y0 + h / 2, class: "fig-text",
      "text-anchor": "end", "dominant-baseline": "middle" }, String(f.height)),
  ]);
};

FIGUREN.ALGEBRA_TILES = (f) => {
  const kinder = [];
  let x = 24;
  f.groups.forEach((gruppe, gi) => {
    for (let i = 0; i < gruppe.count; i++) {
      kinder.push(el("rect", {
        x, y: 26, width: 24, height: 60, rx: 3,
        class: "fig-teil" + (gi % 2 ? " fig-halb" : " fig-gefuellt"),
      }));
      kinder.push(txt(x + 12, 56, gruppe.label, { class: "fig-text fig-auf-flaeche" }));
      x += 30;
    }
    if (gi < f.groups.length - 1) {
      kinder.push(txt(x + 10, 56, "+", { class: "fig-zahl" }));
      x += 28;
    }
  });
  return svg(Math.max(400, x + 24), 112, kinder);
};

FIGUREN.BALANCE = (f) => {
  const kinder = [
    el("line", { x1: 60, y1: 120, x2: 340, y2: 120, class: "fig-achse" }),
    el("polygon", { points: "200,120 182,160 218,160", class: "fig-stuetze" }),
    el("line", { x1: 160, y1: 56, x2: 160, y2: 120, class: "fig-mass" }),
    el("line", { x1: 240, y1: 56, x2: 240, y2: 120, class: "fig-mass" }),
  ];
  const schale = (mitte, inhalt) => {
    kinder.push(el("path", {
      d: `M ${mitte - 58} 56 L ${mitte + 58} 56 L ${mitte + 44} 86 L ${mitte - 44} 86 Z`,
      class: "fig-schale",
    }));
    let x = mitte - inhalt.length * 13 + 13;
    for (const stueck of inhalt) {
      if (stueck === "x") {
        kinder.push(el("rect", { x: x - 11, y: 20, width: 22, height: 32, rx: 3,
          class: "fig-gefuellt" }));
        kinder.push(txt(x, 36, "x", { class: "fig-text fig-auf-flaeche" }));
      } else {
        kinder.push(el("circle", { cx: x, cy: 42, r: 9, class: "fig-teil" }));
        kinder.push(el("circle", { cx: x, cy: 42, r: 9, class: "fig-rahmen" }));
      }
      x += 26;
    }
  };
  const seite = (s) => [...Array(s.x || 0).fill("x"), ...Array(s.units || 0).fill("1")];
  schale(160, seite(f.left));
  schale(240, seite(f.right));
  return svg(400, 176, kinder);
};

// ----------------------------------------------------------- Koordinaten

FIGUREN.COORDINATE_SYSTEM = (f) => {
  const B = 380, H = 280, rand = 26;
  const xmin = f.xmin, xmax = f.xmax, ymin = f.ymin, ymax = f.ymax;
  const px = (x) => rand + ((x - xmin) / (xmax - xmin)) * (B - 2 * rand);
  const py = (y) => H - rand - ((y - ymin) / (ymax - ymin)) * (H - 2 * rand);
  const kinder = [];
  for (let x = Math.ceil(xmin); x <= xmax; x++) {
    kinder.push(el("line", { x1: px(x), y1: py(ymin), x2: px(x), y2: py(ymax),
      class: "fig-gitter" }));
  }
  for (let y = Math.ceil(ymin); y <= ymax; y++) {
    kinder.push(el("line", { x1: px(xmin), y1: py(y), x2: px(xmax), y2: py(y),
      class: "fig-gitter" }));
  }
  kinder.push(el("line", { x1: px(xmin), y1: py(0), x2: px(xmax), y2: py(0),
    class: "fig-achse" }));
  kinder.push(el("line", { x1: px(0), y1: py(ymin), x2: px(0), y2: py(ymax),
    class: "fig-achse" }));
  for (let x = Math.ceil(xmin); x <= xmax; x++) {
    if (x !== 0 && (xmax - xmin <= 12 || x % 2 === 0)) {
      kinder.push(txt(px(x), py(0) + 13, x, { class: "fig-text fig-klein" }));
    }
  }
  for (let y = Math.ceil(ymin); y <= ymax; y++) {
    if (y !== 0 && (ymax - ymin <= 12 || y % 2 === 0)) {
      kinder.push(txt(px(0) - 12, py(y), y, { class: "fig-text fig-klein" }));
    }
  }
  for (const g of f.lines || []) {
    kinder.push(el("line", {
      x1: px(xmin), y1: py(g.m * xmin + g.b), x2: px(xmax), y2: py(g.m * xmax + g.b),
      class: "fig-graph",
    }));
  }
  for (const p of f.parabolas || []) {
    const punkte = [];
    for (let i = 0; i <= 80; i++) {
      const x = xmin + (i / 80) * (xmax - xmin);
      const y = p.a * x * x + (p.b || 0) * x + (p.c || 0);
      if (y >= ymin - 1 && y <= ymax + 1) punkte.push(`${px(x)},${py(y)}`);
    }
    kinder.push(el("polyline", { points: punkte.join(" "), class: "fig-graph" }));
  }
  for (const m of f.markers || []) {
    let y = m.y;
    if (y === undefined && f.parabolas && f.parabolas[0]) {
      const p = f.parabolas[0];
      y = p.a * m.x * m.x + (p.b || 0) * m.x + (p.c || 0);
    }
    kinder.push(el("line", { x1: px(m.x), y1: py(0), x2: px(m.x), y2: py(y),
      class: "fig-mass-gestrichelt" }));
    kinder.push(el("circle", { cx: px(m.x), cy: py(y), r: 5, class: "fig-punkt" }));
    kinder.push(txt(px(m.x), py(0) + 15, `x = ${zahl(m.x)}`,
      { class: "fig-text fig-klein" }));
  }
  return svg(B, H, kinder);
};

// -------------------------------------------------------------- Messbecher

FIGUREN.JUG = (f) => {
  const x0 = 150, b = 100, y0 = 14, h = 200;
  const anteil = f.filled / f.capacity;
  const kinder = [
    el("rect", { x: x0, y: y0 + h * (1 - anteil), width: b, height: h * anteil,
      class: "fig-fluessigkeit" }),
    el("path", { d: `M ${x0} ${y0} L ${x0} ${y0 + h} L ${x0 + b} ${y0 + h} L ${x0 + b} ${y0}`,
      class: "fig-rahmen" }),
  ];
  const schritt = f.step || f.capacity / 8;
  for (let v = 0; v <= f.capacity + 1e-9; v += schritt) {
    const y = y0 + h * (1 - v / f.capacity);
    const lang = Math.abs((v / schritt) % 2) < 1e-9;
    kinder.push(el("line", { x1: x0, y1: y, x2: x0 + (lang ? 22 : 12), y2: y,
      class: "fig-teilstrich" }));
    if (lang) {
      kinder.push(el("text", { x: x0 - 8, y, class: "fig-text fig-klein",
        "text-anchor": "end", "dominant-baseline": "middle" },
        `${zahl(Math.round(v * 1000) / 1000)}`));
    }
  }
  kinder.push(txt(x0 + b + 34, y0 + h + 4, f.unit, { class: "fig-text fig-leise" }));
  if (f.fill_label) {
    const y = y0 + h * (1 - anteil);
    kinder.push(el("line", { x1: x0 + b, y1: y, x2: x0 + b + 34, y2: y,
      class: "fig-mass" }));
    kinder.push(el("text", { x: x0 + b + 38, y, class: "fig-text",
      "text-anchor": "start", "dominant-baseline": "middle" }, f.fill_label));
  }
  return svg(400, y0 + h + 24, kinder);
};

// ----------------------------------------------------------------- Koerper

FIGUREN.CUBOID = (f) => {
  const e = Math.min(26, 190 / (f.l + f.w * 0.5), 120 / (f.h + f.w * 0.4));
  const tiefe = e * 0.5;
  const b = f.l * e, ho = f.h * e, t = f.w * tiefe;
  const x0 = 200 - (b + t) / 2, y0 = 26 + t;
  const kinder = [
    el("polygon", { points: `${x0},${y0} ${x0 + t},${y0 - t} ${x0 + t + b},${y0 - t} ${x0 + b},${y0}`,
      class: "fig-flaeche-oben" }),
    el("polygon", { points: `${x0 + b},${y0} ${x0 + t + b},${y0 - t} ${x0 + t + b},${y0 - t + ho} ${x0 + b},${y0 + ho}`,
      class: "fig-flaeche-seite" }),
    el("rect", { x: x0, y: y0, width: b, height: ho, class: "fig-flaeche-vorn" }),
  ];
  if (f.grid) {
    for (let i = 1; i < f.l; i++) {
      kinder.push(el("line", { x1: x0 + i * e, y1: y0, x2: x0 + i * e, y2: y0 + ho,
        class: "fig-gitter-stark" }));
    }
    for (let i = 1; i < f.h; i++) {
      kinder.push(el("line", { x1: x0, y1: y0 + i * e, x2: x0 + b, y2: y0 + i * e,
        class: "fig-gitter-stark" }));
    }
    for (let i = 1; i < f.w; i++) {
      kinder.push(el("line", {
        x1: x0 + i * tiefe, y1: y0 - i * tiefe, x2: x0 + b + i * tiefe, y2: y0 - i * tiefe,
        class: "fig-gitter-stark",
      }));
    }
  }
  kinder.push(el("polygon", {
    points: `${x0},${y0} ${x0 + t},${y0 - t} ${x0 + t + b},${y0 - t} ${x0 + t + b},${y0 - t + ho} ${x0 + b},${y0 + ho} ${x0},${y0 + ho}`,
    class: "fig-rahmen",
  }));
  if (f.label_edges) {
    const u = f.unit || "";
    kinder.push(txt(x0 + b / 2, y0 + ho + 18, `${f.l} ${u}`.trim()));
    kinder.push(el("text", { x: x0 - 10, y: y0 + ho / 2, class: "fig-text",
      "text-anchor": "end", "dominant-baseline": "middle" }, `${f.h} ${u}`.trim()));
    kinder.push(txt(x0 + b + t / 2 + 22, y0 - t / 2 - 6, `${f.w} ${u}`.trim()));
  }
  return svg(400, y0 + ho + 32, kinder);
};

// ------------------------------------------------------------------ Winkel

FIGUREN.ANGLE = (f) => {
  const cx = 110, cy = 150, r = 130;
  const rad = (f.degrees * Math.PI) / 180;
  const ex = cx + r * Math.cos(-rad), ey = cy + r * Math.sin(-rad);
  const gross = f.degrees > 180 ? 1 : 0;
  const kinder = [
    el("line", { x1: cx, y1: cy, x2: cx + r, y2: cy, class: "fig-schenkel" }),
    el("line", { x1: cx, y1: cy, x2: ex, y2: ey, class: "fig-schenkel" }),
    el("path", {
      d: `M ${cx + 40} ${cy} A 40 40 0 ${gross} 0 ${cx + 40 * Math.cos(-rad)} ${cy + 40 * Math.sin(-rad)}`,
      class: "fig-bogen",
    }),
  ];
  if (f.show_arc !== false) {
    kinder.push(txt(cx + 62 * Math.cos(-rad / 2), cy + 62 * Math.sin(-rad / 2), "?"));
  }
  return svg(400, 190, kinder);
};

FIGUREN.TRIANGLE_ANGLES = (f) => {
  const A = [50, 170], B = [330, 170];
  // Der dritte Punkt folgt aus den beiden gegebenen Winkeln - gezeichnet wird
  // damit genau das Dreieck, von dem die Aufgabe spricht.
  const a = ((f.angles[0] || 60) * Math.PI) / 180;
  const b = ((f.angles[1] || 60) * Math.PI) / 180;
  const laenge = (B[0] - A[0]) * Math.sin(b) / Math.sin(Math.PI - a - b);
  const C = [A[0] + laenge * Math.cos(a), A[1] - laenge * Math.sin(a)];
  const kinder = [
    el("polygon", { points: `${A[0]},${A[1]} ${B[0]},${B[1]} ${C[0]},${C[1]}`,
      class: "fig-koerper" }),
  ];
  const ecken = [A, B, C];
  f.angles.forEach((g, i) => {
    const [x, y] = ecken[i];
    const zx = (ecken[(i + 1) % 3][0] + ecken[(i + 2) % 3][0]) / 2;
    const zy = (ecken[(i + 1) % 3][1] + ecken[(i + 2) % 3][1]) / 2;
    const d = Math.hypot(zx - x, zy - y) || 1;
    kinder.push(txt(x + ((zx - x) / d) * 44, y + ((zy - y) / d) * 44,
      g === null || g === undefined ? "?" : `${g}°`));
  });
  return svg(400, 200, kinder);
};

FIGUREN.RIGHT_TRIANGLE = (f) => {
  const a = f.a, b = f.b, c = f.c;
  // Seitenverhaeltnis aus den bekannten Angaben; fehlt eine, wird sie ueber
  // den Satz des Pythagoras ergaenzt - nur fuers Bild, nicht als Loesung.
  const ka = a ?? (c && b ? Math.sqrt(Math.max(c * c - b * b, 1)) : 3);
  const kb = b ?? (c && a ? Math.sqrt(Math.max(c * c - a * a, 1)) : 4);
  const mass = Math.min(230 / kb, 150 / ka);
  const A = [70, 180], B = [70 + kb * mass, 180], C = [70, 180 - ka * mass];
  const kinder = [
    el("polygon", { points: `${A[0]},${A[1]} ${B[0]},${B[1]} ${C[0]},${C[1]}`,
      class: "fig-koerper" }),
    el("polyline", { points: `${A[0] + 14},${A[1]} ${A[0] + 14},${A[1] - 14} ${A[0]},${A[1] - 14}`,
      class: "fig-schenkel" }),
  ];
  const u = f.unit ? ` ${f.unit}` : "";
  const beschriftung = (p1, p2, wert, standard, dx, dy) => {
    const t = wert === null || wert === undefined ? "?" : `${zahl(wert)}${u}`;
    kinder.push(txt((p1[0] + p2[0]) / 2 + dx, (p1[1] + p2[1]) / 2 + dy,
      wert === undefined && standard ? standard : t));
  };
  if (f.labels) {
    beschriftung(A, C, f.labels[0], f.labels[0], -18, 0);
    beschriftung(A, B, f.labels[1], f.labels[1], 0, 20);
    beschriftung(B, C, f.labels[2], f.labels[2], 22, -8);
  } else {
    beschriftung(A, C, a, null, -22, 0);
    beschriftung(A, B, b, null, 0, 20);
    beschriftung(B, C, c, null, 26, -10);
  }
  if (f.show_squares) {
    kinder.push(el("rect", { x: A[0] - ka * mass, y: 180 - ka * mass,
      width: ka * mass, height: ka * mass, class: "fig-quadrat" }));
    kinder.push(el("rect", { x: A[0], y: 180, width: kb * mass, height: kb * mass,
      class: "fig-quadrat" }));
  }
  if (f.mark_angle) {
    const ecke = f.angle_at === "A" ? B : A;
    const ziel = f.angle_at === "A" ? C : B;
    kinder.push(el("path", {
      d: `M ${ecke[0] + (ziel[0] > ecke[0] ? 26 : -26)} ${ecke[1]}`
         + ` A 26 26 0 0 ${ziel[0] > ecke[0] ? 0 : 1} `
         + `${ecke[0] + (C[0] - ecke[0]) * 0.16} ${ecke[1] + (C[1] - ecke[1]) * 0.16}`,
      class: "fig-bogen",
    }));
    kinder.push(txt(ecke[0] + (ziel[0] > ecke[0] ? 40 : -40), ecke[1] - 14, "α"));
  }
  const hoehe = f.show_squares ? 180 + kb * mass + 16 : 206;
  return svg(400, hoehe, kinder);
};

FIGUREN.TRIANGLE_PAIR = (f) => {
  const mass = 16;
  const bau = (x0, seiten, klein) => {
    const [a, b] = seiten;
    const ka = a * mass * (klein ? 1 : 1), kb = (b ?? a * 1.33) * mass;
    const A = [x0, 180], B = [x0 + kb, 180], C = [x0, 180 - ka];
    const kinder = [el("polygon", {
      points: `${A[0]},${A[1]} ${B[0]},${B[1]} ${C[0]},${C[1]}`, class: "fig-koerper" })];
    const u = f.unit ? ` ${f.unit}` : "";
    kinder.push(txt(x0 - 16, 180 - ka / 2, `${zahl(a)}${u}`));
    kinder.push(txt(x0 + kb / 2, 196,
      b === null || b === undefined ? "?" : `${zahl(b)}${u}`));
    return kinder;
  };
  return svg(400, 212, [...bau(40, f.small, true), ...bau(200, f.big, false)]);
};

FIGUREN.CIRCLE = (f) => {
  const cx = 200, cy = 110, r = 86;
  const kinder = [
    el("circle", { cx, cy, r, class: f.fill ? "fig-koerper" : "fig-rahmen-kreis" }),
  ];
  const u = f.unit ? ` ${f.unit}` : "";
  if (f.show_radius) {
    kinder.push(el("line", { x1: cx, y1: cy, x2: cx + r, y2: cy, class: "fig-mass" }));
    kinder.push(el("circle", { cx, cy, r: 3, class: "fig-punkt" }));
    kinder.push(txt(cx + r / 2, cy - 12, `r = ${zahl(f.r)}${u}`));
  }
  if (f.show_diameter) {
    kinder.push(el("line", { x1: cx - r, y1: cy + 26, x2: cx + r, y2: cy + 26,
      class: "fig-mass-gestrichelt" }));
    kinder.push(txt(cx, cy + 42, "d = ?"));
  }
  return svg(400, 216, kinder);
};

FIGUREN.SCALE_BAR = (f) => {
  const links = 90, laenge = 220;
  return svg(400, 110, [
    el("line", { x1: links, y1: 50, x2: links + laenge, y2: 50, class: "fig-schenkel" }),
    el("line", { x1: links, y1: 40, x2: links, y2: 60, class: "fig-schenkel" }),
    el("line", { x1: links + laenge, y1: 40, x2: links + laenge, y2: 60,
      class: "fig-schenkel" }),
    txt(links + laenge / 2, 26, `${zahl(f.length_cm)} cm auf der Karte`),
    txt(200, 84, `Maßstab ${f.scale}`, { class: "fig-text fig-leise" }),
  ]);
};

// --------------------------------------------------------------- Diagramme

FIGUREN.BAR_CHART = (f) => {
  const links = 46, unten = 190, breite = 320, hoehe = 150;
  const max = Math.max(...f.bars.map((b) => b.value));
  const schritt = f.step || (max <= 10 ? 1 : Math.ceil(max / 8));
  const obergrenze = Math.ceil(max / schritt) * schritt;
  const sb = breite / f.bars.length, kinder = [];
  for (let v = 0; v <= obergrenze; v += schritt) {
    const y = unten - (v / obergrenze) * hoehe;
    kinder.push(el("line", { x1: links, y1: y, x2: links + breite, y2: y,
      class: "fig-gitter" }));
    kinder.push(el("text", { x: links - 8, y, class: "fig-text fig-klein",
      "text-anchor": "end", "dominant-baseline": "middle" }, String(v)));
  }
  f.bars.forEach((bar, i) => {
    const h = (bar.value / obergrenze) * hoehe;
    kinder.push(el("rect", { x: links + i * sb + sb * 0.2, y: unten - h,
      width: sb * 0.6, height: h, class: "fig-gefuellt" }));
    kinder.push(txt(links + i * sb + sb / 2, unten + 16, bar.label));
  });
  kinder.push(el("line", { x1: links, y1: unten, x2: links + breite, y2: unten,
    class: "fig-achse" }));
  kinder.push(el("line", { x1: links, y1: unten, x2: links, y2: unten - hoehe - 10,
    class: "fig-achse" }));
  if (f.axis_y) {
    kinder.push(txt(links + 4, unten - hoehe - 20, f.axis_y,
      { "text-anchor": "start", class: "fig-text fig-leise" }));
  }
  return svg(400, 212, kinder);
};

function bogen(cx, cy, r, von, bis) {
  const p = (w) => [cx + r * Math.sin(w), cy - r * Math.cos(w)];
  const [x1, y1] = p(von), [x2, y2] = p(bis);
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${bis - von > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`;
}

FIGUREN.PIE_CHART = (f) => {
  const cx = 130, cy = 116, r = 96;
  let winkel = 0;
  const kinder = [];
  f.sectors.forEach((s, i) => {
    const bis = winkel + (s.percent / 100) * 2 * Math.PI;
    kinder.push(el("path", { d: bogen(cx, cy, r, winkel, bis),
      class: `fig-sektor fig-sektor-${i % 4}` }));
    winkel = bis;
  });
  f.sectors.forEach((s, i) => {
    const y = 40 + i * 26;
    kinder.push(el("rect", { x: 254, y: y - 9, width: 16, height: 16, rx: 3,
      class: `fig-sektor fig-sektor-${i % 4}` }));
    kinder.push(el("text", { x: 278, y, class: "fig-text",
      "dominant-baseline": "middle" }, `${s.label} – ${s.percent} %`));
  });
  if (f.total_label) {
    kinder.push(txt(cx, cy + r + 22, `insgesamt ${f.total_label}`,
      { class: "fig-text fig-leise" }));
  }
  return svg(400, 244, kinder);
};

FIGUREN.DOT_PLOT = (f) => {
  const von = f.from, bis = f.to, links = 40, breite = 320, unten = 150;
  const px = (w) => links + ((w - von) / (bis - von)) * breite;
  const zaehler = {}, kinder = [];
  for (const w of f.values) {
    zaehler[w] = (zaehler[w] || 0) + 1;
    kinder.push(el("circle", { cx: px(w), cy: unten - 14 - (zaehler[w] - 1) * 22,
      r: 8, class: "fig-gefuellt" }));
  }
  kinder.push(el("line", { x1: links - 10, y1: unten, x2: links + breite + 10, y2: unten,
    class: "fig-achse" }));
  for (let w = von; w <= bis; w++) {
    kinder.push(el("line", { x1: px(w), y1: unten - 4, x2: px(w), y2: unten + 4,
      class: "fig-teilstrich" }));
    kinder.push(txt(px(w), unten + 16, w, { class: "fig-text fig-klein" }));
  }
  return svg(400, 180, kinder);
};

// ------------------------------------------------------------ Zufall

FIGUREN.URN = (f) => {
  const kinder = [el("path", {
    d: "M 130 40 L 130 150 Q 130 176 160 176 L 240 176 Q 270 176 270 150 L 270 40",
    class: "fig-rahmen",
  })];
  const alle = [];
  for (const sorte of f.balls) {
    for (let i = 0; i < sorte.count; i++) alle.push(sorte.color);
  }
  const proReihe = 4;
  alle.forEach((farbe, i) => {
    const r = Math.floor(i / proReihe), c = i % proReihe;
    kinder.push(el("circle", {
      cx: 160 + c * 27, cy: 150 - r * 27, r: 11,
      class: "fig-kugel" + farbklasse(farbe),
    }));
  });
  f.balls.forEach((sorte, i) => {
    kinder.push(el("circle", { cx: 40, cy: 44 + i * 26, r: 8,
      class: "fig-kugel" + farbklasse(sorte.color) }));
    kinder.push(el("text", { x: 56, y: 44 + i * 26, class: "fig-text",
      "dominant-baseline": "middle" }, `${sorte.count}× ${sorte.color}`));
  });
  return svg(400, 196, kinder);
};

FIGUREN.SPINNER = (f) => {
  const cx = 200, cy = 112, r = 94, n = f.sectors, kinder = [];
  for (let i = 0; i < n; i++) {
    kinder.push(el("path", {
      d: bogen(cx, cy, r, (i / n) * 2 * Math.PI, ((i + 1) / n) * 2 * Math.PI),
      class: "fig-sektor " + (i < f.marked
        ? "fig-sektor-markiert" + farbklasse(f.color)
        : "fig-sektor-leer"),
    }));
  }
  kinder.push(el("circle", { cx, cy, r, class: "fig-rahmen-kreis" }));
  kinder.push(el("polygon", { points: `${cx},${cy - r - 6} ${cx - 8},${cy - r + 10} ${cx + 8},${cy - r + 10}`,
    class: "fig-marke" }));
  kinder.push(txt(cx, cy + r + 22,
    `${f.marked} von ${n} Feldern ${f.color || "markiert"}`,
    { class: "fig-text fig-leise" }));
  return svg(400, 240, kinder);
};

FIGUREN.TREE = (f) => {
  const stufen = f.stages || 1, zweige = f.branches, kinder = [];
  const xs = [40, 190, 340];
  const hervor = f.highlight_path || [];
  const zeichneStufe = (x, y, hoehe, stufe, pfad) => {
    if (stufe > stufen) return;
    zweige.forEach((zw, i) => {
      const zy = y - hoehe / 2 + (hoehe / (zweige.length - 1 || 1)) * i;
      const aktiv = hervor.length && hervor[stufe - 1] === zw.label
        && pfad.every((p, k) => p === hervor[k]);
      kinder.push(el("line", { x1: x, y1: y, x2: xs[stufe], y2: zy,
        class: "fig-ast" + (aktiv ? " fig-ast-aktiv" : "") }));
      kinder.push(txt((x + xs[stufe]) / 2, (y + zy) / 2 - 10,
        zw.p === null || zw.p === undefined ? "?" : zahl(zw.p),
        { class: "fig-text fig-klein" }));
      kinder.push(el("circle", { cx: xs[stufe], cy: zy, r: 13,
        class: "fig-knoten" + farbklasse(zw.label) }));
      kinder.push(txt(xs[stufe], zy, String(zw.label).slice(0, 1).toUpperCase(),
        { class: "fig-text fig-auf-flaeche fig-klein" }));
      zeichneStufe(xs[stufe], zy, hoehe / 2.1, stufe + 1, [...pfad, zw.label]);
    });
  };
  kinder.push(el("circle", { cx: xs[0], cy: 110, r: 8, class: "fig-punkt" }));
  zeichneStufe(xs[0], 110, 150, 1, []);
  return svg(400, 220, kinder);
};

// ===================================================== Altform (§42-57)

/** Punktmengen. §9 fuehrt die Anordnung als eigenes Aufgabenmerkmal. */
function punkte(st) {
  const n = st.objects ?? st.target_count ?? 0;
  const anordnung = st.arrangement || "UNDEFINED";
  const kinder = [];
  const form = (x, y, i) => {
    if (!st.heterogeneous) {
      return el("circle", { cx: x, cy: y, r: 11, class: "fig-objekt",
        "data-objekt": i });
    }
    // §44: verschiedene Gegenstaende. Die Form wechselt, die Anzahl nicht.
    if (i % 3 === 0) return el("circle", { cx: x, cy: y, r: 11, class: "fig-objekt", "data-objekt": i });
    if (i % 3 === 1) return el("rect", { x: x - 10, y: y - 10, width: 20, height: 20,
      rx: 3, class: "fig-objekt", "data-objekt": i });
    return el("polygon", { points: `${x},${y - 12} ${x - 11},${y + 9} ${x + 11},${y + 9}`,
      class: "fig-objekt", "data-objekt": i });
  };

  if (anordnung === "STRUCTURED" && st.structure) {
    const gruppen = String(st.structure).split("+").map(Number).filter((g) => g > 0);
    let i = 0, x = 40;
    for (const g of gruppen) {
      for (let k = 0; k < g; k++) {
        kinder.push(form(x + (k % 5) * 30, 50 + Math.floor(k / 5) * 32, i++));
      }
      x += Math.min(g, 5) * 30 + 28;
    }
    return svg(Math.max(360, x), 110, kinder);
  }
  if (anordnung === "ROW") {
    for (let i = 0; i < n; i++) kinder.push(form(34 + i * 28, 46, i));
    return svg(Math.max(360, 34 + n * 28), 92, kinder);
  }
  if (anordnung === "UNORDERED" || st.movable) {
    const { hoehe, plaetze } = streuplaetze(n, 340, 34, 26);
    plaetze.forEach(([x, y], i) => kinder.push(form(30 + x, 20 + y, i)));
    return svg(400, hoehe + 40, kinder);
  }
  // UNDEFINED: ein schlichtes Zeilenraster. Weder Fuenfergruppen (das waere
  // STRUCTURED) noch Streuung (das waere UNORDERED) - §1: was die Daten nicht
  // sagen, wird nicht gesetzt.
  const proReihe = Math.min(8, Math.max(4, Math.ceil(Math.sqrt(n))));
  for (let i = 0; i < n; i++) {
    kinder.push(form(40 + (i % proReihe) * 32, 34 + Math.floor(i / proReihe) * 32, i));
  }
  return svg(400, 34 + Math.ceil(n / proReihe) * 32 + 20, kinder);
}

/** Zehnerstangen, Hunderterplatten, Einerwuerfel. */
function basiszehn(st) {
  const kinder = [];
  let x = 24;
  const einheit = 11;
  for (let i = 0; i < (st.hundreds || 0); i++) {
    kinder.push(el("rect", { x, y: 24, width: einheit * 10, height: einheit * 10,
      class: "fig-material fig-hundert" }));
    for (let k = 1; k < 10; k++) {
      kinder.push(el("line", { x1: x, y1: 24 + k * einheit, x2: x + einheit * 10,
        y2: 24 + k * einheit, class: "fig-gitter-stark" }));
      kinder.push(el("line", { x1: x + k * einheit, y1: 24, x2: x + k * einheit,
        y2: 24 + einheit * 10, class: "fig-gitter-stark" }));
    }
    x += einheit * 10 + 12;
  }
  const zehnerStart = x;
  for (let i = 0; i < (st.tens || 0); i++) {
    kinder.push(el("rect", { x, y: 24, width: einheit, height: einheit * 10,
      class: "fig-material fig-zehn" }));
    for (let k = 1; k < 10; k++) {
      kinder.push(el("line", { x1: x, y1: 24 + k * einheit, x2: x + einheit,
        y2: 24 + k * einheit, class: "fig-gitter-stark" }));
    }
    x += einheit + 6;
  }
  if (st.tens) x += 10;
  const einerStart = x;
  for (let i = 0; i < (st.ones || 0); i++) {
    kinder.push(el("rect", { x: x + (i % 5) * (einheit + 4),
      y: 24 + Math.floor(i / 5) * (einheit + 4), width: einheit, height: einheit,
      class: "fig-material fig-eins" }));
  }
  x = einerStart + Math.min(5, st.ones || 0) * (einheit + 4);
  // §50: gefragt wird nach einer Stelle - die wird hervorgehoben benannt,
  // nicht ihr Wert verraten.
  if (st.asked_place === "TENS" && st.tens) {
    kinder.push(el("rect", {
      x: zehnerStart - 5, y: 18, width: (st.tens) * (einheit + 6) + 4,
      height: einheit * 10 + 12, rx: 4, class: "fig-hervor-rahmen",
    }));
  }
  return svg(Math.max(380, x + 20), 24 + einheit * 10 + 26, kinder);
}

/** Zwanzigerfeld: zwei Zehnerreihen, §46. */
function zwanzigerfeld(st) {
  const z = 28, x0 = 60, y0 = 30, kinder = [];
  for (let r = 0; r < 2; r++) {
    for (let c = 0; c < 10; c++) {
      const i = r * 10 + c;
      kinder.push(el("rect", { x: x0 + c * z, y: y0 + r * z, width: z, height: z,
        class: "fig-feld" }));
      if (i < (st.shown || 0)) {
        kinder.push(el("circle", { cx: x0 + c * z + z / 2, cy: y0 + r * z + z / 2,
          r: 9, class: "fig-gefuellt" }));
      }
    }
  }
  // Die Fuenfergliederung als durchgehende Linie, nicht als dickerer
  // Zellenrand: ein einzelnes staerker umrandetes Kaestchen liest sich als
  // hervorgehobenes Kaestchen, und hervorgehoben ist hier nichts.
  kinder.push(el("line", { x1: x0 + 5 * z, y1: y0, x2: x0 + 5 * z, y2: y0 + 2 * z,
    class: "fig-feld-trenner" }));
  return svg(400, y0 + 2 * z + 24, kinder);
}

/** Punktefeld, im Inneren verdeckt (§51). */
function array(st) {
  const [zeilen, spalten] = st.array;
  const z = Math.min(26, 300 / spalten, 150 / zeilen);
  const x0 = 200 - (spalten * z) / 2, y0 = 24, kinder = [];
  const verdeckt = st.interior_covered;
  for (let r = 0; r < zeilen; r++) {
    for (let c = 0; c < spalten; c++) {
      const rand = r === 0 || c === 0 || r === zeilen - 1 || c === spalten - 1;
      if (verdeckt && !rand) continue;
      kinder.push(el("circle", { cx: x0 + c * z + z / 2, cy: y0 + r * z + z / 2,
        r: z * 0.3, class: "fig-gefuellt" }));
    }
  }
  if (verdeckt) {
    kinder.push(el("rect", { x: x0 + z, y: y0 + z, width: (spalten - 2) * z,
      height: (zeilen - 2) * z, rx: 4, class: "fig-abdeckung" }));
    kinder.push(txt(x0 + (spalten * z) / 2, y0 + (zeilen * z) / 2, "verdeckt",
      { class: "fig-text fig-leise" }));
  }
  kinder.push(el("rect", { x: x0, y: y0, width: spalten * z, height: zeilen * z,
    rx: 4, class: "fig-rahmen" }));
  if (st.shown_decomposition) {
    // §52: die gezeigte Zerlegung wird als Trennlinie sichtbar, nicht als Text.
    const ersterFaktor = Number(String(st.shown_decomposition).split("*")[0]);
    if (ersterFaktor > 0 && ersterFaktor < zeilen) {
      kinder.push(el("line", { x1: x0, y1: y0 + ersterFaktor * z,
        x2: x0 + spalten * z, y2: y0 + ersterFaktor * z, class: "fig-trennlinie" }));
    }
  }
  return svg(400, y0 + zeilen * z + 24, kinder);
}

/** Veraenderung: vorher / Pfeil / nachher (§53, §54). */
function veraenderung(st) {
  const vorher = st.objects_first ?? st.objects_before ?? 0;
  const dazu = st.objects_added ?? 0;
  const weg = st.objects_removed ?? 0;
  const kinder = [];
  const reihe = (anzahl, x0, klasse, start) => {
    for (let i = 0; i < anzahl; i++) {
      kinder.push(el("circle", { cx: x0 + (i % 5) * 26, cy: 40 + Math.floor(i / 5) * 26,
        r: 9, class: klasse, "data-objekt": start + i }));
    }
    return x0 + Math.min(anzahl, 5) * 26;
  };
  let x = reihe(vorher, 26, "fig-gefuellt", 0);
  if (dazu) {
    kinder.push(txt(x + 18, 56, "+", { class: "fig-zahl" }));
    reihe(dazu, x + 42, "fig-neu", vorher);
    x += 42 + Math.min(dazu, 5) * 26;
  }
  if (weg) {
    kinder.push(txt(x + 18, 56, "−", { class: "fig-zahl" }));
    reihe(weg, x + 42, "fig-weg", vorher);
    x += 42 + Math.min(weg, 5) * 26;
  }
  return svg(Math.max(380, x + 20), 150, kinder);
}

/** Gleich grosse Gruppen (§55). */
function gruppen(st) {
  const anzahl = st.groups, proGruppe = st.per_group, kinder = [];
  const gb = Math.min(110, 360 / anzahl);
  for (let g = 0; g < anzahl; g++) {
    const x0 = 24 + g * gb;
    kinder.push(el("rect", { x: x0, y: 24, width: gb - 14, height: 96, rx: 8,
      class: "fig-gruppe" }));
    for (let i = 0; i < proGruppe; i++) {
      kinder.push(el("circle", { cx: x0 + 18 + (i % 3) * 22,
        cy: 44 + Math.floor(i / 3) * 24, r: 8, class: "fig-gefuellt" }));
    }
  }
  return svg(Math.max(380, 24 + anzahl * gb), 142, kinder);
}

/** Zahlenstrahl der Altform: range + marks (§45). */
function altZahlenstrahl(st) {
  return FIGUREN.NUMBER_LINE({
    type: "NUMBER_LINE", from: st.range[0], to: st.range[1],
    step: (st.range[1] - st.range[0]) / 10,
    marks: (st.marks || []).map((m) => ({ at: m, label: String(m) })),
  });
}

/** Signale nacheinander (§49): zeitlich, nicht raeumlich. */
function signale(st) {
  const kinder = [];
  for (let i = 0; i < st.signal_count; i++) {
    kinder.push(el("circle", { cx: 40 + i * 42, cy: 50, r: 14, class: "fig-signal" }));
    kinder.push(txt(40 + i * 42, 82, i + 1, { class: "fig-text fig-klein" }));
  }
  kinder.push(txt(200, 112, "nacheinander gezeigt",
    { class: "fig-text fig-leise" }));
  return svg(Math.max(380, 40 + st.signal_count * 42), 130, kinder);
}

const ALTFORMEN = [
  [(s) => s.place_value_chart,
    (s) => {
      const p = s.place_value_chart;
      const spalten = s.column_labels || ["H", "Z", "E"];
      const ziffern = [p.hundreds, p.tens, p.ones]
        .filter((v) => v !== undefined && v !== null);
      return stellenwerttafel(spalten.slice(-ziffern.length), ziffern, null);
    }],
  [(s) => s.material === "UNIT_CUBES" && s.loose_ones !== undefined,
    (s) => punkte({ objects: s.loose_ones, arrangement: "UNORDERED", movable: true })],
  [(s) => s.hundreds !== undefined || (s.tens !== undefined && s.material),
    basiszehn],
  [(s) => s.field === "TWENTY_FIELD", zwanzigerfeld],
  [(s) => Array.isArray(s.array), array],
  [(s) => Array.isArray(s.range) && s.marks, altZahlenstrahl],
  [(s) => s.signal_count !== undefined, signale],
  [(s) => s.objects_first !== undefined || s.objects_before !== undefined, veraenderung],
  [(s) => s.groups !== undefined && s.per_group !== undefined, gruppen],
  [(s) => s.objects !== undefined || s.target_count !== undefined, punkte],
  [(s) => s.material === "BASE_TEN_BLOCKS" || s.material === "BASE_TEN_RODS", basiszehn],
];

export { punkte, FIGUREN };
