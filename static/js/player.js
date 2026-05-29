const cfg = window.CIFRASFLIX_PLAYER;
const scoreEl = document.getElementById("score");
const tracksEl = document.getElementById("tracks");
const trackCountEl = document.getElementById("trackCount");
const fretStatus = document.getElementById("fretStatus");
const canvas = document.getElementById("fretboard");
const ctx = canvas.getContext("2d");
const pianoCanvas = document.getElementById("pianoKeyboard");
const pianoCtx = pianoCanvas?.getContext("2d") || null;
const chordCanvas = document.getElementById("chordDiagram");
const chordCtx = chordCanvas?.getContext("2d") || null;
const chordReadoutEl = document.getElementById("chordReadout");

const playBtn = document.getElementById("playBtn");
const stopBtn = document.getElementById("stopBtn");
const progressBar = document.getElementById("progressBar");
const currentTimeEl = document.getElementById("currentTime");
const totalTimeEl = document.getElementById("totalTime");
const bpmInput = document.getElementById("bpmInput");
const masterVolume = document.getElementById("masterVolume");
const pitchDown = document.getElementById("pitchDown");
const pitchUp = document.getElementById("pitchUp");
const pitchLabel = document.getElementById("pitchLabel");
const metronomeBtn = document.getElementById("metronomeBtn");
const loopBtn = document.getElementById("loopBtn");
const printBtn = document.getElementById("printBtn");
const layoutBtn = document.getElementById("layoutBtn");
const themeBtn = document.getElementById("themeBtn");
const perfBtn = document.getElementById("perfBtn");
const toggleFretBtn = document.getElementById("toggleFretBtn");
const toggleKeyboardBtn = document.getElementById("toggleKeyboardBtn");
const toggleChordBtn = document.getElementById("toggleChordBtn");
const fretStageEl = document.getElementById("fretStage");
const keyboardStageEl = document.getElementById("keyboardStage");
const chordStageEl = document.getElementById("chordStage");
const playerSearchInput = document.getElementById("playerSearchInput");
const playerSearchResults = document.getElementById("playerSearchResults");
const discoverBtn = document.getElementById("discoverBtn");

let api = null;
let isPlaying = false;
let originalBpm = 120;
let transpose = 0;
let activeTrackIndex = 0;
let fretboardData = [];
let layoutHorizontal = false;
let fretboardTimer = null;
let progressTimer = null;
const trackCursors = new Map();
const playedBeatState = new Map();
let lastDrawSignature = "";
let performanceMode = false;
let usingAlphaTabFretboard = false;
let fretVisible = true;
let keyboardVisible = true;
let chordVisible = true;
let playerSearchTimer = null;
let playerSearchPage = 1;
let lastPlayerSearchTerm = "";
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const STANDARD_TUNING = { 1: 4, 2: 9, 3: 2, 4: 7, 5: 11, 6: 4 };
const STANDARD_TUNING_MIDI = { 1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40 };
const STRING_NOTE_LABELS = { 6: "E", 5: "A", 4: "D", 3: "G", 2: "B", 1: "E" };
const PIANO_START_MIDI = 36;
const PIANO_END_MIDI = 84;
let lastDetectedChordName = "-";
let chordHoldPool = [];
let lastChordShapeNotes = [];

const CHORD_FORMULAS = [
  { suffix: "", intervals: [0, 4, 7], required: [0, 4] },
  { suffix: "m", intervals: [0, 3, 7], required: [0, 3] },
  { suffix: "5", intervals: [0, 7], required: [0, 7] },
  { suffix: "dim", intervals: [0, 3, 6], required: [0, 3, 6] },
  { suffix: "aug", intervals: [0, 4, 8], required: [0, 4, 8] },
  { suffix: "sus2", intervals: [0, 2, 7], required: [0, 2] },
  { suffix: "sus4", intervals: [0, 5, 7], required: [0, 5] },
  { suffix: "6", intervals: [0, 4, 7, 9], required: [0, 4, 9] },
  { suffix: "m6", intervals: [0, 3, 7, 9], required: [0, 3, 9] },
  { suffix: "7", intervals: [0, 4, 7, 10], required: [0, 4, 10] },
  { suffix: "maj7", intervals: [0, 4, 7, 11], required: [0, 4, 11] },
  { suffix: "m7", intervals: [0, 3, 7, 10], required: [0, 3, 10] },
  { suffix: "m7b5", intervals: [0, 3, 6, 10], required: [0, 3, 6, 10] },
  { suffix: "dim7", intervals: [0, 3, 6, 9], required: [0, 3, 6, 9] },
  { suffix: "add9", intervals: [0, 2, 4, 7], required: [0, 4, 2] },
  { suffix: "m(add9)", intervals: [0, 2, 3, 7], required: [0, 3, 2] },
  { suffix: "6/9", intervals: [0, 2, 4, 7, 9], required: [0, 2, 4, 9] },
  { suffix: "m6/9", intervals: [0, 2, 3, 7, 9], required: [0, 2, 3, 9] },
  { suffix: "9", intervals: [0, 2, 4, 7, 10], required: [0, 2, 4, 10] },
  { suffix: "maj9", intervals: [0, 2, 4, 7, 11], required: [0, 2, 4, 11] },
  { suffix: "m9", intervals: [0, 2, 3, 7, 10], required: [0, 2, 3, 10] },
  { suffix: "11", intervals: [0, 2, 4, 5, 7, 10], required: [0, 4, 5, 10] },
  { suffix: "m11", intervals: [0, 2, 3, 5, 7, 10], required: [0, 3, 5, 10] },
  { suffix: "13", intervals: [0, 2, 4, 7, 9, 10], required: [0, 4, 9, 10] },
  { suffix: "m13", intervals: [0, 2, 3, 7, 9, 10], required: [0, 3, 9, 10] },
];

const INTERVAL_LABEL = {
  1: "b9",
  2: "9",
  3: "#9",
  5: "11",
  6: "#11",
  8: "b13",
  9: "13",
  10: "b7",
  11: "7",
};

function setPlayButtonState(playing) {
  if (!playBtn) return;
  playBtn.innerHTML = playing ? "⏸" : "▶";
  playBtn.setAttribute("aria-label", playing ? "Pause" : "Play");
  playBtn.classList.toggle("active", !!playing);
}

function initBackLink() {
  const backLink = document.querySelector(".back-link");
  if (!backLink) return;

  const parts = window.location.pathname.split("/").filter(Boolean);
  const playerIndex = parts.indexOf("tocador-gp4");
  const artistSlug = playerIndex >= 0 ? parts[playerIndex + 1] : "";

  if (artistSlug) {
    backLink.href = `/artista/${decodeURIComponent(artistSlug)}`;
  }
}

function hidePlayerSearchResults() {
  if (!playerSearchResults) return;
  playerSearchResults.hidden = true;
  playerSearchResults.innerHTML = "";
}

function renderPlayerSearchResults(data, append = false) {
  if (!playerSearchResults) return;

  if (!append) {
    playerSearchResults.innerHTML = "";
  }

  if (!data.results || !data.results.length) {
    playerSearchResults.innerHTML = '<div class="player-search-item"><strong>Nenhum FlixPlayer encontrado</strong><small>Tente outro artista ou musica</small></div>';
    playerSearchResults.hidden = false;
    return;
  }

  data.results.forEach((item) => {
    const row = document.createElement("div");
    row.className = "player-search-item";
    row.innerHTML = `
      <strong>${item.titulo}</strong>
      <small>${item.artista_nome}</small>
    `;
    row.onclick = () => {
      window.location.href = item.player_url || `/tocador-gp4/${item.artista}/${item.uid}`;
    };
    playerSearchResults.appendChild(row);
  });

  if (data.has_next) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "discover-btn";
    more.textContent = "Mais resultados";
    more.onclick = () => loadPlayerSearchPage(lastPlayerSearchTerm, true);
    playerSearchResults.appendChild(more);
  }

  playerSearchResults.hidden = false;
}

function loadPlayerSearchPage(q, append = false) {
  if (!playerSearchResults) return;

  if (!q) {
    hidePlayerSearchResults();
    return;
  }

  if (!append) {
    playerSearchPage = 1;
    lastPlayerSearchTerm = q;
  } else {
    playerSearchPage += 1;
  }

  playerSearchResults.hidden = false;
  playerSearchResults.innerHTML = '<div class="player-search-item"><strong>Buscando...</strong><small>Carregando FlixPlayer</small></div>';

  fetch(`/buscar?q=${encodeURIComponent(q)}&page=${playerSearchPage}&gp=1`)
    .then((r) => r.json())
    .then((data) => renderPlayerSearchResults(data, append))
    .catch(() => {
      playerSearchResults.innerHTML = '<div class="player-search-item"><strong>Erro ao buscar</strong><small>Tente novamente</small></div>';
      playerSearchResults.hidden = false;
    });
}

function triggerPlayerSearch() {
  if (!playerSearchInput) return;
  const q = playerSearchInput.value.trim();
  clearTimeout(playerSearchTimer);
  playerSearchTimer = setTimeout(() => loadPlayerSearchPage(q, false), 180);
}

function initPlayerSearch() {
  if (playerSearchInput) {
    playerSearchInput.addEventListener("input", triggerPlayerSearch);
    playerSearchInput.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hidePlayerSearchResults();
        playerSearchInput.blur();
      }
    });
  }

  discoverBtn?.addEventListener("click", () => {
    window.location.href = "/sorteio-flixplayer";
  });

  document.addEventListener("click", (event) => {
    const box = document.querySelector(".player-search-box");
    if (box && playerSearchResults && !box.contains(event.target)) {
      hidePlayerSearchResults();
    }
  });
}

function noteNameFromMidi(midiValue) {
  return NOTE_NAMES[((midiValue % 12) + 12) % 12] || String(midiValue);
}

function noteNameFromPc(pc, preferFlat = false) {
  const idx = ((pc % 12) + 12) % 12;
  return (preferFlat ? NOTE_NAMES_FLAT[idx] : NOTE_NAMES[idx]) || String(pc);
}

function uniqueSorted(values) {
  return Array.from(new Set(values)).sort((a, b) => a - b);
}

function chooseFlatSpelling(rootPc, bassPc) {
  const flatFavored = new Set([1, 3, 6, 8, 10]);
  return flatFavored.has(rootPc) || flatFavored.has(bassPc);
}

function formatMissingIntervals(intervals) {
  const pretty = intervals
    .map((itv) => {
      if (itv === 7) return "5";
      if (itv === 4) return "3";
      if (itv === 3) return "b3";
      return INTERVAL_LABEL[itv] || String(itv);
    })
    .filter(Boolean);

  if (!pretty.length) return "";
  return `(no${pretty.join(",")})`;
}

function formatAddedIntervals(intervals) {
  const pretty = intervals
    .map((itv) => INTERVAL_LABEL[itv] || "")
    .filter(Boolean)
    .filter((txt) => txt !== "b7" && txt !== "7");

  if (!pretty.length) return "";
  return `(add${pretty.join(",")})`;
}

function scoreFormulaMatch(formula, detectedIntervals, rootPc, bassPc) {
  const detected = new Set(detectedIntervals);
  const inTemplate = formula.intervals.filter((itv) => detected.has(itv));
  const missingRequired = formula.required.filter((itv) => !detected.has(itv));

  if (missingRequired.length) {
    return null;
  }

  const missingAll = formula.intervals.filter((itv) => !detected.has(itv));
  const extra = detectedIntervals.filter((itv) => !formula.intervals.includes(itv));

  // Prefer roots in bass and richer complete matches while tolerating guitar omissions.
  let score = 0;
  score += inTemplate.length * 9;
  score -= missingAll.length * 2.2;
  score -= extra.length * 1.1;
  score += rootPc === bassPc ? 2.5 : 0;

  // Penalize contradictory 3rds when formula is clearly major/minor based.
  const hasMinorThird = detected.has(3);
  const hasMajorThird = detected.has(4);
  const formulaNeedsMinor = formula.intervals.includes(3);
  const formulaNeedsMajor = formula.intervals.includes(4);

  if (formulaNeedsMinor && hasMajorThird) score -= 2.4;
  if (formulaNeedsMajor && hasMinorThird) score -= 2.4;

  return {
    formula,
    score,
    missing: missingAll,
    extra,
  };
}

function detectChordNameFromNotes(notes = []) {
  if (!notes.length) return "-";

  const midiValues = uniqueSorted(notes.map((note) => Number(note?.midi)).filter(Number.isFinite));
  if (!midiValues.length) return "-";

  const pitchClasses = uniqueSorted(midiValues.map((midi) => ((midi % 12) + 12) % 12));
  const bassPc = ((midiValues[0] % 12) + 12) % 12;
  const roots = uniqueSorted([bassPc, ...pitchClasses]);

  let best = null;
  for (const root of roots) {
    const intervals = uniqueSorted(pitchClasses.map((pc) => (pc - root + 12) % 12));

    for (const formula of CHORD_FORMULAS) {
      const result = scoreFormulaMatch(formula, intervals, root, bassPc);
      if (!result) continue;

      if (!best || result.score > best.score) {
        best = {
          root,
          bass: bassPc,
          suffix: formula.suffix,
          score: result.score,
          missing: result.missing,
          extra: result.extra,
        };
      }
    }
  }

  if (best) {
    const preferFlat = chooseFlatSpelling(best.root, best.bass);
    const rootName = noteNameFromPc(best.root, preferFlat);
    const bassName = noteNameFromPc(best.bass, preferFlat);
    const missingTxt = formatMissingIntervals(best.missing || []);
    const addedTxt = formatAddedIntervals(best.extra || []);
    const inversion = best.root !== best.bass ? `/${bassName}` : "";
    return `${rootName}${best.suffix}${addedTxt}${missingTxt}${inversion}`;
  }

  if (pitchClasses.length === 1) {
    return noteNameFromPc(pitchClasses[0]);
  }

  return pitchClasses.map((pc) => noteNameFromPc(pc)).join("-");
}

function buildChordNotesFromHoldPool(timeMs = 0) {
  const now = Number.isFinite(Number(timeMs)) ? Number(timeMs) : 0;
  chordHoldPool = chordHoldPool.filter((item) => Number.isFinite(item.expiresAt) && item.expiresAt >= now);

  const uniqueByMidi = new Map();
  for (const item of chordHoldPool) {
    if (!Number.isFinite(item.midi)) continue;
    const key = item.midi;
    if (!uniqueByMidi.has(key) || uniqueByMidi.get(key).expiresAt < item.expiresAt) {
      uniqueByMidi.set(key, item);
    }
  }

  return Array.from(uniqueByMidi.values()).sort((a, b) => a.midi - b.midi);
}

function updateChordReadout(currentNotes = [], timeMs = 0) {
  if (!chordReadoutEl) return;

  const now = Number.isFinite(Number(timeMs)) ? Number(timeMs) : 0;
  for (const note of currentNotes || []) {
    const midi = Number(note?.midi);
    if (!Number.isFinite(midi)) continue;

    const rawDuration = Number(note?.duration);
    const heldDuration = Number.isFinite(rawDuration) && rawDuration > 0
      ? Math.min(1600, Math.max(220, rawDuration))
      : 420;

    chordHoldPool.push({
      midi,
      expiresAt: now + heldDuration,
    });
  }

  const chordNotes = buildChordNotesFromHoldPool(now);
  const chordName = detectChordNameFromNotes(chordNotes);

  // Keep the last chord lit on screen until a new one is detected.
  if (chordName !== "-") {
    lastDetectedChordName = chordName;
  }

  chordReadoutEl.textContent = `Acorde atual: ${lastDetectedChordName}`;
  chordReadoutEl.classList.toggle("is-lit", lastDetectedChordName !== "-");
}

function normalizeChordShapeNotes(notes = []) {
  const bestByString = new Map();

  for (const note of notes || []) {
    const string = Number(note?.string);
    const fret = Number(note?.fret);
    if (!Number.isInteger(string) || !Number.isInteger(fret) || string < 1 || string > 6 || fret < 0) {
      continue;
    }

    const existing = bestByString.get(string);
    if (!existing || fret < existing.fret) {
      bestByString.set(string, { string, fret });
    }
  }

  return Array.from(bestByString.values()).sort((a, b) => a.string - b.string);
}

function drawChordDiagram(currentNotes = []) {
  if (!chordCanvas || !chordCtx) return;

  const width = chordCanvas.width;
  const height = chordCanvas.height;
  chordCtx.clearRect(0, 0, width, height);

  const incoming = normalizeChordShapeNotes(currentNotes);
  if (incoming.length) {
    lastChordShapeNotes = incoming;
  }

  const notes = lastChordShapeNotes;
  if (!notes.length) {
    chordCtx.fillStyle = "rgba(255,255,255,0.72)";
    chordCtx.font = "700 20px Inter, Arial";
    chordCtx.textAlign = "center";
    chordCtx.textBaseline = "middle";
    chordCtx.fillText("-", width / 2, height / 2);
    return;
  }

  // Mirror to match the main fretboard orientation shown above.
  const displayStrings = [1, 2, 3, 4, 5, 6];
  const fretted = notes.filter((n) => n.fret > 0).map((n) => n.fret);
  const minFret = fretted.length ? Math.min(...fretted) : 1;
  const maxFret = fretted.length ? Math.max(...fretted) : 1;

  // For higher shapes, reference two frets before the first pressed fret
  // so the fingering resembles the full neck view.
  let baseFret = 1;
  if (fretted.length) {
    baseFret = maxFret > 5 ? Math.max(1, minFret) : 1;

    // Keep every note inside the 5-fret window.
    if (maxFret > baseFret + 4) {
      baseFret = Math.max(1, maxFret - 4);
    }
  }
  const visibleFrets = 5;

  const padX = 46;
  const padTop = 40;
  const padBottom = 62;
  const boardW = width - padX * 2;
  const boardH = height - padTop - padBottom;
  const stringGap = boardW / (displayStrings.length - 1);
  const fretGap = boardH / visibleFrets;

  chordCtx.strokeStyle = "rgba(255,255,255,0.78)";
  chordCtx.lineWidth = 2;
  for (let i = 0; i < displayStrings.length; i += 1) {
    const x = padX + i * stringGap;
    chordCtx.beginPath();
    chordCtx.moveTo(x, padTop);
    chordCtx.lineTo(x, padTop + boardH);
    chordCtx.stroke();
  }

  for (let fret = 0; fret <= visibleFrets; fret += 1) {
    const y = padTop + fret * fretGap;
    chordCtx.beginPath();
    chordCtx.lineWidth = fret === 0 ? 5 : 2;
    chordCtx.moveTo(padX, y);
    chordCtx.lineTo(padX + boardW, y);
    chordCtx.stroke();
  }

  // Side fret numbers (base reference + 0..4).
  chordCtx.fillStyle = "rgba(255,255,255,0.92)";
  chordCtx.font = "700 13px Inter, Arial";
  chordCtx.textAlign = "right";
  chordCtx.textBaseline = "middle";
  for (let step = 0; step < visibleFrets; step += 1) {
    const y = padTop + step * fretGap + fretGap * 0.5;
    chordCtx.fillText(String(baseFret + step), padX - 12, y);
  }

  if (baseFret > 1) {
    chordCtx.fillStyle = "rgba(255,255,255,0.92)";
    chordCtx.font = "900 42px Inter, Arial";
    chordCtx.textAlign = "left";
    chordCtx.textBaseline = "top";
    chordCtx.fillText(String(baseFret), 10, 8);
  }

  const xByString = new Map();
  displayStrings.forEach((s, i) => {
    xByString.set(s, padX + i * stringGap);
  });

  const noteByString = new Map();
  for (const n of notes) {
    if (!noteByString.has(n.string)) {
      noteByString.set(n.string, n);
    }
  }

  const activeStrings = new Set(notes.map((n) => n.string).filter((s) => Number.isInteger(s) && s >= 1 && s <= 6));

  // Red glow guide lines on strings being played.
  // For fretted notes, red starts at the pressed fret and goes downwards.
  // For open strings (fret 0), red starts at the nut.
  for (const string of activeStrings) {
    const x = xByString.get(string);
    if (!Number.isFinite(x)) continue;

    const note = noteByString.get(string);
    let startY = padTop;

    if (note && Number(note.fret) > 0) {
      const rel = Number(note.fret) - baseFret + 0.5;
      if (Number.isFinite(rel) && rel >= 0 && rel <= visibleFrets) {
        startY = padTop + rel * fretGap;
      }
    }

    if (startY > padTop + 1) {
      chordCtx.save();
      chordCtx.strokeStyle = "rgba(255,255,255,0.34)";
      chordCtx.lineWidth = 2;
      chordCtx.beginPath();
      chordCtx.moveTo(x, padTop);
      chordCtx.lineTo(x, startY);
      chordCtx.stroke();
      chordCtx.restore();
    }

    chordCtx.save();
    chordCtx.shadowColor = "rgba(255, 58, 58, 0.9)";
    chordCtx.shadowBlur = 14;
    chordCtx.strokeStyle = "rgba(255, 45, 45, 0.95)";
    chordCtx.lineWidth = 6;
    chordCtx.beginPath();
    chordCtx.moveTo(x, startY);
    chordCtx.lineTo(x, padTop + boardH);
    chordCtx.stroke();
    chordCtx.restore();
  }

  for (const note of notes) {
    const x = xByString.get(note.string);
    if (!Number.isFinite(x)) continue;

    const relativeFret = note.fret === 0 ? 0 : note.fret - baseFret + 0.5;
    if (relativeFret < 0 || relativeFret > visibleFrets) continue;

    const y = padTop + relativeFret * fretGap;
    chordCtx.beginPath();
    chordCtx.fillStyle = "#7ccfff";
    chordCtx.arc(x, y, 17, 0, Math.PI * 2);
    chordCtx.fill();

    chordCtx.fillStyle = "#0b2234";
    chordCtx.font = "900 16px Inter, Arial";
    chordCtx.textAlign = "center";
    chordCtx.textBaseline = "middle";
    chordCtx.fillText(String(note.fret), x, y + 0.3);
  }

  // String note labels at the bottom (E A D G B E).
  chordCtx.fillStyle = "#e7bd72";
  chordCtx.font = "700 12px Inter, Arial";
  chordCtx.textAlign = "center";
  chordCtx.textBaseline = "middle";
  for (const string of displayStrings) {
    const x = xByString.get(string);
    if (!Number.isFinite(x)) continue;
    chordCtx.fillText(STRING_NOTE_LABELS[string] || "", x, padTop + boardH + 22);
  }
}

function noteNameFromStringFret(string, fret, tuningMidi) {
  const baseMidi = Number.isFinite(tuningMidi) ? tuningMidi : STANDARD_TUNING[string];
  return noteNameFromMidi((baseMidi || 0) + fret);
}

function openStringMidi(string, tuningMidi) {
  if (Number.isFinite(tuningMidi) && tuningMidi > 20) {
    return tuningMidi;
  }
  return STANDARD_TUNING_MIDI[string] ?? 40;
}

function buildRenderableNote(note, time, duration) {
  const string = Number(note?.string);
  const fret = Number(note?.fret);
  const tuningMidi = Number(note?.stringTuning);

  if (!Number.isInteger(string) || !Number.isInteger(fret) || fret < 0) {
    return null;
  }

  if (note?.isPercussion || note?.isVisible === false || note?.isStringed === false) {
    return null;
  }

  const midi = openStringMidi(string, tuningMidi) + fret;

  return {
    id: Number(note?.id) || `${time}:${string}:${fret}`,
    time,
    duration: Math.max(0, Number(duration) || 0),
    string,
    fret,
    midi,
    name: noteNameFromMidi(midi),
    beatId: Number(note?.beat?.id) || null,
  };
}

function extractBeatNotes(beat) {
  if (!beat?.notes?.length) return [];
  const time = Number.isFinite(Number(beat.timer)) ? Number(beat.timer) : 0;
  const duration = Number.isFinite(Number(beat.playbackDuration)) ? Number(beat.playbackDuration) : 0;
  return beat.notes.map((note) => buildRenderableNote(note, time, duration)).filter(Boolean);
}

function getTrackIndexFromBeat(beat) {
  const rawIndex = beat?.voice?.bar?.staff?.track?.index;
  return Number.isInteger(rawIndex) ? rawIndex : -1;
}

function findNextBeatForTrack(beat, trackIndex) {
  let cursor = beat?.nextBeat || null;
  let guard = 0;

  while (cursor && guard < 128) {
    if (getTrackIndexFromBeat(cursor) === trackIndex) {
      const notes = extractBeatNotes(cursor);
      if (notes.length) {
        return cursor;
      }
    }
    cursor = cursor.nextBeat || null;
    guard += 1;
  }

  return null;
}

function resolveBeatTime(beat, fallbackTime = 0) {
  const timer = Number(beat?.timer);
  if (Number.isFinite(timer) && timer > 0) return timer;

  const absolute = Number(beat?.absolutePlaybackStart);
  if (Number.isFinite(absolute) && absolute > 0) return absolute;

  const playback = Number(beat?.playbackStart);
  if (Number.isFinite(playback) && playback > 0) return playback;

  return Number.isFinite(Number(fallbackTime)) ? Number(fallbackTime) : 0;
}

function buildFretboardDataFromScore(score) {
  if (!score?.tracks?.length) return [];

  return score.tracks.map((track, trackIndex) => {
    const notes = [];

    for (const staff of track.staves || []) {
      for (const bar of staff.bars || []) {
        for (const voice of bar.voices || []) {
          for (const beat of voice.beats || []) {
            const time = resolveBeatTime(beat, 0);
            const duration = Number(beat.playbackDuration) || 0;

            for (const note of beat.notes || []) {
              const renderable = buildRenderableNote(note, time, duration);
              if (renderable) notes.push(renderable);
            }
          }
        }
      }
    }

    return {
      index: trackIndex,
      name: track.name || `Track ${trackIndex + 1}`,
      notes,
    };
  });
}

function applyTheme(mode) {
  const dark = mode === "dark";
  document.body.classList.toggle("theme-dark", dark);
  if (themeBtn) {
    themeBtn.textContent = dark ? "☀️ Claro" : "🌙 Escuro";
  }
  try {
    localStorage.setItem("gp4-theme", dark ? "dark" : "light");
    localStorage.setItem("theme", dark ? "dark" : "light");
  } catch (e) {
    // ignore storage errors
  }
}

function initTheme() {
  let saved = "light";
  try {
    saved = localStorage.getItem("gp4-theme") || localStorage.getItem("theme") || "light";
  } catch (e) {
    saved = "light";
  }
  applyTheme(saved === "dark" ? "dark" : "light");
  themeBtn?.addEventListener("click", () => {
    const isDark = document.body.classList.contains("theme-dark");
    applyTheme(isDark ? "light" : "dark");
  });
}

function applyPerformanceMode(enabled) {
  performanceMode = !!enabled;
  document.body.classList.toggle("performance-mode", performanceMode);
  if (perfBtn) {
    perfBtn.classList.toggle("is-active", performanceMode);
    perfBtn.textContent = performanceMode ? "⚡ Performance ON" : "⚡ Performance";
  }
  if (toggleFretBtn) {
    toggleFretBtn.disabled = performanceMode;
    toggleFretBtn.title = performanceMode ? "Desativado no modo Performance" : "Mostrar ou ocultar violao";
  }
  if (toggleKeyboardBtn) {
    toggleKeyboardBtn.disabled = performanceMode;
    toggleKeyboardBtn.title = performanceMode ? "Desativado no modo Performance" : "Mostrar ou ocultar teclado";
  }
  if (toggleChordBtn) {
    toggleChordBtn.disabled = performanceMode;
    toggleChordBtn.title = performanceMode ? "Desativado no modo Performance" : "Mostrar ou ocultar acorde";
  }

  if (performanceMode) {
    setSectionVisible(fretStageEl, toggleFretBtn, false, "Violao");
    setSectionVisible(keyboardStageEl, toggleKeyboardBtn, false, "Teclado");
    setSectionVisible(chordStageEl, toggleChordBtn, false, "Acorde");
  } else {
    setSectionVisible(fretStageEl, toggleFretBtn, fretVisible, "Violao");
    setSectionVisible(keyboardStageEl, toggleKeyboardBtn, keyboardVisible, "Teclado");
    setSectionVisible(chordStageEl, toggleChordBtn, chordVisible, "Acorde");
  }

  try {
    localStorage.setItem("gp4-performance", performanceMode ? "on" : "off");
  } catch (e) {
    // ignore storage errors
  }
}

function setSectionVisible(element, button, visible, label) {
  if (!element || !button) return;
  element.classList.toggle("is-hidden", !visible);
  button.classList.toggle("is-active", visible);
  button.textContent = label;
}

function initSectionToggles() {
  setSectionVisible(fretStageEl, toggleFretBtn, fretVisible, "Violao");
  setSectionVisible(keyboardStageEl, toggleKeyboardBtn, keyboardVisible, "Teclado");
  setSectionVisible(chordStageEl, toggleChordBtn, chordVisible, "Acorde");

  toggleFretBtn?.addEventListener("click", () => {
    if (performanceMode) return;
    fretVisible = fretStageEl?.classList.contains("is-hidden");
    setSectionVisible(fretStageEl, toggleFretBtn, !!fretVisible, "Violao");
  });

  toggleKeyboardBtn?.addEventListener("click", () => {
    if (performanceMode) return;
    keyboardVisible = keyboardStageEl?.classList.contains("is-hidden");
    setSectionVisible(keyboardStageEl, toggleKeyboardBtn, !!keyboardVisible, "Teclado");
  });

  toggleChordBtn?.addEventListener("click", () => {
    if (performanceMode) return;
    chordVisible = chordStageEl?.classList.contains("is-hidden");
    setSectionVisible(chordStageEl, toggleChordBtn, !!chordVisible, "Acorde");
  });
}

function initPerformanceMode() {
  let saved = "off";
  try {
    saved = localStorage.getItem("gp4-performance") || "off";
  } catch (e) {
    saved = "off";
  }
  applyPerformanceMode(saved === "on");
  perfBtn?.addEventListener("click", () => {
    applyPerformanceMode(!performanceMode);
  });
}

function applyTrackSafetyDefaults(score) {
  if (!score?.tracks?.length) return;
  score.tracks.forEach((track) => {
    track.isMute = false;
    track.isSolo = false;
    api.changeTrackMute(track, false);
    api.changeTrackSolo(track, false);
  });
}

function selectTrack(index) {
  if (!api?.score?.tracks?.length) return;

  activeTrackIndex = Math.max(0, Math.min(index, api.score.tracks.length - 1));
  const selectedTrack = api.score.tracks[activeTrackIndex];

  trackCursors.set(activeTrackIndex, 0);
  api.renderTracks([selectedTrack]);
  document.querySelectorAll(".track-row").forEach((el, i) => {
    el.classList.toggle("active", i === activeTrackIndex);
  });

  lastDrawSignature = "";
  updateLiveFretboard(true);
}

function updateFretDebug(currentNotes, nextNotes, time, source = "timer") {
  void currentNotes;
  void nextNotes;
  void time;
  void source;
}

function drawCurrentFretboardState(currentNotes, nextNotes, time, source) {
  const nextToDraw = performanceMode ? [] : nextNotes;
  updateFretDebug(currentNotes, nextToDraw, time, source);
  updateChordReadout(currentNotes, time);
  drawChordDiagram(currentNotes);

  const signature = `${currentNotes.map((n) => `${n.string}:${n.fret}:${n.id}`).join("|")}__${nextToDraw
    .map((n) => `${n.string}:${n.fret}:${n.id}`)
    .join("|")}__${source}__${Math.floor(time / (performanceMode ? 120 : 80))}`;

  if (signature !== lastDrawSignature) {
    drawFretboard(currentNotes, nextToDraw);
    drawPiano(currentNotes, nextToDraw);
    lastDrawSignature = signature;
  }
}

function updateLiveFretboard(forceClear = false) {
  if (!usingAlphaTabFretboard) return false;

  const state = playedBeatState.get(activeTrackIndex);
  if (!state) {
    if (forceClear) {
      updateFretDebug([], [], api?.timePosition || 0, isPlaying ? "alphatab" : "idle");
      drawFretboard([], []);
      drawPiano([], []);
      lastDrawSignature = "";
    }
    return false;
  }

  drawCurrentFretboardState(state.currentNotes, state.nextNotes, state.time, "alphatab");
  return true;
}

function bindAlphaTabEvents() {
  if (!api) return;

  api.playedBeatChanged?.on((beat) => {
    const trackIndex = getTrackIndexFromBeat(beat);
    if (trackIndex < 0) return;

    const nextBeat = findNextBeatForTrack(beat, trackIndex);
    playedBeatState.set(trackIndex, {
      beatId: Number(beat?.id) || null,
      time: resolveBeatTime(beat, api?.timePosition || 0),
      currentNotes: extractBeatNotes(beat),
      nextNotes: nextBeat ? extractBeatNotes(nextBeat) : [],
    });

    if (trackIndex === activeTrackIndex) {
      updateLiveFretboard();
    }
  });

  api.playerStateChanged?.on((args) => {
    const state = Number(args?.state);
    const playerState = window.alphaTab?.synth?.PlayerState || {};
    isPlaying = state === playerState.Playing;
    setPlayButtonState(isPlaying);

    if (args?.stopped) {
      playedBeatState.clear();
      lastDrawSignature = "";
      updateFretDebug([], [], 0, "stop");
      drawFretboard([], []);
      drawPiano([], []);
      lastDetectedChordName = "-";
      chordHoldPool = [];
      lastChordShapeNotes = [];
      updateChordReadout([]);
      drawChordDiagram([]);
    }
  });
}

function initAlphaTab() {
  api = new alphaTab.AlphaTabApi(scoreEl, {
    file: cfg.fileUrl,
    display: {
      scale: 1,
      layoutMode: alphaTab.LayoutMode.Page,
    },
    player: {
      enablePlayer: true,
      enableCursor: true,
      enableAnimatedBeatCursor: true,
      scrollElement: document.querySelector(".score-stage"),
      soundFont: cfg.soundFont || cfg.soundFontFallback || cfg.soundFontLocal,
    },
  });

  api.scoreLoaded.on((score) => {
    applyTrackSafetyDefaults(score);
    document.getElementById("scoreTitle").textContent = score.title || cfg.title;
    originalBpm = score.tempo || 120;
    bpmInput.value = originalBpm;
    const alphaTabTracks = buildFretboardDataFromScore(score);
    const hasAlphaTabNotes = alphaTabTracks.some((track) => track.notes.length > 0);
    if (hasAlphaTabNotes) {
      usingAlphaTabFretboard = true;
      fretboardData = alphaTabTracks;
      fretStatus.textContent = "";
    } else {
      usingAlphaTabFretboard = false;
      loadFretboard();
    }
    renderTracks(score);
  });

  bindAlphaTabEvents();
}

function renderTracks(score) {
  tracksEl.innerHTML = "";
  trackCountEl.textContent = String(score.tracks.length);

  score.tracks.forEach((track, index) => {
    const row = document.createElement("div");
    row.className = `track-row${index === activeTrackIndex ? " active" : ""}`;

    const name = document.createElement("div");
    name.className = "track-main";
    name.innerHTML = `<strong>${escapeHtml(track.name || `Track ${index + 1}`)}</strong><small>${track.playbackInfo?.program ?? 0}</small>`;

    const controls = document.createElement("div");
    controls.className = "track-controls";

    const mute = document.createElement("button");
    mute.textContent = "M";
    mute.title = "Mute";
    mute.classList.toggle("is-active", !!track.isMute);
    mute.onclick = (event) => {
      event.stopPropagation();
      // Fade effect duration in ms
      const fadeDuration = 200;
      const steps = 20;
      const stepTime = fadeDuration / steps;
      let currentStep = 0;
      let startVolume = track.isMute ? 0 : 1;
      let endVolume = track.isMute ? 1 : 0;
      // If already fading, skip
      if (track._fadeTimeout) {
        clearTimeout(track._fadeTimeout);
      }
      function fadeStep() {
        currentStep++;
        const progress = currentStep / steps;
        const newVolume = startVolume + (endVolume - startVolume) * progress;
        api.changeTrackVolume(track, newVolume);
        if (currentStep < steps) {
          track._fadeTimeout = setTimeout(fadeStep, stepTime);
        } else {
          // Finalize
          api.changeTrackVolume(track, endVolume);
          track.isMute = !track.isMute;
          api.changeTrackMute(track, track.isMute);
          mute.classList.toggle("is-active", track.isMute);
          track._fadeTimeout = null;
        }
      }
      fadeStep();
    };

    const solo = document.createElement("button");
    solo.textContent = "S";
    solo.title = "Solo";
    solo.onclick = (event) => {
      event.stopPropagation();
      track.isSolo = !track.isSolo;
      api.changeTrackSolo(track, track.isSolo);
      solo.classList.toggle("is-active", track.isSolo);
    };

    const volume = document.createElement("input");
    volume.type = "range";
    volume.min = "0";
    volume.max = "1";
    volume.step = "0.01";
    volume.value = "1";
    volume.oninput = (event) => {
      event.stopPropagation();
      api.changeTrackVolume(track, parseFloat(volume.value));
    };

    controls.append(mute, solo, volume);
    row.append(name, controls);

    row.onclick = () => {
      selectTrack(index);
    };

    tracksEl.appendChild(row);
  });

  if (score.tracks[0]) {
    selectTrack(activeTrackIndex);
  }
}

async function loadFretboard() {
  try {
    const response = await fetch(cfg.fretboardUrl);
    const data = await response.json();
    if (usingAlphaTabFretboard) {
      return;
    }
    fretboardData = data.tracks || [];
    fretStatus.textContent = data.available ? "" : data.message;
  } catch {
    if (usingAlphaTabFretboard) {
      return;
    }
    fretStatus.textContent = "Braco indisponivel para este arquivo.";
  }
}

function drawFretboard(currentNotes = [], nextNotes = []) {
  const width = canvas.width;
  const height = canvas.height;
  const strings = 6;
  const frets = 14;
  const stringGap = height / (strings + 1);
  const fretGap = width / (frets + 1);
  const openFretWidth = fretGap * 0.5;
  const nutX = openFretWidth;

  ctx.clearRect(0, 0, width, height);

  const wood = ctx.createLinearGradient(0, 0, width, 0);
  wood.addColorStop(0, "#3d2518");
  wood.addColorStop(0.45, "#6d4428");
  wood.addColorStop(1, "#2b1b13");
  ctx.fillStyle = wood;
  ctx.fillRect(0, 0, width, height);

    const sheen = ctx.createLinearGradient(0, 0, 0, height);
    sheen.addColorStop(0, "rgba(255,255,255,0.12)");
    sheen.addColorStop(0.35, "rgba(255,255,255,0.03)");
    sheen.addColorStop(0.75, "rgba(0,0,0,0.08)");
    sheen.addColorStop(1, "rgba(0,0,0,0.16)");
    ctx.fillStyle = sheen;
    ctx.fillRect(0, 0, width, height);

  // Highlight open-string fret area (fret 0) between nut and fret 1.
    const openArea = ctx.createLinearGradient(0, 0, openFretWidth, 0);
    openArea.addColorStop(0, "rgba(8, 5, 3, 0.84)");
    openArea.addColorStop(1, "rgba(22, 12, 8, 0.46)");
    ctx.fillStyle = openArea;
    ctx.fillRect(0, 0, openFretWidth, height);

  for (let fret = 1; fret <= frets; fret += 1) {
    const x = fret * fretGap;
    ctx.strokeStyle = "rgba(255,255,255,0.45)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let string = 1; string <= strings; string += 1) {
    const y = string * stringGap;
    const lineWidth = 1 + (strings - string) * 0.38;

    // Darker strings on fret 0 area for better nut contrast.
    ctx.strokeStyle = "rgba(74, 74, 74, 0.85)";
    ctx.lineWidth = lineWidth;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(openFretWidth, y);
    ctx.stroke();

    ctx.strokeStyle = "rgba(255,255,255,0.74)";
    ctx.lineWidth = lineWidth;
    ctx.beginPath();
    ctx.moveTo(openFretWidth, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw nut on top so strings do not wash out its color.
    const nut = ctx.createLinearGradient(0, 0, nutX, 0);
    nut.addColorStop(0, "#050302");
    nut.addColorStop(0.5, "#1c130d");
    nut.addColorStop(1, "#090604");
    ctx.strokeStyle = nut;
    ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.moveTo(nutX, 0);
  ctx.lineTo(nutX, height);
  ctx.stroke();

  // Fret numbers with better readability.
  ctx.font = "700 12px Inter, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let fret = 1; fret <= frets; fret += 1) {
    const x = fret * fretGap;
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.beginPath();
    ctx.arc(x, height - 11, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.86)";
    ctx.fillText(String(fret), x, height - 11);
  }

  // Open string marker near the nut.
  const openX = openFretWidth * 0.5;
  ctx.fillStyle = "rgba(0,0,0,0.38)";
  ctx.beginPath();
  ctx.arc(openX, height - 11, 9, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,0.9)";
  ctx.fillText("0", openX, height - 11);

  drawNotes(nextNotes, "#d8ebff", "#18324f", 13);
  drawNotes(currentNotes, "#7ccfff", "#082033", 18);
}

function stringToY(string, strings, stringGap) {
  return (strings - string + 1) * stringGap;
}

function isBlackMidi(midi) {
  const step = ((midi % 12) + 12) % 12;
  return step === 1 || step === 3 || step === 6 || step === 8 || step === 10;
}

function drawPiano(currentNotes = [], nextNotes = []) {
  if (!pianoCanvas || !pianoCtx) return;

  const width = pianoCanvas.width;
  const height = pianoCanvas.height;
  const whiteKeyHeight = height;
  const blackKeyHeight = Math.floor(height * 0.62);

  const whiteMidis = [];
  for (let midi = PIANO_START_MIDI; midi <= PIANO_END_MIDI; midi += 1) {
    if (!isBlackMidi(midi)) whiteMidis.push(midi);
  }

  const whiteWidth = width / whiteMidis.length;

  const currentMidiSet = new Set(currentNotes.map((note) => note.midi));
  const nextMidiSet = new Set(nextNotes.map((note) => note.midi));

  pianoCtx.clearRect(0, 0, width, height);
  pianoCtx.fillStyle = "#0f1114";
  pianoCtx.fillRect(0, 0, width, height);

  pianoCtx.fillStyle = "#101418";
  pianoCtx.fillRect(0, 0, width, height);

  const whiteIndexByMidi = new Map();
  whiteMidis.forEach((midi, index) => {
    whiteIndexByMidi.set(midi, index);
    const x = index * whiteWidth;

    const fill = currentMidiSet.has(midi)
      ? "#3d96ff"
      : nextMidiSet.has(midi)
        ? "#b7d8ff"
        : "#f6f7f9";

    pianoCtx.fillStyle = fill;
    pianoCtx.fillRect(x, 0, whiteWidth, whiteKeyHeight);
    pianoCtx.strokeStyle = "rgba(0,0,0,0.24)";
    pianoCtx.lineWidth = 1;
    pianoCtx.strokeRect(x, 0, whiteWidth, whiteKeyHeight);

    pianoCtx.fillStyle = currentMidiSet.has(midi) ? "#14324c" : "#2e333a";
    pianoCtx.font = "700 11px Inter, Arial";
    pianoCtx.textAlign = "center";
    pianoCtx.textBaseline = "alphabetic";
    pianoCtx.fillText(noteNameFromMidi(midi), x + whiteWidth / 2, whiteKeyHeight - 8);
  });

  for (let midi = PIANO_START_MIDI; midi <= PIANO_END_MIDI; midi += 1) {
    if (!isBlackMidi(midi)) continue;

    const leftWhite = midi - 1;
    const leftIndex = whiteIndexByMidi.get(leftWhite);
    if (leftIndex === undefined) continue;

    const x = (leftIndex + 1) * whiteWidth - whiteWidth * 0.32;
    const blackWidth = whiteWidth * 0.64;

    const fill = currentMidiSet.has(midi)
      ? "#3d96ff"
      : nextMidiSet.has(midi)
        ? "#b7d8ff"
        : "#111317";

    pianoCtx.fillStyle = fill;
    pianoCtx.fillRect(x, 0, blackWidth, blackKeyHeight);
    pianoCtx.strokeStyle = "rgba(0,0,0,0.88)";
    pianoCtx.lineWidth = 1;
    pianoCtx.strokeRect(x, 0, blackWidth, blackKeyHeight);

    pianoCtx.fillStyle = currentMidiSet.has(midi) ? "#f7fbff" : "rgba(235,240,246,0.92)";
    pianoCtx.font = "700 10px Inter, Arial";
    pianoCtx.textAlign = "center";
    pianoCtx.textBaseline = "alphabetic";
    pianoCtx.fillText(noteNameFromMidi(midi), x + blackWidth / 2, blackKeyHeight - 6);
  }
}

function drawNotes(notes, fill, textFill, radius) {
  const strings = 6;
  const stringGap = canvas.height / (strings + 1);
  const fretGap = canvas.width / 15;
  const openFretWidth = fretGap * 0.5;

  notes.forEach((note) => {
    if (note.fret > 14) return;
    const x = note.fret <= 0 ? openFretWidth * 0.5 : note.fret * fretGap;
    const y = stringToY(note.string, strings, stringGap);

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.fillStyle = textFill;
    ctx.font = "700 12px Inter, Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(note.fret === 0 ? "0" : note.name || note.fret, x, y);
  });
}

function syncFretboard() {
  if (usingAlphaTabFretboard && updateLiveFretboard()) {
    fretboardTimer = setTimeout(syncFretboard, performanceMode ? 120 : 40);
    return;
  }

  const track = fretboardData[activeTrackIndex];
  const notes = track?.notes || [];
  const time = api?.timePosition || 0;
  const syncWindow = performanceMode ? 180 : 140;
  const maxPreview = performanceMode ? 2 : 5;

  if (!notes.length) {
    fretStatus.textContent = "Track selecionada sem notas para o braco.";
    updateFretDebug([], [], time, usingAlphaTabFretboard ? "alphatab" : "timer");
    drawFretboard([], []);
    fretboardTimer = setTimeout(syncFretboard, performanceMode ? 120 : 50);
    return;
  }

  if (fretStatus.textContent !== "Sincronizado") {
    fretStatus.textContent = "Sincronizado";
  }

  let cursor = trackCursors.get(activeTrackIndex) || 0;

  while (cursor > 0 && notes[cursor - 1]?.time > time - 180) {
    cursor -= 1;
  }
  while (cursor < notes.length && notes[cursor].time < time - 180) {
    cursor += 1;
  }
  trackCursors.set(activeTrackIndex, cursor);

  const current = [];
  const next = [];

  for (let i = cursor; i < notes.length; i += 1) {
    const note = notes[i];
    const noteEnd = note.time + Math.max(note.duration || 0, syncWindow);
    if (time >= note.time && time <= noteEnd) current.push(note);
    if (note.time > time && next.length < maxPreview) next.push(note);
    if (current.length >= 6 && next.length >= maxPreview) break;
    if (note.time > time + 1400) break;
  }

  drawCurrentFretboardState(current, next, time, "timer");

  fretboardTimer = setTimeout(syncFretboard, performanceMode ? 120 : 40);
}

function updateProgress() {
  const timePos = (api?.timePosition || 0) / 1000;
  const endTime = (api?.endTime || 0) / 1000;

  currentTimeEl.textContent = formatTime(timePos);
  totalTimeEl.textContent = formatTime(endTime);
  progressBar.max = endTime || 100;
  progressBar.value = timePos;

  progressTimer = setTimeout(updateProgress, performanceMode ? 220 : 120);
}

function formatTime(seconds) {
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${min}:${String(sec).padStart(2, "0")}`;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value || "";
  return div.innerHTML;
}

playBtn.onclick = () => {
  api.playPause();
};

stopBtn.onclick = () => {
  api.stop();
  isPlaying = false;
  setPlayButtonState(false);
};

progressBar.oninput = () => {
  if (api?.player) api.player.timePosition = parseFloat(progressBar.value) * 1000;
};

bpmInput.oninput = () => {
  const nextBpm = parseFloat(bpmInput.value);
  if (nextBpm > 0) api.playbackSpeed = nextBpm / originalBpm;
};

masterVolume.oninput = () => {
  api.masterVolume = parseFloat(masterVolume.value);
};

pitchDown.onclick = () => changePitch(-1);
pitchUp.onclick = () => changePitch(1);

function changePitch(delta) {
  transpose += delta;
  pitchLabel.textContent = String(transpose);

  const transposableTracks = (api.score?.tracks || []).filter((track) => {
    if (!track) return false;
    if (track.isPercussion) return false;
    if (Number(track.playbackInfo?.program) === 0) return false;

    return true;
  });

  if (transposableTracks.length) {
    api.changeTrackTranspositionPitch(transposableTracks, transpose);
  }
}

metronomeBtn.onclick = () => {
  metronomeBtn.classList.toggle("is-active");
  api.metronomeVolume = metronomeBtn.classList.contains("is-active") ? 1 : 0;
};

loopBtn.onclick = () => {
  loopBtn.classList.toggle("is-active");
  api.isLooping = loopBtn.classList.contains("is-active");
};

printBtn.onclick = () => api.print();

layoutBtn.onclick = () => {
  layoutHorizontal = !layoutHorizontal;
  api.settings.display.layoutMode = layoutHorizontal ? alphaTab.LayoutMode.Horizontal : alphaTab.LayoutMode.Page;
  api.updateSettings();
  api.render();
};

document.addEventListener("keydown", (event) => {
  const target = event.target;
  const isTypingTarget =
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    target?.isContentEditable;

  if (isTypingTarget) return;

  if (event.code === "Space") {
    event.preventDefault();
    api?.playPause();
    return;
  }

  if (event.shiftKey && event.code === "ArrowUp") {
    event.preventDefault();
    changePitch(1);
    return;
  }

  if (event.shiftKey && event.code === "ArrowDown") {
    event.preventDefault();
    changePitch(-1);
  }
});

drawFretboard();
drawPiano();
updateChordReadout([]);
drawChordDiagram([]);
initSectionToggles();
initBackLink();
initPlayerSearch();
setPlayButtonState(false);
initTheme();
initPerformanceMode();
initAlphaTab();
loadFretboard();
syncFretboard();
updateProgress();
