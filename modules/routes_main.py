def destacar_acordes(texto):


    """
    Garante span em C#, D#, F#, G#, A#
    mesmo dentro de textos com acento.
    """

    return texto

def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()

    

@app.route("/debug/banco")
def debug_banco():
    conn = sqlite3.connect("cifras.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    resultado = {}

    # pegar tabelas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [t["name"] for t in cur.fetchall()]

    for tabela in tabelas:
        cur.execute(f"SELECT * FROM {tabela}")
        resultado[tabela] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return jsonify(resultado)
    
# ==========================================
# ROTAS
# ==========================================
@app.route("/")
def home():
    import math

    page = int(request.args.get("page", 1))
    per_page = 48
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM artistas")
    total = c.fetchone()[0]
    total_pages = max(1, math.ceil(total / per_page))

    c.execute("""
        SELECT nome, slug
        FROM artistas
        ORDER BY nome COLLATE NOCASE
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    artistas = c.fetchall()

    dashboard = home_dashboard_data(c)
    conn.close()

    html = header("CifrasFlix - Central")

    html += """
    <section class="dashboardHero">
        <div>
            <p class="eyebrow">Central do sistema</p>
            <h1>CifrasFlix Studio</h1>
            <p class="heroCopy">Biblioteca, discografia, letras, capas e importadores em um fluxo unico.</p>
        </div>
        <div class="heroActions">
            <a class="primaryAction" href="/importar">Importar cifras</a>
            <a class="secondaryAction" href="/albuns">Ver discografia</a>
            <a class="secondaryAction" href="/treinar/">Treinar Piano</a>
        </div>
    </section>

    <section class="statsGrid" aria-label="Resumo da biblioteca">
    """

    for label, value, hint in dashboard["stats"]:
        html += f"""
        <article class="statCard">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{hint}</small>
        </article>
        """

    html += """
    </section>

    <section class="systemGrid">
        <div class="systemPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Modulos</p>
                    <h2>Ferramentas disponiveis</h2>
                </div>
            </div>
            <div class="moduleGrid">
    """

    for title, desc, href, action in dashboard["modules"]:
        html += f"""
        <a class="moduleCard" href="{href}">
            <strong>{title}</strong>
            <span>{desc}</span>
            <em>{action}</em>
        </a>
        """

    html += """
            </div>
        </div>

        <aside class="systemPanel compactPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Atividade</p>
                    <h2>Destaques</h2>
                </div>
            </div>
            <div class="rankingList">
    """

    if dashboard["top_artistas"]:
        for index, (nome, slug, total_musicas, total_views) in enumerate(dashboard["top_artistas"], start=1):
            html += f"""
            <a class="rankingItem" href="/artista/{slug}">
                <b>{index}</b>
                <span>{nome}</span>
                <small>{fmt_int(total_views)} views - {fmt_int(total_musicas)} musicas</small>
            </a>
            """
    else:
        html += '<p class="emptyState">Sem artistas para destacar ainda.</p>'

    html += """
            </div>
        </aside>
    </section>

    <section class="systemPanel">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Biblioteca</p>
                <h2>Artistas</h2>
            </div>
            <span class="pageInfo">Pagina """ + f"{page} de {total_pages}" + """</span>
        </div>
        <div class="artistGrid">
    """

    for nome, slug in artistas:
        inicial = (nome[:1] or "?").upper()
        html += f"""
        <a class="artistCardHome" href="/artista/{slug}?page={page}">
            <span class="artistAvatar">{inicial}</span>
            <strong>{nome}</strong>
        </a>
        """

    html += "</div>"

    if total_pages > 1:
        html += '<nav class="pagination" aria-label="Paginacao de artistas">'
        if page > 1:
            html += f'<a href="/?page={page-1}" class="pageBtn">Anterior</a>'
        html += f'<span class="pageInfo">Pagina {page} de {total_pages}</span>'
        if page < total_pages:
            html += f'<a href="/?page={page+1}" class="pageBtn">Proxima</a>'
        html += "</nav>"

    html += """
    </section>
    </main>
    """

    return html


@app.route("/flix-play")
def flix_play():
    import html as html_escape
    import random
    q = (request.args.get("q") or "").strip()

    def limpar_titulo_gp(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        return valor

    def _carregar_gp_catalogo():
        _refresh_guitarpro_index_txt()
        idx_path = _guitarpro_index_file_path()
        if not idx_path.exists():
            return []

        vistos = set()
        catalogo = []
        try:
            conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        for linha in conteudo.splitlines():
            if not linha.strip():
                continue
            partes = linha.split("\t")
            if len(partes) < 5:
                continue

            artista_norm = (partes[0] or "").strip()
            musica_norm = (partes[1] or "").strip()
            file_name = (partes[2] or "").strip()
            artista_raw = (partes[3] or "").strip()
            musica_raw = (partes[4] or "").strip()
            if not musica_norm or not file_name:
                continue

            chave = (artista_norm, musica_norm)
            if chave in vistos:
                continue
            vistos.add(chave)

            catalogo.append(
                {
                    "artista_nome": artista_raw or artista_norm.title(),
                    "musica_titulo": limpar_titulo_gp(musica_raw or musica_norm.title()),
                    "artista_norm": artista_norm,
                    "musica_norm": musica_norm,
                }
            )

        return catalogo

    catalogo_gp = _carregar_gp_catalogo()

    sugestoes = random.sample(catalogo_gp, min(6, len(catalogo_gp))) if catalogo_gp else []

    def _card_html(row):
        titulo = (row["musica_titulo"] or "").strip()
        artista_nome = (row["artista_nome"] or "").strip()
        artista_slug = normalizar_slug(artista_nome)
        lyric_link = f"/letra/{artista_slug}/{normalizar_slug(titulo)}"
        play_link = f"/tocador-gp4/{artista_slug}/{normalizar_slug(titulo)}"
        train_link = f"/treinar/{artista_slug}/{normalizar_slug(titulo)}"
        destino = play_link
        acao_html = f'<a class="flixCardAction" href="{play_link}">Tocar no FlixPlayer</a>'

        return f"""
        <article class="flixSongCard" role="button" tabindex="0" onclick="location.href='{destino}'" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();location.href='{destino}'}}">
            <div class="flixSongInfo">
                <p class="eyebrow">{html_escape.escape(artista_nome)}</p>
                <h3><a href="{play_link}">{html_escape.escape(titulo)}</a></h3>
                <div class="flixCardLinks">
                    {acao_html}
                    <a class="flixCardAction ghost" href="{lyric_link}">Ver letra</a>
                    <a class="flixCardAction alt" href="{train_link}">Treinar</a>
                </div>
            </div>
        </article>
        """

    html = header("Flix Play") + f"""
    <style>
    .flixHero {{
        margin-top: 18px;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        background: radial-gradient(circle at 16% -20%, rgba(255, 122, 0, 0.18), transparent 45%), #ffffff;
    }}
    .flixHero h1 {{
        margin: 0;
        font-size: clamp(30px, 4vw, 48px);
    }}
    .flixHero p {{
        margin: 10px 0 0;
        color: #6b7280;
        max-width: 760px;
    }}
    .flixSearchBar {{
        margin-top: 18px;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
    }}
    .flixSearchBar input {{
        height: 46px;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 0 14px;
        font-size: 15px;
    }}
    .flixSearchBar button {{
        height: 46px;
        border-radius: 12px;
        border: 1px solid #fdba74;
        background: linear-gradient(135deg, #ffd29d, #ff9b47);
        color: #2b1200;
        font-weight: 800;
        padding: 0 18px;
        cursor: pointer;
    }}
    .flixQuickActions {{
        margin-top: 10px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }}
    .flixQuickBtn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 34px;
        border-radius: 999px;
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        color: #334155;
        padding: 0 12px;
        font-size: 12px;
        font-weight: 800;
        text-decoration: none;
    }}
    .flixSection {{
        margin-top: 22px;
    }}
    .flixSuggestionsSection {{
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 16px;
        background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 52%, #ecfeff 100%);
    }}
    .flixSuggestionsSection .sectionHeader h2 {{
        color: #312e81;
    }}
    .flixSuggestionsSection .eyebrow {{
        color: #4338ca;
        font-weight: 800;
        letter-spacing: .04em;
    }}
    .flixSuggestionsSection .flixSongCard {{
        border-color: #c7d2fe;
        background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
        box-shadow: 0 8px 22px rgba(79, 70, 229, 0.10);
    }}
    .flixSuggestionsSection .flixSongCard:hover {{
        border-color: #6366f1;
        box-shadow: 0 12px 26px rgba(79, 70, 229, 0.16);
    }}
    .flixSuggestionsSection .flixCardAction {{
        border-color: #818cf8;
        background: #eef2ff;
        color: #3730a3;
    }}
    .flixSuggestionsSection .flixCardAction.ghost {{
        border-color: #c7d2fe;
        background: #ffffff;
        color: #312e81;
    }}
    .flixGrid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
    }}
    .flixSongCard {{
        display: block;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        background: #ffffff;
        padding: 12px;
        cursor: pointer;
        transition: border-color .16s ease, transform .16s ease, box-shadow .16s ease;
    }}
    .flixSongCard:hover {{
        border-color: #fdba74;
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
    }}
    .flixSongInfo h3 {{
        margin: 0;
        font-size: 17px;
        line-height: 1.25;
    }}
    .flixSongInfo h3 a {{
        color: inherit;
        text-decoration: none;
    }}
    .flixSongInfo .eyebrow {{
        margin: 0 0 5px;
    }}
    .flixSearchSection .flixSongCard.withThumb {{
        display: grid;
        grid-template-columns: 60px minmax(0, 1fr);
        gap: 12px;
        align-items: center;
    }}
    .flixSearchThumb {{
        width: 60px;
        height: 60px;
        border-radius: 10px;
        object-fit: cover;
        border: 1px solid #dbeafe;
        background: #f8fafc;
    }}
    .flixAlbumName {{
        margin: 6px 0 0;
        color: #64748b;
        font-size: 13px;
    }}
    .flixCardLinks {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
    }}
    .flixCardAction {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 32px;
        border-radius: 999px;
        border: 1px solid #fdba74;
        background: #fff7ed;
        color: #9a3412;
        padding: 0 10px;
        font-size: 12px;
        font-weight: 800;
        text-decoration: none;
    }}
    .flixCardAction.ghost {{
        border-color: #cbd5e1;
        background: #ffffff;
        color: #334155;
    }}
    .flixCardAction.alt {{
        border-color: #cbd5e1;
        background: #f8fafc;
        color: #334155;
    }}
    .flixEmpty {{
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 14px;
        color: #64748b;
        background: #f8fafc;
    }}
    @media (max-width: 720px) {{
        .flixSearchBar {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>

    <section class="flixHero">
        <p class="eyebrow">Flix Play</p>
        <h1>Bem vindo ao Flix Play</h1>
        <p>Digite uma musica ou artista para aprender a tocar.</p>
        <form class="flixSearchBar" id="flixSearchForm" onsubmit="return false;">
            <input type="text" id="flixSearchInput" placeholder="Ex: Animals, Maroon 5, The Kill..." autocomplete="off" value="{html_escape.escape(q)}">
            <button type="button" id="flixSearchBtn">Buscar</button>
        </form>
        <div class="flixQuickActions">
            <a class="flixQuickBtn" href="/treinar/">Treinar Piano</a>
        </div>
    </section>
    """

    html += """
    <section class="flixSection flixSearchSection" id="flixSearchSection" style="display:none;">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Resultados</p>
                <h2 id="flixSearchTitle">Busca</h2>
            </div>
        </div>
        <div class="flixGrid" id="flixSearchGrid"></div>
    """

    html += """
        </div>
    </section>
    """

    html += """
    <section class="flixSection flixSuggestionsSection">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Sugestoes</p>
                <h2>Comece por aqui</h2>
            </div>
        </div>
        <div class="flixGrid">
    """

    if sugestoes:
        for row in sugestoes:
            html += _card_html(row)
    else:
        html += '<div class="flixEmpty">Nenhuma sugestao GP encontrada no indice.</div>'

    html += """
        </div>
    </section>
        <script>
        (function () {
            const input = document.getElementById("flixSearchInput");
            const btn = document.getElementById("flixSearchBtn");
            const section = document.getElementById("flixSearchSection");
            const grid = document.getElementById("flixSearchGrid");
            const title = document.getElementById("flixSearchTitle");

            if (!input || !btn || !section || !grid || !title) return;

            const esc = (v) => String(v || "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\"/g, "&quot;")
                .replace(/'/g, "&#39;");

            function card(item) {
                const hasThumb = !!item.album_thumb;
                const albumLine = item.album_name ? `<p class="flixAlbumName">${esc(item.album_name)}</p>` : "";
                return `
                    <article class="flixSongCard ${hasThumb ? "withThumb" : ""}" role="button" tabindex="0" onclick="location.href='${esc(item.play_url)}'" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();location.href='${esc(item.play_url)}'}">
                        ${hasThumb ? `<img class="flixSearchThumb" src="${esc(item.album_thumb)}" alt="${esc(item.album_name || item.title)}">` : ""}
                        <div class="flixSongInfo">
                            <p class="eyebrow">${esc(item.artist)}</p>
                            <h3><a href="${esc(item.play_url)}">${esc(item.title)}</a></h3>
                            ${albumLine}
                            <div class="flixCardLinks">
                                <a class="flixCardAction" href="${esc(item.play_url)}">Tocar no FlixPlayer</a>
                                <a class="flixCardAction ghost" href="${esc(item.lyric_url)}">Ver letra</a>
                                <a class="flixCardAction alt" href="${esc(item.train_url)}">Treinar</a>
                            </div>
                        </div>
                    </article>
                `;
            }

            async function runSearch() {
                const q = (input.value || "").trim();
                if (!q) {
                    section.style.display = "none";
                    grid.innerHTML = "";
                    return;
                }

                title.textContent = `Busca por "${q}"`;
                section.style.display = "block";
                grid.innerHTML = '<div class="flixEmpty">Buscando...</div>';

                try {
                    const r = await fetch(`/api/flix-play/search?q=${encodeURIComponent(q)}&limit=10`);
                    const data = await r.json();
                    const items = Array.isArray(data.results) ? data.results : [];
                    if (!items.length) {
                        grid.innerHTML = '<div class="flixEmpty">Nada encontrado para essa busca. Tente outro termo.</div>';
                        return;
                    }
                    grid.innerHTML = items.map(card).join("");
                } catch (_) {
                    grid.innerHTML = '<div class="flixEmpty">Falha ao buscar agora. Tente novamente.</div>';
                }
            }

            let timer = null;
            input.addEventListener("input", () => {
                clearTimeout(timer);
                timer = setTimeout(runSearch, 220);
            });
            btn.addEventListener("click", runSearch);
            input.addEventListener("keydown", (ev) => {
                if (ev.key === "Enter") {
                    ev.preventDefault();
                    runSearch();
                }
            });

            if ((input.value || "").trim()) {
                runSearch();
            }
        })();
        </script>
    </main>
    """

    return html


@app.route("/api/flix-play/search")
def flix_play_search_api():
    q = (request.args.get("q") or "").strip()
    try:
        limit = int(request.args.get("limit") or 10)
    except Exception:
        limit = 10
    limit = max(1, min(10, limit))

    if not q:
        return jsonify({"results": []})

    def limpar_titulo_gp(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        return valor

    def titulo_exibicao(texto):
        valor = (texto or "").strip()
        if not valor:
            return ""
        # Remove only trailing version markers from visual title, preserving raw value for slug resolution.
        valor = re.sub(r"\s*\((?:ver\.?\s*)?\d+\)\s*$", "", valor, flags=re.IGNORECASE)
        return valor.strip()

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    if not idx_path.exists():
        return jsonify({"results": []})

    q_norm = _normalizar_guitarpro_nome(q)
    if not q_norm:
        return jsonify({"results": []})
    q_flat = q_norm.replace(" ", "")
    q_tokens = [tok for tok in q_norm.split(" ") if tok]

    out = []
    vistos = set()
    conn = None
    cur = None

    def _album_info_for_track(artista_slug, musica_slug, musica_titulo):
        if not cur:
            return ("", "")

        try:
            slug_base = re.sub(r"-(?:ver-\d+|\d+)$", "", musica_slug or "").strip("-")
            titulo_base_txt = re.sub(r"\s*\(.*?\)\s*$", "", (musica_titulo or "").strip())
            titulo_base_like = f"{titulo_base_txt} (%" if titulo_base_txt else ""
            artista_hint_like = f"%{(artista_slug or '').replace('-', ' ')}%"
            cur.execute(
                """
                SELECT
                    al.id AS album_id,
                    al.nome AS album_nome,
                    COALESCE(al.capa, '') AS album_capa
                FROM cancao c
                JOIN albuns al ON al.id = c.album_id
                JOIN artistas ar ON ar.id = al.artista_id
                WHERE (ar.slug = ? OR ar.slug = 'unknown')
                  AND (
                    c.cancao_slug = ?
                    OR c.cancao_slug = ?
                    OR c.cancao_slug LIKE ?
                    OR LOWER(TRIM(c.titulo)) = LOWER(TRIM(?))
                    OR LOWER(TRIM(c.titulo)) LIKE LOWER(TRIM(?))
                  )
                ORDER BY
                    CASE
                        WHEN ar.slug = ? THEN 0
                        WHEN ar.slug = 'unknown' AND LOWER(COALESCE(al.nome, '')) LIKE LOWER(?) THEN 1
                        WHEN ar.slug = 'unknown' THEN 2
                        ELSE 9
                    END,
                    CASE
                        WHEN c.cancao_slug = ? THEN 0
                        WHEN c.cancao_slug = ? THEN 1
                        WHEN LOWER(TRIM(c.titulo)) = LOWER(TRIM(?)) THEN 2
                        WHEN LOWER(TRIM(c.titulo)) LIKE LOWER(TRIM(?)) THEN 3
                        WHEN c.cancao_slug LIKE ? THEN 4
                        ELSE 8
                    END,
                    c.id
                LIMIT 1
                """,
                (
                    artista_slug,
                    musica_slug,
                    musica_slug,
                    slug_base,
                    titulo_base_txt,
                    titulo_base_like,
                    artista_slug,
                    artista_hint_like,
                    musica_slug,
                    slug_base,
                    titulo_base_txt,
                    titulo_base_like,
                    f"{slug_base}-%",
                ),
            )
            row = cur.fetchone()
            if not row:
                return ("", "")

            album_nome = (row[1] or "").strip()
            capa_raw = (row[2] or "").strip()
            if capa_raw and capa_raw.lower() not in {"null", "none", "nan"}:
                return (album_nome, capa_raw)

            return (album_nome, "")
        except Exception:
            return ("", "")

        return ("", "")

    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return jsonify({"results": []})

    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
    except Exception:
        conn = None
        cur = None

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 5:
            continue

        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        artista_nome = (partes[3] or artista_norm.title()).strip()
        musica_titulo = limpar_titulo_gp((partes[4] or musica_norm.title()).strip())
        musica_titulo_view = titulo_exibicao(musica_titulo) or musica_titulo
        if not artista_norm or not musica_norm:
            continue

        artista_raw_norm = _normalizar_guitarpro_nome(artista_nome)
        musica_raw_norm = _normalizar_guitarpro_nome(musica_titulo)
        artista_raw_low = artista_nome.lower()
        musica_raw_low = musica_titulo.lower()
        artista_flat = (artista_norm or artista_raw_norm).replace(" ", "")
        musica_flat = (musica_norm or musica_raw_norm).replace(" ", "")
        q_low = q.lower()
        combined_norm = " ".join(
            [artista_norm, musica_norm, artista_raw_norm, musica_raw_norm]
        ).strip()
        token_match = bool(q_tokens) and all(tok in combined_norm for tok in q_tokens)

        direct_match = not (
            q_norm not in artista_norm
            and q_norm not in musica_norm
            and q_norm not in artista_raw_norm
            and q_norm not in musica_raw_norm
            and q_flat not in artista_flat
            and q_flat not in musica_flat
            and q_low not in artista_raw_low
            and q_low not in musica_raw_low
        )

        if not direct_match and not token_match:
            continue

        chave = (artista_norm, musica_norm)
        if chave in vistos:
            continue
        vistos.add(chave)

        artista_slug = normalizar_slug(artista_nome)
        musica_slug = normalizar_slug(musica_titulo)
        musica_slug_padrao = normalizar_slug(musica_titulo_view) or musica_slug
        album_nome, album_thumb = _album_info_for_track(artista_slug, musica_slug, musica_titulo)
        out.append(
            {
                "artist": artista_nome,
                "title": musica_titulo_view,
                "play_url": f"/tocador-gp4/{artista_slug}/{musica_slug_padrao}",
                "lyric_url": f"/letra/{artista_slug}/{musica_slug}",
                "train_url": f"/treinar/{artista_slug}/{musica_slug}",
                "album_name": album_nome,
                "album_thumb": album_thumb,
            }
        )

        if len(out) >= limit:
            break

    if conn:
        conn.close()

    return jsonify({"results": out})


@app.route("/treinar/")
@app.route("/treinar/<artista>/<musica>")
def treinar_piano(artista="", musica=""):
    import html as html_escape

    artista_nome = (artista or "").replace("-", " ").strip().title()
    musica_nome = (musica or "").replace("-", " ").strip().title()
    modo_livre = not (artista or musica)

    html = header("Treinar Piano" + (" - " + musica_nome if musica_nome else ""))
    html += f"""
    <script src="https://cdn.jsdelivr.net/npm/jzz"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-midi-gm"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-synth-tiny"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-kbd"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-midi-smf"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-pad"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-slider"></script>
    <style>
        .treinarPage {{
            margin: 0;
            background: #eef2f7;
            color: #1f2937;
            font-family: 'Segoe UI', Tahoma, sans-serif;
        }}
        .treinarPage.wrap {{
            max-width: 1160px;
            margin: 18px auto;
            padding: 0 14px 30px;
        }}
        .treinarPage .globalCard {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #dbe4ee;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 14px 36px rgba(15, 23, 42, 0.10);
        }}
        .treinarPage .sectionDivider {{
            height: 1px;
            background: linear-gradient(90deg, rgba(148, 163, 184, 0.05), rgba(148, 163, 184, 0.5), rgba(148, 163, 184, 0.05));
            margin: 14px 0;
        }}
        .treinarPage .head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .treinarPage .head a {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 34px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.4);
            color: #334155;
            text-decoration: none;
            padding: 0 13px;
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(4px);
        }}
        .treinarPage .headMeta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 2px;
        }}
        .treinarPage .metaChip {{
            display: inline-flex;
            align-items: center;
            min-height: 26px;
            padding: 0 10px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(255, 255, 255, 0.7);
            color: #475569;
            font-size: 12px;
            font-weight: 700;
        }}
        .treinarPage h1 {{ margin: 0; font-size: 28px; letter-spacing: 0.2px; }}
        .treinarPage .meta {{ color: #64748b; margin-top: 4px; font-size: 13px; }}
        .treinarPage h2 {{
            margin: 0 0 10px;
            font-size: 15px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #475569;
        }}
        .treinarPage .instrumentHeader {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .treinarPage .controls {{
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 10px;
        }}
        .treinarPage .controlGroup {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.72);
            padding: 7px 10px;
        }}
        .treinarPage label {{ font-size: 13px; color: #334155; }}
        .treinarPage input[type=range] {{ width: 170px; }}
        .treinarPage #piano {{ margin: 10px auto; overflow-x: auto; }}
        .treinarPage .note-hint {{ color: #64748b; font-size: 12px; }}
        .treinarPage .instrument-name {{
            font-size: 13px;
            font-weight: 700;
            color: #1f2937;
            margin: 0;
            white-space: nowrap;
        }}
        .treinarPage .extra-controls {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 6px;
        }}
        .treinarPage .extra-controls button {{
            border: 1px solid rgba(148, 163, 184, 0.38);
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            border-radius: 8px;
            padding: 6px 10px;
            cursor: pointer;
            backdrop-filter: blur(4px);
        }}
        .treinarPage .extra-controls button:disabled {{
            opacity: 0.42;
            cursor: not-allowed;
        }}
        .treinarPage .statusPill {{
            display: inline-flex;
            align-items: center;
            min-height: 32px;
            border: 1px solid rgba(148, 163, 184, 0.38);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            font-size: 12px;
            font-weight: 700;
            padding: 0 12px;
        }}
        .treinarPage .instrumentMenu {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 4px;
        }}
        .treinarPage .menu-btn {{
            border: 1px solid rgba(148, 163, 184, 0.38);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            padding: 8px 12px;
            cursor: pointer;
            font-weight: 700;
            backdrop-filter: blur(4px);
        }}
        .treinarPage .menu-btn:hover {{
            background: rgba(226, 232, 240, 0.95);
            border-color: rgba(99, 102, 241, 0.55);
            color: #312e81;
        }}
        .treinarOverlay {{
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.24);
            backdrop-filter: blur(3px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }}
        .treinarOverlay .overlay-content {{
            width: min(360px, 92vw);
            max-height: 78vh;
            overflow: auto;
            border-radius: 12px;
            border: 1px solid #d1d9e2;
            background: #ffffff;
            padding: 10px;
        }}
        .treinarPage .instrument {{
            padding: 9px 10px;
            border-radius: 8px;
            border: 1px solid #dbe4ee;
            margin-bottom: 8px;
            cursor: pointer;
            color: #334155;
            background: rgba(248, 250, 252, 0.9);
        }}
        .treinarPage .instrument:hover {{
            border-color: #93c5fd;
            background: #eef6ff;
        }}
        .treinarPage #controlArea {{
            position: relative;
            width: 320px;
            height: 165px;
        }}
        .treinarPage #pad, .treinarPage #sld1, .treinarPage #sld2 {{ position: absolute; }}
        .treinarPage #pad {{ left: 70px; top: 0; }}
        .treinarPage #sld1 {{ left: 30px; top: 0; }}
        .treinarPage #sld2 {{ left: 0; top: 0; }}
        .treinarPage #piano [data-kbd]::after {{
            content: attr(data-kbd);
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            bottom: 8px;
            font-size: 10px;
            font-weight: 800;
            line-height: 1;
            color: #0f172a;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.6);
            border-radius: 999px;
            padding: 2px 6px;
            pointer-events: none;
            white-space: nowrap;
        }}
        .treinarPage #piano [data-kbd-black="1"]::after {{
            bottom: 6px;
            font-size: 9px;
            color: #e2e8f0;
            background: rgba(15, 23, 42, 0.92);
            border-color: rgba(100, 116, 139, 0.9);
        }}
    </style>

    <section class="wrap treinarPage">
        <div class="globalCard">
            <div class="head">
                <div>
                    <h1>Treinar no Piano</h1>
                    <div class="meta">{"Modo livre" if modo_livre else html_escape.escape(artista_nome) + " - " + html_escape.escape(musica_nome)}</div>
                </div>
                <a href="{'/flix-play' if modo_livre else '/tocador-gp4/' + html_escape.escape(artista) + '/' + html_escape.escape(musica)}">{'Voltar ao Flix Play' if modo_livre else 'Voltar ao tocador'}</a>
            </div>
            <div class="headMeta">
                <span class="metaChip">Teclado com atalhos visiveis</span>
                <span class="metaChip">Gravacao e exportacao MIDI</span>
                <span class="metaChip">Troca rapida de timbre</span>
            </div>
            <div class="sectionDivider"></div>

            <div class="instrumentHeader">
                <h2>Instrumentos</h2>
                <div class="instrument-name" id="instrumentName">Instrumento: Piano</div>
            </div>
            <div class="instrumentMenu" id="menu"></div>

            <div class="sectionDivider"></div>

            <div class="controls">
                <label class="controlGroup">Volume <input type="range" id="volume" min="0" max="127" value="100"></label>
                <label class="controlGroup">Oitava <input type="range" id="octave" min="2" max="7" value="4"></label>
            </div>
            <div class="extra-controls">
                <label class="controlGroup">MIDI <input type="file" id="midiFile" accept=".mid,.midi"></label>
                <button id="playBtn" disabled>Play</button>
                <button id="recStartBtn">Gravar</button>
                <button id="recStopBtn">Parar</button>
                <button id="exportBtn">Exportar</button>
                <span class="statusPill" id="status">Parado</span>
            </div>

            <div id="piano"></div>
            <div class="note-hint">Atalhos logicos ativos: q=Do, 2=Do#, w=Re, 3=Re#, e continuacao em x/d/c/f ... ;/~.</div>

            <div class="sectionDivider"></div>

            <h2>Controles PRO</h2>
            <div id="controlArea">
                <span id="pad"></span>
                <span id="sld1"></span>
                <span id="sld2"></span>
            </div>
        </div>
    </section>

    <div class="overlay treinarOverlay" id="overlay">
        <div class="overlay-content" id="overlayContent"></div>
    </div>

    <script>
        JZZ.synth.Tiny.register('Web Audio');
        var out = JZZ().openMidiOut();

        var piano = JZZ.input.Kbd({{ at: 'piano', from: 'C3', to: 'C6', ww: 38, bw: 24, wl: 170, bl: 105 }});
        piano.connect(out);

        function noteRange(fromMidi, toMidi) {{
            var noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
            var outNotes = [];
            for (var m = fromMidi; m <= toMidi; m += 1) {{
                var octave = Math.floor(m / 12) - 1;
                var name = noteNames[m % 12] + octave;
                outNotes.push(name);
            }}
            return outNotes;
        }}

        function keyboardMaps(o) {{
            var keyToNote = {{
                // Linha principal: q=Do, 2=Do#, w=Re, 3=Re#...
                Q: 'C' + (o - 1),
                '2': 'C#' + (o - 1),
                W: 'D' + (o - 1),
                '3': 'D#' + (o - 1),
                E: 'E' + (o - 1),
                R: 'F' + (o - 1),
                '5': 'F#' + (o - 1),
                T: 'G' + (o - 1),
                '6': 'G#' + (o - 1),
                Y: 'A' + (o - 1),
                '7': 'A#' + (o - 1),
                U: 'B' + (o - 1),

                // Continua apos U: I, O, P...
                I: 'C' + o,
                '9': 'C#' + o,
                O: 'D' + o,
                '0': 'D#' + o,
                P: 'E' + o,
                '[': 'F' + o,
                '=': 'F#' + o,

                // Depois de [ e =, segue linha de baixo: z s x d...
                Z: 'G' + o,
                S: 'G#' + o,
                X: 'A' + o,
                D: 'A#' + o,
                C: 'B' + o,
                V: 'C' + (o + 1),
                G: 'C#' + (o + 1),
                B: 'D' + (o + 1),
                H: 'D#' + (o + 1),
                N: 'E' + (o + 1),
                M: 'F' + (o + 1),
                K: 'F#' + (o + 1),
                ',': 'G' + (o + 1),
                L: 'G#' + (o + 1),
                '.': 'A' + (o + 1),
                ';': 'A#' + (o + 1),
                '/': 'B' + (o + 1),
                '`': 'C' + (o + 2)
            }};

            var noteToKey = {{}};
            Object.keys(keyToNote).forEach(function(keyName) {{
                var noteName = keyToNote[keyName];
                if (!noteToKey[noteName]) noteToKey[noteName] = keyName;
            }});

            return {{ keyToNote: keyToNote, noteToKey: noteToKey }};
        }}

        function keyboardLegendMap(o) {{
            return keyboardMaps(o).noteToKey;
        }}

        function annotatePianoKeys(o) {{
            var pianoRoot = document.querySelector('#piano > span');
            if (!pianoRoot) return;

            var keys = Array.prototype.slice.call(pianoRoot.children || []);
            if (!keys.length) return;

            var notes = noteRange(48, 84); // C3 to C6
            var whiteNotes = notes.filter(function(n) {{ return n.indexOf('#') === -1; }});
            var blackNotes = notes.filter(function(n) {{ return n.indexOf('#') !== -1; }});

            var whiteKeys = keys
                .filter(function(el) {{ return parseInt(el.style.height || '0', 10) >= 150; }})
                .sort(function(a, b) {{ return parseInt(a.style.left || '0', 10) - parseInt(b.style.left || '0', 10); }});

            var blackKeys = keys
                .filter(function(el) {{ return parseInt(el.style.height || '0', 10) < 150; }})
                .sort(function(a, b) {{ return parseInt(a.style.left || '0', 10) - parseInt(b.style.left || '0', 10); }});

            var legendMap = keyboardLegendMap(o);

            function paintLegend(el, noteName, isBlack) {{
                if (!el) return;
                var keyName = legendMap[noteName] || noteName;
                el.setAttribute('data-kbd', keyName);
                if (isBlack) el.setAttribute('data-kbd-black', '1');
                else el.removeAttribute('data-kbd-black');
            }}

            for (var i = 0; i < whiteKeys.length; i += 1) {{
                paintLegend(whiteKeys[i], whiteNotes[i], false);
            }}

            for (var j = 0; j < blackKeys.length; j += 1) {{
                paintLegend(blackKeys[j], blackNotes[j], true);
            }}
        }}

        function createKeyboard(o) {{
            return JZZ.input.ASCII(keyboardMaps(o).keyToNote).connect(piano);
        }}

        var ascii = createKeyboard(4);
        annotatePianoKeys(4);

        var midiPlayer = null;
        var isPlaying = false;
        var recSmf = null;
        var recTrack = null;
        var isRecording = false;
        var recLastTs = null;
        var recEventCount = 0;
        var REC_BPM = 120;
        var REC_PPQ = 96;

        var statusEl = document.getElementById('status');
        var playBtn = document.getElementById('playBtn');
        var midiFileInput = document.getElementById('midiFile');

        function setStatus(text) {{
            if (statusEl) statusEl.textContent = text;
        }}

        midiFileInput.addEventListener('change', function(e) {{
            var file = e.target.files && e.target.files[0];
            if (!file) return;

            var reader = new FileReader();
            reader.onload = function(ev) {{
                var bytes = new Uint8Array(ev.target.result);
                var data = '';
                for (var i = 0; i < bytes.length; i += 1) data += String.fromCharCode(bytes[i]);
                try {{
                    midiPlayer = JZZ.MIDI.SMF(data).player();
                    midiPlayer.connect(out);
                    playBtn.disabled = false;
                    setStatus('MIDI carregado');
                }} catch (err) {{
                    setStatus('Falha ao carregar MIDI');
                }}
            }};
            reader.readAsArrayBuffer(file);
        }});

        playBtn.addEventListener('click', function() {{
            if (!midiPlayer) return;
            if (!isPlaying) {{
                midiPlayer.play();
                isPlaying = true;
                playBtn.textContent = 'Stop';
                setStatus('Tocando MIDI');
            }} else {{
                midiPlayer.stop();
                isPlaying = false;
                playBtn.textContent = 'Play';
                setStatus('Parado');
            }}
        }});

        document.getElementById('recStartBtn').addEventListener('click', function() {{
            recSmf = new JZZ.MIDI.SMF(0, REC_PPQ);
            recTrack = new JZZ.MIDI.SMF.MTrk();
            recSmf.push(recTrack);
            recTrack.smfBPM(REC_BPM);
            isRecording = true;
            recLastTs = null;
            recEventCount = 0;
            setStatus('Gravando');
        }});

        document.getElementById('recStopBtn').addEventListener('click', function() {{
            if (!isRecording || !recTrack) return;
            isRecording = false;
            recTrack.smfEndOfTrack();
            if (!recEventCount) setStatus('Gravacao vazia');
            else setStatus('Gravacao finalizada (' + recEventCount + ' eventos)');
        }});

        document.getElementById('exportBtn').addEventListener('click', function() {{
            if (!recSmf || !recEventCount) {{
                setStatus('Nada para exportar');
                return;
            }}
            try {{
                var dump = recSmf.dump();
                var bin = dump.split('').map(function(c) {{ return c.charCodeAt(0); }});
                var blob = new Blob([new Uint8Array(bin)], {{ type: 'audio/midi' }});
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'gravacao.mid';
                a.click();
                URL.revokeObjectURL(url);
                setStatus('MIDI exportado (' + recEventCount + ' eventos)');
            }} catch (err) {{
                setStatus('Falha ao exportar');
            }}
        }});

        var categories = [
            {{ name: 'Piano', range: [0, 7] }},
            {{ name: 'Guitar', range: [24, 31] }},
            {{ name: 'Bass', range: [32, 39] }},
            {{ name: 'Strings', range: [40, 47] }},
            {{ name: 'Orchestra', range: [48, 55] }},
            {{ name: 'Synth', range: [80, 87] }},
            {{ name: 'Drums', range: [112, 119] }}
        ];

        var menu = document.getElementById('menu');
        var overlay = document.getElementById('overlay');
        var overlayContent = document.getElementById('overlayContent');
        var instrumentName = document.getElementById('instrumentName');

        function closeOverlay() {{
            overlay.style.display = 'none';
            overlayContent.innerHTML = '';
        }}

        function openOverlay(cat) {{
            overlay.style.display = 'flex';
            overlayContent.innerHTML = '';

            for (var i = cat.range[0]; i <= cat.range[1]; i += 1) {{
                (function(program) {{
                    var row = document.createElement('div');
                    row.className = 'instrument';
                    row.textContent = JZZ.MIDI.programName(program);
                    row.addEventListener('click', function() {{
                        try {{
                            out.program(0, program);
                            instrumentName.textContent = 'Instrumento: ' + JZZ.MIDI.programName(program);
                        }} catch (err) {{}}
                        closeOverlay();
                    }});
                    overlayContent.appendChild(row);
                }})(i);
            }}
        }}

        categories.forEach(function(cat) {{
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'menu-btn';
            btn.textContent = cat.name;
            btn.addEventListener('click', function() {{ openOverlay(cat); }});
            menu.appendChild(btn);
        }});

        overlay.addEventListener('click', function(e) {{
            if (e.target === overlay) closeOverlay();
        }});

        try {{
            var pad = JZZ.input.Pad({{ at: 'pad', rh: 100, kw: 20 }}).connect(piano);
            var slider1 = JZZ.input.Slider({{ at: 'sld1' }}).connect(out);
            var slider2 = JZZ.input.Slider({{ at: 'sld2', data: 'mod' }}).connect(out);
            pad.connect(slider1).connect(slider2);
        }} catch (err) {{}}

        piano.connect(function(msg) {{
            if (!isRecording || !recTrack) return;

            var now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
            var deltaMs = recLastTs == null ? 0 : Math.max(0, now - recLastTs);
            var ticksPerMs = (REC_PPQ * REC_BPM) / 60000;
            var deltaTicks = recLastTs == null ? 0 : Math.max(1, Math.round(deltaMs * ticksPerMs));

            recTrack.tick(deltaTicks).send(msg);
            recLastTs = now;
            recEventCount += 1;
        }});

        document.getElementById('volume').addEventListener('input', function (e) {{
            out.control(0, 7, parseInt(e.target.value || '100', 10));
        }});

        document.getElementById('octave').addEventListener('input', function (e) {{
            var o = parseInt(e.target.value || '4', 10);
            ascii.disconnect();
            ascii = createKeyboard(o);
            annotatePianoKeys(o);
        }});
    </script>

    """
    return html

def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()


_GUITARPRO_INDEX_CACHE = None
_GUITARPRO_INDEX_CACHE_MTIME = None


def _normalizar_guitarpro_nome(texto):
    import unicodedata

    if not texto:
        return ""

    ascii_text = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[\'\u00b4`]+", "", ascii_text)
    ascii_text = re.sub(r"\s*\(.*?\)", " ", ascii_text)
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _guitarpro_index_file_path():
    return Path("static") / "guitarpro" / "_gp_index.txt"


def _refresh_guitarpro_index_txt(max_age_seconds=21600):
    import time

    base_dir = Path("static") / "guitarpro"
    idx_path = _guitarpro_index_file_path()
    extensoes = {".gp", ".gp3", ".gp4", ".gp5", ".gpx"}

    if not base_dir.exists():
        return

    precisa_rebuild = True
    if idx_path.exists():
        try:
            idade = time.time() - idx_path.stat().st_mtime
            precisa_rebuild = idade > max_age_seconds
        except Exception:
            precisa_rebuild = True

    if not precisa_rebuild:
        return

    linhas = []
    for arquivo in base_dir.iterdir():
        if not arquivo.is_file() or arquivo.suffix.lower() not in extensoes:
            continue

        stem = arquivo.stem.strip()
        if " - " in stem:
            artista_nome, musica_nome = stem.split(" - ", 1)
        elif "-" in stem:
            artista_nome, musica_nome = stem.split("-", 1)
        else:
            artista_nome, musica_nome = "", stem

        artista_norm = _normalizar_guitarpro_nome(artista_nome)
        musica_norm = _normalizar_guitarpro_nome(musica_nome)
        if not musica_norm:
            continue

        linhas.append(
            "\t".join(
                [
                    artista_norm,
                    musica_norm,
                    arquivo.name,
                    (artista_nome or "").strip().replace("\t", " "),
                    (musica_nome or "").strip().replace("\t", " "),
                ]
            )
        )

    try:
        idx_path.write_text("\n".join(linhas), encoding="utf-8")
    except Exception:
        pass


def _guitarpro_index():
    global _GUITARPRO_INDEX_CACHE, _GUITARPRO_INDEX_CACHE_MTIME

    _refresh_guitarpro_index_txt()
    idx_path = _guitarpro_index_file_path()
    index = {}

    if not idx_path.exists():
        _GUITARPRO_INDEX_CACHE = index
        _GUITARPRO_INDEX_CACHE_MTIME = None
        return _GUITARPRO_INDEX_CACHE

    try:
        mtime = idx_path.stat().st_mtime
    except Exception:
        mtime = None

    if _GUITARPRO_INDEX_CACHE is not None and _GUITARPRO_INDEX_CACHE_MTIME == mtime:
        return _GUITARPRO_INDEX_CACHE

    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        conteudo = ""

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 2:
            continue
        artista_norm = (partes[0] or "").strip()
        musica_norm = (partes[1] or "").strip()
        if not artista_norm or not musica_norm:
            continue
        index.setdefault(artista_norm, set()).add(musica_norm)

    _GUITARPRO_INDEX_CACHE = index
    _GUITARPRO_INDEX_CACHE_MTIME = mtime
    return _GUITARPRO_INDEX_CACHE


def _has_flixplayer_tab(artista_nome, musica_titulo):
    tracks = _guitarpro_index().get(_normalizar_guitarpro_nome(artista_nome), set())
    if not tracks:
        return False

    titulo_norm = _normalizar_guitarpro_nome(musica_titulo)
    titulo_base_norm = _normalizar_guitarpro_nome(titulo_base(musica_titulo))

    if titulo_norm in tracks or titulo_base_norm in tracks:
        return True

    for track_norm in tracks:
        if titulo_norm and (titulo_norm in track_norm or track_norm in titulo_norm):
            return True
        if titulo_base_norm and (titulo_base_norm in track_norm or track_norm in titulo_base_norm):
            return True

    return False



@app.route("/artista/<slug>")
def artista(slug):
    page_voltar = request.args.get("page", 1)
    pagina = int(request.args.get("p", 1))
    ordem = request.args.get("o", "views")
    mostrar_todas = request.args.get("todas") == "1"

    por_pagina = 50
    offset = (pagina - 1) * por_pagina
    limite_inicial = 18

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id,nome FROM artistas WHERE slug=?", (slug,))
    artista = c.fetchone()
    if not artista:
        conn.close()
        return "Artista nao encontrado"

    artista_id, nome = artista
    fotoartista = pegar_foto_artista(artista)

    c.execute("SELECT COUNT(*) FROM musicas WHERE artista_id=?", (artista_id,))
    total_musicas = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(views), 0) FROM musicas WHERE artista_id=?", (artista_id,))
    total_views = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM albuns WHERE artista_id=?", (artista_id,))
    total_albuns = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM favoritos f JOIN musicas m ON m.id = f.musica_id WHERE m.artista_id=?", (artista_id,))
    total_favoritos = c.fetchone()[0]

    if ordem == "flixplayer":
        c.execute(
            """
            SELECT titulo, uid, views, conteudo, tom, slug
            FROM musicas
            WHERE artista_id=?
            """,
            (artista_id,),
        )
        musicas_raw = c.fetchall()
    else:
        order_sql = "views DESC" if ordem == "views" else "titulo COLLATE NOCASE ASC"
        c.execute(
            f"""
            SELECT titulo, uid, views, conteudo, tom, slug
            FROM musicas
            WHERE artista_id=?
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            (artista_id, por_pagina, offset),
        )
        musicas_raw = c.fetchall()

    c.execute("""
        SELECT id, nome, ano, capa
        FROM albuns
        WHERE artista_id=?
        ORDER BY ano
    """, (artista_id,))
    albuns = c.fetchall()
    conn.close()

    agrupadas = {}
    for titulo, uid, views, conteudo, tom_salvo, musica_slug in musicas_raw:
        base = titulo_base(titulo)
        if base not in agrupadas:
            tom = tom_salvo or extrair_tom_da_cifra(conteudo or "") or "-"
            agrupadas[base] = {
                "titulo": re.sub(r'\s*\(.*?\)', '', titulo).strip(),
                "uid": uid,
                "slug": musica_slug or slugify(titulo),
                "views": views or 0,
                "count": 0,
                "tom": tom,
            }
        else:
            agrupadas[base]["count"] += 1

    musicas = list(agrupadas.values())
    if ordem == "flixplayer":
        for m in musicas:
            m["has_player"] = _has_flixplayer_tab(nome, m["titulo"])

        musicas.sort(
            key=lambda m: (
                not m.get("has_player", False),
                -(m.get("views") or 0),
                (m.get("titulo") or "").lower(),
            )
        )

        total_agrupadas = len(musicas)
        total_paginas = max(1, (total_agrupadas // por_pagina) + (1 if total_agrupadas % por_pagina else 0))
        inicio = max(0, (pagina - 1) * por_pagina)
        fim = inicio + por_pagina
        musicas = musicas[inicio:fim]

    musicas_exibir = musicas if mostrar_todas else musicas[:limite_inicial]

    import os
    nome_safe = nome.replace(" ", "+")
    nome_pasta = nome.lower().replace(" ", "_")
    mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

    if os.path.exists(mini_path):
        foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
    else:
        foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

    if ordem != "flixplayer":
        total_paginas = max(1, (total_musicas // por_pagina) + (1 if total_musicas % por_pagina else 0))

    html = header(nome) + f"""
    <section class="artistProfileHero">
        <a class="backBtn softBack" href="/?page={page_voltar}">Voltar para artistas</a>
        <div class="artistHeroMain">
            <div class="artistPortrait">
                <img src="{foto_url}" alt="{nome}">
                {fotoartista}
            </div>
            <div class="artistHeroCopy">
                <p class="eyebrow">Artista</p>
                <h1>{nome}</h1>
                <p>Catalogo de cifras, letras e discografia organizado para tocar, estudar e revisar rapido.</p>
                <div class="artistStats">
                    <span><strong>{fmt_int(total_musicas)}</strong> musicas</span>
                    <span><strong>{fmt_int(total_albuns)}</strong> albuns</span>
                    <span><strong>{fmt_int(total_views)}</strong> views</span>
                    <span><strong>{fmt_int(total_favoritos)}</strong> favoritos</span>
                </div>
            </div>
        </div>
    </section>

    <section class="artistWorkspace">
        <aside class="artistSidePanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Organizacao</p>
                    <h2>Cifras</h2>
                </div>
            </div>
            <div class="sortChips">
                <a href="?o=views&p=1" class="ordBtn {'active' if ordem=='views' else ''}">Mais vistas</a>
                <a href="?o=alpha&p=1" class="ordBtn {'active' if ordem=='alpha' else ''}">A-Z</a>
                <a href="?o=flixplayer&p=1" class="ordBtn {'active' if ordem=='flixplayer' else ''}">FlixPlayer</a>
            </div>
            <p class="panelHint">A lista agrupa versoes da mesma musica e mostra o tom detectado quando existe cifra.</p>
        </aside>

        <div class="artistMainPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Repertorio</p>
                    <h2>Musicas</h2>
                </div>
                <span class="pageInfo">Pagina {pagina} de {total_paginas}</span>
            </div>
            <div class="musicListHeader artistMusicHeader">
                <span>#</span><span>Musica</span><span>Views</span><span>Tom</span><span>Acoes</span>
            </div>
            <div class="musicGrid artistMusicList">
    """

    if musicas_exibir:
        for i, m in enumerate(musicas_exibir, start=1 + offset):
            badge = f'<span class="versaoBadge">+{m["count"]}</span>' if m["count"] > 0 else ""
            has_player = m.get("has_player")
            if has_player is None:
                has_player = _has_flixplayer_tab(nome, m["titulo"])

            if has_player:
                player_btn = f'<a class="trackActionBtn playerBtn" href="/tocador-gp4/{slug}/{m["uid"]}" title="Abrir no FlixPlayer">FlixPlay</a>'
            else:
                player_btn = '<span class="trackActionBtn playerBtn disabled" title="Sem arquivo Guitar Pro">FlixPlay</span>'
            html += f"""
            <div class="musicRow artistTrackRow">
                <div class="musicIndex">{i:02d}</div>
                <a class="musicTitle trackMainLink" href="/artista/{slug}/{m["uid"]}">{m["titulo"]} {badge}</a>
                <div class="musicViews">{fmt_int(m["views"])}</div>
                <div class="musicKey">{m["tom"]}</div>
                <div class="artistTrackActions">
                    <a class="trackActionBtn cifraBtn" href="/artista/{slug}/{m["uid"]}" title="Ver cifra">Cifra</a>
                    <a class="trackActionBtn letraBtn" href="/letra/{slug}/{m["slug"]}" title="Ver letra">Letra</a>
                    {player_btn}
                </div>
            </div>
            """
    else:
        html += """
        <div class="emptyState artistEmptyState">
            <strong>Nenhuma cifra vinculada ainda.</strong>
            <span>Use a discografia abaixo para navegar pelas letras e depois vincule cifras quando elas forem importadas.</span>
        </div>
        """

    html += "</div>"

    if not mostrar_todas and len(musicas) > limite_inicial:
        html += f"""
        <div class="centerActions">
            <a href="?todas=1&o={ordem}&p={pagina}" class="pageBtn">Mostrar todas as cifras desta pagina</a>
        </div>
        """

    html += '<nav class="paginacao">'
    if pagina > 1:
        html += f'<a href="?p={pagina-1}&o={ordem}" class="pageBtn">Anterior</a>'
    html += f'<span class="pageInfo">Pagina {pagina} de {total_paginas}</span>'
    if pagina < total_paginas:
        html += f'<a href="?p={pagina+1}&o={ordem}" class="pageBtn">Proxima</a>'
    html += "</nav></div></section>"

    if albuns:
        html += """
        <section class="discographyPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Discografia</p>
                    <h2>Albuns</h2>
                </div>
            </div>
            <div class="albumGrid">
        """
        for aid, nome_album, ano_album, capa_url in albuns:
            ano_fmt = str(ano_album)[:4] if ano_album else ""
            capa_src = (capa_url or "").strip()
            if not capa_src.lower().startswith(("http://", "https://")):
                capa_src = f"/capa_album/{aid}"
            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="{capa_src}" class="albumCover" alt="{nome_album}">
                <div class="albumTitle">{nome_album}</div>
                <div class="albumYear">{ano_fmt}</div>
            </a>
            """
        html += "</div></section>"

    html += "</main>"
    return html


import re


import requests

def pegar_foto_artista(nome_artista):
        return ""


def extrair_tom_da_cifra(texto_pre):
    import re
    # -------------------------------------------------
    # 1️⃣ Procurar Tecla ou Key
    # -------------------------------------------------
    m = re.search(r'(?:Tecla|Key)\s*:\s*([A-G](?:#|b)?)', texto_pre, re.IGNORECASE)
    if m:
        return m.group(1)

    # regex de acorde (mesmo padrão que você usa)
    chord_pattern = (
        r'\b([A-G](?:#|b)?'
        r'(?:maj7|m7|m|7sus4|sus4|sus2|dim|aug|add9|m6|6|9|11|13|'
        r'7#9|7b9|7#5|7b5|7#11|7b13|7|5)?'
        r'(?:/[A-G](?:#|b)?)?)\b'
    )

    # -------------------------------------------------
    # 2️⃣ Procurar após [Verse ou [Intro
    # -------------------------------------------------
    bloco = re.search(
        r'\[(?:Verse|Intro)[^\]]*\](.*)',
        texto_pre,
        re.IGNORECASE | re.DOTALL
    )

    if bloco:
        trecho = bloco.group(1)
        m2 = re.search(chord_pattern, trecho)
        if m2:
            raiz = re.match(r'^([A-G](?:#|b)?)', m2.group(1))
            if raiz:
                return raiz.group(1)

    # -------------------------------------------------
    # 3️⃣ Fallback: primeiro acorde do texto inteiro
    # -------------------------------------------------
    m3 = re.search(chord_pattern, texto_pre)
    if m3:
        raiz = re.match(r'^([A-G](?:#|b)?)', m3.group(1))
        if raiz:
            return raiz.group(1)

    return None

def extrair_tom(texto):
    """
    Procura por:
    Tecla: C
    Key: C
    Tom: C
    """

    padrao = re.search(
        r'(?:Tecla|Key|Tom)\s*:\s*([A-G][#b]?(?:m|maj7|7)?)',
        texto,
        re.IGNORECASE
    )

    if padrao:
        return padrao.group(1).upper()

    return None


@app.route("/artista/<slug>/<uid>")
def musica(slug, uid):
    import html as html_escape

    semitons = int(request.args.get("t", 0))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT 
        m.id,
        m.titulo,
        m.conteudo,
        m.tom,
        m.capotraste,
        m.afinacao,
        a.nome,
        a.slug
    FROM musicas m
    JOIN artistas a ON m.artista_id = a.id
    WHERE a.slug=? AND m.uid=?
    """, (slug, uid))

    musica = c.fetchone()

    if not musica:
        return "Não encontrada"

    (
        musica_id,
        titulo,
        conteudo,
        tom_musica,
        capotraste,
        afinacao,
        artista_nome,
        artista_slug
    ) = musica

    c.execute(
        "UPDATE musicas SET views=views+1 WHERE id=?",
        (musica_id,)
    )

    conn.commit()
    conn.close()

    # buscar outras versões da mesma música
    base_titulo = titulo.split("(")[0].strip()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT uid, titulo
    FROM musicas
    WHERE artista_id = (
        SELECT id FROM artistas WHERE slug=?
    )
    AND titulo LIKE ?
    ORDER BY titulo
    """, (slug, base_titulo + "%"))

    versoes = c.fetchall()

    c.execute("""
    SELECT id, nome, ano, capa
    FROM albuns
    WHERE artista_id = (
        SELECT id FROM artistas WHERE slug=?
    )
    ORDER BY ano
    """, (slug,))
    albuns_artista = c.fetchall()

    conn.close()

    conteudo = transpor_acordes(conteudo, semitons)

    tom_musica = tom_musica or extrair_tom(conteudo) or extrair_tom_da_cifra(conteudo) or "—"
    capo_texto = str(capotraste).strip() if capotraste is not None else ""
    mostrar_capo = bool(capo_texto) and capo_texto not in {"0", "0.0", "0,0", "00"}
    capotraste = capo_texto
    afinacao = afinacao or ""
    #tom_musica = video_url
    conteudo = re.sub(
        r'(?:Tecla|Key|Tom)\s*:\s*[A-G][#b]?(?:m|maj7|7)?',
        '',
        conteudo,
        flags=re.IGNORECASE
    )
        
        
    conteudo = destacar_acordes(conteudo)

    html = header(titulo) + f"""
  <style>main{{
    
    width:100%;
    max-width:none;   /* 🔥 ESSENCIAL */
}}
        /* ===== LAYOUT 2 COLUNAS ===== */
       .songLayout{{
    width:100%;
    max-width:1280px;
    margin:20px auto;
    padding:0 20px;

    display:grid;

    /* 🎯 centro manda no layout */
    grid-template-columns: 250px minmax(0, 1fr);

    gap:28px;
    align-items:start;
}}

        /* ===== CONTROLES ===== */
        .songLeft{{
            display:flex;
            flex-direction:column;
            gap:18px;
        }}

        .controlCard{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:16px;
            padding:18px;
            box-shadow:0 2px 6px rgba(0,0,0,0.04);
            border: 1px solid #666;
            margin-bottom: 13px;
        }}

        .controlTitle{{
            font-size:16px;
            font-weight:600;
            color:#111827;
            margin-bottom:14px;
        }}

        .controlBtns{{
            display:flex;
            gap:10px;
            margin-bottom:14px;
        }}

        .controlBtn{{
            height:38px;
            border-radius:10px;
            border:1px solid #e5e7eb;
            background:#f9fafb;
            font-weight:700;
            cursor:pointer;
            transition:.15s;
        }}

        .controlBtn:hover{{
            background:#f3f4f6;
        }}

        .transposePanel{{
            display:grid;
            grid-template-columns: 56px minmax(0,1fr) 56px;
            gap:10px;
            align-items:center;
        }}

        .transposeState{{
            text-align:center;
            border:1px solid #f2c9a2;
            border-radius:12px;
            padding:10px 6px;
            background:#fff7ef;
        }}

        .transposeState strong{{
            display:block;
            font-size:34px;
            line-height:1;
            color:#c45100;
            font-weight:800;
        }}

        .transposeState span{{
            display:block;
            margin-top:6px;
            font-size:12px;
            color:#b45309;
            font-weight:700;
        }}

        .toneStep{{
            width:56px;
            height:56px;
            border-radius:12px;
            font-size:30px;
            line-height:1;
        }}

        .transposeResetRow{{
            display:grid;
            grid-template-columns: 56px minmax(0,1fr) 56px;
            gap:10px;
            margin-top:8px;
            align-items:center;
        }}

        .transposeResetBtn{{
            width:56px;
            height:38px;
            border-radius:10px;
            font-size:20px;
            font-weight:800;
        }}

        .favoriteWide{{
            width:100%;
        }}

        .favBtn{{
            width:100%;
            border:1px solid #e5e7eb;
            background:#fafafa;
            border-radius:12px;
            padding:10px;
            font-weight:600;
            cursor:pointer;
            transition:.15s;
        }}
    .songKeyBadge{{
        font-size:22px;
        font-weight:800;
        background:#ff7a00;
        color:#fff;
        padding:10px 0;
        border-radius:12px;
        text-align:center;
        letter-spacing:1px;
    }}
        .favBtn:hover{{
            background:#f3f4f6;
        }}

        .autoScrollBtn{{
            width:100%;
            border:1px solid #e5e7eb;
            background:#f9fafb;
            border-radius:12px;
            padding:10px;
            font-weight:600;
            cursor:pointer;
        }}

        .speedBox{{
            margin-top:12px;
            padding:12px;
            border-radius:12px;
            background-color:#eee;
            border-color:#ccc;
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:10px; font-size:10px;
        }}

        .speedLabel{{
            font-size:10px;
            color:#6b7280;
        }}

        .speedValue{{
            font-weight:600;
            color:#111827;
        }}

        .speedBtn{{
            width:32px;
            height:32px;
            border-radius:8px;
            border:1px solid #d1d5db;
            background:#ffffff;
            font-weight:700;
            cursor:pointer;
        }}
        /* ===== CIFRA ===== */
        .songCenter{{
            min-width:0;
            
    margin-top: 0;
    padding-top: 0;

        }}

        .songTitle{{
            margin-bottom:14px;
            margin-top:0px;
        }}

        .cifraBox{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:14px;
            padding:24px;
            font-size:15px;
            line-height:1.6;
            white-space:pre-wrap;
            color:#111827;
        }}
        .songCenter{{
    min-width:0;
    width:100%;
}}

.cifraBox{{
    width:100%;
    max-width:none;
    overflow-x:auto;   /* 🔥 evita quebrar tudo */
}}

        .cifraBox{{
            width:100%;
            max-width:none;   /* 🔥 MUITO IMPORTANTE */
        }}
        /* ===== RESPONSIVO ===== */

*,
*::before,
*::after{{
    box-sizing:border-box;
}}
         .versionSelect{{
            width:100%;
            display:block;
            margin-top:8px;
            padding:12px 40px 12px 14px; /* espaço pra setinha */
            border-radius:12px;
            border:1px solid #e5e7eb;
            background:#f3f4f6;
            color:#111827;
            font-weight:600;
            font-size:14px;
            cursor:pointer;
            appearance:none;
            -webkit-appearance:none;
            -moz-appearance:none;
            transition:all .18s ease;
        }}

        .versionSelect:hover{{
            border-color:#d1d5db;
        }}

        .versionSelect:focus{{
            outline:none;
            border-color:#9ca3af;
            box-shadow:0 0 0 2px rgba(156,163,175,.15);
        }}
        .versionSelect{{
            width:100%;
            margin-top:8px;
            padding:12px 14px;
            border-radius:12px;
            border:1px solid #e5e7eb;
            background:#f3f4f6; /* cinzinha clean */
            color:#111827;
            font-weight:600;
            font-size:14px;
            cursor:pointer;
            appearance:none;
            -webkit-appearance:none;
            -moz-appearance:none;
            transition:all .18s ease;
            position:relative;
        }}

        /* hover clean */
        .versionSelect:hover{{
            background:#e5e7eb;
            border-color:#d1d5db;
        }}
        .selectWrapper{{
            position:relative;
        }}

        .selectWrapper::after{{
             content:"▾";
            position:absolute;
            right:14px;
            top:50%;
            transform:translateY(-50%);
            pointer-events:none;
            color:#6b7280;
            font-size:14px;
        }}
        /* focus elegante */
        .versionSelect:focus{{
            outline:none;
            background:#e5e7eb;
            border-color:#9ca3af;
            box-shadow:0 0 0 3px rgba(156,163,175,.18);
        }}
        /* ===== VOLTAR ===== */
        .backWrapper{{
            margin-bottom:16px;
        }}
        .songControls {{
            position: sticky;
            top: 90px;
            max-width: 360px;
                         /* ajuste conforme quiser */
            background: #f4f4f4;
            box-sizing: border-box;
            position: sticky;         /* faz ficar fixo ao rolar */
         
            overflow-y: auto;         /* rolagem interna do menu se necessário */
        }}
        .play-btn {{
            width: 34px;
            height: 34px;
            border-radius: 50%;
            border: 1px solid #d1d5db;
            background: #ffffff;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all .15s ease;
        }}

        .play-btn:hover {{
            background: #f3f4f6;
            transform: scale(1.05);
        }}

        .play-btn.playing {{
            background: #00e676;
            color: white;
            border-color: #00e676;
        }}

        .previewGlassBtn {{
            border: 1px solid rgba(255, 122, 0, 0.35);
            background: linear-gradient(135deg, rgba(255, 240, 226, 0.85), rgba(255, 222, 192, 0.72));
            backdrop-filter: blur(8px) saturate(130%);
            -webkit-backdrop-filter: blur(8px) saturate(130%);
            border-radius: 999px;
            padding: 9px 16px;
            font-weight: 800;
            cursor: pointer;
            color: #9a3412;
            font-size: 13px;
            line-height: 1;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
            margin: 8px 0 14px;
        }}

        .previewGlassBtn.playing {{
            background: linear-gradient(135deg, rgba(255, 202, 149, 0.96), rgba(255, 140, 41, 0.9));
            color: #2b1200;
            border-color: rgba(255, 122, 0, 0.72);
            box-shadow: 0 6px 16px rgba(255, 122, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.48);
        }}

        
        </style>
        <script>
        function trocarVersao(uid){{
            const partes = window.location.pathname.split("/");
            const artista = partes[2];
            window.location.href = "/artista/" + artista + "/" + uid;
        }}

        </script>

        <div class="backWrapper">
            <button class="backBtn" onclick="location.href='/artista/{slug}'">
                ← Voltar para músicas
            </button>
        </div>
        
        <div class="songLayout">

            <!-- 🎛️ CONTROLES ESQUERDA -->
            <aside class="songControls">
                <div class="controlCard">
                    <div class="controlTitle">🎸 Versões</div>
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
                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Tom da cifra</div>

                    <div class="transposePanel">
                        <button class="controlBtn toneStep" onclick="transpor(-1)">-</button>
                        <div class="transposeState">
                            <strong id="transposeKey" data-base-key="{tom_musica}">{tom_musica}</strong>
                            <span id="transposeLabel">{semitons:+d} semitons</span>
                        </div>
                        <button class="controlBtn toneStep" onclick="transpor(1)">+</button>
                    </div>

                    <div class="transposeResetRow">
                        <button class="controlBtn transposeResetBtn" onclick="resetTransposicao()" title="Voltar ao tom original" aria-label="Voltar ao tom original">↺</button>
                        <div></div>
                        <div></div>
                    </div>
                </div>

                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Favoritos</div>
                    <button class="controlBtn favoriteWide"
                        onclick="location.href='/favoritar/{musica_id}'">
                        Favoritar
                    </button>
                </div>

                <div class="controlCard chordControlCard">
                    <div class="controlTitle">Rolagem</div>

                    <button class="controlBtn autoScrollPrimary" onclick="toggleScroll()" id="scrollBtn">
                        Iniciar autorrolagem
                    </button>

                    <div class="speedBox autoScrollBox">
                        <span>Velocidade</span>
                        <button class="controlBtn" onclick="changeSpeed(-0.2)">-</button>
                        <span id="speedLabel">1.0x</span>
                        <button class="controlBtn" onclick="changeSpeed(0.2)">+</button>
                    </div>
                    <div class="autoScrollHint">Espaco pausa/continua. Esc interrompe.</div>
                </div>

            </aside>

            <!-- 🎸 CIFRA CENTRAL -->
            <main class="songCenter">
                <h2 class="songTitle">{titulo} </h2>
                <p><a class="chord" href="/artista/{artista_slug}">{artista_nome}</a></p>
                <button class="previewGlassBtn" type="button"
                        data-artista="{html_escape.escape(artista_nome, quote=True)}"
                        data-titulo="{html_escape.escape(titulo, quote=True)}"
                        data-preview=""
                        onclick="toggleSongPreview(this)">Ouvir trecho</button>
                <div class="musicMetaGrid">
                    {f'''<div class="musicMetaCard"><span>Capotraste</span><strong>{capotraste}</strong></div>''' if mostrar_capo else ''}
                    <div class="musicMetaCard">
                        <span>Afinacao</span>
                        <strong>{afinacao or "Padrao"}</strong>
                    </div>
                    <div class="musicMetaCard highlight">
                        <span>Tom</span>
                        <strong class="metaTomKey" data-base-key="{tom_musica}">{tom_musica}</strong>
                    </div>
                </div>
                <pre class="cifraBox">{conteudo}</pre>
            </main>

        </div>
    <script>
    document.addEventListener("DOMContentLoaded", function () {{
        const chordRegex = /(?<![A-Za-z0-9#b])([A-G](?:[#b])?(?:maj9|maj7|m7b5|m7|m|7sus4|7sus2|7#11|7b13|7#9|7b9|7#5|7b5|7|sus4|sus2|dim|aug|add9|m6|6|9|11|13|5)?(?:\/[A-G](?:[#b])?)?)(?![A-Za-z0-9#b])/g;

        document.querySelectorAll("pre.cifraBox").forEach((pre) => {{
            const walker = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT, null, false);
            const textNodes = [];
            let node;

            while ((node = walker.nextNode())) {{
                textNodes.push(node);
            }}

            textNodes.forEach((textNode) => {{
                const text = textNode.nodeValue || "";
                if (!text.match(chordRegex)) return;
                chordRegex.lastIndex = 0;

                const frag = document.createDocumentFragment();
                let lastIndex = 0;

                text.replace(chordRegex, (match, _cap, offset) => {{
                    frag.appendChild(document.createTextNode(text.slice(lastIndex, offset)));

                    const span = document.createElement("span");
                    span.className = "chord";
                    span.textContent = match;

                    const diagram = document.createElement("div");
                    diagram.className = "chord-diagram";

                    const jtabDiv = document.createElement("div");
                    jtabDiv.className = "jtab";
                    diagram.appendChild(jtabDiv);
                    span.appendChild(diagram);

                    let rendered = false;
                    let renderedFor = "";
                    span.addEventListener("mouseenter", () => {{
                        diagram.style.display = "block";
                        const chordNow = (span.firstChild && span.firstChild.nodeType === Node.TEXT_NODE)
                            ? (span.firstChild.nodeValue || "").trim()
                            : (span.textContent || "").trim();
                        if (window.jtab && typeof window.jtab.render === "function" && chordNow) {{
                            try {{
                                if (!rendered || renderedFor !== chordNow) {{
                                    jtabDiv.innerHTML = "";
                                    window.jtab.render(jtabDiv, chordNow);
                                    renderedFor = chordNow;
                                    rendered = true;
                                }}
                            }} catch (_err) {{}}
                        }}
                    }});

                    span.addEventListener("mouseleave", () => {{
                        diagram.style.display = "none";
                    }});

                    frag.appendChild(span);
                    lastIndex = offset + match.length;
                    return match;
                }});

                frag.appendChild(document.createTextNode(text.slice(lastIndex)));
                textNode.parentNode.replaceChild(frag, textNode);
            }});
        }});
    }});
    </script>
    <script>
        // =============================
        // AUTO ROLAGEM
        // =============================
        let scrollSpeed = 1.0;
        let scrolling = false;
        let scrollFrame = null;
        let lastScrollTs = 0;
        let songPreviewAudio = null;
        let songPreviewBtn = null;
        const INITIAL_SEMITONS = {semitons};
        let currentSemitons = INITIAL_SEMITONS;

        async function toggleSongPreview(btn) {{
            const titleIdle = "Ouvir trecho";
            const titlePlaying = "Pausar trecho";
            let url = btn.dataset.preview || "";

            if (!url) {{
                try {{
                    const r = await fetch(`/preview?artista=${{encodeURIComponent(btn.dataset.artista || "")}}&titulo=${{encodeURIComponent(btn.dataset.titulo || "")}}`);
                    const data = await r.json();
                    url = data.preview || "";
                    btn.dataset.preview = url;
                }} catch (_e) {{}}
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

            if (songPreviewAudio) {{
                songPreviewAudio.pause();
                if (songPreviewBtn) {{
                    songPreviewBtn.classList.remove("playing");
                    songPreviewBtn.textContent = titleIdle;
                }}
            }}

            const audio = new Audio(url);
            btn.audio = audio;
            songPreviewAudio = audio;
            songPreviewBtn = btn;
            audio.play();
            btn.classList.add("playing");
            btn.textContent = titlePlaying;
            audio.onended = () => {{
                btn.classList.remove("playing");
                btn.textContent = titleIdle;
            }};
        }}

        const NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
        const NOTE_TO_INDEX = {{
            "C": 0, "B#": 0,
            "C#": 1, "Db": 1,
            "D": 2,
            "D#": 3, "Eb": 3,
            "E": 4, "Fb": 4,
            "F": 5, "E#": 5,
            "F#": 6, "Gb": 6,
            "G": 7,
            "G#": 8, "Ab": 8,
            "A": 9,
            "A#": 10, "Bb": 10,
            "B": 11, "Cb": 11
        }};

        function mod12(value) {{
            return ((value % 12) + 12) % 12;
        }}

        function transposeNoteName(note, delta) {{
            const clean = (note || "").trim();
            if (!clean) return clean;
            const idx = NOTE_TO_INDEX[clean];
            if (idx === undefined) return clean;
            const preferFlat = clean.includes("b");
            const scale = preferFlat ? NOTES_FLAT : NOTES_SHARP;
            return scale[mod12(idx + delta)];
        }}

        function transposeChordSymbol(symbol, delta) {{
            const chord = (symbol || "").trim();
            if (!chord) return chord;

            const rootMatch = chord.match(/^([A-G])([#b]?)(.*)$/);
            if (!rootMatch) return chord;

            const root = rootMatch[1] + (rootMatch[2] || "");
            let suffix = rootMatch[3] || "";
            const newRoot = transposeNoteName(root, delta);

            suffix = suffix.replace(/\/([A-G](?:#|b)?)/, (all, bass) => "/" + transposeNoteName(bass, delta));
            return newRoot + suffix;
        }}

        function updateTransposeLabel() {{
            const label = document.getElementById("transposeLabel");
            if (label) label.innerText = `${{currentSemitons >= 0 ? "+" : ""}}${{currentSemitons}} semitons`;
        }}

        function updateTomVisual() {{
            document.querySelectorAll("[data-base-key]").forEach((el) => {{
                const base = (el.dataset.baseKey || "").trim();
                if (!base || base === "—") return;
                const shifted = transposeChordSymbol(base, currentSemitons);
                if (shifted) el.textContent = shifted;
            }});
        }}

        function cacheBaseChords() {{
            document.querySelectorAll("pre.cifraBox .chord").forEach((span) => {{
                if (!span.dataset.baseChord) {{
                    const txt = (span.firstChild && span.firstChild.nodeType === Node.TEXT_NODE)
                        ? (span.firstChild.nodeValue || "").trim()
                        : (span.textContent || "").trim();
                    if (txt) span.dataset.baseChord = txt;
                }}
            }});
        }}

        function applyTransposeOnFly() {{
            cacheBaseChords();
            document.querySelectorAll("pre.cifraBox .chord").forEach((span) => {{
                const base = span.dataset.baseChord || "";
                if (!base) return;
                const shifted = transposeChordSymbol(base, currentSemitons);
                if (!shifted) return;

                if (span.firstChild && span.firstChild.nodeType === Node.TEXT_NODE) {{
                    span.firstChild.nodeValue = shifted;
                }} else {{
                    span.insertBefore(document.createTextNode(shifted), span.firstChild || null);
                }}
            }});
            updateTomVisual();
            updateTransposeLabel();
        }}

        function syncTransposeInUrl() {{
            const url = new URL(window.location.href);
            if (currentSemitons === 0) {{
                url.searchParams.delete("t");
            }} else {{
                url.searchParams.set("t", String(currentSemitons));
            }}
            window.history.replaceState({{}}, "", url.toString());
        }}

        function updateScrollButton(){{
            const btn = document.getElementById("scrollBtn");
            if (btn) btn.innerText = scrolling ? "Pausar autorrolagem" : "Iniciar autorrolagem";
        }}

        function scrollStep(ts){{
            if (!scrolling) return;
            if (!lastScrollTs) lastScrollTs = ts;
            const delta = Math.min(48, ts - lastScrollTs);
            lastScrollTs = ts;
            window.scrollBy(0, scrollSpeed * delta / 12);

            const chegouFim = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8;
            if (chegouFim) {{
                scrolling = false;
                lastScrollTs = 0;
                updateScrollButton();
                return;
            }}

            scrollFrame = requestAnimationFrame(scrollStep);
        }}

        function toggleScroll(){{
            scrolling = !scrolling;
            updateScrollButton();
            if (scrolling) {{
                lastScrollTs = 0;
                cancelAnimationFrame(scrollFrame);
                scrollFrame = requestAnimationFrame(scrollStep);
            }} else {{
                cancelAnimationFrame(scrollFrame);
            }}
        }}

        function changeSpeed(delta){{
            scrollSpeed = Math.max(0.2, Math.min(4, scrollSpeed + delta));
            document.getElementById("speedLabel").innerText = scrollSpeed.toFixed(1) + "x";
        }}

        // =============================
        // TRANSPOSICAO VIA URL
        // =============================
        function transpor(v){{
            currentSemitons += v;
            applyTransposeOnFly();
            syncTransposeInUrl();
        }}

        function resetTransposicao(){{
            currentSemitons = 0;
            applyTransposeOnFly();
            syncTransposeInUrl();
        }}

        document.addEventListener("keydown", (event) => {{
            if (event.code === "Space" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {{
                event.preventDefault();
                toggleScroll();
            }}
            if (event.key === "Escape" && scrolling) {{
                scrolling = false;
                cancelAnimationFrame(scrollFrame);
                updateScrollButton();
            }}
        }});

        document.addEventListener("DOMContentLoaded", () => {{
            applyTransposeOnFly();
        }});
        </script>"""

    if albuns_artista:
        html += """
        <section class="discographyPanel">
            <div class="sectionHeader">
                <div>
                    <p class="eyebrow">Discografia</p>
                    <h2>Albuns</h2>
                </div>
            </div>
            <div class="albumGrid">
        """
        for aid, nome_album, ano_album, capa_url in albuns_artista:
            ano_fmt = str(ano_album)[:4] if ano_album else ""
            capa_src = (capa_url or "").strip()
            if not capa_src.lower().startswith(("http://", "https://")):
                capa_src = f"/capa_album/{aid}"
            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="{capa_src}" class="albumCover" alt="{nome_album}">
                <div class="albumTitle">{nome_album}</div>
                <div class="albumYear">{ano_fmt}</div>
            </a>
            """
        html += "</div></section>"

    html += "</main>"
    return html

def buscar_video_youtube(artista, musica, indice=5):
    query = urllib.parse.quote(f"{artista}  {musica}")
    url = f"https://www.youtube.com/results?search_query={query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    html = requests.get(url, headers=headers).text

    # pega TODOS os vídeos
    matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)

    # remove duplicados mantendo ordem
    vistos = []
    for m in matches:
        if m not in vistos:
            vistos.append(m)

    # 🔥 terceiro vídeo = índice 2
    if len(vistos) > indice:
        video_id = vistos[indice]
        return f"https://www.youtube.com/watch?v={video_id}"

    return None

@app.route("/favoritar/<int:id>")
def favoritar(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO favoritos (musica_id) VALUES (?)", (id,))
    conn.commit()
    conn.close()
    return redirect("/favoritos")

@app.route("/favoritos")
def favoritos():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    SELECT m.titulo, a.slug, m.uid
    FROM favoritos f
    JOIN musicas m ON f.musica_id=m.id
    JOIN artistas a ON m.artista_id=a.id
    """)
    favs = c.fetchall()
    conn.close()
    html = header("Favoritos") + "<ul>"
    for titulo, slug, uid in favs:
        html += f"<li style='padding:6px 0;'><a href='/artista/{slug}/{uid}' style='color:white;text-decoration:none;'>{titulo}</a></li>"
    html += "</ul></main>"
    return html

@app.route("/stats")
def stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT titulo, views FROM musicas ORDER BY views DESC LIMIT 10")
    top = c.fetchall()
    conn.close()
    html = header("Mais Vistas") + "<ul>"
    for titulo, views in top:
        html += f"<li style='padding:6px 0;'>{titulo} 👁 {views}</li>"
    html += "</ul></main>"
    return html

@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip().lower()
    gp_only = request.args.get("gp", "").strip().lower() in {"1", "true", "yes"}
    page = int(request.args.get("page", 1))
    per_page = 7  # pequeno como no exemplo
    offset = (page-1) * per_page

    if not q:
        return jsonify({"results": [], "page": 1, "has_next": False})

    q_like = f"%{q}%"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if gp_only:
        c.execute(
            """
            SELECT m.titulo, m.uid, a.slug, a.nome
            FROM musicas m
            JOIN artistas a ON m.artista_id = a.id
            WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
            ORDER BY m.titulo ASC
            """,
            (q_like, q_like),
        )

        todos = [
            {
                "titulo": r[0],
                "uid": r[1],
                "artista": r[2],
                "artista_nome": r[3],
                "player_url": f"/tocador-gp4/{r[2]}/{r[1]}",
            }
            for r in c.fetchall()
        ]

        filtrados = [
            item
            for item in todos
            if _has_flixplayer_tab(item["artista_nome"], item["titulo"])
        ]
        total = len(filtrados)
        dados = filtrados[offset:offset + per_page]
        has_next = (offset + per_page) < total
    else:
        c.execute(
            """
            SELECT m.titulo, m.uid, a.slug, a.nome
            FROM musicas m
            JOIN artistas a ON m.artista_id = a.id
            WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
            ORDER BY m.titulo ASC
            LIMIT ? OFFSET ?
            """,
            (q_like, q_like, per_page, offset),
        )
        dados = [
            {"titulo": r[0], "uid": r[1], "artista": r[2], "artista_nome": r[3]}
            for r in c.fetchall()
        ]

        # verificar se existe próxima página
        c.execute(
            """
            SELECT COUNT(*)
            FROM musicas m
            JOIN artistas a ON m.artista_id = a.id
            WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
            """,
            (q_like, q_like),
        )
        total = c.fetchone()[0]
        has_next = (offset + per_page) < total

    conn.close()
    return jsonify({"results": dados, "page": page, "has_next": has_next})

@app.route("/importar")
def importar():
    importar_txt()
    return redirect("/")



# ==========================
# Tela de Login
# ==========================
@app.route("/login")
def login():
    html = header("Favoritos")
    html += """
    <div class="container">
        <h2>Entrar</h2>
        <form id="loginForm">
            <label for="email">E-mail</label>
            <input type="email" id="email" name="email" placeholder="seu@email.com" required>

            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" placeholder="******" required>

            <button type="submit">Entrar</button>
        </form>

        <p>Não tem conta? <a href="/cadastro">Cadastre-se</a></p>
    </div>
    """
    return html

# ==========================
# Tela de Cadastro
# ==========================
@app.route("/cadastro")
def cadastro():
    html = header("Favoritos")
    html += """
    <div class="container">
        <h2>Cadastro</h2>
        <form id="cadastroForm">
            <label for="nome">Nome</label>
            <input type="text" id="nome" name="nome" placeholder="Seu nome" required>

            <label for="email">E-mail</label>
            <input type="email" id="email" name="email" placeholder="seu@email.com" required>

            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" placeholder="******" required>

            <button type="submit">Cadastrar</button>
        </form>

        <p>Já tem conta? <a href="/login">Entrar</a></p>
    </div>
    """
    return html
