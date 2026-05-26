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

def titulo_base(titulo):
    return re.sub(r'\s*\(.*?\)', '', titulo).strip().lower()



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

    order_sql = "views DESC" if ordem == "views" else "titulo COLLATE NOCASE ASC"

    c.execute(f"""
        SELECT titulo, uid, views, conteudo, tom, slug
        FROM musicas
        WHERE artista_id=?
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """, (artista_id, por_pagina, offset))
    musicas_raw = c.fetchall()

    c.execute("""
        SELECT id, nome, ano
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
    musicas_exibir = musicas if mostrar_todas else musicas[:limite_inicial]

    import os
    nome_safe = nome.replace(" ", "+")
    nome_pasta = nome.lower().replace(" ", "_")
    mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

    if os.path.exists(mini_path):
        foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
    else:
        foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

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
            html += f"""
            <div class="musicRow artistTrackRow">
                <div class="musicIndex">{i:02d}</div>
                <a class="musicTitle trackMainLink" href="/artista/{slug}/{m["uid"]}">{m["titulo"]} {badge}</a>
                <div class="musicViews">{fmt_int(m["views"])}</div>
                <div class="musicKey">{m["tom"]}</div>
                <div class="artistTrackActions">
                    <a class="trackActionBtn cifraBtn" href="/artista/{slug}/{m["uid"]}" title="Ver cifra">Cifra</a>
                    <a class="trackActionBtn letraBtn" href="/letra/{slug}/{m["slug"]}" title="Ver letra">Letra</a>
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
        for aid, nome_album, ano_album in albuns:
            ano_fmt = str(ano_album)[:4] if ano_album else ""
            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="/capa_album/{aid}" class="albumCover" alt="{nome_album}">
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

    conn.close()

    video_url = buscar_video_youtube(artista_nome, titulo)

    # extrai o ID do vídeo
    video_id = video_url.split("v=")[-1]

    iframe_video = f'''
    <iframe id="ytplayer"
            src="https://www.youtube.com/embed/{video_id}"
            frameborder="0"
            allowfullscreen>
    </iframe>
    '''

    conteudo = transpor_acordes(conteudo, semitons)

    tom_musica = tom_musica or "—"
    capotraste = capotraste or ""
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
        /* ===== LAYOUT 3 COLUNAS ===== */
       .songLayout{{
    width:100%;
    max-width:1280px;
    margin:20px auto;
    padding:0 20px;

    display:grid;

    /* 🎯 centro manda no layout */
    grid-template-columns: 250px minmax(0, 1fr) 300px;

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
                /* ===== VIDEO ===== */
                .songVideo{{
                    position:sticky;
                    top:90px;
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
                            <strong>{tom_musica}</strong>
                            <span id="transposeLabel">{semitons:+d} semitons</span>
                        </div>
                        <button class="controlBtn toneStep" onclick="transpor(1)">+</button>
                    </div>
                    <div class="transposeQuick">
                        <button class="controlBtn" onclick="transpor(-2)">-1 tom</button>
                        <button class="controlBtn" onclick="resetTransposicao()">Original</button>
                        <button class="controlBtn" onclick="transpor(2)">+1 tom</button>
                    </div>

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
                <div class="musicMetaGrid">
                    <div class="musicMetaCard">
                        <span>Capotraste</span>
                        <strong>{capotraste or "Sem capotraste"}</strong>
                    </div>
                    <div class="musicMetaCard">
                        <span>Afinacao</span>
                        <strong>{afinacao or "Padrao"}</strong>
                    </div>
                    <div class="musicMetaCard highlight">
                        <span>Tom</span>
                        <strong>{tom_musica}</strong>
                    </div>
                </div>
                <pre class="cifraBox">{conteudo}</pre>
            </main>

            <!-- 🎬 VÍDEO DIREITA -->
            <aside class="songVideo">
                <div class="videoWrapper">
                   {iframe_video}
                </div>
            </aside>

        </div>

        </main>
    <script>
    document.addEventListener("DOMContentLoaded", function () {{
const chordRegex = /\\b([A-G](?:[#b])?(?:maj9|maj7|m7b5|m7|m|7sus4|7sus2|7#11|7b13|7#9|7b9|7#5|7b5|7|sus4|sus2|dim|aug|add9|m6|6|9|11|13|5)?(?:\/[A-G](?:[#b])?)?)\\b/g;    document.querySelectorAll("pre").forEach(pre => {{

        const walker = document.createTreeWalker(
        pre,
        NodeFilter.SHOW_TEXT,
        null,
        false
        );

        const textNodes = [];
        let node;

        while (node = walker.nextNode()) {{
        textNodes.push(node);
        }}

        textNodes.forEach(textNode => {{
        const text = textNode.nodeValue;

        // ⚠️ IMPORTANTE: usar match, não test
        if (!text.match(chordRegex)) return;

        const frag = document.createDocumentFragment();
        let lastIndex = 0;

        text.replace(chordRegex, (match, _, offset) => {{

            frag.appendChild(
            document.createTextNode(text.slice(lastIndex, offset))
            );

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

            span.addEventListener("mouseenter", () => {{
            diagram.style.display = "block";
            if (!rendered) {{
                jtab.render(jtabDiv, match);
                rendered = true;
            }}
            }});

            span.addEventListener("mouseleave", () => {{
            diagram.style.display = "none";
            }});

            frag.appendChild(span);
            lastIndex = offset + match.length;
        }});

        frag.appendChild(
            document.createTextNode(text.slice(lastIndex))
        );

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
            const url = new URL(window.location.href);
            const t = parseInt(url.searchParams.get("t") || "0");
            url.searchParams.set("t", t + v);
            window.location.href = url.toString();
        }}

        function resetTransposicao(){{
            const url = new URL(window.location.href);
            url.searchParams.delete("t");
            window.location.href = url.toString();
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

        // =============================
        // BUSCA YOUTUBE AUTOMÁTICA
        // =============================
        document.addEventListener("DOMContentLoaded", async () => {{

            const titulo = document.querySelector("h2")?.innerText || "";
            const artista = document.querySelector("#tituloPagina")?.innerText || "";
            const query = `${{artista}} ${{titulo}}`;

            try{{
                const r = await fetch(
                    "https://ytsearch.vercel.app/api?q=" +
                    encodeURIComponent(query)
                );

                const data = await r.json();

                if(data?.videos?.length){{
                    const videoId = data.videos[0].videoId;
                    document.getElementById("ytplayer").src =
                        "https://www.youtube.com/embed/" + videoId;
                }}
            }}catch(e){{
                console.log("YT search falhou");
            }}

        }});
        </script>"""
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
    page = int(request.args.get("page", 1))
    per_page = 7  # pequeno como no exemplo
    offset = (page-1) * per_page

    if not q:
        return jsonify({"results": [], "page": 1, "has_next": False})

    q_like = f"%{q}%"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT m.titulo, m.uid, a.slug, a.nome
        FROM musicas m
        JOIN artistas a ON m.artista_id = a.id
        WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
        ORDER BY m.titulo ASC
        LIMIT ? OFFSET ?
    """, (q_like, q_like, per_page, offset))
    dados = [
        {"titulo": r[0], "uid": r[1], "artista": r[2], "artista_nome": r[3]}
        for r in c.fetchall()
    ]

    # verificar se existe próxima página
    c.execute("""
        SELECT COUNT(*) 
        FROM musicas m
        JOIN artistas a ON m.artista_id = a.id
        WHERE LOWER(m.titulo) LIKE ? OR LOWER(a.nome) LIKE ?
    """, (q_like, q_like))
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
