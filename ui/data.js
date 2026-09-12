/* Datenzugriffsschicht.
 *
 * Die einzige Datei, die weiß, woher die Daten kommen. Keine Ansicht ruft
 * fetch() auf; alle gehen über dieses Modul. Genau das verlangt der
 * Implementierungsauftrag, und es ist zugleich die Stelle, an der sich die
 * Datenquelle austauschen ließe.
 *
 * Ein Punkt zum Entwicklungsmodus: Mock-Daten gibt es hier nicht. Der MVP
 * existiert und liefert echte Endpunkte. Mock-Daten wären hier nicht nur
 * überflüssig, sondern gefährlich – jeder erfundene Kompetenzstatus oder
 * Schwellenwert wäre eine fachliche Entscheidung, und genau die sind
 * untersagt. Wer die Quelle wechseln will, ersetzt `hole()`.
 */

const WURZEL = "/api";

const zwischenspeicher = new Map();

async function hole(pfad) {
  if (zwischenspeicher.has(pfad)) return zwischenspeicher.get(pfad);
  const versprechen = fetch(`${WURZEL}/${pfad}`, { headers: { Accept: "application/json" } })
    .then(async (antwort) => {
      const inhalt = await antwort.json().catch(() => ({ error: antwort.statusText }));
      if (!antwort.ok) throw new Error(inhalt.error || `HTTP ${antwort.status}`);
      return inhalt;
    })
    .catch((fehler) => {
      zwischenspeicher.delete(pfad);   // ein Fehlschlag darf sich nicht festsetzen
      throw fehler;
    });
  zwischenspeicher.set(pfad, versprechen);
  return versprechen;
}

/** Graph, Aufgabenbank und Vokabular – für alle Schüler:innen gleich. */
export const katalog = () => hole("catalog");

/** Liste der pseudonymen Kennungen (§86). */
export const schuelerListe = () => hole("students").then((d) => d.students);

/** Das vollständige Profil einer Schüler:in: alle fünfzehn Objektarten. */
export const profil = (id) => hole(`student/${encodeURIComponent(id)}`);

/** Die Konfigurationsschlüssel mit Status und Fundstelle (§35, §41). */
export const konfiguration = () => hole("config").then((d) => d.config);

/* ------------------------------------------------------------- Nachschlagen
 *
 * Reine Nachschlagehilfen über bereits geladene Daten. Sie verknüpfen
 * Kennungen mit Datensätzen – sie rechnen nichts aus und leiten nichts ab.
 */

export function nachId(liste, feld) {
  const karte = new Map();
  for (const eintrag of liste) karte.set(eintrag[feld], eintrag);
  return karte;
}

/** Gruppiert eine Liste nach dem Rückgabewert von `schluessel`. */
export function gruppieren(liste, schluessel) {
  const karte = new Map();
  for (const eintrag of liste) {
    const k = schluessel(eintrag);
    if (!karte.has(k)) karte.set(k, []);
    karte.get(k).push(eintrag);
  }
  return karte;
}
