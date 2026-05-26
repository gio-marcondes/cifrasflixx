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

    # 🔥 1. procura no banco primeiro
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
        return row["letra_original"], row["letra_traduzida"]

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

    conn.commit()
    conn.close()

    return letra_html, letra_traduzida

@app.route("/letra/<artista>/<musica>")
def ver_letra(artista, musica):
    letra_html, traducao_html = procura_letra(artista, musica)

    if not letra_html:
        letra_html = "<p>Letra não encontrada.</p>"

    # 🔹 slugs
    artista_slug = normalizar_slug(artista)
    slug = artista_slug

    # 🔹 título formatado
    titulo = musica.replace("-", " ").title()
    artista_nome = artista.replace("-", " ").title()

    # 🔹 dados mock (ajuste se já tiver)
    versoes = [(1, titulo)]
    uid = 1
    iframe_video = ""  # coloque seu player se tiver
    musica_slug = musica
    html = header(titulo) + f"""
<style>
main{{
    width:100%;
    max-width:none;
}}

.songLayout{{
    width:100%;
    max-width:1280px;
    margin:20px auto;
    padding:0 20px;
    display:grid;
    grid-template-columns: 240px minmax(0, 1fr) 300px;
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
    padding:18px;
    box-shadow:0 2px 6px rgba(0,0,0,0.04);
    margin-bottom:13px;
}}

.songCenter{{
    min-width:0;
    width:100%;
    margin-top: 0px;
    padding-top: 0px;

}}

.songTitle{{
    margin-bottom:14px;
}}

.lyricBox{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:28px;
    font-size:16px;
    line-height:1.7;
    color:#111827;
}}

.lyricBox p{{
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
</style>
<script>
function traduzirLetra() {{
    const original = document.getElementById("lyricOriginal");
    const traducao = document.getElementById("lyricTraducao");
    const btn = document.querySelector(".btnTraducao");

    if (!traducao || !traducao.innerHTML.trim()) {{
        alert("Tradução não disponível");
        return;
    }}

    const mostrandoTraducao = traducao.style.display !== "none";

    if (!mostrandoTraducao) {{
        original.style.display = "none";
        traducao.style.display = "block";
        btn.innerHTML = "🔁 Ver original";
    }} else {{
        original.style.display = "block";
        traducao.style.display = "none";
        btn.innerHTML = "🌐 Ver tradução";
    }}
}}

function abrirImpressaoLetra(artista, musica) {{
    window.open(`/letra/${{artista}}/${{musica}}/print?translation=pt`, "_blank");
}}

function ajustarFonteLetra(delta) {{
    const reader = document.querySelector(".lyricReader");
    const atual = Number(reader?.dataset.fontScale || 0);
    const proximo = Math.max(-2, Math.min(4, atual + delta));
    if (reader) reader.dataset.fontScale = proximo;
    document.querySelectorAll(".lyricBox").forEach(box => {{
        box.style.fontSize = `${{17 + proximo}}px`;
    }});
}}

function alternarDuasColunas() {{
    document.querySelector(".lyricReader")?.classList.toggle("compareMode");
    const original = document.getElementById("lyricOriginal");
    const traducao = document.getElementById("lyricTraducao");
    if (original && traducao) {{
        original.style.display = "block";
        traducao.style.display = "block";
    }}
}}
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
        <div style="margin-bottom:12px;">
    <button class="btnTraducao" onclick="traduzirLetra()">
        🌐 Ver tradução
    </button>
</div>
        <div class="controlCard lyricActionCard">
            <div class="controlTitle">Estudo</div>
            <button type="button" onclick="abrirImpressaoLetra('{artista_slug}', '{musica_slug}')">Imprimir</button>
            <button type="button" onclick="alternarDuasColunas()">Original + traducao</button>
            <div class="fontControls">
                <button type="button" onclick="ajustarFonteLetra(-1)">A-</button>
                <button type="button" onclick="ajustarFonteLetra(1)">A+</button>
            </div>
        </div>
    </aside>

    <!-- 🔥 LETRA -->
    <main class="songCenter lyricReader">
        <p class="eyebrow">Letra</p>\n        <h1 class="songTitle">{titulo}</h1>
        <p>
            <a class="chord" href="/artista/{artista_slug}">
                {artista_nome}
            </a>
        </p>

        <div class="lyricBox" id="lyricTraducao" style="display:none;">
            {traducao_html}
        </div>
        <div class="lyricBox" id="lyricOriginal">
            {letra_html}
        </div>
    <script>
let traduzido = false
let letraOriginalCache = ""


</script>


    </main>

    <!-- 🎬 VÍDEO -->
    <aside class="songVideo lyricAside">
        <div class="videoWrapper">
            {iframe_video}
        </div>
    </aside>

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
