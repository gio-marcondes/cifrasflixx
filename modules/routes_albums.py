@app.route("/albuns")
def listar_albuns():
    import os
    import string
    from urllib.parse import urlencode

    pagina = max(1, int(request.args.get("p", 1)))
    letra = (request.args.get("letra", "").strip() or "").upper()
    busca = (request.args.get("q", "").strip() or "")
    por_pagina = 40
    offset = (pagina - 1) * por_pagina

    letras_validas = set(string.ascii_uppercase)
    if letra not in letras_validas:
        letra = ""

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    where = ["1=1", "COALESCE(TRIM(al.capa), '') <> ''"]
    params = []

    if letra:
        where.append("UPPER(SUBSTR(ar.nome, 1, 1)) = ?")
        params.append(letra)

    if busca:
        where.append("ar.nome LIKE ? COLLATE NOCASE")
        params.append(f"%{busca}%")

    where_sql = " AND ".join(where)

    c.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT ar.id
            FROM artistas ar
            JOIN albuns al ON al.artista_id = ar.id
            WHERE {where_sql}
            GROUP BY ar.id
        ) base
        """,
        tuple(params),
    )
    total = c.fetchone()[0] or 0

    c.execute(
        f"""
        SELECT ar.id, ar.nome, ar.slug, COUNT(al.id) AS total_albuns
        FROM artistas ar
        JOIN albuns al ON al.artista_id = ar.id
        WHERE {where_sql}
        GROUP BY ar.id, ar.nome, ar.slug
        ORDER BY ar.nome COLLATE NOCASE ASC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [por_pagina, offset]),
    )
    artistas = c.fetchall()
    conn.close()

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    html = header(titulo="Albuns") + f"""
    <section class="systemPanel" style="margin-top:20px;">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Biblioteca</p>
                <h2>Artistas com albuns</h2>
            </div>
            <span class="pageInfo">Pagina {pagina} de {total_paginas}</span>
        </div>

        <form method="get" class="sortChips" style="gap:10px;align-items:center;flex-wrap:wrap;">
            <input type="text" name="q" value="{busca}" placeholder="Buscar artista" style="min-width:220px;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px;">
            <input type="hidden" name="letra" value="{letra}">
            <button type="submit" class="ordBtn active">Buscar</button>
            <a href="/albuns" class="ordBtn">Limpar</a>
        </form>

        <div class="sortChips" style="margin-top:12px;flex-wrap:wrap;">
            <a href="/albuns" class="ordBtn {'active' if not letra else ''}">Todos</a>
    """

    for l in string.ascii_uppercase:
        qs = urlencode({"letra": l, "q": busca, "p": 1})
        html += f'<a href="/albuns?{qs}" class="ordBtn {"active" if letra == l else ""}">{l}</a>'

    html += """
        </div>

        <div class="albumGrid" style="margin-top:18px;">
    """

    if artistas:
        for _, artista_nome, artista_slug, total_albuns in artistas:
            nome_safe = artista_nome.replace(" ", "+")
            nome_pasta = artista_nome.lower().replace(" ", "_")
            mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

            if os.path.exists(mini_path):
                foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
            else:
                foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

            html += f"""
            <a href="/artista/{artista_slug}/albuns" class="albumCard">
                <img src="{foto_url}" class="albumCover" alt="{artista_nome}">
                <div class="albumTitle">{artista_nome}</div>
                <div class="albumYear">{fmt_int(total_albuns)} albuns</div>
            </a>
            """
    else:
        html += '<p class="emptyState">Nenhum artista com albuns encontrado para os filtros informados.</p>'

    html += "</div>"

    html += '<nav class="pagination" style="margin-top:16px;">'
    if pagina > 1:
        prev_qs = urlencode({"p": pagina - 1, "letra": letra, "q": busca})
        html += f'<a href="/albuns?{prev_qs}" class="pageBtn">Anterior</a>'

    html += f'<span class="pageInfo">{fmt_int(total)} artistas</span>'

    if pagina < total_paginas:
        next_qs = urlencode({"p": pagina + 1, "letra": letra, "q": busca})
        html += f'<a href="/albuns?{next_qs}" class="pageBtn">Proxima</a>'

    html += "</nav></section></main>"
    return html


def _album_cover_src(capa_url, album_id):
    capa_txt = (capa_url or "").strip()
    if capa_txt.lower().startswith(("http://", "https://")):
        return capa_txt
    return f"/capa_album/{album_id}"

@app.route("/artista/<slug>/albuns")
def artista_albuns(slug):
    page_voltar = request.args.get("page", 1)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 🔥 buscar artista
    c.execute("SELECT id, nome FROM artistas WHERE slug=?", (slug,))
    artista = c.fetchone()
    if not artista:
        return "Artista não encontrado"

    artista_id, nome = artista
    fotoartista = pegar_foto_artista(artista)

    # 🔥 buscar albuns do artista
    c.execute("""
        SELECT id, nome, ano, capa
        FROM albuns
        WHERE artista_id=?
        ORDER BY ano
    """, (artista_id,))
    albuns = c.fetchall()
    conn.close()

    # ==========================================
    # FOTO ARTISTA (igual sua página)
    # ==========================================
    import os

    nome_safe = nome.replace(" ", "+")
    nome_pasta = nome.lower().replace(" ", "_")

    pasta_fotos_artista = os.path.join("static", "fotos", "artista", nome_pasta)
    mini_path = os.path.join(pasta_fotos_artista, "mini.jpg")

    if os.path.exists(mini_path):
        foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
    else:
        foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

    # ==========================================
    # HTML
    # ==========================================
    html = header(nome + " - Álbuns") + f"""
    <div class="backBar">
        <button class="backBtn" onclick="location.href='/albuns'">
            ← Voltar para álbuns
        </button>
    </div>

    <br>

    <div class="artistLayout">

        <div class="artistCard">
            <img src="{foto_url}" class="artistPhoto">
            {fotoartista}
            <div class="artistName">{nome}</div>
        </div>

        <div class="musicGrin">
            <h3 style="margin-bottom:20px;">Álbuns</h3>
            <div class="albumGrid">
    """

    # ==========================================
    # LISTA DE ÁLBUNS
    # ==========================================
    for aid, nome_album, ano, capa_url in albuns:
        ano=pegar_ano(ano)
        cover_src = _album_cover_src(capa_url, aid)
        html += f"""
        <a href="/album/{aid}" class="albumCard">
             <img src="{cover_src}" class="albumCover" alt="{nome_album}">
            <div class="albumTitle">{nome_album}</div>
            <div class="albumYear">{ano or ""}</div>
        </a>
        """

    html += """
            </div>
        </div>
    </div>
    </main>
    """

    return html



@app.route("/preview")
def preview():
    artista = request.args.get("artista")
    titulo = request.args.get("titulo")

    url = buscar_preview_deezer(artista, titulo)

    return jsonify({"preview": url})

@app.route("/album/<int:album_id>")
def ver_album(album_id):
    def formatar_duracao(valor):
        if valor in (None, ""):
            return ""

        texto = str(valor).strip()
        if not texto:
            return ""

        if ":" in texto:
            return texto

        try:
            total = int(float(texto))
        except ValueError:
            return ""

        # Alguns provedores retornam em ms; outros em segundos.
        if total >= 1000:
            total = round(total / 1000)

        minutos, segundos = divmod(max(0, total), 60)
        return f"{minutos}:{segundos:02d}"

    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT al.nome, al.ano, al.capa, al.gravadora, al.descricao, al.pais, al.status, al.artista_id,
               ar.nome AS artista_nome, ar.slug AS artista_slug
        FROM albuns al
        JOIN artistas ar ON al.artista_id = ar.id
        WHERE al.id=?
    """, (album_id,))
    album = c.fetchone()

    if not album:
        conn.close()
        return "Album nao encontrado"

    c.execute("""
        SELECT
        c.titulo,
        c.duracao,
        c.compositor,
        c.preview_url,
        c.cancao_slug,
        (
            SELECT m.uid
            FROM musicas m
            JOIN artistas a ON a.id = m.artista_id
            WHERE (
                m.slug = c.cancao_slug
                OR REPLACE(REPLACE(LOWER(m.titulo), 'â€™', ''), char(39), '') =
                   REPLACE(REPLACE(LOWER(c.titulo), 'â€™', ''), char(39), '')
            )
            AND a.slug = (
                SELECT ar.slug
                FROM albuns al2
                JOIN artistas ar ON ar.id = al2.artista_id
                WHERE al2.id = c.album_id
            )
            LIMIT 1
        ) AS uid,
        (
            SELECT a.slug
            FROM musicas m
            JOIN artistas a ON a.id = m.artista_id
            WHERE (
                m.slug = c.cancao_slug
                OR REPLACE(REPLACE(LOWER(m.titulo), 'â€™', ''), char(39), '') =
                   REPLACE(REPLACE(LOWER(c.titulo), 'â€™', ''), char(39), '')
            )
            AND a.slug = (
                SELECT ar.slug
                FROM albuns al2
                JOIN artistas ar ON ar.id = al2.artista_id
                WHERE al2.id = c.album_id
            )
            LIMIT 1
        ) AS artista_slug_musica
        ,
        (
            SELECT m.tom
            FROM musicas m
            JOIN artistas a ON a.id = m.artista_id
            WHERE (
                m.slug = c.cancao_slug
                OR REPLACE(REPLACE(LOWER(m.titulo), 'Ã¢â‚¬â„¢', ''), char(39), '') =
                   REPLACE(REPLACE(LOWER(c.titulo), 'Ã¢â‚¬â„¢', ''), char(39), '')
            )
            AND a.slug = (
                SELECT ar.slug
                FROM albuns al2
                JOIN artistas ar ON ar.id = al2.artista_id
                WHERE al2.id = c.album_id
            )
            LIMIT 1
        ) AS tom_cifra,
        (
            SELECT m.conteudo
            FROM musicas m
            JOIN artistas a ON a.id = m.artista_id
            WHERE (
                m.slug = c.cancao_slug
                OR REPLACE(REPLACE(LOWER(m.titulo), 'Ã¢â‚¬â„¢', ''), char(39), '') =
                   REPLACE(REPLACE(LOWER(c.titulo), 'Ã¢â‚¬â„¢', ''), char(39), '')
            )
            AND a.slug = (
                SELECT ar.slug
                FROM albuns al2
                JOIN artistas ar ON ar.id = al2.artista_id
                WHERE al2.id = c.album_id
            )
            LIMIT 1
        ) AS conteudo_cifra
        FROM cancao c
        WHERE c.album_id = ?
        ORDER BY c.id
    """, (album_id,))
    faixas = c.fetchall()

    c.execute("""
        SELECT id, nome, ano, capa
        FROM albuns
        WHERE artista_id = ?
        ORDER BY ano
    """, (album["artista_id"],))
    albuns_artista = c.fetchall()

    conn.close()

    ano = formatar_data(album["ano"])
    total_faixas = len(faixas)
    total_cifras = sum(1 for f in faixas if f["uid"] and f["artista_slug_musica"])
    total_previews = sum(1 for f in faixas if f["preview_url"])
    descricao = album["descricao"] or "Descricao ainda nao cadastrada para este album."

    html = header(titulo=f"{album['nome']} - {album['artista_nome']}")
    cover_src = _album_cover_src(album["capa"], album_id)
    html += f"""
    <section class="albumDetailHero">
        <a class="backBtn softBack" href="/artista/{album['artista_slug']}/albuns">Voltar para artista</a>
        <div class="albumDetailGrid">
            <div class="albumCoverPanel">
                <img src="{cover_src}" alt="{album['nome']}">
            </div>
            <div class="albumDetailCopy">
                <p class="eyebrow">Album</p>
                <h1>{album['nome']}</h1>
                <a class="artistInlineLink" href="/artista/{album['artista_slug']}">{album['artista_nome']}</a>
                <div class="albumMetaPills">
                    <span>{ano or 'Ano indisponivel'}</span>
                    <span>{album['gravadora'] or 'Gravadora nao informada'}</span>
                    <span>{album['pais'] or 'Pais nao informado'}</span>
                    <span>{album['status'] or 'Status nao informado'}</span>
                </div>
                <p class="albumDescription">{descricao}</p>
            </div>
        </div>
    </section>

    <section class="albumStatsGrid">
        <article><strong>{fmt_int(total_faixas)}</strong><span>faixas</span></article>
        <article><strong>{fmt_int(total_cifras)}</strong><span>com cifra</span></article>
        <article><strong>{fmt_int(total_previews)}</strong><span>previews</span></article>
    </section>

    <section class="tracks-card albumTracksPanel">
        <div class="sectionHeader">
            <div>
                <p class="eyebrow">Tracklist</p>
                <h2>Faixas</h2>
            </div>
        </div>
    """

    if not faixas:
        html += '<p class="emptyState">Nenhuma faixa encontrada.</p>'

    for numero, f in enumerate(faixas, start=1):
        tem_cifra = bool(f["uid"] and f["artista_slug_musica"])
        duracao_fmt = formatar_duracao(f["duracao"])
        tom_cifra = ""
        if tem_cifra:
            tom_cifra = f["tom_cifra"] or extrair_tom_da_cifra(f["conteudo_cifra"] or "") or ""

        info_extra = ""
        if f["compositor"]:
            info_extra += f'<small>{f["compositor"]}</small>'

        player_html = f"""
        <button class="play-btn" type="button"
                data-artista="{album['artista_nome']}"
                data-titulo="{f['titulo']}"
                data-preview="{f['preview_url'] or ''}"
                onclick="togglePlay(this)">
        Play</button>
        """

        musica_slug = f["cancao_slug"] or normalizar_slug(f["titulo"])
        letra_link = f"/letra/{album['artista_slug']}/{musica_slug}"

        if tem_cifra:
            link_cifra = f"/artista/{f['artista_slug_musica']}/{f['uid']}"
            titulo_html = f'<a class="trackMainLink" href="{link_cifra}">{f["titulo"]}</a>'
            flixplay_btn = ""
            if _has_flixplayer_tab(album["artista_nome"], f["titulo"]):
                flixplay_btn = f'<a class="trackActionBtn playerBtn" href="/tocador-gp4/{f["artista_slug_musica"]}/{f["uid"]}" title="Abrir no FlixPlayer">FlixPlay</a>'

            tom_btn = f'<span class="trackActionBtn tomBtn" title="Tom da cifra">Tom: {tom_cifra}</span>' if tom_cifra else ''
            actions = (
                f'{tom_btn}'
                f'<a class="trackActionBtn cifraBtn" href="{link_cifra}" title="Ver cifra">Cifra</a>'
                f'<a class="trackActionBtn letraBtn" href="{letra_link}" title="Ver letra">Letra</a>'
                f'{flixplay_btn}'
            )
        else:
            titulo_html = f'<a class="trackMainLink only-lyric" href="{letra_link}">{f["titulo"]}</a>'
            actions = f'<a class="trackActionBtn letraBtn only-lyric" href="{letra_link}" title="Ver letra">Letra</a>'

        duracao_col = f'Duracao: {duracao_fmt}' if duracao_fmt else 'Duracao: -'

        html += f"""
        <div class="track-row albumTrackRow">
            <div class="trackNumber">{numero:02d}</div>
            <div class="track-title">
                {titulo_html}
                <div class="trackSubline">{info_extra}</div>
            </div>
            <div class="track-duration-col">{duracao_col}</div>
            <div class="track-player">{player_html}</div>
            <div class="trackActions">{actions}</div>
        </div>
        """

    html += "</section>"

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
            capa_src = _album_cover_src(capa_url, aid)
            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="{capa_src}" class="albumCover" alt="{nome_album}">
                <div class="albumTitle">{nome_album}</div>
                <div class="albumYear">{ano_fmt}</div>
            </a>
            """

        html += """
        </div>
    </section>
        """

    html += """
    <script>
    let currentAudio = null
    let currentBtn = null

    async function togglePlay(btn) {
        const titleIdle = "Play"
        const titlePlaying = "Pause"
        let url = btn.dataset.preview

        if (!url) {
            try {
                const r = await fetch(`/preview?artista=${encodeURIComponent(btn.dataset.artista)}&titulo=${encodeURIComponent(btn.dataset.titulo)}`)
                const data = await r.json()
                url = data.preview || ""
                btn.dataset.preview = url
            } catch (e) {
                console.error("Erro preview:", e)
            }
        }

        if (!url) {
            btn.textContent = "Sem preview"
            return
        }

        if (btn.audio) {
            if (!btn.audio.paused) {
                btn.audio.pause()
                btn.classList.remove("playing")
                btn.textContent = titleIdle
                return
            }
            btn.audio.play()
            btn.classList.add("playing")
            btn.textContent = titlePlaying
            return
        }

        if (currentAudio) {
            currentAudio.pause()
            if (currentBtn) {
                currentBtn.classList.remove("playing")
                currentBtn.textContent = titleIdle
            }
        }

        const audio = new Audio(url)
        btn.audio = audio
        currentAudio = audio
        currentBtn = btn
        audio.play()
        btn.classList.add("playing")
        btn.textContent = titlePlaying
        audio.onended = () => {
            btn.classList.remove("playing")
            btn.textContent = titleIdle
        }
    }
    </script>
    </main>
    """
    return html


@app.route("/mb_album")
def mb_album():
    return """
    
    <h2>Album Hunter Web</h2>

    Artista:
    <input id="artista">

    Álbum:
    <input id="album">
    <textarea id="albunsLote" rows="10" cols="50" placeholder="Digite um álbum por linha"></textarea><br>
    <button onclick="startBatch()">🚀 Start Lote</button>

    pais <div id="pais"></div>
    gravadora <div type="text" id="gravadora"></div>
    ano <div type="text" id="ano"></div>

    <button onclick="buscarEdicoes()">Buscar edições</button>
 <div id="descricaoAlbum"></div>
    <br><br>

    <select id="edicoes" style="width:500px"></select>

    <br><br>

    <button onclick="carregarAlbum()">Carregar álbum</button>

    <br><br>
    
    <textarea id="tracklist" rows="20" cols="80"></textarea><br>
<button onclick="salvarAlbum()">💾 Salvar no Banco</button>
<script>
async function startBatch() {
    const textoAlbuns = document.getElementById("albunsLote").value.trim()
    if (!textoAlbuns) return alert("Digite ao menos 1 álbum!")

    const linhas = textoAlbuns
        .split("\\n")
        .map(l => l.trim())
        .filter(l => l)

    for (let i = 0; i < linhas.length; i++) {
        const linha = linhas[i]

        console.log(`🔹 Processando ${i+1}/${linhas.length}: ${linha}`)

        // 🔥 separa artista e álbum
        const partes = linha.split(" - ")

        if (partes.length < 2) {
            console.warn(`⚠️ Linha ignorada (formato inválido): ${linha}`)
            continue
        }

        const artistaAtual = partes[0].trim()
        let albumAtual = partes.slice(1).join(" - ").trim()

        // remove ano no final se existir
        albumAtual = albumAtual.replace(/\s-\s\d{4}$/, "").trim()
        // 👆 importante caso álbum tenha hífen no nome

        // 🔥 pega inputs
        const artistaInput = document.getElementById("artista")
        const albumInput = document.getElementById("album")

        if (!artistaInput || !albumInput) {
            console.error("⚠️ Inputs não encontrados!")
            return
        }

        // ⚡ preenche campos
        artistaInput.value = artistaAtual
        albumInput.value = albumAtual

        try {
            await buscarEdicoes()

            console.log(`✅ Álbum "${albumAtual}" processado.`)

            // opcional: respiro entre álbuns
            await new Promise(r => setTimeout(r, 1000))

        } catch (err) {
            console.error(`❌ Erro ao processar "${linha}":`, err)
        }
    }

    alert("🚀 Processamento do lote finalizado!")
}
</script> 
    
     
 <script>

    let tracksCarregadas = []
    let previews =[]
    let albumInfo = null
    let previewsGlobais =[]

    function selecionarEdicaoMaisAntiga() {
            const select = document.getElementById("edicoes")
            const options = Array.from(select.options)

            if (!options.length) return

            // extrai ano do texto: "Angels Cry - 1999 • BR • Official"
            options.sort((a, b) => {
                const anoA = extrairAnoOption(a.text)
                const anoB = extrairAnoOption(b.text)
                return anoA - anoB
            })

            // limpa e reinsere ordenado
            select.innerHTML = ""
            options.forEach(opt => select.appendChild(opt))

            // seleciona a mais antiga
            select.selectedIndex = 0
        }
        function extrairAnoOption(texto) {
            const match = texto.match(/\b(19|20)\d{2}\b/)
            return match ? parseInt(match[0]) : 9999
        }
function capturarPreviewsDosBotoes() {
    const botoes = document.querySelectorAll(".btn-preview")
    const mapa = {}

    botoes.forEach(btn => {
        const url = btn.dataset.preview
        const index = btn.dataset.index

        if (!url || index === undefined) return

        mapa[Number(index)] = url
    })

    return mapa
}

function extrairTracksDaTextarea() {
    const texto = document.getElementById("tracklist").value.trim()
    if (!texto) return []

    const linhas = texto.split("\\n")
    const tracks = []

    for (let linha of linhas) {
        linha = linha.trim()
        if (!linha) continue

        // regex para capturar tudo
        const match = linha.match(/^(\d+)\.\s*(.*?)\s*\((\d+:\d+)\)\s*—\s*(.*)$/)

        if (match) {
            const numero = parseInt(match[1])
            const titulo = match[2].trim()
            const duracao = match[3].trim()
            const compositor = match[4].trim()

            tracks.push({
                numero,
                titulo,
                duracao,
                compositor
            })
        } else {
            console.warn("Linha não reconhecida:", linha)
        }
    }

    return tracks
}
        
 async function salvarAlbum() {

    const artista = document.getElementById("artista").value
    const album = document.getElementById("album").value
    const release_id = document.getElementById("edicoes").value
    const gravadora = document.getElementById("gravadora").innerText
    const pais = document.getElementById("pais").innerText
    const ano = document.getElementById("ano").innerText
    const capa = document.getElementById("capa").src
    const album1 = document.getElementById("album")
    const tracks = extrairTracksDaTextarea()

    // 🔥 pega mapa de previews
    const previewsMapa = capturarPreviewsDosBotoes()

    // 🔥 casa pelo título
    tracks.forEach((track, i) => {
    track.preview = previewsMapa[i] || null
    })

    const payload = {
        artista,
        album,
        gravadora,
        capa,
        pais,
        ano,
        release_id,
        tracks
    }
    
    
    await fetch("/salvar-album", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
}

 async function buscarEdicoes() {
    const artista = document.getElementById("artista").value
    const album = document.getElementById("album").value

    const r = await fetch(`/buscar-edicoes?artista=${encodeURIComponent(artista)}&album=${encodeURIComponent(album)}`)
    const data = await r.json()

    const select = document.getElementById("edicoes")
    select.innerHTML = ""

    if (data.erro) {
        alert(data.erro)
        return
    }

    if (!data.edicoes || !data.edicoes.length) {
        alert("Nenhuma edição encontrada")
        return
    }

    data.edicoes.forEach(e => {
        const opt = document.createElement("option")
        opt.value = e.id
        opt.textContent = e.label
        select.appendChild(opt)
    })

    selecionarEdicaoMaisAntiga()

    // 🔥 dispara carregamento automático
    await carregarAlbum()
    
    }

    async function carregarAlbum() {
    const artista = document.getElementById("artista").value
    const album = document.getElementById("album").value
    const release_id = document.getElementById("edicoes").value
    const textarea = document.getElementById("tracklist")

    textarea.value = "⏳ Carregando álbum..."
    textarea.disabled = true

    try {
        const r = await fetch(
            `/carregar-album?artista=${encodeURIComponent(artista)}&album=${encodeURIComponent(album)}&release_id=${release_id}`
        )

        const data = await r.json()

        if (data.erro) {
            alert(data.erro)
            return
        }
                // 🔥 GUARDA GLOBALMENTE
        tracksCarregadas = data.tracklist || []


        textarea.value = data.tracklist
        
        let desc = document.getElementById("descricaoAlbum")
        let gravad1 = document.getElementById("gravadora")
        let pais1 = document.getElementById("pais")
        let ano1 = document.getElementById("ano")
        let album1 = document.getElementById("album")
        if (!desc) {
            desc = document.createElement("div")
            desc.id = "descricaoAlbum"
            desc.style.whiteSpace = "pre-wrap"
            desc.style.marginTop = "10px"
            document.body.appendChild(desc)
        }
        gravad1.innerText = data.info.gravadora
        pais1.innerText = data.info.pais
        ano1.innerText = data.info.ano
        album1.value = data.info.titulo
        desc.innerText = data.info.descricao || "Descrição não encontrada."

        // 🎨 capa
        if (data.info.capa) {
            let img = document.getElementById("capa")
            if (!img) {
                img = document.createElement("img")
                img.id = "capa"
                img.style.width = "200px"
                document.body.appendChild(img)
            }
            img.src = data.info.capa
        }
        
        // 🧹 remove botões antigos (EVITA DUPLICAR)
        document.querySelectorAll(".btn-preview").forEach(b => b.remove())

        
        // 🔥 garante array
        const previews =  []
        previewsGlobais =  []

        // 🔥 vincula preview às tracksCarregadas
        if (Array.isArray(tracksCarregadas)) {
            tracksCarregadas = tracksCarregadas.map((t, i) => ({
                ...t,
                preview_url: previews[i]?.url || ""
            }))
        }

        // 🔥 cria botões
        previews.forEach((p, i) => {
            if (p.url) {
                const btn = document.createElement("button")
                btn.classList.add("btn-preview")
                btn.innerText = "▶ " + p.track

                // ⭐ GUARDA URL NO BOTÃO
                btn.dataset.preview = p.url
                btn.dataset.index = i

                btn.onclick = () => window.open(p.url, "_blank")

                document.body.appendChild(btn)
            }
        })
        // 🔹 CHAMADA AUTOMÁTICA DE SALVAR COM CONFIRM
        // 🔹 AGORA sim, depois de tudo carregado, pede confirm
        if (tracksCarregadas.length) {
            await new Promise(resolve => setTimeout(resolve, 5000))
            //const ok = confirm("Deseja salvar este álbum no banco?")
            //if (ok)
            salvarAlbum()
        } else {
            alert("❌ Nenhuma faixa carregada. Não é possível salvar.")
        }

        
    } catch (e) {
        textarea.value = "❌ erro ao carregar"
        console.error(e)
    } finally {
        textarea.disabled = false
    }
}
    </script>


    
    """

@app.route("/buscar-edicoes")
def mb_buscar_edicoes():
    artista = request.args.get("artista", "").strip()
    album = request.args.get("album", "").strip()

    if not artista or not album:
        return jsonify({"erro": "Digite artista e álbum"})

    artist_id = buscar_artista(artista)
    if not artist_id:
        return jsonify({"erro": "Artista não encontrado"})

    edicoes = buscar_edicoes(artist_id, album)

    return jsonify({
        "edicoes": [
            {"label": e[0], "id": e[1]}
            for e in edicoes
        ]
    })

HEADERS = {
    "User-Agent": "AlbumHunterProPlus/1.0 (seuemail@exemplo.com)"
}
@app.route("/carregar-album")
def mb_carregar_album():
    artista = request.args.get("artista")
    album = request.args.get("album")
    release_id = request.args.get("release_id")

    if not release_id:
        return jsonify({"erro": "release_id ausente"})

    data, pais, status, gravadora, tracks,titulo_album = buscar_detalhes_release(release_id)

    # 🎨 CAPA VIA DEEZER (AGORA CORRETO)
    capa = buscar_capa_deezer(artista, album)

    # 📚 descrição
    descricao = ''

    linhas = []
    spotify_links = []
    previews = []

    for i, t in enumerate(tracks, 1):
        compositor = buscar_compositor(t["recording_id"])
        preview = ''

        linha = f"{i}. {t['title']} ({t['duracao']}) — {compositor}"
        linhas.append(linha)

        previews.append({
            "track": t["title"],
            "url": preview or ""
        })

        time.sleep(1.1)

    return jsonify({
        "info": {
            "ano": data,
            "pais": pais,
            "status": status,
            "gravadora": gravadora,
            "capa": capa,
            "descricao": descricao,
            "titulo": titulo_album
        },
        "tracklist": "\n".join(linhas),
        "deezer_preview": previews
    })





def buscar_descricao_album(release_id):
    try:
        # pegar release-group
        url = f"https://musicbrainz.org/ws/2/release/{release_id}"
        params = {"inc": "release-groups", "fmt": "json"}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15).json()

        rg_id = r["release-group"]["id"]

        # pegar relações (Wikipedia)
        url2 = f"https://musicbrainz.org/ws/2/release-group/{rg_id}"
        params2 = {"inc": "url-rels", "fmt": "json"}
        r2 = requests.get(url2, headers=HEADERS, params=params2, timeout=15).json()

        wiki_url = None
        for rel in r2.get("relations", []):
            if rel.get("type") == "wikipedia":
                wiki_url = rel["url"]["resource"]
                break

        if not wiki_url:
            return "Descrição não encontrada."

        # extrair título da página
        titulo = wiki_url.split("/")[-1]

        # API da Wikipedia
        api = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{titulo}"
        w = requests.get(api, timeout=15)

        if w.status_code != 200:
            # tenta inglês
            api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{titulo}"
            w = requests.get(api, timeout=15)

        data = w.json()
        return data.get("extract", "Descrição não encontrada.")

    except:
        return "Descrição não encontrada."
    

    try:
        # 🔎 pega release-group
        url = f"https://musicbrainz.org/ws/2/release/{release_id}"
        params = {"inc": "release-groups", "fmt": "json"}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)

        if r.status_code != 200:
            return "Descrição não encontrada."

        data = r.json()
        rg = data.get("release-group")
        if not rg:
            return "Descrição não encontrada."

        rg_id = rg["id"]

        # 🔎 procura link da wikipedia
        url2 = f"https://musicbrainz.org/ws/2/release-group/{rg_id}"
        params2 = {"inc": "url-rels", "fmt": "json"}
        r2 = requests.get(url2, headers=HEADERS, params=params2, timeout=15)

        if r2.status_code != 200:
            return "Descrição não encontrada."

        data2 = r2.json()

        wiki_url = None
        for rel in data2.get("relations", []):
            if rel.get("type") == "wikipedia":
                wiki_url = rel["url"]["resource"]
                break

        if not wiki_url:
            return "Descrição não encontrada."

        # 🧠 extrai título da página
        titulo = wiki_url.split("/")[-1]

        # 🇧🇷 tenta PT primeiro
        api_pt = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{titulo}"
        w = requests.get(api_pt, timeout=15)

        if w.status_code == 200:
            return w.json().get("extract", "Descrição não encontrada.")

        # 🇺🇸 fallback EN
        api_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{titulo}"
        w = requests.get(api_en, timeout=15)

        if w.status_code == 200:
            return w.json().get("extract", "Descrição não encontrada.")

    except Exception as e:
        print("Erro buscar_descricao_album:", e)

    return "Descrição não encontrada."

import urllib.parse
import re


def buscar_capa_deezer(artista, album):
    try:
        url = f"https://api.deezer.com/search/album?q={artista} {album}"
        r = requests.get(url, timeout=10).json()
        if r.get("data"):
            return r["data"][0]["cover_big"]
    except:
        pass
    return None

def buscar_preview_deezer(artista, musica):
    try:
        url = f"https://api.deezer.com/search?q={artista} {musica}"
        r = requests.get(url, timeout=10).json()
        if r["data"]:
            return r["data"][0]["preview"]
    except:
        pass
    return None


def buscar_artista(nome):
    try:
        nome = nome.strip()

        url = "https://musicbrainz.org/ws/2/artist/"
        params = {
            "query": f'artist:"{nome}"',
            "fmt": "json",
            "limit": 1
        }

        r = requests.get(url, headers=HEADERS, params=params, timeout=15)

        if r.status_code != 200:
            print("MB erro status:", r.status_code)
            return None

        data = r.json()

        if data.get("artists"):
            return data["artists"][0]["id"]

        # 🔥 fallback mais flexível
        params["query"] = nome
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = r.json()

        if data.get("artists"):
            return data["artists"][0]["id"]

    except Exception as e:
        print("Erro buscar_artista:", e)

    return None

def buscar_edicoes(artist_id, album):
    try:
        url = "https://musicbrainz.org/ws/2/release/"
        params = {
            "query": f'release:{album} AND arid:{artist_id}',
            "fmt": "json",
            "limit": 20
        }

        r = requests.get(url, headers=HEADERS, params=params, timeout=15).json()

        edicoes = []
        for rel in r.get("releases", []):
            data = rel.get("date", "")
            pais = rel.get("country", "")
            title = rel.get("title", "")
            status = rel.get("status", "")
            label = f"{title} - {data} • {pais} • {status}"
            edicoes.append((label, rel["id"]))


        edicoes.sort(
            key=lambda x: re.search(r'(19|20)\d{2}', x[0]).group(0)
            if re.search(r'(19|20)\d{2}', x[0])
            else "9999"
        )
        return edicoes
    except:
        return []




def buscar_detalhes_release(release_id):
    try:
        url = f"https://musicbrainz.org/ws/2/release/{release_id}"
        params = {
            "inc": "recordings+labels+release-groups",
            "fmt": "json"
        }

        r = requests.get(url, headers=HEADERS, params=params, timeout=20).json()

        

        data = r.get("date", "")
        pais = r.get("country", "")
        status = r.get("status", "")
        title =  r.get("release-group", {}).get("title", "") 
        gravadora = "—"
        if r.get("label-info"):
            info = r["label-info"][0]
            if info.get("label"):
                gravadora = info["label"]["name"]

        tracks = []
        for media in r.get("media", []):
            for t in media.get("tracks", []):
                dur_ms = t.get("length")
                duracao = ms_para_tempo(dur_ms) if dur_ms else "—"

                tracks.append({
                    "title": t["title"],
                    "recording_id": t["recording"]["id"],
                    "duracao": duracao
                })

        return data, pais, status, gravadora, tracks, title

    except:
        return "", "", "", "—", [], ""

def buscar_compositor(recording_id):
    try:
        url = f"https://musicbrainz.org/ws/2/recording/{recording_id}"
        params = {"inc": "work-rels", "fmt": "json"}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15).json()

        for rel in r.get("relations", []):
            if rel.get("type") == "performance":
                work_id = rel["work"]["id"]

                url2 = f"https://musicbrainz.org/ws/2/work/{work_id}"
                params2 = {"inc": "artist-rels", "fmt": "json"}
                w = requests.get(url2, headers=HEADERS, params=params2, timeout=15).json()

                compositores = []
                for a in w.get("relations", []):
                    if a.get("type") in ["composer", "writer"]:
                        compositores.append(a["artist"]["name"])

                if compositores:
                    return ", ".join(compositores)
    except:
        pass

    return "—"
def ms_para_tempo(ms):
    s = int(ms / 1000)
    return f"{s//60}:{s%60:02d}"

import sqlite3
from flask import request, jsonify

import re
import unicodedata

def gerar_slug(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9\s-]", "", texto)
    texto = texto.strip().lower()
    texto = re.sub(r"[\s_-]+", "-", texto)
    return texto

@app.route("/salvar-album", methods=["POST"])
def salvar_album():
    try:
        payload = request.get_json()

        print("\n===== PAYLOAD RECEBIDO =====")
        print(payload)
        print("============================\n")

        artista_nome = payload.get("artista", "").strip()
        info = payload.get("info", {})
        tracks = payload.get("tracks", [])
        release_id = payload.get("release_id")

        if not artista_nome:
            return jsonify({"erro": "artista ausente"})

        conn = sqlite3.connect("cifras.db")
        cur = conn.cursor()

        # 🎤 ARTISTA
        slug_artista = gerar_slug(artista_nome)
        cur.execute(
            "INSERT OR IGNORE INTO artistas (nome,slug) VALUES (?, ?)",
            (artista_nome,slug_artista)
        )

        cur.execute(
            "SELECT id FROM artistas WHERE nome=?",
            (artista_nome,)
        )
        row_artista = cur.fetchone()

        if not row_artista:
            raise Exception(f"Artista não encontrado após insert: {artista_nome}")

        artista_id = row_artista[0]

        # 📀 ÁLBUM
        cur.execute(
            "SELECT id FROM albuns WHERE release_mbid=?",
            (release_id,)
        )
        row = cur.fetchone()

        if row:
            album_id = row[0]
            album_novo = False
        else:

            capa_blob = baixar_imagem_blob(payload.get("capa"))

            print("CAPA RECEBIDA:", payload.get("capa"))

            if capa_blob:
                print("TAMANHO BLOB:", len(capa_blob))
            else:
                print("❌ blob vazio")

            cur.execute("""
                INSERT INTO albuns
                (
                    artista_id,
                    nome,
                    ano,
                    pais,
                    gravadora,
                    capa_blob,
                    release_mbid
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                artista_id,
                payload.get("album"),
                payload.get("ano"),
                payload.get("pais"),
                payload.get("gravadora"),
                sqlite3.Binary(capa_blob) if capa_blob else None,
                release_id
            ))
            album_id = cur.lastrowid
            album_novo = True

        # 🎵 MUSICAS
        total_tracks = 0

        for t in tracks:
            titulo_track = t.get("titulo")

            # 🔥 gerar slug da música
            cancao_slug = slug_letras(titulo_track)

            # 🔥 BUSCAR LETRA AUTOMÁTICA
            print(f"🔎 Buscando letra: {artista_nome} - {titulo_track}")
            letra_html,traducao_html,titulo_traduzido = buscar_letra_html(artista_nome, titulo_track)
            print (traducao_html)
            print ("e==============")
            cur.execute("""
                INSERT OR IGNORE INTO cancao
                (album_id, titulo, cancao_slug, compositor, duracao,
                recording_mbid,  cifra_url, letra_original,letra_traduzida,titulo_traduzido)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,?,?)
            """, (
                album_id,
                titulo_track,
                cancao_slug,  # ✅ NOVO
                t.get("compositor"),
                t.get("duracao"),
                t.get("recording_id"),
                t.get("cifra_url"),
                letra_html,
                traducao_html,
                titulo_traduzido
            ))

            total_tracks += 1

        conn.commit()
        conn.close()

        # 🔥 LOG BONITO NO CONSOLE
        print("\n---------------- DADOS SALVOS ----------------")
        print("Artista:", artista_nome)
        print("Álbum:", info.get("titulo"))
        print("Release MBID:", release_id)
        print("Álbum novo?:", "SIM" if album_novo else "JÁ EXISTIA")
        print("Faixas salvas:", total_tracks)
        print("---------------------------------------------\n")

        return jsonify({"msg": "✅ Álbum salvo com sucesso!"})

    except Exception as e:
        print("❌ ERRO salvar_album:", e)
        return jsonify({"erro": str(e)})

    
import requests
import unicodedata
import re
from bs4 import BeautifulSoup

import re
import unicodedata
