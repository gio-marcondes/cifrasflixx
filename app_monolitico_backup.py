import os
import re
import random
import sqlite3
import time
from flask import Flask, request, redirect, jsonify
from pathlib import Path

from flask import Flask, request, render_template_string
import os
import requests
from bs4 import BeautifulSoup
import json

import requests
import re
import urllib.parse
import requests
import urllib.parse
import re

app = Flask(__name__)
DB = "cifras.db"
PASTA_TXT = "cifras_txt"

from flask import Flask, request, redirect, url_for, render_template_string, session
import os
from werkzeug.utils import secure_filename

app.secret_key = "ttx15_secret"  # necessário para session

UPLOAD_FOLDER = "static/capas"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
HEADERS_MB = {
    "User-Agent": "CifrasFlix/1.0 (seuemail@exemplo.com)"
}

def formatar_data(data_str):
    if not data_str:
        return ""

    try:
        from datetime import datetime

        # tenta YYYY-MM-DD
        dt = datetime.strptime(data_str[:10], "%Y-%m-%d")

        meses = [
            "", "janeiro", "fevereiro", "março", "abril",
            "maio", "junho", "julho", "agosto",
            "setembro", "outubro", "novembro", "dezembro"
        ]

        return f"{dt.day} de {meses[dt.month]} de {dt.year}"

    except:
        return data_str
# ==========================================
# SLUGIFY
# ==========================================
def slugify(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')
def normalizar_slug(texto):
    import re
    texto = texto.lower().strip()
    texto = texto.replace(" ", "-")
    texto = re.sub(r"[^a-z0-9\-]", "", texto)
    return texto
# ==========================================
# BANCO
# ==========================================


def baixar_imagem_blob(url):

    print("URL CAPA:", url)

    if not url:
        print("❌ URL vazia")
        return None

    try:

        r = requests.get(url, timeout=20)

        print("STATUS IMG:", r.status_code)

        if r.status_code == 200:

            print("BYTES:", len(r.content))

            return r.content

    except Exception as e:

        print("ERRO DOWNLOAD:", e)

    return None

def pegar_ano(data_str):
    if not data_str:
        return ""

    # pega os 4 primeiros caracteres se forem números
    ano = str(data_str)[:4]

    return ano if ano.isdigit() else ""

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS artistas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        slug TEXT UNIQUE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS musicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        slug TEXT,
        uid TEXT UNIQUE,
        artista_id INTEGER,
        conteudo TEXT,
        views INTEGER DEFAULT 0,
        FOREIGN KEY (artista_id) REFERENCES artistas(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS favoritos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        musica_id INTEGER UNIQUE
    )
    """)
    conn.commit()
    conn.close()

# ==========================================
# IMPORTADOR TXT
# ==========================================
def importar_txt():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    pasta = Path(PASTA_TXT)

    if not pasta.exists():
        print("Pasta cifras_txt não encontrada.")
        return

    for pasta_artista in pasta.iterdir():

        if pasta_artista.is_dir():

            artista_nome = pasta_artista.name.strip()
            artista_slug = slugify(artista_nome)

            c.execute(
                "INSERT OR IGNORE INTO artistas (nome, slug) VALUES (?,?)",
                (artista_nome, artista_slug)
            )

            c.execute(
                "SELECT id FROM artistas WHERE slug=?",
                (artista_slug,)
            )

            artista_id = c.fetchone()[0]

            print(f"\n🎤 ARTISTA: {artista_nome}")

            for arquivo in pasta_artista.glob("*.txt"):

                try:

                    with open(arquivo, "r", encoding="utf-8", errors="ignore") as f:
                        conteudo_original = f.read()

                    linhas = conteudo_original.splitlines()

                    afinacao = ""
                    tom = ""
                    capotraste = ""

                    # ------------------------
                    # TITULO
                    # ------------------------
                    titulo = arquivo.stem.strip()

                    if linhas:
                        primeira = linhas[0].replace(" Cifra", "").strip()

                        if primeira:
                            titulo = primeira

                    # ------------------------
                    # CAPTURA INFORMAÇÕES
                    # ------------------------
                    for linha in linhas:

                        linha_strip = linha.strip()

                        # afinação
                        if linha_strip.lower().startswith("afinação:"):
                            afinacao = linha_strip.split(":", 1)[1].strip()

                        # tom
                        if linha_strip.lower().startswith("tecla:"):
                            tom = linha_strip.split(":", 1)[1].strip()

                        # capotraste
                        if linha_strip.lower().startswith("capotraste:"):

                            match = re.search(r"(\d+)", linha_strip)

                            if match:
                                capotraste = match.group(1)
                            else:
                                capotraste = "0"

                    # -----------------------------------
                    # PEGA SOMENTE O QUE VEM APÓS TAB:
                    # -----------------------------------
                    match_tab = re.search(
                        r"TAB:\s*(.*)",
                        conteudo_original,
                        re.DOTALL | re.IGNORECASE
                    )

                    if match_tab:
                        conteudo = match_tab.group(1).strip()
                    else:
                        conteudo = ""

                    slug = slugify(titulo)

                    uid = f"{slug}-{random.randint(10000,99999)}"

                    c.execute("""
                    INSERT OR IGNORE INTO musicas
                    (
                        titulo,
                        slug,
                        uid,
                        artista_id,
                        conteudo,
                        afinacao,
                        tom,
                        capotraste
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        titulo,
                        slug,
                        uid,
                        artista_id,
                        conteudo,
                        afinacao,
                        tom,
                        capotraste
                    ))

                    print(f"   ✅ {titulo}")
                    print(f"      Tom: {tom}")
                    print(f"      Afinação: {afinacao}")
                    print(f"      Capotraste: {capotraste}")

                except Exception as e:

                    print(f"   ❌ ERRO: {arquivo.name}")
                    print(e)

    conn.commit()
    conn.close()

    print("\n✅ Importação concluída.")

# ==========================================
# TRANSPOSIÇÃO REAL
# ==========================================
NOTAS = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def transpor_acordes(texto, semitons):
    def trocar(match):
        acorde = match.group(0)
        if acorde in NOTAS:
            idx = NOTAS.index(acorde)
            novo = NOTAS[(idx + semitons) % 12]
            return novo
        return acorde
    padrao = r'\b(' + '|'.join(NOTAS) + r')\b'
    return re.sub(padrao, trocar, texto)

# ==========================================
# HEADER / CSS estilo Netflix
# ==========================================
def header(titulo="CifrasFlix"):
    return f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>{titulo}</title>

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
:root{{
    --bg:#f5f6f7;
    --card:#ffffff;
    --accent:#ff7a00;
    --text:#1f2937;
    --muted:#6b7280;
    --border:#e5e7eb;
}}
main{{
    margin-top: 48px;
}}

*{{box-sizing:border-box;}}

body{{
    margin:0;
    font-family:'Inter', sans-serif;
    background:var(--bg);
    color:var(--text);
}}

/* TOP BAR */
.topBar{{
    position:fixed;
    top:0;
    width:100%;
    height:70px;
    background:#ffffff;
    display:flex;
    align-items:center;
    padding:0 40px;
    z-index:1000;
    border-bottom:1px solid var(--border);
}}
.letra-link{{
    color:#2563eb;
    font-weight:500;
    text-decoration:none;
    margin-left:8px;
}}

.letra-link:hover{{
    text-decoration:underline;
}}

.only-lyric{{
    color:#059669; /* verde quando só tem letra */
}}

.only-lyric:hover{{
    color:#047857;
}}
.logo a{{
    color:var(--accent);
    font-size:26px;
    font-weight:700;
    text-decoration:none;
}}

.menu{{
    margin-left:40px;
    display:flex;
    gap:24px;
}}

.menu a{{
    color:var(--muted);
    text-decoration:none;
    font-size:15px;
    font-weight:500;
    transition:.2s;
}}
.letraBox {{
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 20px;
    line-height: 1.6;
    white-space: normal;
}}

.letraBox p {{
    margin-bottom: 16px;
}}
.menu a:hover{{
    color:var(--text);
}}
.musicInfoRow{{
    display:flex;
    gap:40px;
    margin-bottom:20px;
}}

.infoBox{{
    flex:1;
}}

/* SEARCH */
#busca{{
    margin-left:auto;
    width:260px;
    padding:10px 14px;
    border-radius:10px;
    border:1px solid var(--border);
    background:#fafafa;
    outline:none;
}}

#busca:focus{{
    border-color:var(--accent);
}}

/* MAIN */
main{{
    padding:30px 20px;
    
}}

#tituloPagina{{
    font-size:36px;
    margin-bottom:4px;
}}

.subtitulo{{
    color:var(--accent);
    font-weight:600;
    margin-bottom:20px;
}}



.albumGrid{{
    display:grid !important;
    grid-template-columns:repeat(auto-fill,minmax(180px,1fr)) !important;
    gap:16px;
    width:100%;
}}
.albumCard{{
    text-decoration:none;
    color:inherit;
    background:#f3f4f6;
    border:1px solid #e5e7eb;
    border-radius:10px;
    padding:12px;
    transition:.15s;
    display:block;
    width:100%;
    box-sizing:border-box;
}}

.albumCard:hover{{
    transform:translateY(-2px);
    background:#ffffff;
    border-color:#d1d5db;
    box-shadow:0 4px 12px rgba(0,0,0,0.06);
}}

.albumCover{{
    width:100%;
    height:170px;
    object-fit:cover;
    border-radius:8px;
    background:#e5e7eb;
    display:block;
}}

.albumTitle{{
    margin-top:8px;
    font-weight:600;
    font-size:14px;
    color:#111827;
    line-height:1.25;
}}

.albumYear{{
    font-size:12px;
    color:#6b7280;
    margin-top:2px;
}}
/* CARD */
.card{{
    background:var(--card);
    border:1px solid var(--border);
    border-radius:14px;
    padding:18px;
    margin-bottom:20px;
}}

/* LIST */
.list-item{{
    padding:14px;
    border-radius:10px;
    cursor:pointer;
    transition:.2s;
}}

.list-item:hover{{
    background:#f1f5f9;
}}

/* BUTTON */
button,.backBtn{{
    background:#fff;
    border:1px solid var(--border);
    padding:10px 16px;
    border-radius:10px;
    cursor:pointer;
    font-weight:600;
    transition:.2s;
    text-decoration:none;
    color:#666;
}}

button:hover,.backBtn:hover{{
    border-color:var(--accent);
    color:var(--accent);
}}

/* PRE CIFRA */
pre{{
    background:#f8fafc;
    padding:24px;
    border-radius:14px;
    overflow:auto;
    white-space:pre-wrap;
    line-height:1.6;
    border:1px solid var(--border);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}}

/* ACORDES */
.chord{{
    font-weight:700;
    color:var(--accent);
    cursor:pointer;
    position:relative; text-decoration:none;
}}

.chord-diagram{{
    position:absolute;
    top:24px;
    left:0;
    background:#fff;
    padding:6px;
    border-radius:8px;
    border:1px solid #ccc;
    display:none;
    z-index:9999;
    box-shadow:0 8px 24px rgba(0,0,0,0.15);
}}

.controlsBar{{
    display:flex;
    gap:12px;
    flex-wrap:wrap;
    align-items:center;
    margin:15px 0;
}}

.ctrlBtn{{
    background:#2a2a2a;
    border:1px solid #444;
    color:#fff;
    padding:8px 14px;
    border-radius:8px;
    cursor:pointer;
    transition:.2s;
    font-size:14px;
}}

.ctrlBtn:hover{{
    background:#e50914;
    border-color:#e50914;
}}

.speedBox{{
        display:flex;
    align-items:center;
    gap:6px;
    background:#1c1c1c;
    padding:6px 10px;
    border-radius:8px;
    border:1px solid #333;
}}

.videoBox{{
    width:100%;
    max-width:520px;
    aspect-ratio:16/9;
    border-radius:14px;
    overflow:hidden;
    background:#000;
    box-shadow:0 8px 30px rgba(0,0,0,.6);
}}

</style>
<style>
/* ===== ARTISTA PAGE ===== */

.artistLayout{{
    display:grid;
    grid-template-columns: 320px 1fr;
    gap:40px;
}}

.artistCard{{
    background: #ccc;
    border-radius:16px;
    padding:25px;
    text-align:center;
    height:fit-content;
    box-shadow:0 10px 40px rgba(0,0,0,.5);
}}

.artistPhoto{{
    width:220px;
    height:220px;
    border-radius:50%;
    object-fit:cover;
    margin-bottom:15px;
    border:4px solid #2a2a2a;
}}

.artistName{{
    font-size:32px;
    font-weight:700;
}}

.musicTable{{
    width:100%;
}}

.musicRow{{
    display:grid;
    grid-template-columns: 60px 1fr 120px 80px;
    align-items:center;
    padding:12px 10px;
    border-bottom:1px solid #2a2a2a;
    transition:.2s;
    cursor:pointer;
}}

.musicRow:hover{{
    background:#1c1c1c;
}}

.musicIndex{{
    opacity:.6;
}}

.musicTitle{{
    font-weight:500;
}}

.musicViews{{
    opacity:.7;
}}

.musicKey{{
    background:#2a2a2a;
    padding:4px 10px;
    border-radius:6px;
    text-align:center;
    font-weight:bold;
}}

@media(max-width:900px){{
    .artistLayout{{
        grid-template-columns:1fr;
    }}
}}
</style>
<style>
/* ===== KEY (Tom) ===== */
.musicKey{{
    background:#e5e7eb; /* cinza claro */
    color:#374151;
    padding:4px 10px;
    border-radius:6px;
    font-size:13px;
    font-weight:600;
    text-align:center;
}}

/* ===== LINHA ===== */
.musicRow{{
    display:grid;
    grid-template-columns: 60px 1fr 120px 80px;
    align-items:center;
    padding:12px 10px;
    border-bottom:1px solid #262626;
    cursor:pointer;
}}

/* 🔥 hover SÓ no nome */
.musicTitle{{
    font-weight:500;
    padding:4px 6px;
    border-radius:6px;
    transition:background .18s ease;
}}

.musicRow:hover {{
    background:#f3f4f6; /* cinza bem leve */
}}

/* ===== BADGE VERSÕES ===== */
.versaoBadge{{
    background:#e50914;
    color:white;
    font-size:11px;
    font-weight:bold;
    padding:2px 6px;
    border-radius:6px;
    margin-left:8px;
}}
.musicGrid{{
    display:grid;
    grid-template-columns: 1fr 1fr;
    gap:14px;
}}

.musicRow{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:10px;
    padding:12px;
    transition:.15s;

    display:grid;
    grid-template-columns: 60px 205px 120px 90px; /* 👈 largura fixa */
    align-items:center;
    gap:10px;
}}

.musicRow:hover{{
    background:#f3f4f6; /* cinza bem leve */
}}

.musicKey{{
    background:#e5e7eb;
    color:#374151;
}}

.paginacao{{
    grid-column:1/-1;
    display:flex;
    justify-content:center;
    align-items:center;
    gap:16px;
    margin-top:20px;
}}

.pageBtn{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    padding:8px 14px;
    border-radius:8px;
    text-decoration:none;
    color:#111827;
    font-weight:600;
}}

.pageBtn:hover{{
    background:#f3f4f6;
}}

.pageInfo{{
    font-weight:600;
    color:#6b7280;
}}
.ordenarBar{{
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:14px;
}}

.ordLabel{{
    font-weight:600;
    color:#6b7280;
}}

.ordBtn{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    padding:6px 12px;
    border-radius:8px;
    text-decoration:none;
    color:#111827;
    font-weight:600;
    font-size:13px;
}}

.ordBtn:hover{{
    background:#f3f4f6;
}}

.ordBtn.active{{
    background:#111827;
    color:#ffffff;
    border-color:#111827;
}}
body.dark{{
    background:#0f172a;
    color:#e5e7eb;
}}

body.dark .musicRow{{
    background:#111827;
    border-color:#1f2937;
}}

body.dark .musicRow:hover{{
    background:#1f2937;
}}

body.dark .musicKey{{
    background:#1f2937;
    color:#e5e7eb;
}}

body.dark .ordBtn{{
    background:#111827;
    border-color:#1f2937;
    color:#e5e7eb;
}}

body.dark .ordBtn.active{{
    background:#e5e7eb;
    color:#111827;
}}

.darkToggle{{
 
    border:none;
    background:#666;
    color:#fff;
    padding:4px 4px;
    border-radius:10px;
    cursor:pointer; margin:0px 10px 10px 10px;
}}
/* ===== HOME WRAPPER ===== */
.homeContainer{{
    max-width:1200px;
    margin:30px auto;
    padding:0 20px;
}}

/* ===== GRID DE LETRAS ===== */
.homeAZ{{
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
    gap:10px;
    margin-bottom:25px;
}}

/* ===== BOTÃO LETRA ===== */
.homeLetter{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:10px;
    padding:10px 0;
    text-align:center;
    font-weight:600;
    color:#111827;
    cursor:pointer;
    transition:all .15s ease;
    user-select:none;
}}

.homeLetter:hover{{
    background:#f3f4f6;
    border-color:#d1d5db;
}}

/* ===== LISTA DE ARTISTAS ===== */
.artistList{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    overflow:hidden;
}}

/* ===== LINHA ARTISTA ===== */
.artistRow{{
    display:grid;
    grid-template-columns: 60px 1fr 120px;
    align-items:center;
    padding:12px 16px;
    border-bottom:1px solid #f1f5f9;
    cursor:pointer;
    transition:background .15s ease;
}}

.artistRow:hover{{
    background:#f9fafb;
}}

/* ===== INDEX ===== */
.artistIndex{{
    color:#9ca3af;
    font-weight:600;
}}

/* ===== NOME ===== */
.artistNameRow{{
    font-weight:500;
    color:#111827;
}}

/* ===== TOTAL MUSICAS ===== */
.artistCount{{
    text-align:right;
    color:#6b7280;
    font-size:13px;
}}
/* ===== GRID HOME ===== */
.artistGrid{{
    display:grid;
    grid-template-columns: repeat(3, 1fr);
    gap:12px;
}}

/* ===== CARD ARTISTA ===== */
.artistCardHome{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:12px;
    padding:14px 16px;
    cursor:pointer;
    transition:all .15s ease;
    font-weight:500;
    color:#111827;
}}

.artistCardHome:hover{{
    background:#f3f4f6;
    border-color:#d1d5db;
}}

/* ===== PAGINAÇÃO ===== */
.pagination{{
    display:flex;
    justify-content:center;
    align-items:center;
    gap:16px;
    margin-top:24px;
}}

.pageBtn{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    padding:6px 12px;
    border-radius:8px;
    text-decoration:none;
    color:#111827;
    font-weight:600;
}}

.pageBtn:hover{{
    background:#f3f4f6;
}}

.pageInfo{{
    color:#6b7280;
    font-size:14px;
}}
/* ===== BACK BAR ===== */
.backBar{{
    max-width:1200px;
}}
#loadingOverlay {{
    position: fixed;
    top:0; left:0; right:0; bottom:0;
    width: 100vw;         /* cobre toda largura */
    height: 100vh;        /* cobre toda altura da tela */
    display: none;        /* escondido inicialmente */
    justify-content: center;
    align-items: center;
    z-index: 9999;
    backdrop-filter: blur(2px);             /* fundo desfocado */
    transition: opacity 0.4s ease;
}}

#loadingOverlay.show {{
    display: flex;
    
}}

/* ===== BOTÃO VOLTAR ===== */
</style>
</head>

<body class="light">
<div id="loadingOverlay">
    <div class="spinner"></div>
</div>

<style>

.spinner {{
    width: 50px;
    height: 50px;
    border: 5px solid #f3f3f3;
    border-top: 5px solid #ff7a00; /* cor do seu accent */
    border-radius: 50%;
    animation: spin 1s linear infinite;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg);}}
    100% {{ transform: rotate(360deg);}}
}}
.modal {{
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background-color: rgba(0,0,0,0.6); /* fundo desfocado/escuro */
}}

/* Conteúdo do modal */
.modal-content {{
    background-color: #aaa; /* fundo escuro tipo Netflix */
    color: #fff;
    margin: 10% auto; /* centraliza vertical e horizontal */
    padding: 20px;
    border-radius: 10px;
    width: 320px;
    text-align: center;
}}

/* Fechar modal */
.close {{
    color: #aaa;
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
}}

.close:hover {{
    color: #fff;
}}

/* Botões de login */
.login-option {{
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    font-size: 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.login-option:nth-child(2) {{ background-color: #4285F4; color: #fff; }} /* Google */
.login-option:nth-child(3) {{ background-color: #1877F2; color: #fff; }} /* Facebook */
.login-option:nth-child(4) {{ background-color: #000; color: #fff; }} /* Apple */

.loginButton {{
    margin-left: 20px;
    padding: 6px 12px;
    cursor: pointer;
    border-radius: 6px;
    border: none;
    background-color: #ff6600;
    color: #fff;
    font-weight: bold;
}}




/* ===== LAYOUT GERAL ===== */
.album-layout {{
    display: grid;
    grid-template-columns: 320px 1000px;
    gap: 28px;
    margin-top: 20px;
}}

/* ===== CARD DO ÁLBUM ===== */
.album-card {{
    background: #ddd;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 8px 25px rgba(0,0,0,.35);
    text-align: center;
}}

.album-card img {{
    width: 100%;
    border-radius: 10px;
    margin-bottom: 12px;
}}

/* ===== LISTA DE FAIXAS ===== */
.tracks-card {{
    background: #eee;
    border-radius: 14px;
    padding: 18px;
    box-shadow:
        0 10px 30px rgba(0,0,0,.55),
        inset 0 1px 0 rgba(255,255,255,.05);
}}

/* ===== LINHA DA FAIXA ===== */
.track-row {{
    display: grid;
    grid-template-columns: 50px minmax(260px,1fr) 90px 220px 90px;
  
}}
/* ===== LINHA DA FAIXA ===== */
.track-row {{
    display: grid;
        grid-template-columns: 40px 630px 100px 90px;
    gap: 12px;
    align-items: center;
    padding: 10px 12px;
    border-radius: 10px;
    transition: all .18s ease;
    cursor: pointer;
}}

/* hover bonito (agora visível no light) */
.track-row:hover {{
    background: #f9fafb;
    transform: translateX(3px);
    box-shadow: 0 4px 14px rgba(0,0,0,.08);
}}

/* ===== TÍTULO ===== */
.track-title {{
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* ===== DURAÇÃO ===== */
.track-duration {{
    opacity: .7;
    font-size: 13px;
    white-space: nowrap;
}}

/* ===== PLAYER ===== */
.track-player audio {{
    height: 28px;
    width: 200px;
}}

.discografia{{
    background-color: #eee;
    padding: 20px;
}}
//* ===== CIFRA ===== */
.cifra-link A {{
    font-size: 13px;
    font-weight: 600;
    color: #00e676;
    text-decoration: none;
    padding: 4px 8px;
    border-radius: 6px;
    background: rgba(0,230,118,.12);
    transition: .18s;
    position: relative;
    z-index: 5;
}}

.cifra-link:hover {{
    color:darkorange;
}}
.track-title A{{
    color: var(--accent); text-decoration:none;font-weight: 600;
}}

/* ===== TICK VERDE ===== */
.cifra-ok {{
    color: #16a34a;
    font-weight: bold;
    font-size: 16px;
}}

/* ===== RESPONSIVO ===== */
@media (max-width: 900px) {{
    .track-row {{
        grid-template-columns: 40px 1fr;
        row-gap: 6px;
    }}

    .track-player,
    .track-duration {{
        grid-column: span 2;
    }}
}}
</style>
<header class="topBar">
    <div class="logo"><a href="/">🎸 CifrasFlix</a></div>
    <!-- Botão Entrar -->
    <!-- Modal de Login -->
    <div id="loginModal" class="modal">
    <div class="modal-content">
        <span class="close">&times;</span>
        <h2>Entrar</h2>
        
        <button class="login-option">👤 Entrar com e-mail e senha</button>
        <button class="login-option">G Entrar com o Google</button>
        <button class="login-option">f Entrar com o Facebook</button>
        <button class="login-option"> Entrar com a Apple</button>
        
        <p><a class="backBtn" href="#">Esqueci minha senha</a></p>
        <p>Não tem uma conta? </P><p><a class="backBtn" href="#">Cadastre-se</a></p>
    </div>
    </div>
 
    <nav class="menu">
        <a href="/">Home</a>
        <a href="/favoritos">Favoritos</a>
        <a href="/stats">Stats</a>
         <a href="/albuns">Albuns</a>
        <a href="/importar">Importar</a>
        <a href="/atualizarfoto">Atualizar Foto</a>
        <a href="/pegarfotos">pegarfotos</a>
        
        <a href="/admin">adm</a>
        <a href="mb_album">mbalbum</a>
    </nav>
   <div class="busca-container"  style="position: relative; display: inline-block; margin-left:auto; float: right;">        
    <input type="text" id="busca" placeholder="Buscar..." onkeyup="buscar()">
    <div id="resultado" class="list-container" style="display: none;"></div>
</div>
    

   <button onclick="toggleDark()" class="darkToggle">
    🌙
    </button>    <button id="loginBtn" class="loginButton">Entrar</button>

</header>

<main>


<style>
.list-container {{
    border: 1px solid #ccc;
    border-radius: 6px;
    max-height: 250px;
    overflow-y: auto;
    background: #fff;
    padding: 4px;
    font-family: sans-serif;
}}

.list-item {{
    padding: 6px 8px;
    cursor: pointer;
    border-bottom: 1px solid #eee;
}}

.list-item:last-child {{
    border-bottom: none;
}}

.list-item:hover {{
    background-color: #f0f0f0;
}}

.mais-btn {{
    background:#fff; 
    border:1px solid #e5e7eb; 
    padding:4px 8px; 
    border-radius:6px; 
    font-size:12px;
    cursor:pointer;
    margin-top: 4px;
}}
.mais-btn:hover {{
    background:#f9f9f9;
}}
.busca-container {{
    position: relative;   /* importante para que o absolute do resultado seja relativo a esse container */
    display: inline-block; /* mantém o input no tamanho do conteúdo */
    float: right;          /* mantém o container à direita da tela */
}}
#resultado {{
    position: absolute;  /* posicionamento em relação ao .busca-container */
    top: 100%;           /* logo abaixo do input */
    right: 0;            /* alinhado à direita do input */
    width: 260px;        /* mesma largura do input */
    border: 1px solid #ccc;
    border-radius: 6px;
    max-height: 250px;
    overflow-y: auto;
    background: #fff;
    z-index: 1000;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-top: 4px;
}}
body.dark-mode {{
    background-color: #121212;
    color: #eee;
}}

body.dark-mode .songControls {{
    background-color: #1e1e1e;
}}

body.dark-mode .songContent, {{
    background-color: #444;
}}

body.dark-mode .controlBtn:hover ,
body.dark-mode  #busca {{

 background-color: #111;
}}
body.dark-mode button,
body.dark-mode select,
body.dark-mode .artistCard,
body.dark-mode .versionSelect:hover

 {{
    background-color: #333;
    color: #eee;
}}
body.dark-mode .menu A,
body.dark-mode .controlTitle
{{
 color:white;

}}

body.dark-mode .controlBtn {{
border: 0px;

}}
body.dark-mode .cifraBox,
body.dark-mode .controlCard,
body.dark-mode .musicRow,
body.dark-mode .artistCardHome,
body.dark-mode .topBar,body.dark-mode .musicKey,
body.dark-mode .videoWrapper,
body.dark-mode .speedBox {{
    background-color: #444444; /* fundo escuro */
    color: #eee;               /* texto claro */
    border: 1px solid #666;
}}



</style>

<script>
let currentPage = 1;
function showLoading() {{
    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.add("show");
    document.body.style.overflow = "hidden"; // bloqueia rolagem
        document.documentElement.style.overflow = "hidden";    document.documentElement.style.overflow = "";


}}

function hideLoading() {{
    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.remove("show");
    document.body.style.overflow = ""; // libera rolagem
}}


// efeito estilo Netflix: zoom-out leve
// 🔥 função de efeito
function navegarComEfeito(url) {{
    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.add("show");
    document.body.style.transition = "transform 0.3s ease, opacity 0.3s ease";
    document.body.style.transform = "scale(1)";
    document.body.style.opacity = "0.5";

    setTimeout(() => {{
        window.location.href = url;
    }}, 300);
}}

// 🔥 delegação de eventos para músicas, paginação e artistas
// 🔥 delegação de eventos geral para navegação com efeito
document.addEventListener("click", function(e) {{

    // Função auxiliar que verifica se o elemento tem onclick com location.href
    function handleClick(el) {{
        if(!el) return false;
        const hrefMatch = el.getAttribute("onclick")?.match(/location\.href='(.+)'/);
        if(hrefMatch) {{
            e.preventDefault();
            navegarComEfeito(hrefMatch[1]);
            return true;
        }}
        return false;
    }}

    // Captura músicas
    if(e.target.closest(".musicRow")) {{
        handleClick(e.target.closest(".musicRow"));
        return;
    }}

    // Captura paginação
    if(e.target.classList.contains("pageBtn") || e.target.closest(".pageBtn")) {{
        const btn = e.target.closest(".pageBtn");
        e.preventDefault();
        navegarComEfeito(btn.href);
        return;
    }}

    // Captura itens da lista de busca
    if(e.target.closest(".list-item")) {{
        handleClick(e.target.closest(".list-item"));
        return;
    }}

    // Captura artistas na home
    if(e.target.closest(".artistCardHome")) {{
        handleClick(e.target.closest(".artistCardHome"));
        return;
    }}

    // Captura links de acordes
    if(e.target.classList.contains("chord") || e.target.closest("a.chord")) {{
        const chordLink = e.target.closest("a.chord");
        e.preventDefault();
        navegarComEfeito(chordLink.href);
        return;
    }}

}});

const modal = document.getElementById("loginModal");
const btn = document.getElementById("loginBtn");
const span = document.getElementsByClassName("close")[0];

btn.onclick = function() {{
    modal.style.display = "block";
}}

span.onclick = function() {{
    modal.style.display = "none";
}}

// Fecha modal clicando fora
window.onclick = function(event) {{
    if (event.target == modal) {{
        modal.style.display = "none";
    }}
}}

function buscar() {{
    let q = document.getElementById("busca").value;
    if(!q) return document.getElementById("resultado").innerHTML = "";
    let div = document.getElementById("resultado");

    if(!q) {{
        div.style.display = "none";  // esconde a caixa se campo vazio
        div.innerHTML = "";
        return;
    }}
    div.style.display = "block";     // mostra a caixa
    div.innerHTML = "";               // limpa resultados

    fetch(`/buscar?q=${{encodeURIComponent(q)}}&page=${{currentPage}}`)
    .then(r => r.json())
    .then(data => {{
        let div = document.getElementById("resultado");
        div.innerHTML = "";
        data.results.forEach(item => {{
            div.innerHTML += `
                <div class="list-item"
                     onclick="location.href='/artista/${{item.artista}}/${{item.uid}}'">
                    <strong>${{item.titulo}}</strong><br>
                    <span style="color:#6b7280">${{item.artista_nome}}</span>
                </div>
            `;
        }});

        if(data.has_next){{
            div.innerHTML += `<div style="text-align:center;">
                <button onclick="proximaPagina('${{q}}')" class="mais-btn">Mais...</button>
            </div>`;
        }}
    }});
}}
document.addEventListener('click', function(event) {{
    let container = document.querySelector('.busca-container'); // ou div pai do input
    let resultado = document.getElementById('resultado');
    if (!container.contains(event.target)) {{
        resultado.style.display = 'none'; // esconde se clicou fora
    }}
}});
function proximaPagina(q){{
    currentPage += 1;
    fetch(`/buscar?q=${{encodeURIComponent(q)}}&page=${{currentPage}}`)
    .then(r => r.json())
    .then(data => {{
        let div = document.getElementById("resultado");
        data.results.forEach(item => {{
            div.innerHTML += `
                <div class="list-item"
                     onclick="location.href='/artista/${{item.artista}}/${{item.uid}}'">
                    <strong>${{item.titulo}}</strong><br>
                    <span style="color:#6b7280">${{item.artista_nome}}</span>
                </div>
            `;
        }});
        if(!data.has_next){{
            div.querySelector("button")?.remove();
        }}
    }});
}}
</script>


<link type="text/css" rel="stylesheet" href="http://jtab.tardate.com/css/jtab-helper.css"/>
<script src="https://jtab.tardate.com/javascripts/jquery.js"></script>
<script src="https://jtab.tardate.com/javascripts/raphael.js"></script>
<script src="https://jtab.tardate.com/javascripts/jtab.js"></script>

<script>
// Ao carregar a página, aplica o tema salvo
document.addEventListener("DOMContentLoaded", () => {{
    const theme = localStorage.getItem("theme");
    if (theme === "dark") {{
        document.body.classList.add("dark-mode");
    }}
}});

// Função para alternar tema
function toggleDark() {{
    document.body.classList.toggle("dark-mode");
    
    // Salva a escolha no localStorage
    if (document.body.classList.contains("dark-mode")) {{
        localStorage.setItem("theme", "dark");
    }} else {{
        localStorage.setItem("theme", "light");
    }}
}}
</script>
"""
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
    page_voltar = request.args.get("page", 1)
    # 📄 página atual
    page = int(request.args.get("page", 1))
    per_page = 50
    offset = (page - 1) * per_page

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # total de artistas
    c.execute("SELECT COUNT(*) FROM artistas")
    total = c.fetchone()[0]
    total_pages = math.ceil(total / per_page)

    # artistas paginados
    c.execute("""
        SELECT nome, slug
        FROM artistas
        ORDER BY nome
        LIMIT ? OFFSET ?
    """, (per_page, offset))

    artistas = c.fetchall()
    conn.close()

    html = header("Artistas")

    html += """
   
    <div class="homeContainer">
        <div class="artistGrid">
    """

    # 🎯 lista em grid
    for nome, slug in artistas:
        html += f"""
        <div class="artistCardHome"
             onclick="location.href='/artista/{slug}?page={page}'">
            {nome}
        </div>
        """

    html += "</div>"

    # 📄 paginação
    if total_pages > 1:
        html += '<div class="pagination">'

        if page > 1:
            html += f'<a href="/?page={page-1}" class="pageBtn">‹</a>'

        html += f'<span class="pageInfo">Página {page} de {total_pages}</span>'

        if page < total_pages:
            html += f'<a href="/?page={page+1}" class="pageBtn">›</a>'

        html += "</div>"

    html += "</div></main>"

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
    LIMITE_INICIAL = 15

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # ==========================================
    # 🔥 ARTISTA
    # ==========================================
    c.execute("SELECT id,nome FROM artistas WHERE slug=?", (slug,))
    artista = c.fetchone()
    if not artista:
        return "Artista não encontrado"

    artista_id, nome = artista
    fotoartista = pegar_foto_artista(artista)

    # total músicas
    c.execute("SELECT COUNT(*) FROM musicas WHERE artista_id=?", (artista_id,))
    total_musicas = c.fetchone()[0]

    order_sql = "views DESC" if ordem == "views" else "titulo COLLATE NOCASE ASC"

    c.execute(f"""
        SELECT titulo, uid, views
        FROM musicas
        WHERE artista_id=?
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """, (artista_id, por_pagina, offset))

    musicas_raw = c.fetchall()
    conn.close()

    # ==========================================
    # 🔥 AGRUPAR VERSÕES
    # ==========================================
    agrupadas = {}

    for titulo, uid, views in musicas_raw:
        base = titulo_base(titulo)

        if base not in agrupadas:
            agrupadas[base] = {
                "titulo": re.sub(r'\s*\(.*?\)', '', titulo).strip(),
                "uid": uid,
                "views": views,
                "count": 0
            }
        else:
            agrupadas[base]["count"] += 1

    musicas = list(agrupadas.values())

    # limitar visualmente
    musicas_exibir = musicas if mostrar_todas else musicas[:LIMITE_INICIAL]

    # ==========================================
    # 🔥 FOTO
    # ==========================================
    import os

    nome_safe = nome.replace(" ", "+")
    nome_pasta = nome.lower().replace(" ", "_")

    mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

    if os.path.exists(mini_path):
        foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
    else:
        foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

    # ==========================================
    # 🔥 HTML HEADER
    # ==========================================
    html = header(nome) + f"""
    <div class="backBar">
        <button class="backBtn" onclick="location.href='/?page={page_voltar}'">
            ← Voltar para artistas
        </button>
    </div>
    <br>

    <div class="ordenarBar">
        <span class="ordLabel">Ordenar:</span>

        <a href="?o=views&p=1" class="ordBtn {'active' if ordem=='views' else ''}">
            🔥 Views
        </a>

        <a href="?o=alpha&p=1" class="ordBtn {'active' if ordem=='alpha' else ''}">
            🔤 A-Z
        </a>
    </div>

    <div class="artistLayout">
        <div class="artistCard">
            <img src="{foto_url}" class="artistPhoto">
            {fotoartista}
            <div class="artistName">{nome}</div>
        </div>

        <div class="musicGrid">
    """

    # ==========================================
    # 🔥 LISTA DE MÚSICAS
    # ==========================================
    for i, m in enumerate(musicas_exibir, start=1 + offset):
        badge = f'<span class="versaoBadge">+{m["count"]}</span>' if m["count"] > 0 else ""

        # pegar tom
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT conteudo FROM musicas WHERE uid=?", (m["uid"],))
        row = c.fetchone()
        conn.close()

        tom = "—"
        if row:
            tom_extraido = extrair_tom_da_cifra(row[0])
            if tom_extraido:
                tom = tom_extraido

        html += f"""
        <div class="musicRow"
            onclick="location.href='/artista/{slug}/{m["uid"]}'">
            <div class="musicIndex">{i:02d}</div>
            <div class="musicTitle">
                {m["titulo"]} {badge}
            </div>
            <div class="musicViews">👁 {m["views"]}</div>
            <div class="musicKey">{tom}</div>
        </div>
        """

    # ==========================================
    # 🔥 BOTÃO MOSTRAR TODAS
    # ==========================================
    if not mostrar_todas and len(musicas) > LIMITE_INICIAL:
        html += f"""
        <div style="margin-top:14px;text-align:center;">
            <a href="?todas=1&o={ordem}&p={pagina}" class="pageBtn">
                Mostrar todas as cifras
            </a>
        </div>
        """

    # ==========================================
    # 🔥 PAGINAÇÃO
    # ==========================================
    total_paginas = (total_musicas // por_pagina) + (1 if total_musicas % por_pagina else 0)

    html += '<div class="paginacao">'

    if pagina > 1:
        html += f'<a href="?p={pagina-1}&o={ordem}" class="pageBtn">← Anterior</a>'

    html += f'<span class="pageInfo">Página {pagina} de {total_paginas}</span>'

    if pagina < total_paginas:
        html += f'<a href="?p={pagina+1}&o={ordem}" class="pageBtn">Próxima →</a>'

    html += '</div></div>'

    # ==========================================
    # 🔥 DISCOGRAFIA
    # ==========================================
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT id, nome, ano
    FROM albuns
    WHERE artista_id=?
    ORDER BY ano
    """, (artista_id,))

    albuns = c.fetchall()
    conn.close()

    if albuns:
        html += """<p></p><div class='discografia'>
        <h3 style="margin:30px 0 16px;">Discografia</h3>
        <div class="albumGrid">
        """

        for aid, nome_album, ano_album in albuns:
            ano_fmt = str(ano_album)[:4] if ano_album else ""

            html += f"""
            <a href="/album/{aid}" class="albumCard">
                <img src="/capa_album/{aid}" class="albumCover">
                <div class="albumTitle">{nome_album}</div>
                <div class="albumYear">{ano_fmt}</div>
            </a>
            """

        html += "</div>"

    html += "</div></div></div></main>"
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
    max-width:1600px;
    margin:20px auto;
    padding:0 20px;

    display:grid;

    /* 🎯 centro manda no layout */
    grid-template-columns: 240px minmax(800px, 1fr) 380px;

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
            max-width:360px;
        }}
        .videoWrapper{{
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:14px;
            padding:10px;
        }}

        .videoWrapper iframe{{
            width:100%;
            height:240px;
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
                <div class="controlCard">
                    
                    <div class="controlTitle">🎵 Tom</div>

                    <div class="toneButtons">
                        <button class="controlBtn" onclick="transpor(-1)">−</button>
                        <button class="controlBtn" onclick="transpor(1)">+</button>
                        </div>
                    
                    <button class="controlBtn" style="margin-top:10px;width:100%;"
                        onclick="location.href='/favoritar/{musica_id}'">
                        ❤️ Favoritar
                    </button>
                </div>

                <div class="controlCard">
                    <div class="controlTitle">🎼 Rolagem</div>

                    <button class="controlBtn" onclick="toggleScroll()" id="scrollBtn">
                        ▶ Auto Rolagem
                    </button>

                    <div class="speedBox">
                        Vel.:
                        <button class="controlBtn" onclick="changeSpeed(-0.2)">-</button>
                        <span id="speedLabel">1.0x</span>
                        <button class="controlBtn" onclick="changeSpeed(0.2)">+</button>
                    </div>
                </div>

            </aside>

            <!-- 🎸 CIFRA CENTRAL -->
            <main class="songCenter">
                <h2 class="songTitle">{titulo} </h2>
                <p><a class="chord" href="/artista/{artista_slug}">{artista_nome}</a></p>
                <div class="controlCard musicInfoRow">

                    <div style="width:30%;">
                            <div class="controlTitle">Capotraste</div>
                            <div class="speedBox">{capotraste}</div>
                        </div>
                        <div  style="width:30%;">
                            <div class="controlTitle">Afinação</div>
                            <div class="speedBox">{afinacao}</div>
                        </div>
                        <div  style="width:30%;">
                            <div class="controlTitle">Tom</div>
                            <div class="speedBox">{tom_musica}</div>
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
        let scrollInterval = null;
        let scrollSpeed = 1.0;
        let scrolling = false;

        function toggleScroll(){{
            const btn = document.getElementById("scrollBtn");

            if(scrolling){{
                clearInterval(scrollInterval);
                scrolling = false;
                btn.innerText = "▶ Auto Rolagem";
                return;
            }}

            scrolling = true;
            btn.innerText = "⏸ Pausar";

            scrollInterval = setInterval(()=>{{
                window.scrollBy(0, scrollSpeed);
            }}, 40);
        }}

        function changeSpeed(delta){{
            scrollSpeed = Math.max(0.2, scrollSpeed + delta);
            document.getElementById("speedLabel").innerText =
                scrollSpeed.toFixed(1) + "x";
        }}

        // =============================
        // TRANSPOSIÇÃO VIA URL
        // =============================
        function transpor(v){{
            const url = new URL(window.location.href);
            const t = parseInt(url.searchParams.get("t") || "0");
            url.searchParams.set("t", t + v);
            window.location.href = url.toString();
        }}

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

html = header("Baixar")
html += """
   <h1>Baixar Wallpapers de Bandas</h1>
    
    <form action="/pegarfotos" method="POST">
        <label for="banda">Nome da Banda:</label>
        <input type="text" id="banda" name="banda" required>
        <br><br>
        <label for="offset">Offset (número da primeira imagem):</label>
        <input type="number" id="offset" name="offset" value="0" min="0">
        <br><br>
        <button type="submit">Baixar Wallpapers</button>
    </form>

      {% if arquivos is not none %}
        <h2>Resultado para "{{ banda }}"</h2>
        {% if erro %}
            <p>{{ erro }}</p>
        {% else %}
            <ul>
                {% for arquivo in arquivos %}
                    <li>{{ arquivo }}</li>
                {% endfor %}
            </ul>
            <h3>Preview:</h3>
            {% for arquivo in arquivos %}
                <img src="{{ arquivo }}" alt="Wallpaper" style="max-width:300px; margin:5px;">
            {% endfor %}
        {% endif %}
    {% endif %}
"""

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

    return render_template_string(html, arquivos=arquivos, erro=erro, banda=banda)




@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == "ttx15":
            session["admin"] = True
            return redirect("/admin/painel")
        else:
            return "Senha incorreta"
    return """
    <h2>Login Admin</h2>
    <form method="post">
        <input type="password" name="senha" placeholder="Senha"/>
        <button type="submit">Entrar</button>
    </form>
    """


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

@app.route("/albuns")
def listar_albuns():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT ar.id, ar.nome, ar.slug, COUNT(al.id) as total
        FROM artistas ar
        LEFT JOIN albuns al ON al.artista_id = ar.id
        GROUP BY ar.id
        HAVING total > 0
        ORDER BY ar.nome
    """)
    artistas = c.fetchall()
    conn.close()

    import os

    html = header(titulo="Álbuns por Artista") + """
    <h3 style="margin-bottom:20px;">Artistas com Álbuns</h3>
    <div class="albumGrid">
    """

    for aid, nome, slug, total in artistas:
        nome_safe = nome.replace(" ", "+")
        nome_pasta = nome.lower().replace(" ", "_")

        mini_path = os.path.join("static", "fotos", "artista", nome_pasta, "mini.jpg")

        if os.path.exists(mini_path):
            foto_url = f"/static/fotos/artista/{nome_pasta}/mini.jpg"
        else:
            foto_url = f"https://ui-avatars.com/api/?name={nome_safe}&background=ddd&color=333&size=256"

        html += f"""
        <a href="/artista/{slug}/albuns" class="albumCard">
            <img src="{foto_url}" class="albumCover">
            <div class="albumTitle">{nome}</div>
            <div class="albumYear">{total} álbuns</div>
        </a>
        """

    html += "</div></main>"
    return html

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
        SELECT id, nome, ano
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
    for aid, nome_album, ano in albuns:
        ano=pegar_ano(ano)
        html += f"""
        <a href="/album/{aid}" class="albumCard">
             <img src="/capa_album/{aid}" class="albumCover">
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
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 🎵 dados do álbum
    c.execute("""
        SELECT al.nome, al.ano, al.capa, al.gravadora,
               ar.nome AS artista_nome, ar.slug AS artista_slug
        FROM albuns al
        JOIN artistas ar ON al.artista_id = ar.id
        WHERE al.id=?
    """, (album_id,))
    album = c.fetchone()

    if not album:
        conn.close()
        return "Álbum não encontrado"

    # 🔥 TRACKLIST REAL + preview + vínculo automático
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
            WHERE REPLACE(REPLACE(LOWER(m.titulo), '’', ''), '''', '') =
                REPLACE(REPLACE(LOWER(c.titulo), '’', ''), '''', '')
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
            WHERE REPLACE(REPLACE(LOWER(m.titulo), '’', ''), '''', '') =
                REPLACE(REPLACE(LOWER(c.titulo), '’', ''), '''', '')
            AND a.slug = (
                SELECT ar.slug
                FROM albuns al2
                JOIN artistas ar ON ar.id = al2.artista_id
                WHERE al2.id = c.album_id
            )
            LIMIT 1
        ) AS artista_slug_musica

        FROM cancao c
        WHERE c.album_id = ?
        ORDER BY c.id
        """, (album_id,))
    faixas = c.fetchall()

    conn.close()

    # 🧱 HTML
    html = header(titulo="Albuns")

    html += f"""
    <div class="backBar">
        <button class="backBtn" onclick="location.href='/artista/{album['artista_slug']}/albuns'">
            ← Voltar para artista
        </button>
    </div>
    <script>
    
    
    function renderFaixas(faixas) {{
        const lista = document.getElementById("lista-faixas")
        lista.innerHTML = ""

        faixas.forEach(f => {{

            const temCifra = f.cifra_url && f.cifra_url.trim() !== ""

            const row = document.createElement("div")
            row.className = "track-row"

            row.innerHTML = `
                <div>${{f.numero}}</div>

                <div class="track-title">
                    ${{f.titulo}}
                </div>

                <div class="track-duration">
                    ${{f.duracao || ""}}
                </div>

                <div class="track-player">
                    ${{f.preview_url ? `
                        <audio controls preload="none">
                            <source src="${{f.preview_url}}" type="audio/mpeg">
                        </audio>
                    ` : ``}}
                </div>

                <div>
                    ${{temCifra ? `
                        <span class="cifra-ok">✓</span>
                        <a href="${{f.cifra_url}}" target="_blank" class="cifra-link">
                            Cifra
                        </a>
                    ` : ``}}
                </div>
            `

            // hover
            row.addEventListener("mouseenter", () => {{
                row.style.boxShadow = "0 4px 18px rgba(0,0,0,.35)"
            }})

            row.addEventListener("mouseleave", () => {{
                row.style.boxShadow = "none"
            }})

            lista.appendChild(row)
        }})
    }}
    </script>

    <script>
        let currentAudio = null
        let currentBtn = null

        function togglePlay(btn) {{

            const url = btn.dataset.preview

            // se já existe áudio neste botão
            if (btn.audio) {{

                if (!btn.audio.paused) {{
                    btn.audio.pause()
                    btn.classList.remove("playing")
                    btn.innerHTML = "▶"
                    return
                }}

                btn.audio.play()
                btn.classList.add("playing")
                btn.innerHTML = "⏸"
                return
            }}

            // 🔥 parar o anterior
            if (currentAudio) {{
                currentAudio.pause()
                if (currentBtn) {{
                    currentBtn.classList.remove("playing")
                    currentBtn.innerHTML = "▶"
                }}
            }}

            // criar novo áudio
            const audio = new Audio(url)
            btn.audio = audio
            currentAudio = audio
            currentBtn = btn

            audio.play()
            btn.classList.add("playing")
            btn.innerHTML = "⏸"

            audio.onended = () => {{
                btn.classList.remove("playing")
                btn.innerHTML = "▶"
            }}
        }}
        </script>
        <script>
async function carregarPreviews() {{
    const botoes = document.querySelectorAll(".play-btn")

    for (const btn of botoes) {{
        const artista = btn.dataset.artista
        const titulo = btn.dataset.titulo

        try {{
            const r = await fetch(
                `/preview?artista=${{encodeURIComponent(artista)}}&titulo=${{encodeURIComponent(titulo)}}`
            )
            const data = await r.json()

           
                btn.dataset.preview = data.preview
            
        }} catch (e) {{
            console.error("Erro preview:", e)
        }}
    }}
}}

document.addEventListener("DOMContentLoaded", carregarPreviews)
</script>

    """
    ano=formatar_data(album['ano'])
    html += f"""


    <div class="album-layout">

        <!-- CARD DO ÁLBUM -->
        <div class="album-card">
        <img src="/capa_album/{album_id}">
            <h1>{album['nome']}</h1>
            <h3>{album['artista_nome']} </h3>
            <p><i> {ano}</i></p>
            <p><b>Gravadora:</b> {album['gravadora'] or '-'}</p>
            
        </div>

        <!-- LISTA DE FAIXAS -->
        <div class="tracks-card">
            <h2>Faixas</h2>
    """

    if not faixas:
        html += "<p>⚠️ Nenhuma faixa encontrada</p>"

    for f in faixas:
        info_extra = ""

        if f["duracao"]:
            info_extra += f'<span class="track-duration">{f["duracao"]}</span>'

        if f["compositor"]:
            info_extra += f' — <small>{f["compositor"]}</small>'

        # 🎧 preview
        player_html = ""
       
        player_html = f"""
        <button class="play-btn"
                data-artista="{album['artista_nome']}"
                data-titulo="{f['titulo']}"
                data-preview=""
                onclick="togglePlay(this)">
        ▶</button>
        """

        # 🔹 slug da música para letra
        musica_slug = normalizar_slug(f["titulo"])
        musica_slug = f["cancao_slug"]
        letra_link = f"/letra/{album['artista_slug']}/{musica_slug}"

        tem_cifra = bool(f["uid"] and f["artista_slug_musica"])

        # ===============================
        # 🎯 COM CIFRA
        # ===============================
        if tem_cifra:
            link_cifra = f"/artista/{f['artista_slug_musica']}/{f['uid']}"

            cifra_nome = f'<a class="cifra-link" href="{link_cifra}">{f["titulo"]}</a>'

            cifra_html = (
                f'<a class="cifra-link" href="{link_cifra}">Cifra</a>'
                f'<a class="letra-link" href="{letra_link}">Letra</a>'
            )

            tick_html = '<span class="cifra-ok">✔</span>'

        # ===============================
        # 🎯 SEM CIFRA
        # ===============================
        else:
            cifra_nome = f'<a class="letra-link only-lyric" href="{letra_link}">{f["titulo"]}</a>'
            cifra_html = f'<a class="letra-link only-lyric" href="{letra_link}">Letra</a>'
            tick_html = '<span style="opacity:.25">•</span>'

        html += f"""
        <div class="track-row">
            <div>{tick_html}</div>
            <div class="track-title">
                {cifra_nome} {info_extra}
            </div>
            <div class="track-player">{player_html}</div>
            <div>{cifra_html}</div>
        </div>
        """

    html += """
        </div>
    </div>
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

def slug_letras(texto: str) -> str:
    if not texto:
        return ""

    if callable(texto):  # blindagem
        return ""

    texto = str(texto)

    # remove acentos
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")

    texto = texto.lower().strip()

    # troca qualquer coisa não alfanumérica por hífen
    texto = re.sub(r"[^a-z0-9]+", "-", texto)

    # remove hífens duplicados
    texto = re.sub(r"-+", "-", texto).strip("-")

    return texto

# ==========================================
# 🔥 slug inteligente (nível profissional)
# ==========================================
def slug_letras(texto: str) -> str:
    
    texto = texto.lower().strip()

    # remove acentos
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")

    # substituições comuns
    texto = texto.replace("&", "and")
    texto = texto.replace("'", "")
    texto = texto.replace(".", "")
    texto = texto.replace("(", "")
    texto = texto.replace(")", "")

    # troca espaços por hífen
    texto = re.sub(r"\s+", "-", texto)

    # remove lixo
    texto = re.sub(r"[^a-z0-9\-]", "", texto)

    # remove hífen duplicado
    texto = re.sub(r"-+", "-", texto).strip("-")

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

        esperado = normalizar(musica1)
        titulo_normalizado = normalizar(titulo_site)

        palavras_esperadas = [

            p

            for p in esperado.split()

            if len(p) > 2

        ]

        encontradas = 0

        for palavra in palavras_esperadas:

            if palavra in titulo_normalizado:
                encontradas += 1

        porcentagem = 0

        if palavras_esperadas:

            porcentagem = (
                encontradas /
                len(palavras_esperadas)
            ) * 100

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
    max-width:1600px;
    margin:20px auto;
    padding:0 20px;
    display:grid;
    grid-template-columns: 240px minmax(800px, 1fr) 380px;
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
    max-width:360px;
}}

.videoWrapper{{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:10px;
}}

.videoWrapper iframe{{
    width:100%;
    height:240px;
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
</script>
<div class="backWrapper">
    <button class="backBtn" onclick="location.href='/artista/{slug}'">
        ← Voltar para músicas
    </button>
</div>

<div class="songLayout">

    <!-- ESQUERDA -->
    <aside class="songControls">

    
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
    </aside>

    <!-- 🔥 LETRA -->
    <main class="songCenter">
        <h2 class="songTitle">{titulo}</h2>
        <p>
            <a class="chord" href="/artista/{artista_slug}">
                {artista_nome}
            </a>
        </p>

        <div class="lyricBox" id="lyricTraducao">
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
    <aside class="songVideo">
        <div class="videoWrapper">
            {iframe_video}
        </div>
    </aside>

</div>

</main>
"""
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

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, jsonify

app = Flask(__name__)
