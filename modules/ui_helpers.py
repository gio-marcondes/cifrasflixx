def fmt_int(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def db_scalar(cursor, sql, params=(), default=0):
    try:
        row = cursor.execute(sql, params).fetchone()
        return row[0] if row and row[0] is not None else default
    except sqlite3.Error:
        return default


def db_rows(cursor, sql, params=()):
    try:
        return cursor.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


_FLIXPLAY_COUNT_CACHE = {"dir_mtime_ns": None, "value": 0}


def contar_arquivos_guitarpro():
    from pathlib import Path

    base_dir = Path("static") / "guitarpro"
    extensoes = {".gp", ".gp3", ".gp4", ".gp5", ".gpx"}
    if not base_dir.exists():
        return 0

    global _FLIXPLAY_COUNT_CACHE
    dir_mtime_ns = base_dir.stat().st_mtime_ns
    if _FLIXPLAY_COUNT_CACHE["dir_mtime_ns"] == dir_mtime_ns:
        return _FLIXPLAY_COUNT_CACHE["value"]

    total = 0
    for arquivo in base_dir.iterdir():
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
            total += 1

    _FLIXPLAY_COUNT_CACHE = {"dir_mtime_ns": dir_mtime_ns, "value": total}
    return total


def home_dashboard_data(cursor):
    total_artistas = db_scalar(cursor, "SELECT COUNT(*) FROM artistas")
    total_musicas = db_scalar(cursor, "SELECT COUNT(*) FROM musicas")
    total_albuns = db_scalar(cursor, "SELECT COUNT(*) FROM albuns")
    total_favoritos = db_scalar(cursor, "SELECT COUNT(*) FROM favoritos")
    total_letras = db_scalar(
        cursor,
        "SELECT COUNT(*) FROM cancao WHERE letra_original IS NOT NULL AND TRIM(letra_original) != ''",
    )
    total_views = db_scalar(cursor, "SELECT COALESCE(SUM(views), 0) FROM musicas")

    top_artistas = db_rows(
        cursor,
        """
        SELECT ar.nome, ar.slug, COUNT(m.id) AS total_musicas, COALESCE(SUM(m.views), 0) AS total_views
        FROM artistas ar
        LEFT JOIN musicas m ON m.artista_id = ar.id
        GROUP BY ar.id
        ORDER BY total_views DESC, total_musicas DESC, ar.nome COLLATE NOCASE ASC
        LIMIT 5
        """,
    )

    ultimas_musicas = db_rows(
        cursor,
        """
        SELECT m.titulo, m.uid, ar.nome, ar.slug
        FROM musicas m
        JOIN artistas ar ON ar.id = m.artista_id
        ORDER BY m.id DESC
        LIMIT 6
        """,
    )

    stats = [
        ("Artistas", fmt_int(total_artistas), "biblioteca"),
        ("Musicas", fmt_int(total_musicas), "cifras importadas"),
        ("Albuns", fmt_int(total_albuns), "discografia"),
        ("Letras", fmt_int(total_letras), "originais salvas"),
        ("Favoritos", fmt_int(total_favoritos), "selecionadas"),
        ("Views", fmt_int(total_views), "leituras"),
    ]

    modules = [
        ("Biblioteca", "Navegue por artistas e cifras.", "/", "Abrir"),
        ("Discografia", "Albuns, faixas, capas e previews.", "/albuns", "Ver albuns"),
        ("Favoritos", "Musicas separadas para voltar rapido.", "/favoritos", "Ver favoritos"),
        ("Importador TXT", "Carrega cifras da pasta cifras_txt.", "/importar", "Importar"),
        ("Separador de audio", "Escolha uma MP3 e abra as faixas em um player dedicado.", "/separar-audio", "Abrir"),
        ("Capas e fotos", "Atualize imagens de artistas.", "/atualizarfoto", "Atualizar"),
        ("MusicBrainz", "Busque albuns e edicoes externas.", "/mb_album", "Abrir modulo"),
    ]

    return {
        "stats": stats,
        "modules": modules,
        "top_artistas": top_artistas,
        "ultimas_musicas": ultimas_musicas,
    }
