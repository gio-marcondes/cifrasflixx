PASTA_FOTOS = Path("static/fotos/artista")
PASTA_FOTOS.mkdir(parents=True, exist_ok=True)

@app.route("/atualizarfoto", methods=["GET", "POST"])
def atualizar_foto():
    senha_correta = "ttx15"

    # POST - enviar fotos
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha != senha_correta:
            return "<h3>Senha incorreta!</h3><a href='/atualizarfoto'>Voltar</a>"

        artista_slug = request.form.get("artista_slug")
        capa = request.files.get("capa")
        mini = request.files.get("mini")

        if artista_slug:
            pasta_artista = PASTA_FOTOS / artista_slug
            pasta_artista.mkdir(parents=True, exist_ok=True)

            if capa:
                capa.save(pasta_artista / "capa.jpg")
            if mini:
                mini.save(pasta_artista / "mini.jpg")

            return f"<h3>Fotos atualizadas para {artista_slug}!</h3><a href='/atualizarfoto?senha={senha}'>Voltar</a>"

    # GET - formulário de senha ou lista de artistas
    senha = request.args.get("senha")
    if senha != senha_correta:
       
        html = header("Fotos")
        html +="""
            <h2>Digite a senha</h2>
            <form method="get">
                <input type="password" name="senha">
                <button type="submit">Entrar</button>
            </form>
        """;
       
        return  html

    # mostrar artistas
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT nome, slug FROM artistas ORDER BY nome")
    artistas = c.fetchall()
    conn.close()
    html    = header("Fotos")
    html += "<h2>Atualizar fotos do artista</h2>"
    for nome, slug in artistas:
        pasta_artista = PASTA_FOTOS / slug
        mini_url = f"{pasta_artista}/mini.jpg"
        capa_url = f"{pasta_artista}/capa.jpg"

        # verificar se as fotos existem
        mini_html = f"<img src='/{mini_url}' width='80'>" if (pasta_artista / "mini.jpg").exists() else "Sem miniatura"
        capa_html = f"<img src='/{capa_url}' width='150'>" if (pasta_artista / "capa.jpg").exists() else "Sem capa"
 
        html += f"""
        <h3>{nome}</h3>
        Miniatura atual: {mini_html}<br>
        Capa atual: {capa_html}<br>
        <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="senha" value="{senha}">
            <input type="hidden" name="artista_slug" value="{slug}">
            Nova capa (grande): <input type="file" name="capa"><br>
            Nova miniatura: <input type="file" name="mini"><br>
            <button type="submit">Enviar fotos</button>
        </form>
        <hr>
        """

    return html
 


PASTA_STATIC = "static/fotos/artista"  # pasta base das imagens

def baixar_wallpapers_banda(banda, offset=0):
    # criar pasta do artista
    pasta_destino = os.path.join(PASTA_STATIC, banda.replace(" ", "_"))
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
    
    query = banda.replace(" ", "+")
    url = f"https://www.bing.com/images/search?q={query}&qft=+filterui:imagesize-wallpaper&FORM=IRFLTR"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    imagens = []
    for a_tag in soup.find_all("a", {"class": "iusc"}):
        try:
            m_json = json.loads(a_tag.get("m", "{}"))
            img_url = m_json.get("murl")
            if img_url and img_url.startswith("http"):
                imagens.append(img_url)
        except:
            continue
    
    # aplicar offset e pegar 2 imagens consecutivas
    imagens = imagens[offset:offset+2]
    
    arquivos_salvos = []
    nomes = ["capa.jpg", "mini.jpg"]
    for i, img_url in enumerate(imagens):
        try:
            response = requests.get(img_url)
            nome_arquivo = os.path.join(pasta_destino, nomes[i])
            with open(nome_arquivo, "wb") as f:
                f.write(response.content)
            # caminho relativo para uso no browser
            arquivos_salvos.append(url_for('static', filename=f"fotos/artista/{banda.replace(' ','_')}/{nomes[i]}"))
        except Exception as e:
            print(f"Erro ao baixar {img_url}: {e}")
    
    return arquivos_salvos

@app.route("/pegarfotos", methods=["GET", "POST"])
def pegar_fotos():
    arquivos = None
    erro = None
    banda = None

    if request.method == "POST":
        banda = request.form.get("banda")
        try:
            offset = int(request.form.get("offset", 0))
            if offset < 0:
                offset = 0
        except:
            offset = 0

        if not banda:
            erro = "Informe o nome da banda!"
        else:
            # baixar as imagens
            caminhos_fisicos = baixar_wallpapers_banda(banda, offset)
            if not caminhos_fisicos:
                erro = "Nenhuma imagem encontrada"
            else:
                # gerar URLs para o browser usando url_for
                arquivos = [url_for('static', filename=f"fotos/artista/{banda.replace(' ','_')}/{os.path.basename(c)}") for c in caminhos_fisicos]

    return render_template("pegar_fotos.html", titulo="Baixar", arquivos=arquivos, erro=erro, banda=banda)




@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == "ttx15":
            session["admin"] = True
            return redirect("/admin/painel")
        else:
            return "Senha incorreta"
    return render_template("admin_login.html")


    import requests
import re

def buscar_capa_album_bing(artista, album):
    query = f"{artista} {album} album cover"
    url = f"https://www.bing.com/images/search?q={requests.utils.quote(query)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    html = requests.get(url, headers=headers).text
    
    # regex simples para pegar a primeira URL de imagem
    match = re.search(r'murl&quot;:&quot;(http[s]?://[^&]+)&quot;', html)
    if match:
        return match.group(1)
    return None


@app.route("/admin/procurar_capa")
def procurar_capa():
    artista = request.args.get("artista", "")
    album = request.args.get("album", "")
    url = buscar_capa_album_bing(artista, album)
    return jsonify({"url": url})




@app.route("/admin/painel", methods=["GET"])
def admin_painel():
    if not session.get("admin"):
        return redirect("/admin")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Lista artistas
    c.execute("SELECT id, nome FROM artistas ORDER BY nome")
    artistas = c.fetchall()
    conn.close()

    html = """
    <h2>Painel Admin - Criar Álbum</h2>
    <form method="post" action="/admin/criar_album" enctype="multipart/form-data">
        <label>Artista:</label><br>
        <select id="artista" name="artista_id">
    """

    for id_, nome in artistas:
        html += f'<option value="{id_}">{nome}</option>'

    html += """
        </select><br><br>

<script>
function procurarCapa() {
    const artista = document.querySelector('select[name="artista_id"]').selectedOptions[0].text;
    const album = document.getElementById("album_nome").value;

    if (!album) {
        alert("Digite o nome do álbum primeiro!");
        return;
    }

    fetch(`/admin/procurar_capa?artista=${encodeURIComponent(artista)}&album=${encodeURIComponent(album)}`)
        .then(res => res.json())
        .then(data => {
            if (data.url) {
                document.getElementById("preview_capa").src = data.url;
                document.getElementById("capa_url").value = data.url;
            } else {
                alert("Nenhuma capa encontrada!");
            }
        });
}
</script>
<script>
async function importarWiki() {
    const nome = document.getElementById("album_nome").value;
    const artistaSelect = document.getElementById("artista");
    const artista = artistaSelect.options[artistaSelect.selectedIndex].text;

    if (!nome) {
        alert("Digite o nome do álbum!");
        return;
    }

    try {
        const resp = await fetch(`/admin/importar_wiki?nome=${encodeURIComponent(nome)}&artista=${encodeURIComponent(artista)}`);
        const data = await resp.json();

        const textarea = document.getElementById("tracklist");

        if (data.tracklist && data.tracklist.trim() !== "") {
            textarea.value = data.tracklist;
        } else {
            textarea.value = `❌ Não achei tracklist.\n\n🔎 Link pesquisado:\n${data.url || "Não encontrado"}`;
        }

    } catch (e) {
        alert("Erro ao importar da Wiki");
        console.error(e);
    }
}
async function confirmarEdicao() {
    const select = document.getElementById("selectEdicao");
    const releaseId = select.value;

    if (!releaseId) {
        alert("Selecione uma edição primeiro!");
        return;
    }

    const loading = document.getElementById("loadingAlbum");
    loading.innerHTML = "⏳ Carregando dados do álbum...";

    try {
        await cacarAlbum(releaseId);
    } catch (e) {
        loading.innerHTML =
            "<span style='color:red'>❌ Erro ao carregar edição.</span>";
        console.error(e);
    }
}
</script>  
     <script>
async function cacarAlbum(releaseId=null) {
    const artista = document.getElementById("artista").value;
    const album = document.getElementById("album_nome").value;

    document.getElementById("loading").style.display = "block";

    let url = "/admin/mb_album?artista=" + encodeURIComponent(artista)
            + "&album=" + encodeURIComponent(album);

    if (releaseId) {
        url += "&release_id=" + releaseId;
    }

    const r = await fetch(url);
    const data = await r.json();

    document.getElementById("loading").style.display = "none";

    // 🔹 se vier lista de edições
    // 🔹 se vier lista de edições
    if (data.edicoes) {

        // ❗ caso não tenha nenhuma edição
        if (!data.edicoes.length) {
            document.getElementById("resultado").innerHTML =
                "<div style='color:red'>❌ Nenhuma edição encontrada.</div>";
            return;
        }

        let html = `
            <h3>Escolha a edição:</h3>

            <select id="selectEdicao" style="padding:6px; min-width:280px;">
                <option value="">-- selecione uma versão --</option>
        `;

        data.edicoes.forEach(e => {
            html += `
                <option value="${e.id}">
                    ${e.titulo} ${e.data ? "— " + e.data : ""}
                </option>
            `;
        });

        html += `
            </select>

            <button onclick="confirmarEdicao()" style="margin-left:8px;">
                🔎 Carregar
            </button>

            <div id="loadingAlbum" style="margin-top:10px;"></div>
        `;

        document.getElementById("resultado").innerHTML = html;
        return;
    }

    // 🔹 capa
    let capaHtml = data.capa
        ? `<img src="${data.capa}" style="max-width:200px;">`
        : "";

    // 🔹 header do álbum
    let html = `
        <div style="margin-bottom:20px;">
            ${capaHtml}
            <p><b>Data:</b> ${data.data || ""}</p>
            <p><b>País:</b> ${data.pais || ""}</p>
            <p><b>Status:</b> ${data.status || ""}</p>
            <p><b>Gravadora:</b> ${data.gravadora || ""}</p>
            <p>${data.descricao || ""}</p>
        </div>
    `;

    // 🔹 tracklist
    html += "<h3>Faixas</h3>";

    data.tracks.forEach(t => {
        let botaoPlay = t.preview
            ? `<a href="${t.preview}" target="_blank">🎧 ouvir</a>`
            : "";

        html += `
            <div style="margin:6px 0;">
                ${t.titulo} – ${t.duracao_formatada || ""}
                / ${t.compositor || ""}
                ${botaoPlay}
            </div>
        `;
    });

    document.getElementById("resultado").innerHTML = html;
}
</script>
        <div id="loading" style="display:none; margin:20px 0;">
  🔎 Caçando dados do álbum...
</div>
         <button type="button" onclick="cacarAlbum()">😈 Caçar Álbum</button> 
    
    <div id="resultado"></div>

<label>Nome do Álbum:</label><br>
<input type="text" name="nome" id="album_nome" required><br><br>

<label>Ano:</label><br>
<input type="text" name="ano"><br><br>

<button type="button" onclick="procurarCapa()">🔎 Buscar Capa</button><br><br>

<img id="preview_capa" src="" style="max-width:200px; border-radius:8px;"><br><br>
<input type="hidden" name="capa_url" id="capa_url">
<button type="button" onclick="importarWiki()">Importar da Wiki</button>

<label>Tracklist (uma música por linha):</label><br>
<textarea
    name="tracklist" id="tracklist"
    rows="12"
    style="width:350px; padding:8px;"
    placeholder="1. Música Um
2. Música Dois
3. Música Três
4. Música Quatro"
></textarea><br><br>

<button type="submit">💾 Criar Álbum</button>
</form>
    """

    return html

import requests
from bs4 import BeautifulSoup
import re

def importar_tracklist_wiki(nome_album, artista):
    headers = {"User-Agent": "Mozilla/5.0"}

    # =========================
    # 1️⃣ TENTA WIKIPEDIA
    # =========================
    query = f"{nome_album} {artista} album wikipedia".replace(" ", "+")
    url_busca = f"https://www.bing.com/search?q={query}"

    html_busca = requests.get(url_busca, headers=headers).text

    match = re.search(
        r"https://(en|pt)\.wikipedia\.org/wiki/[A-Za-z0-9_%()\-]+",
        html_busca
    )

    url_wiki = ""

    if match:
        url_wiki = match.group(0)

        try:
            html = requests.get(url_wiki, headers=headers).text
            soup = BeautifulSoup(html, "html.parser")

            tracklist_final = []

            tabelas = soup.select("table.wikitable")

            for tabela in tabelas:
                linhas = tabela.find_all("tr")

                for linha in linhas:
                    cols = linha.find_all(["td", "th"])

                    if len(cols) >= 2:
                        numero = cols[0].get_text(strip=True)
                        titulo = cols[1].get_text(strip=True)

                        duracao = ""
                        if len(cols) >= 3:
                            possivel_dur = cols[-1].get_text(strip=True)
                            if re.match(r"\d{1,2}:\d{2}", possivel_dur):
                                duracao = possivel_dur

                        if re.match(r"^\d+", numero):
                            linha_formatada = f"{numero}. {titulo}"
                            if duracao:
                                linha_formatada += f" {duracao}"
                            tracklist_final.append(linha_formatada)

            if tracklist_final:
                return "\n".join(tracklist_final), url_wiki

        except:
            pass

    # =========================
    # 2️⃣ FALLBACK MUSICBRAINZ
    # =========================
    try:
        mb_query = requests.utils.quote(f"{nome_album} {artista}")
        mb_url = f"https://musicbrainz.org/search?query={mb_query}&type=release&method=indexed"
        return "", mb_url
    except:
        pass

    # =========================
    # 3️⃣ Fallback final (Bing)
    # =========================
    return "", url_busca

@app.route("/admin/importar_wiki")
def importar_wiki():
    nome = request.args.get("nome")
    artista = request.args.get("artista")

    tracklist, url_wiki = importar_tracklist_wiki(nome, artista)

    return jsonify({
        "tracklist": tracklist,
        "url": url_wiki
    })

@app.route("/admin/musicas_artista")
def musicas_artista():
    artista_id = request.args.get("artista_id")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, titulo FROM musicas WHERE artista_id=? ORDER BY titulo", (artista_id,))
    musicas = [{"id": m[0], "titulo": m[1]} for m in c.fetchall()]
    conn.close()
    return jsonify(musicas)

@app.route("/admin/criar_album", methods=["POST"])
def criar_album():
    if not session.get("admin"):
        return redirect("/admin")

    artista_id = request.form.get("artista_id")
    nome = request.form.get("nome")
    ano = request.form.get("ano")
    tracklist = request.form.get("tracklist", "")
    capa_url = request.form.get("capa_url", "")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 🔥 baixa imagem da URL
    capa_blob = baixar_imagem_blob(capa_url)

    c.execute(
        """
        INSERT INTO albuns
        (
            artista_id,
            nome,
            ano,
            capa_blob
        )
        VALUES (?,?,?,?)
        """,
        (
            artista_id,
            nome,
            ano,
            sqlite3.Binary(capa_blob) if capa_blob else None
        )
    )
    album_id = c.lastrowid

    # 🔥 processar tracklist (VERSÃO PRO MASTER)
    import re

    linhas = [l.strip() for l in tracklist.split("\n") if l.strip()]

    for i, linha in enumerate(linhas, start=1):
        # remove numeração inicial: "1. "
        linha = re.sub(r'^\d+\.\s*', '', linha)

        titulo = linha
        duracao = ""
        compositores = ""

        # separa compositores
        if " / " in linha:
            parte_musica, compositores = linha.split(" / ", 1)
            linha = parte_musica.strip()
            compositores = compositores.strip()

        # pega duração
        match_hifen = re.search(r'\s*-\s*(\d{1,2}:\d{2})$', linha)
        match_espaco = re.search(r'\s+(\d{1,2}:\d{2})$', linha)

        if match_hifen:
            duracao = match_hifen.group(1)
            titulo = linha[:match_hifen.start()].strip()
        elif match_espaco:
            duracao = match_espaco.group(1)
            titulo = linha[:match_espaco.start()].strip()
        else:
            titulo = linha.strip()

        # salva faixa
        c.execute("""
            INSERT INTO faixas_album
            (album_id, numero, titulo, duracao, compositores, musica_id)
            VALUES (?,?,?,?,?,NULL)
        """, (album_id, i, titulo, duracao, compositores))

    # ✅ commit DEPOIS do loop
    conn.commit()
    conn.close()

    return redirect(f"/admin/vincular_album/{album_id}")


@app.route("/admin/vincular_album/<int:album_id>", methods=["GET", "POST"])
def vincular_album(album_id):
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        for key, value in request.form.items():
            if key.startswith("faixa_") and value:
                faixa_id = key.replace("faixa_", "")
                c.execute(
                    "UPDATE faixas_album SET musica_id=? WHERE id=?",
                    (value, faixa_id)
                )
        conn.commit()
        conn.close()
        return "Vinculação salva! <a href='/admin/painel'>Voltar</a>"

    # dados do álbum
    c.execute("""
        SELECT f.id, f.numero, f.titulo, a.artista_id
        FROM faixas_album f
        JOIN albuns a ON f.album_id = a.id
        WHERE f.album_id=?
        ORDER BY f.numero
    """, (album_id,))
    faixas = c.fetchall()

    artista_id = faixas[0][3] if faixas else None

    # músicas do artista
    c.execute(
        "SELECT id, titulo FROM musicas WHERE artista_id=? ORDER BY titulo",
        (artista_id,)
    )
    musicas = c.fetchall()
    conn.close()

    # HTML
    html = "<h2>Vincular Faixas</h2><form method='post'>"

    for faixa_id, numero, titulo, _ in faixas:
        html += f"<b>{numero}. {titulo}</b><br>"
        html += f"<select name='faixa_{faixa_id}'>"
        html += "<option value=''>-- selecionar música --</option>"
        for mid, mtitulo in musicas:
            html += f"<option value='{mid}'>{mtitulo}</option>"
        html += "</select><br><br>"

    html += "<button type='submit'>Salvar vínculos</button></form>"
    return html


def ms_para_min(ms):
    if not ms:
        return ""
    s = int(ms / 1000)
    return f"{s//60}:{s%60:02d}"
