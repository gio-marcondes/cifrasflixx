def slug_letras(texto: str) -> str:

    if not texto:
        return ""

    texto = str(texto)

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("utf-8")

    texto = texto.replace("&", "and")
    texto = texto.replace("'", "")
    texto = texto.replace(".", "")
    texto = texto.replace("(", "")
    texto = texto.replace(")", "")

    texto = re.sub(
        r"[^a-z0-9]+",
        "-",
        texto
    )

    texto = re.sub(
        r"-+",
        "-",
        texto
    ).strip("-")

    return texto


def buscar_video_youtube(artista, musica, indice=2):
    import urllib.parse

    query = urllib.parse.quote(f"{artista}  {musica}")
    url = f"https://www.youtube.com/results?search_query={query}"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        html = requests.get(url, headers=headers, timeout=15).text
    except Exception:
        return None

    matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)

    vistos = []
    for m in matches:
        if m not in vistos:
            vistos.append(m)

    if len(vistos) > indice:
        video_id = vistos[indice]
        return f"https://www.youtube.com/watch?v={video_id}"

    return None


# ==========================================
# 🎵 BUSCAR LETRA → HTML
# ==========================================
import requests
from bs4 import BeautifulSoup


def buscar_letra_html(artista1: str, musica1: str):
    """
    Retorna:
        letra_html,
        traducao_html,
        titulo_traduzido
    """

    import time
    import re
    import unicodedata

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait

    # =========================================
    # NORMALIZAR
    # =========================================

    def normalizar(texto):

        texto = texto.lower().strip()

        texto = unicodedata.normalize(
            "NFKD",
            texto
        )

        texto = texto.encode(
            "ascii",
            "ignore"
        ).decode("utf-8")

        return texto

    artista_slug1 = slug_letras(artista1)
    musica_slug1 = slug_letras(musica1)

    url = (
        f"https://www.letras.mus.br/"
        f"{artista_slug1}/"
        f"{musica_slug1}/print.html?translation=pt"
    )

    driver = None

    try:

        options = Options()

        #options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")

        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        )
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)

        driver.get(url)

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        time.sleep(2)

        # =========================================
        # VALIDA TITULO
        # =========================================

        try:

            titulo_site = driver.find_element(
                By.CSS_SELECTOR,
                "div.page-header h1"
            ).text.strip()

        except:

            print("❌ Não encontrou título")

            return None, None, None

        from difflib import SequenceMatcher

        esperado = slug_letras(musica1)
        titulo_normalizado = slug_letras(titulo_site)

        porcentagem = (
            SequenceMatcher(
                None,
                esperado,
                titulo_normalizado
            ).ratio() * 100
        )
        print(
            f"Compatibilidade: {porcentagem:.1f}%"
        )

        # =========================================
        # REJEITA MÚSICA ERRADA
        # =========================================

        if porcentagem < 60:

            print("❌ Música incompatível")
            print("Buscada   :", musica1)
            print("Encontrada:", titulo_site)

            return None, None, None

        # =========================================
        # CONTAINERS
        # =========================================

        containers = driver.find_elements(
            By.CSS_SELECTOR,
            "div.page-container"
        )

        if not containers:
            return None, None, None

        original_parts = []
        traducao_parts = []

        titulo_traduzido = None

        # =========================================
        # LOOP ORIGINAL / TRADUÇÃO
        # =========================================

        for i, div in enumerate(containers):

            try:

                h3 = div.find_element(
                    By.TAG_NAME,
                    "h3"
                ).text.strip()

            except:

                h3 = None

            linhas = div.text.strip().splitlines()

            if h3 and linhas and linhas[0] == h3:
                linhas = linhas[1:]

            html_parte = (
                "<p>"
                + (h3 or "")
                + "</p>\n"
                + "<br>".join(linhas)
            )

            if i % 2 == 0:
                original_parts.append(html_parte)
            else:
                traducao_parts.append(html_parte)

        # =========================================
        # TÍTULO TRADUZIDO
        # =========================================

        if len(containers) > 1:

            try:

                titulo_traduzido = containers[1].find_element(
                    By.TAG_NAME,
                    "h3"
                ).text.strip()

            except:

                titulo_traduzido = (
                    musica1 + " (Tradução)"
                )

        letra_html = (
            "\n".join(original_parts)
            if original_parts
            else None
        )

        traducao_html = (
            "\n".join(traducao_parts)
            if traducao_parts
            else None
        )

        return (
            letra_html,
            traducao_html,
            titulo_traduzido
        )

    except Exception as e:

        print("Erro Selenium:", e)

        return None, None, None

    finally:

        if driver:
            driver.quit()






def procura_letra(artista_slug, musica_slug):

    conn = sqlite3.connect("cifras.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    musica_slug = (musica_slug or "").lower().strip()
    artista_slug = (artista_slug or "").lower().strip()

    # 🔥 1. procura no banco primeiro (cache direto por slug)
    cur.execute("""
        SELECT c.letra_original, c.letra_traduzida
        FROM cancao c
        JOIN albuns al ON al.id = c.album_id
        JOIN artistas ar ON ar.id = al.artista_id
        WHERE ar.slug = ?
        AND c.cancao_slug = ?
        LIMIT 1
    """, (artista_slug, musica_slug))

    row = cur.fetchone()

    # ✅ se achou no banco
    if row and row["letra_original"]:
        conn.close()
        letra_original = row["letra_original"].replace("\n", "<br>") if row["letra_original"] else None
        letra_traduzida = row["letra_traduzida"].replace("\n", "<br>") if row["letra_traduzida"] else None
        return letra_original, letra_traduzida

    # 🔥 1.1 fallback por título normalizado (quando cancao_slug diverge)
    titulo_guess = (musica_slug or "").replace("-", " ").strip().lower()
    if titulo_guess:
        cur.execute("""
            SELECT c.letra_original, c.letra_traduzida
            FROM cancao c
            JOIN albuns al ON al.id = c.album_id
            JOIN artistas ar ON ar.id = al.artista_id
            WHERE ar.slug = ?
            AND LOWER(TRIM(c.titulo)) = ?
            LIMIT 1
        """, (artista_slug, titulo_guess))

        row = cur.fetchone()
        if row and row["letra_original"]:
            conn.close()
            letra_original = row["letra_original"].replace("\n", "<br>") if row["letra_original"] else None
            letra_traduzida = row["letra_traduzida"].replace("\n", "<br>") if row["letra_traduzida"] else None
            return letra_original, letra_traduzida

    # 🔥 2. se não achou → busca no site
    letra_html, letra_traduzida, titulo_traduzido = buscar_letra_html(artista_slug, musica_slug)

    if not letra_html:
        conn.close()
        return None, None

    # 🔥 3. salva no banco (cache)
    cur.execute("""
        UPDATE cancao
        SET letra_original = ?,
            letra_traduzida = ?
        WHERE cancao_slug = ?
        AND album_id IN (
            SELECT al.id
            FROM albuns al
            JOIN artistas ar ON ar.id = al.artista_id
            WHERE ar.slug = ?
        )
    """, (letra_html, letra_traduzida, musica_slug, artista_slug))

    # fallback por título quando slug não casou
    if cur.rowcount == 0 and titulo_guess:
        cur.execute("""
            UPDATE cancao
            SET letra_original = ?,
                letra_traduzida = ?
            WHERE LOWER(TRIM(titulo)) = ?
            AND album_id IN (
                SELECT al.id
                FROM albuns al
                JOIN artistas ar ON ar.id = al.artista_id
                WHERE ar.slug = ?
            )
        """, (letra_html, letra_traduzida, titulo_guess, artista_slug))

    # se não encontrou linha para update, cria uma entrada de cache mínima no cancao
    if cur.rowcount == 0:
        cur.execute("""
            SELECT al.id
            FROM albuns al
            JOIN artistas ar ON ar.id = al.artista_id
            WHERE ar.slug = ?
            ORDER BY al.id
            LIMIT 1
        """, (artista_slug,))
        album_ref = cur.fetchone()

        if album_ref:
            cur.execute("""
                INSERT INTO cancao (album_id, titulo, cancao_slug, letra_original, letra_traduzida)
                VALUES (?, ?, ?, ?, ?)
            """, (
                album_ref[0],
                titulo_guess.title() if titulo_guess else musica_slug.replace("-", " ").title(),
                musica_slug,
                letra_html,
                letra_traduzida,
            ))

    conn.commit()
    conn.close()

    return letra_html, letra_traduzida


def _normalizar_titulo_texto(texto):
    import unicodedata

    base = (texto or "").strip().lower()
    base = unicodedata.normalize("NFKD", base)
    base = base.encode("ascii", "ignore").decode("utf-8")
    base = re.sub(r"[^a-z0-9]+", " ", base).strip()
    return base


def _extrair_primeira_linha_texto(html_texto):
    if not html_texto:
        return ""

    soup = BeautifulSoup(html_texto, "html.parser")
    for node in soup.find_all(["h1", "h2", "h3", "p", "div"]):
        texto = " ".join(node.get_text(" ", strip=True).split())
        if texto:
            return texto

    return ""


def _remover_titulo_inicial(html_texto, titulos):
    if not html_texto:
        return html_texto

    alvos = {
        _normalizar_titulo_texto(titulo)
        for titulo in (titulos or [])
        if _normalizar_titulo_texto(titulo)
    }
    if not alvos:
        return html_texto

    soup = BeautifulSoup(html_texto, "html.parser")

    # If the first rendered line is the song title inside a block like
    # <p>TITLE<br><br>...</p>, remove only that line and keep the stanza.
    for bloco in soup.find_all(["p", "div"], limit=1):
        filhos = list(bloco.contents)
        if not filhos:
            break

        idx = 0
        while idx < len(filhos):
            atual = filhos[idx]
            if isinstance(atual, str):
                linha = " ".join(atual.split())
                if not linha:
                    idx += 1
                    continue
                if _normalizar_titulo_texto(linha) in alvos:
                    atual.extract()
                    for prox in list(bloco.contents):
                        if getattr(prox, "name", "") == "br":
                            prox.extract()
                            continue
                        if isinstance(prox, str) and not " ".join(prox.split()):
                            prox.extract()
                            continue
                        break
                break
            elif getattr(atual, "name", "") == "br":
                idx += 1
                continue
            else:
                break
        break

    # Some sources return the song title as a raw text node before any tag.
    # Remove this leading node when it matches a known title.
    for child in list(soup.contents):
        if isinstance(child, str):
            texto = " ".join(child.split())
            if not texto:
                child.extract()
                continue
            if _normalizar_titulo_texto(texto) in alvos:
                child.extract()
                for prox in list(soup.contents):
                    if getattr(prox, "name", "") == "br":
                        prox.extract()
                        continue
                    if isinstance(prox, str) and not " ".join(prox.split()):
                        prox.extract()
                        continue
                    break
            break
        # Keep non-content tags (e.g. wrappers) and continue until first content.
        if getattr(child, "name", "") in {"br", "hr"}:
            continue
        break

    for node in soup.find_all(["h1", "h2", "h3", "p", "div"]):
        texto = " ".join(node.get_text(" ", strip=True).split())
        if not texto:
            continue

        if _normalizar_titulo_texto(texto) in alvos:
            node.decompose()
        break

    return str(soup)


def _inserir_divisor_estrofes(html_texto):
    if not html_texto:
        return html_texto

    saida = html_texto
    saida = re.sub(
        r"<p>\s*(?:&nbsp;|&#160;|\u00a0)?\s*</p>",
        '<div class="lyricStanzaDivider" aria-hidden="true"></div>',
        saida,
        flags=re.IGNORECASE
    )
    saida = re.sub(
        r"(?:<br\s*/?>\s*){2,}",
        '<div class="lyricStanzaDivider" aria-hidden="true"></div>',
        saida,
        flags=re.IGNORECASE
    )
    saida = re.sub(
        r"(?:<div class=\"lyricStanzaDivider\" aria-hidden=\"true\"></div>\s*){2,}",
        '<div class="lyricStanzaDivider" aria-hidden="true"></div>',
        saida
    )

    return saida

@app.route("/letra/<artista>/<musica>")
def ver_letra(artista, musica):
    import html as html_escape

    letra_html, traducao_html = procura_letra(artista, musica)

    if not letra_html:
        letra_html = "<p>Letra não encontrada.</p>"

    # 🔹 slugs
    artista_slug = normalizar_slug(artista)
    slug = artista_slug

    # 🔹 título formatado
    titulo = musica.replace("-", " ").title()
    artista_nome = artista.replace("-", " ").title()
    preview_titulo = musica.replace("-", " ").strip()

    titulo_traduzido = _extrair_primeira_linha_texto(traducao_html)
    if not titulo_traduzido or _normalizar_titulo_texto(titulo_traduzido) == _normalizar_titulo_texto(titulo):
        titulo_traduzido = titulo

    letra_html = _remover_titulo_inicial(letra_html, [titulo, titulo_traduzido])
    traducao_html = _remover_titulo_inicial(traducao_html, [titulo, titulo_traduzido])

    letra_html = _inserir_divisor_estrofes(letra_html)
    traducao_html = _inserir_divisor_estrofes(traducao_html)

    # 🔹 dados mock (ajuste se já tiver)
    versoes = [(1, titulo)]
    uid = 1
    musica_slug = musica

    sugestoes_html = ""
    try:
        conn_s = sqlite3.connect("cifras.db")
        conn_s.row_factory = sqlite3.Row
        cur_s = conn_s.cursor()
        cur_s.execute("""
            SELECT
                c.titulo AS musica_titulo,
                c.cancao_slug,
                c.album_id,
                al.nome AS album_nome,
                al.capa AS album_capa,
                al.ano AS album_ano
            FROM cancao c
            JOIN albuns al ON al.id = c.album_id
            JOIN artistas ar ON ar.id = al.artista_id
            WHERE ar.slug = ?
              AND COALESCE(TRIM(c.titulo), '') <> ''
            ORDER BY COALESCE(al.ano, ''), al.nome, c.id
        """, (artista_slug,))
        candidatas = cur_s.fetchall()
        conn_s.close()

        atual_slug = (musica_slug or "").strip().lower()
        atual_titulo_norm = _normalizar_titulo_texto(titulo)
        por_album = {}
        cards = []

        for row in candidatas:
            album_id = row["album_id"]
            if not album_id:
                continue

            if por_album.get(album_id, 0) >= 2:
                continue

            musica_titulo = (row["musica_titulo"] or "").strip()
            if not musica_titulo:
                continue

            titulo_norm = _normalizar_titulo_texto(musica_titulo)
            slug_cancao = (row["cancao_slug"] or normalizar_slug(musica_titulo) or "").strip().lower()

            if slug_cancao and atual_slug and slug_cancao == atual_slug:
                continue
            if titulo_norm and titulo_norm == atual_titulo_norm:
                continue

            capa_raw = (row["album_capa"] or "").strip()
            if capa_raw.lower().startswith(("http://", "https://")):
                capa_src = capa_raw
            else:
                capa_src = f"/capa_album/{album_id}"

            album_nome = (row["album_nome"] or "Album").strip()
            album_ano = str(row["album_ano"])[:4] if row["album_ano"] else ""
            link_letra = f"/letra/{artista_slug}/{slug_cancao or normalizar_slug(musica_titulo)}"

            cards.append(f"""
                <a class="lyricSuggestionCard" href="{link_letra}" title="Abrir letra de {html_escape.escape(musica_titulo, quote=True)}">
                    <img class="lyricSuggestionThumb" src="{capa_src}" alt="{html_escape.escape(album_nome, quote=True)}">
                    <div class="lyricSuggestionBody">
                        <strong>{html_escape.escape(musica_titulo)}</strong>
                        <span>{html_escape.escape(album_nome)}{(' • ' + html_escape.escape(album_ano)) if album_ano else ''}</span>
                    </div>
                </a>
            """)

            por_album[album_id] = por_album.get(album_id, 0) + 1
            if len(cards) >= 8:
                break

        if cards:
            sugestoes_html = """
            <section class="lyricSuggestions">
                <div class="sectionHeader">
                    <div>
                        <p class="eyebrow">Sugestoes</p>
                        <h2>Mais musicas</h2>
                    </div>
                </div>
                <div class="lyricSuggestionsGrid">
            """ + "".join(cards) + """
                </div>
            </section>
            """
    except Exception:
        try:
            conn_s.close()
        except Exception:
            pass
        sugestoes_html = ""

    # Performance: avoid external YouTube lookup on lyric page load.
    video_id = ""
    iframe_video = ""
    if video_id:
        iframe_video = f'''
    <iframe id="ytplayer"
            src="https://www.youtube.com/embed/{video_id}"
            frameborder="0"
            allowfullscreen>
    </iframe>
    '''

    video_dock_html = ""
    video_dock_css = ""
    video_dock_js = ""

    lyric_prefs_css = """
.lyricReader {
    --lyric-font-family: 'Georgia', 'Times New Roman', serif;
    --lyric-font-size: 18px;
    --lyric-line-height: 1.72;
    --lyric-letter-spacing: 0px;
    --lyric-text-color: #111827;
    --lyric-accent-color: #ff7a00;
}

.lyricBox {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 28px;
    font-size: var(--lyric-font-size);
    line-height: var(--lyric-line-height);
    letter-spacing: var(--lyric-letter-spacing);
    color: var(--lyric-text-color);
    font-family: var(--lyric-font-family);
}

.lyricReader .songTitle,
.lyricReader .eyebrow,
.lyricReader .chord {
    color: var(--lyric-accent-color);
}

.lyricReader .chord {
    text-decoration: none;
    font-weight: 700;
}

.lyricPanels {
    display: grid;
    gap: 14px;
}

.lyricPanels.compareMode {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
}

.lyricPanels.compareMode .lyricBox {
    min-width: 0;
    padding: 10px 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
}

.lyricModeTabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 14px;
}

.lyricModeBtn {
    border: 1px solid rgba(148, 163, 184, 0.45);
    background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(255,255,255,0.48));
    backdrop-filter: blur(8px) saturate(130%);
    -webkit-backdrop-filter: blur(8px) saturate(130%);
    border-radius: 999px;
    padding: 8px 14px;
    font-weight: 800;
    cursor: pointer;
    color: #334155;
    font-size: 13px;
    line-height: 1;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}

.lyricModeBtn:hover {
    border-color: rgba(255, 122, 0, 0.45);
    color: #1f2937;
}

.lyricModeBtn.is-active {
    background: linear-gradient(135deg, rgba(255, 202, 149, 0.88), rgba(255, 140, 41, 0.78));
    color: #2b1200;
    border-color: rgba(255, 122, 0, 0.65);
    box-shadow: 0 6px 16px rgba(255, 122, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.48);
}

.lyricPanels.compareMode #lyricOriginal {
    color: #9ca3af;
}

.lyricPanels.compareMode #lyricTraducao {
    color: var(--lyric-text-color);
}

.lyricStanzaDivider {
    position: relative;
    height: 22px;
    margin: 12px 0 16px;
}

.lyricStanzaDivider::before {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 1px;
    background: linear-gradient(90deg, rgba(148, 163, 184, 0), rgba(148, 163, 184, .55), rgba(148, 163, 184, 0));
}

.lyricStanzaDivider::after {
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    transform: translate(-50%, -50%);
    background: rgba(148, 163, 184, 0.55);
    box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.9);
}

.lyricControlGrid {
    display: grid;
    gap: 10px;
}

.lyricControlRow {
    display: grid;
    gap: 6px;
}

.lyricControlRow label {
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.lyricControlRow select,
.lyricControlRow input[type="color"] {
    width: 100%;
    height: 34px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    padding: 0 8px;
}

.lyricControlRow input[type="color"] {
    padding: 2px;
}

.lyricControlRow input[type="range"] {
    width: 100%;
}

.lyricControlValue {
    min-width: 46px;
    text-align: right;
    font-weight: 700;
    color: #111827;
    font-size: 12px;
}

@media (max-width: 980px) {
    .lyricPanels.compareMode {
        grid-template-columns: 1fr;
    }
}
"""

    quote_popup_js = """
let lyricSelectedSnippet = "";
    const QUOTE_STORAGE_KEY = "lyricQuotePrefs";
    const DEFAULT_QUOTE_PREFS = {
        background: "#111827",
        fontFamily: "Georgia, 'Times New Roman', serif",
        signatureMode: "artista",
        imageFormat: "square"
    };

    function getQuotePrefs() {
        try {
            return Object.assign({}, DEFAULT_QUOTE_PREFS, JSON.parse(localStorage.getItem(QUOTE_STORAGE_KEY) || "null") || {});
        } catch (e) {
            return Object.assign({}, DEFAULT_QUOTE_PREFS);
        }
    }

    function saveQuotePrefs(nextPrefs) {
        const prefs = Object.assign({}, getQuotePrefs(), nextPrefs || {});
        try {
            localStorage.setItem(QUOTE_STORAGE_KEY, JSON.stringify(prefs));
        } catch (e) {}
        return prefs;
    }

    function applyQuotePrefsToInputs(prefs) {
        const finalPrefs = Object.assign({}, DEFAULT_QUOTE_PREFS, prefs || {});
        const bg = document.getElementById("quoteBackgroundInput");
        const font = document.getElementById("quoteFontFamilyInput");
        const sig = document.getElementById("quoteSignatureModeInput");
        const format = document.getElementById("quoteFormatInput");

        if (bg) bg.value = finalPrefs.background;
        if (font) font.value = finalPrefs.fontFamily;
        if (sig) sig.value = finalPrefs.signatureMode;
        if (format) format.value = finalPrefs.imageFormat;

        return finalPrefs;
    }

function normalizeQuoteText(text) {
    return (text || "").replace(/\s+/g, " ").trim();
}

    function adjustQuoteColor(hex, amount) {
        const base = normalizeQuoteText(hex || "").replace("#", "");
        if (!/^([0-9a-fA-F]{6})$/.test(base)) return hex;
        const num = parseInt(base, 16);
        const clamp = (v) => Math.max(0, Math.min(255, v));
        const r = clamp(((num >> 16) & 255) + amount);
        const g = clamp(((num >> 8) & 255) + amount);
        const b = clamp((num & 255) + amount);
        return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
    }

function selectionInsideLyrics(selection) {
    if (!selection || selection.rangeCount === 0) return false;
    const range = selection.getRangeAt(0);
    const panels = document.getElementById("lyricPanels");
    if (!panels) return false;
    return panels.contains(range.commonAncestorContainer);
}

function hideQuoteSelectionFab() {
    const fab = document.getElementById("quoteSelectionFab");
    if (fab) fab.classList.remove("show");
}

function updateQuoteSelectionFab() {
    const fab = document.getElementById("quoteSelectionFab");
    if (!fab) return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selectionInsideLyrics(selection)) {
        hideQuoteSelectionFab();
        return;
    }

    const text = normalizeQuoteText(selection.toString());
    if (!text || text.length < 6) {
        hideQuoteSelectionFab();
        return;
    }

    lyricSelectedSnippet = text;
    const rangeRect = selection.getRangeAt(0).getBoundingClientRect();
    const left = window.scrollX + rangeRect.left + (rangeRect.width / 2);
    const top = window.scrollY + rangeRect.bottom + 10;

    fab.style.left = `${left}px`;
    fab.style.top = `${top}px`;
    fab.classList.add("show");
}

function openQuoteModal() {
    const modal = document.getElementById("quoteModal");
    const quoteInput = document.getElementById("quoteTextInput");
    if (!modal || !quoteInput) return;

    quoteInput.value = lyricSelectedSnippet || quoteInput.value || "";
    applyQuotePrefsToInputs(getQuotePrefs());
    modal.classList.add("show");
    hideQuoteSelectionFab();
    renderQuoteImage();
}

function closeQuoteModal() {
    const modal = document.getElementById("quoteModal");
    if (modal) modal.classList.remove("show");
}

function wrapCanvasText(ctx, text, maxWidth) {
    const words = text.split(" ");
    const lines = [];
    let line = "";

    words.forEach((word) => {
        const testLine = line ? (line + " " + word) : word;
        if (ctx.measureText(testLine).width > maxWidth && line) {
            lines.push(line);
            line = word;
        } else {
            line = testLine;
        }
    });

    if (line) lines.push(line);
    return lines;
}

function getQuoteFormatConfig(format) {
    if (format === "wide") {
        return { width: 1600, height: 900, titleY: 0.82, quoteSize: 54, quoteWidth: 0.70, lineHeight: 72, signatureSize: 32 };
    }

    if (format === "story") {
        return { width: 1080, height: 1920, titleY: 0.88, quoteSize: 56, quoteWidth: 0.72, lineHeight: 78, signatureSize: 36 };
    }

    return { width: 1080, height: 1080, titleY: 0.87, quoteSize: 58, quoteWidth: 0.72, lineHeight: 76, signatureSize: 34 };
}

function renderQuoteImage() {
    const canvas = document.getElementById("quoteCanvas");
    const preview = document.getElementById("quotePreview");
    const downloadLink = document.getElementById("quoteDownloadLink");
    const quoteInput = document.getElementById("quoteTextInput");
    const artistInput = document.getElementById("quoteArtistInput");
    const bgInput = document.getElementById("quoteBackgroundInput");
    const fontInput = document.getElementById("quoteFontFamilyInput");
    const signatureModeInput = document.getElementById("quoteSignatureModeInput");
    const formatInput = document.getElementById("quoteFormatInput");
    if (!canvas || !quoteInput || !artistInput || !bgInput || !fontInput || !signatureModeInput || !formatInput) return;

    const text = normalizeQuoteText(quoteInput.value);
    const artist = normalizeQuoteText(artistInput.value || "Artista");
    const songTitle = normalizeQuoteText(document.getElementById("lyricMainTitle")?.dataset?.originalTitle || document.getElementById("lyricMainTitle")?.textContent || "Música");
    const background = normalizeQuoteText(bgInput.value || DEFAULT_QUOTE_PREFS.background);
    const signatureMode = signatureModeInput.value || DEFAULT_QUOTE_PREFS.signatureMode;
    const fontFamily = fontInput.value || DEFAULT_QUOTE_PREFS.fontFamily;
    const imageFormat = formatInput.value || DEFAULT_QUOTE_PREFS.imageFormat;
    if (!text) return;

    saveQuotePrefs({ background, fontFamily, signatureMode, imageFormat });

    const formatConfig = getQuoteFormatConfig(imageFormat);
    canvas.width = formatConfig.width;
    canvas.height = formatConfig.height;

    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    const grad = ctx.createLinearGradient(0, 0, w, h);
    grad.addColorStop(0, adjustQuoteColor(background, 26));
    grad.addColorStop(0.52, background);
    grad.addColorStop(1, adjustQuoteColor(background, -24));
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.beginPath();
    ctx.arc(w * 0.18, h * 0.18, 160, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(w * 0.82, h * 0.78, 210, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.font = "700 " + Math.round(formatConfig.quoteSize * 1.3) + "px " + fontFamily;
    ctx.textAlign = "center";
    ctx.fillText('"', w * 0.12, h * 0.24);
    ctx.fillText('"', w * 0.88, h * 0.76);

    ctx.font = "600 " + formatConfig.quoteSize + "px " + fontFamily;
    const lines = wrapCanvasText(ctx, text, w * formatConfig.quoteWidth);
    const lineHeight = formatConfig.lineHeight;
    const textBlockHeight = lines.length * lineHeight;
    let y = (h - textBlockHeight) / 2;

    lines.forEach((line) => {
        ctx.fillText(line, w / 2, y);
        y += lineHeight;
    });

    ctx.font = "500 " + formatConfig.signatureSize + "px 'Inter', 'Segoe UI', sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.86)";
    const signature = signatureMode === "musica" ? ("- " + songTitle + " (" + artist + ")") : ("- " + artist);
    ctx.fillText(signature, w / 2, h * formatConfig.titleY);

    if (preview) preview.src = canvas.toDataURL("image/png");
    if (downloadLink) downloadLink.href = canvas.toDataURL("image/png");
}

document.addEventListener("selectionchange", () => {
    requestAnimationFrame(updateQuoteSelectionFab);
});

document.addEventListener("mouseup", () => {
    setTimeout(updateQuoteSelectionFab, 0);
});

document.addEventListener("touchend", () => {
    setTimeout(updateQuoteSelectionFab, 0);
});

document.addEventListener("click", (event) => {
    const modal = document.getElementById("quoteModal");
    const fab = document.getElementById("quoteSelectionFab");
    if (modal && modal.classList.contains("show") && event.target === modal) {
        closeQuoteModal();
        return;
    }

    if (fab && !fab.contains(event.target)) {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) hideQuoteSelectionFab();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const quoteInput = document.getElementById("quoteTextInput");
    const artistInput = document.getElementById("quoteArtistInput");
    const bgInput = document.getElementById("quoteBackgroundInput");
    const fontInput = document.getElementById("quoteFontFamilyInput");
    const signatureModeInput = document.getElementById("quoteSignatureModeInput");
    const formatInput = document.getElementById("quoteFormatInput");
    if (quoteInput) quoteInput.addEventListener("input", renderQuoteImage);
    if (artistInput) artistInput.addEventListener("input", renderQuoteImage);
    if (bgInput) bgInput.addEventListener("input", renderQuoteImage);
    if (fontInput) fontInput.addEventListener("change", renderQuoteImage);
    if (signatureModeInput) signatureModeInput.addEventListener("change", renderQuoteImage);
    if (formatInput) formatInput.addEventListener("change", renderQuoteImage);
    applyQuotePrefsToInputs(getQuotePrefs());
});
"""

    lyric_prefs_js = """
const LYRIC_STORAGE_KEY = "lyricReaderPrefs";
const LYRIC_MODE_KEY = "lyricReaderMode";
const DEFAULT_LYRIC_PREFS = {
    family: "Georgia, 'Times New Roman', serif",
    fontSize: 18,
    lineHeight: 1.72,
    letterSpacing: 0,
    textColor: "#111827",
    accentColor: "#ff7a00"
};

function getLyricPrefs() {
    try {
        return JSON.parse(localStorage.getItem(LYRIC_STORAGE_KEY) || "null") || {};
    } catch (e) {
        return {};
    }
}

function persistLyricPrefs(nextPrefs) {
    const prefs = Object.assign({}, DEFAULT_LYRIC_PREFS, nextPrefs || getLyricPrefs());
    try {
        localStorage.setItem(LYRIC_STORAGE_KEY, JSON.stringify(prefs));
    } catch (e) {}
}

function applyLyricPrefs(prefs) {
    const finalPrefs = Object.assign({}, DEFAULT_LYRIC_PREFS, prefs || {});
    const root = document.querySelector(".lyricReader") || document.documentElement;
    root.style.setProperty("--lyric-font-family", finalPrefs.family);
    root.style.setProperty("--lyric-font-size", finalPrefs.fontSize + "px");
    root.style.setProperty("--lyric-line-height", String(finalPrefs.lineHeight));
    root.style.setProperty("--lyric-letter-spacing", finalPrefs.letterSpacing + "px");
    root.style.setProperty("--lyric-text-color", finalPrefs.textColor);
    root.style.setProperty("--lyric-accent-color", finalPrefs.accentColor);

    const familySelect = document.getElementById("lyricFontFamily");
    const fontRange = document.getElementById("lyricFontSize");
    const lineRange = document.getElementById("lyricLineHeight");
    const letterRange = document.getElementById("lyricLetterSpacing");
    const textPicker = document.getElementById("lyricTextColor");
    const accentPicker = document.getElementById("lyricAccentColor");

    if (familySelect) familySelect.value = finalPrefs.family;
    if (fontRange) fontRange.value = String(finalPrefs.fontSize);
    if (lineRange) lineRange.value = String(finalPrefs.lineHeight);
    if (letterRange) letterRange.value = String(finalPrefs.letterSpacing);
    if (textPicker) textPicker.value = finalPrefs.textColor;
    if (accentPicker) accentPicker.value = finalPrefs.accentColor;

    const fontValue = document.getElementById("lyricFontSizeValue");
    const lineValue = document.getElementById("lyricLineHeightValue");
    const letterValue = document.getElementById("lyricLetterSpacingValue");
    if (fontValue) fontValue.innerText = finalPrefs.fontSize + "px";
    if (lineValue) lineValue.innerText = Number(finalPrefs.lineHeight).toFixed(1);
    if (letterValue) letterValue.innerText = finalPrefs.letterSpacing + "px";

    persistLyricPrefs(finalPrefs);
}

function ajustarLyricFamilia(value) {
    const prefs = getLyricPrefs();
    prefs.family = value;
    applyLyricPrefs(prefs);
}

function ajustarLyricFonte(value) {
    const prefs = getLyricPrefs();
    prefs.fontSize = Math.max(14, Math.min(24, Number(value) || DEFAULT_LYRIC_PREFS.fontSize));
    applyLyricPrefs(prefs);
}

function ajustarLyricLineHeight(value) {
    const prefs = getLyricPrefs();
    prefs.lineHeight = Number(Math.max(1.3, Math.min(2.2, Number(value) || DEFAULT_LYRIC_PREFS.lineHeight)).toFixed(1));
    applyLyricPrefs(prefs);
}

function ajustarLyricLetterSpacing(value) {
    const prefs = getLyricPrefs();
    prefs.letterSpacing = Number(Math.max(-0.5, Math.min(1.8, Number(value) || DEFAULT_LYRIC_PREFS.letterSpacing)).toFixed(1));
    applyLyricPrefs(prefs);
}

function ajustarLyricTextColor(value) {
    const prefs = getLyricPrefs();
    prefs.textColor = value || DEFAULT_LYRIC_PREFS.textColor;
    applyLyricPrefs(prefs);
}

function ajustarLyricAccentColor(value) {
    const prefs = getLyricPrefs();
    prefs.accentColor = value || DEFAULT_LYRIC_PREFS.accentColor;
    applyLyricPrefs(prefs);
}

function setLyricMode(mode) {
    const original = document.getElementById("lyricOriginal");
    const traducao = document.getElementById("lyricTraducao");
    const panels = document.getElementById("lyricPanels");
    const buttons = document.querySelectorAll(".lyricModeBtn");
    const titleEl = document.getElementById("lyricMainTitle");

    if (!original || !traducao || !panels) return;

    const hasTranslation = !!(traducao.innerHTML || "").trim();
    let nextMode = mode || "normal";
    if (!hasTranslation && nextMode !== "normal") nextMode = "normal";

    if (titleEl) {
        const originalTitle = titleEl.dataset.originalTitle || titleEl.textContent || "";
        const translatedTitle = titleEl.dataset.translationTitle || originalTitle;
        titleEl.textContent = (nextMode === "normal") ? originalTitle : translatedTitle;
    }

    panels.classList.toggle("compareMode", nextMode === "side");
    original.style.display = (nextMode === "translation") ? "none" : "block";
    traducao.style.display = (nextMode === "normal") ? "none" : "block";

    buttons.forEach((btn) => {
        const active = btn.dataset.mode === nextMode;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    try {
        localStorage.setItem(LYRIC_MODE_KEY, nextMode);
    } catch (e) {}
}

function resetLyricPrefs() {
    applyLyricPrefs(DEFAULT_LYRIC_PREFS);
}

document.addEventListener("DOMContentLoaded", () => {
    applyLyricPrefs(getLyricPrefs());
    let savedMode = "normal";
    try {
        savedMode = localStorage.getItem(LYRIC_MODE_KEY) || "normal";
    } catch (e) {}
    setLyricMode(savedMode);

    const bind = (id, eventName, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(eventName, () => handler(el.value));
    };

    bind("lyricFontFamily", "change", ajustarLyricFamilia);
    bind("lyricFontSize", "input", ajustarLyricFonte);
    bind("lyricLineHeight", "input", ajustarLyricLineHeight);
    bind("lyricLetterSpacing", "input", ajustarLyricLetterSpacing);
    bind("lyricTextColor", "input", ajustarLyricTextColor);
    bind("lyricTextColor", "change", ajustarLyricTextColor);
    bind("lyricAccentColor", "input", ajustarLyricAccentColor);
    bind("lyricAccentColor", "change", ajustarLyricAccentColor);
});
"""

    html = header(titulo) + f"""
<style>
main{{
    width:100%;
    max-width:none;
}}

.songLayout{{
    width:100%;
    max-width:1360px;
    margin:20px auto;
    padding:0 20px;
    display:grid;
    grid-template-columns: 290px minmax(0, 1fr);
    gap:28px;
    align-items:start;
}}

.songControls{{
    position: sticky;
    top: 90px;
    background: #f4f4f4;
    overflow-y: auto;
}}

.controlCard{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:16px;
    padding:14px;
    box-shadow:0 2px 6px rgba(0,0,0,0.04);
    margin-bottom:9px;
}}

.songCenter{{
    min-width:0;
    width:100%;
    margin-top: 0px;
    padding-top: 10px;

}}

.songTitle{{
    margin: 4px 0 12px;
    font-size: clamp(36px, 3.5vw, 52px);
    line-height: 1.14;
    letter-spacing: -0.01em;
    overflow-wrap: anywhere;
}}

.controlCard .selectWrapper,
.controlCard .versionSelect {{
    width: 100%;
}}

.controlCard .versionSelect {{
    min-height: 40px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 0 10px;
    font-size: 16px;
}}

.lyricReader .chord {{
    font-size: 30px;
    line-height: 1.2;
    display: inline-block;
    margin-bottom: 6px;
}}

.lyricReader .lyricBox{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:28px;
    font-size:16px;
    line-height:1.7;
    color:#111827;
}}

.lyricReader .lyricBox p{{
    margin-bottom:18px;
}}

.songVideo{{
    position:sticky;
    top:90px;
    max-width:300px;
}}

.videoWrapper{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:10px;
}}

.videoWrapper iframe{{
    width:100%;
    height:210px;
    border:none;
    border-radius:10px;
}}
{video_dock_css}
.lyricReader {{
    --lyric-font-family: 'Georgia', 'Times New Roman', serif;
    --lyric-font-size: 18px;
    --lyric-line-height: 1.72;
    --lyric-letter-spacing: 0px;
    --lyric-text-color: #111827;
    --lyric-accent-color: #ff7a00;
    padding-top: 6px;
}}

.lyricReader .eyebrow {{
    margin: 0 0 6px;
}}

.lyricReader .lyricBox {{
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 28px;
    font-size: var(--lyric-font-size);
    line-height: var(--lyric-line-height);
    letter-spacing: var(--lyric-letter-spacing);
    color: var(--lyric-text-color);
    font-family: var(--lyric-font-family);
}}

.lyricReader .songTitle,
.lyricReader .eyebrow,
.lyricReader .chord {{
    color: var(--lyric-accent-color);
}}

.lyricReader .chord {{
    text-decoration: none;
    font-weight: 700;
}}

.lyricPanels {{
    display: grid;
    gap: 14px;
}}

.lyricPanels.compareMode {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
}}

.lyricPanels.compareMode .lyricBox {{
    min-width: 0;
    padding: 10px 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
}}

.lyricModeTabs {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 14px;
}}

.lyricPreviewBtn {{
    border: 1px solid rgba(255, 122, 0, 0.35);
    background: linear-gradient(135deg, rgba(255, 240, 226, 0.85), rgba(255, 222, 192, 0.72));
    backdrop-filter: blur(8px) saturate(130%);
    -webkit-backdrop-filter: blur(8px) saturate(130%);
    border-radius: 999px;
    padding: 8px 14px;
    font-weight: 800;
    cursor: pointer;
    color: #9a3412;
    font-size: 13px;
    line-height: 1;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}}

.lyricPreviewBtn.playing {{
    background: linear-gradient(135deg, rgba(255, 202, 149, 0.96), rgba(255, 140, 41, 0.9));
    color: #2b1200;
    border-color: rgba(255, 122, 0, 0.72);
    box-shadow: 0 6px 16px rgba(255, 122, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.48);
}}

.lyricModeBtn {{
    border: 1px solid rgba(148, 163, 184, 0.45);
    background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(255,255,255,0.48));
    backdrop-filter: blur(8px) saturate(130%);
    -webkit-backdrop-filter: blur(8px) saturate(130%);
    border-radius: 999px;
    padding: 8px 14px;
    font-weight: 800;
    cursor: pointer;
    color: #334155;
    font-size: 13px;
    line-height: 1;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}}

.lyricModeBtn:hover {{
    border-color: rgba(255, 122, 0, 0.45);
    color: #1f2937;
}}

.lyricModeBtn.is-active {{
    background: linear-gradient(135deg, rgba(255, 202, 149, 0.88), rgba(255, 140, 41, 0.78));
    color: #2b1200;
    border-color: rgba(255, 122, 0, 0.65);
    box-shadow: 0 6px 16px rgba(255, 122, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.48);
}}

.lyricPanels.compareMode #lyricOriginal {{
    color: #9ca3af;
}}

.lyricPanels.compareMode #lyricTraducao {{
    color: var(--lyric-text-color);
}}

.lyricStanzaDivider {{
    display: block;
    position: relative;
    height: 24px;
    margin: 12px 0 16px;
}}

.lyricStanzaDivider::before {{
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 1px;
    transform: translateY(-50%);
    background: linear-gradient(90deg, rgba(148, 163, 184, 0), rgba(148, 163, 184, .58), rgba(148, 163, 184, 0));
}}

.lyricStanzaDivider::after {{
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    transform: translate(-50%, -50%);
    background: rgba(148, 163, 184, 0.62);
    box-shadow: 0 0 0 5px rgba(255, 255, 255, .92);
}}

.lyricControlGrid {{
    display: grid;
    gap: 8px;
}}

.lyricControlRow {{
    display: grid;
    gap: 4px;
}}

.lyricControlRow label {{
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}}

.lyricControlRow select,
.lyricControlRow input[type="color"] {{
    width: 100%;
    height: 32px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    padding: 0 8px;
}}

.lyricControlRow input[type="color"] {{
    padding: 2px;
}}

.lyricControlRow input[type="range"] {{
    width: 100%;
}}

.lyricControlValue {{
    min-width: 46px;
    text-align: right;
    font-weight: 700;
    color: #111827;
    font-size: 12px;
}}

.quoteSelectionFab {{
    position: absolute;
    transform: translateX(-50%);
    z-index: 2200;
    border: 0;
    border-radius: 999px;
    padding: 9px 14px;
    background: #111827;
    color: #ffffff;
    font-size: 12px;
    font-weight: 800;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.28);
    cursor: pointer;
    opacity: 0;
    pointer-events: none;
    transition: opacity .18s ease;
}}

.quoteSelectionFab.show {{
    opacity: 1;
    pointer-events: auto;
}}

.quoteModal {{
    position: fixed;
    inset: 0;
    background: rgba(2, 6, 23, 0.58);
    display: none;
    align-items: center;
    justify-content: center;
    padding: 16px;
    z-index: 2500;
}}

.quoteModal.show {{
    display: flex;
}}

.quoteModalCard {{
    width: min(94vw, 760px);
    max-height: 92vh;
    overflow: auto;
    border-radius: 18px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    box-shadow: 0 24px 48px rgba(2, 6, 23, 0.26);
    padding: 16px;
}}

.quoteModalHeader {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}}

.quoteModalHeader strong {{
    font-size: 16px;
    color: #0f172a;
}}

.quoteCloseBtn {{
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    color: #111827;
    font-weight: 700;
    padding: 6px 10px;
    cursor: pointer;
}}

.quoteForm {{
    display: grid;
    gap: 10px;
    margin-bottom: 12px;
}}

.quoteForm label {{
    font-size: 12px;
    color: #475569;
    font-weight: 700;
    text-transform: uppercase;
}}

.quoteForm textarea,
.quoteForm input {{
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 10px;
    font-size: 14px;
    color: #111827;
    background: #ffffff;
}}

.quoteForm textarea {{
    min-height: 110px;
    resize: vertical;
}}

.quoteForm select {{
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 10px;
    font-size: 14px;
    color: #111827;
    background: #ffffff;
}}

.quoteActions {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}

.quoteActionBtn {{
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: #ffffff;
    color: #111827;
    font-weight: 700;
    padding: 8px 12px;
    cursor: pointer;
    text-decoration: none;
}}

.quoteActionBtn.primary {{
    background: #111827;
    color: #ffffff;
    border-color: #111827;
}}

.quotePreviewWrap {{
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #f8fafc;
    padding: 10px;
}}

.quotePreview {{
    width: 100%;
    border-radius: 10px;
    display: block;
}}

.lyricSuggestions {{
    margin-top: 22px;
}}

.lyricSuggestionsGrid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}}

.lyricSuggestionCard {{
    display: grid;
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    text-decoration: none;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 8px;
    transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease;
}}

.lyricSuggestionCard:hover {{
    border-color: #fdba74;
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}}

.lyricSuggestionThumb {{
    width: 56px;
    height: 56px;
    border-radius: 8px;
    object-fit: cover;
    background: #e5e7eb;
}}

.lyricSuggestionBody {{
    min-width: 0;
}}

.lyricSuggestionBody strong {{
    display: block;
    color: #0f172a;
    font-size: 14px;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.lyricSuggestionBody span {{
    display: block;
    margin-top: 4px;
    color: #64748b;
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

@media (max-width: 980px) {{
    .songLayout {{
        grid-template-columns: 1fr;
    }}

    .songControls {{
        position: static;
    }}

    .lyricPanels.compareMode {{
        grid-template-columns: 1fr;
    }}

    .lyricModeTabs {{
        gap: 6px;
    }}

    .lyricModeBtn {{
        padding: 8px 12px;
    }}
}}
</style>
<script>
function abrirImpressaoLetra(artista, musica) {{
    window.open(`/letra/${{artista}}/${{musica}}/print?translation=pt`, "_blank");
}}

let lyricPreviewAudio = null;
let lyricPreviewBtnAtual = null;

async function toggleLyricPreview(btn) {{
    const titleIdle = "Ouvir trecho";
    const titlePlaying = "Pausar trecho";
    let url = btn.dataset.preview || "";

    if (!url) {{
        try {{
            const r = await fetch(`/preview?artista=${{encodeURIComponent(btn.dataset.artista || "")}}&titulo=${{encodeURIComponent(btn.dataset.titulo || "")}}`);
            const data = await r.json();
            url = data.preview || "";
            btn.dataset.preview = url;
        }} catch (e) {{
            console.error("Erro preview:", e);
        }}
    }}

    if (!url) {{
        btn.textContent = "Sem preview";
        return;
    }}

    if (btn.audio) {{
        if (!btn.audio.paused) {{
            btn.audio.pause();
            btn.classList.remove("playing");
            btn.textContent = titleIdle;
            return;
        }}

        btn.audio.play();
        btn.classList.add("playing");
        btn.textContent = titlePlaying;
        return;
    }}

    if (lyricPreviewAudio) {{
        lyricPreviewAudio.pause();
        if (lyricPreviewBtnAtual) {{
            lyricPreviewBtnAtual.classList.remove("playing");
            lyricPreviewBtnAtual.textContent = titleIdle;
        }}
    }}

    const audio = new Audio(url);
    btn.audio = audio;
    lyricPreviewAudio = audio;
    lyricPreviewBtnAtual = btn;
    audio.play();
    btn.classList.add("playing");
    btn.textContent = titlePlaying;
    audio.onended = () => {{
        btn.classList.remove("playing");
        btn.textContent = titleIdle;
    }};
}}
{video_dock_js}
{lyric_prefs_js}
{quote_popup_js}
</script>
<div class="backWrapper lyricBack">
    <button class="backBtn" onclick="location.href='/artista/{slug}'">
        ← Voltar para músicas
    </button>
</div>

<div class="songLayout lyricDetailLayout">

    <!-- ESQUERDA -->
    <aside class="songControls lyricTools">

    
        <div class="controlCard">
            <div class="controlTitle">🎵 Versões</div>
            <div class="selectWrapper">
                <select class="versionSelect"
                    onchange="trocarVersao(this.value)">
                    {''.join([
                        f"<option value='{v_uid}' {'selected' if v_uid==uid else ''}>{v_titulo}</option>"
                        for v_uid, v_titulo in versoes
                    ])}
                </select>
            </div>
        </div>
        <div class="controlCard lyricPrefsCard">
            <div class="controlTitle">Fonte</div>
            <div class="lyricControlGrid" style="margin-top:12px;">
                <div class="lyricControlRow">
                    <label for="lyricFontFamily">Família</label>
                    <select id="lyricFontFamily" onchange="ajustarLyricFamilia(this.value)">
                        <option value="Georgia, 'Times New Roman', serif">Serif</option>
                        <option value="'Palatino Linotype', 'Book Antiqua', Palatino, serif">Palatino</option>
                        <option value="Cambria, 'Times New Roman', serif">Cambria</option>
                        <option value="Inter, system-ui, sans-serif">Sans</option>
                        <option value="Arial, Helvetica, sans-serif">Arial</option>
                        <option value="Verdana, Geneva, sans-serif">Verdana</option>
                        <option value="'Trebuchet MS', 'Lucida Sans Unicode', 'Lucida Grande', sans-serif">Trebuchet</option>
                        <option value="'Avenir Next', Avenir, 'Segoe UI', sans-serif">Avenir</option>
                        <option value="'Gill Sans', 'Segoe UI', sans-serif">Gill Sans</option>
                        <option value="ui-monospace, SFMono-Regular, Menlo, monospace">Mono</option>
                        <option value="'Courier New', Courier, monospace">Courier</option>
                    </select>
                </div>

                <div class="lyricControlRow">
                    <label for="lyricFontSize">Fonte</label>
                    <span class="lyricControlValue" id="lyricFontSizeValue">18px</span>
                </div>
                <input id="lyricFontSize" type="range" min="14" max="24" step="1" value="18" oninput="ajustarLyricFonte(this.value)">

                <div class="lyricControlRow">
                    <label for="lyricLineHeight">Espaço</label>
                    <span class="lyricControlValue" id="lyricLineHeightValue">1.7</span>
                </div>
                <input id="lyricLineHeight" type="range" min="1.3" max="2.2" step="0.1" value="1.7" oninput="ajustarLyricLineHeight(this.value)">

                <div class="lyricControlRow">
                    <label for="lyricLetterSpacing">Letra</label>
                    <span class="lyricControlValue" id="lyricLetterSpacingValue">0px</span>
                </div>
                <input id="lyricLetterSpacing" type="range" min="-0.5" max="1.8" step="0.1" value="0" oninput="ajustarLyricLetterSpacing(this.value)">

                <div class="lyricControlRow">
                    <label for="lyricTextColor">Cor do texto</label>
                    <input id="lyricTextColor" type="color" value="#111827" onchange="ajustarLyricTextColor(this.value)">
                </div>

                <div class="lyricControlRow">
                    <label for="lyricAccentColor">Cor destaque</label>
                    <input id="lyricAccentColor" type="color" value="#ff7a00" onchange="ajustarLyricAccentColor(this.value)">
                </div>

                <button class="controlBtn" type="button" onclick="resetLyricPrefs()">Reset fonte</button>
            </div>
        </div>
        <div class="controlCard lyricActionCard">
            <div class="controlTitle">Estudo</div>
            <button type="button" onclick="abrirImpressaoLetra('{artista_slug}', '{musica_slug}')">Imprimir</button>
        </div>
    </aside>

    <!-- 🔥 LETRA -->
    <main class="songCenter lyricReader">
        <p class="eyebrow">Letra</p>\n        <h1 class="songTitle" id="lyricMainTitle" data-original-title="{html_escape.escape(titulo, quote=True)}" data-translation-title="{html_escape.escape(titulo_traduzido, quote=True)}">{titulo}</h1>
        <p>
            <a class="chord" href="/artista/{artista_slug}">
                {artista_nome}
            </a>
        </p>

        <div class="lyricModeTabs" role="tablist" aria-label="Modos de leitura">
            <button class="lyricModeBtn is-active" type="button" data-mode="normal" onclick="setLyricMode('normal')">Letra</button>
            <button class="lyricModeBtn" type="button" data-mode="translation" onclick="setLyricMode('translation')">Tradução</button>
            <button class="lyricModeBtn" type="button" data-mode="side" onclick="setLyricMode('side')">Letra + tradução</button>
            <button class="lyricPreviewBtn" type="button"
                    data-artista="{html_escape.escape(artista_nome, quote=True)}"
                    data-titulo="{html_escape.escape(preview_titulo, quote=True)}"
                    data-preview=""
                    onclick="toggleLyricPreview(this)">Ouvir trecho</button>
        </div>

        <div class="lyricPanels" id="lyricPanels">
            <div class="lyricBox" id="lyricOriginal">
                {letra_html}
            </div>
            <div class="lyricBox" id="lyricTraducao" style="display:none;">
                {traducao_html}
            </div>
        </div>
        {sugestoes_html}
    <script>
let traduzido = false
let letraOriginalCache = ""


</script>


    </main>

</div>

{video_dock_html}

<button type="button" class="quoteSelectionFab" id="quoteSelectionFab" onclick="openQuoteModal()">
    Criar citacao
</button>

<div class="quoteModal" id="quoteModal">
    <div class="quoteModalCard" role="dialog" aria-modal="true" aria-label="Criar citacao poetica">
        <div class="quoteModalHeader">
            <strong>Criar Imagem de Citacao</strong>
            <button type="button" class="quoteCloseBtn" onclick="closeQuoteModal()">Fechar</button>
        </div>

        <div class="quoteForm">
            <label for="quoteTextInput">Trecho</label>
            <textarea id="quoteTextInput" placeholder="Selecione um trecho da letra para começar..."></textarea>

            <label for="quoteArtistInput">Artista</label>
            <input id="quoteArtistInput" value="{html_escape.escape(artista_nome, quote=True)}" />

            <label for="quoteBackgroundInput">Cor do fundo</label>
            <input id="quoteBackgroundInput" type="color" value="#111827" />

            <label for="quoteFontFamilyInput">Fonte da citacao</label>
            <select id="quoteFontFamilyInput">
                <option value="Georgia, 'Times New Roman', serif">Georgia</option>
                <option value="'Times New Roman', Times, serif">Times New Roman</option>
                <option value="Palatino, 'Palatino Linotype', serif">Palatino</option>
                <option value="Cambria, 'Times New Roman', serif">Cambria</option>
                <option value="'Trebuchet MS', 'Lucida Sans Unicode', 'Lucida Grande', sans-serif">Trebuchet</option>
                <option value="Arial, Helvetica, sans-serif">Arial</option>
                <option value="Verdana, Geneva, sans-serif">Verdana</option>
                <option value="'Avenir Next', Avenir, 'Segoe UI', sans-serif">Avenir</option>
            </select>

            <label for="quoteSignatureModeInput">Assinatura</label>
            <select id="quoteSignatureModeInput">
                <option value="artista">- artista</option>
                <option value="musica">- musica (artista)</option>
            </select>

            <label for="quoteFormatInput">Formato da imagem</label>
            <select id="quoteFormatInput">
                <option value="square">Quadrado 1:1</option>
                <option value="wide">Wide 16:9</option>
                <option value="story">Story 9:16</option>
            </select>
        </div>

        <div class="quoteActions">
            <button type="button" class="quoteActionBtn primary" onclick="renderQuoteImage()">Atualizar imagem</button>
            <a id="quoteDownloadLink" class="quoteActionBtn" href="#" download="citacao-poetica.png">Baixar imagem</a>
        </div>

        <div class="quotePreviewWrap">
            <img id="quotePreview" class="quotePreview" alt="Pre-visualizacao da citacao" />
            <canvas id="quoteCanvas" width="1080" height="1080" style="display:none;"></canvas>
        </div>
    </div>
</div>

</main>
"""
    return html
    

@app.route("/letra/<artista>/<musica>/print")
def imprimir_letra(artista, musica):
    letra_html, traducao_html = procura_letra(artista, musica)

    if not letra_html:
        letra_html = "<p>Letra nao encontrada.</p>"

    titulo = musica.replace("-", " ").title()
    artista_nome = artista.replace("-", " ").title()
    mostrar_traducao = request.args.get("translation") == "pt" and bool(traducao_html)

    traducao_coluna = ""
    if mostrar_traducao:
        traducao_coluna = f"""
        <section class="printLyricColumn">
            <h2>Traducao</h2>
            <div class="printLyricText">{traducao_html}</div>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>{titulo} - impressao</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/css/app.css">
</head>
<body class="printBody">
    <main class="printSheet">
        <header class="printHeader">
            <div>
                <p>CifrasFlix</p>
                <h1>{titulo}</h1>
                <span>{artista_nome}</span>
            </div>
            <div class="printToolbar">
                <button type="button" onclick="window.print()">Imprimir</button>
                <a href="/letra/{artista}/{musica}">Voltar</a>
            </div>
        </header>

        <div class="printMeta">
            <span>Original</span>
            {"<span>Traducao PT</span>" if mostrar_traducao else ""}
        </div>

        <div class="printColumns {'hasTranslation' if mostrar_traducao else ''}">
            <section class="printLyricColumn">
                <h2>Letra original</h2>
                <div class="printLyricText">{letra_html}</div>
            </section>
            {traducao_coluna}
        </div>
    </main>
</body>
</html>"""
    return html


from flask import request, jsonify
from deep_translator import GoogleTranslator

@app.route("/traduzir-letra", methods=["POST"])
def traduzir_letra():
    data = request.get_json()

    artista = data.get("artista")
    musica = data.get("musica")

    letra_html = procura_letra(artista, musica)

    if not letra_html:
        return jsonify({"erro": "letra não encontrada"})

    try:
        texto_puro = BeautifulSoup(letra_html, "html.parser").get_text("\n")

        traducao = GoogleTranslator(
            source="auto",
            target="pt"
        ).translate(texto_puro)

        # mantém quebras
        traducao_html = "<p>" + traducao.replace("\n", "</p><p>") + "</p>"

        return jsonify({"traducao": traducao_html})

    except Exception as e:
        return jsonify({"erro": str(e)})
      

from flask import Response

@app.route("/capa_album/<int:album_id>")
def capa_album(album_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT capa_blob
        FROM albuns
        WHERE id=?
    """, (album_id,))

    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return "", 404

    return Response(
        row[0],
        mimetype="image/jpeg"
    )
