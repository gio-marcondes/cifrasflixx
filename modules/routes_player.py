def _normalizar_gp_nome(texto):
    import unicodedata

    if not texto:
        return ""

    ascii_text = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"\s*\(.*?\)", " ", ascii_text)
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _limpar_titulo_gp_exibicao(texto):
    valor = (texto or "").strip()
    if not valor:
        return ""
    valor = re.sub(r"\(([^)]*?)\s+by\s+[^)]*\)", r"(\1)", valor, flags=re.IGNORECASE)
    valor = re.sub(r"\s{2,}", " ", valor).strip()
    return valor


def _titulo_base_sem_versao(texto):
    valor = (texto or "").strip()
    if not valor:
        return ""
    valor = _limpar_titulo_gp_exibicao(valor)
    valor = re.sub(r"\s*\((?:ver\.?\s*)?\d+\)\s*$", "", valor, flags=re.IGNORECASE)
    valor = re.sub(r"\s{2,}", " ", valor).strip()
    return valor


def _listar_versoes_gp(slug, artista_nome, titulo_referencia, current_url):
    titulo_base_norm = _normalizar_gp_nome(_titulo_base_sem_versao(titulo_referencia))
    artista_norm = _normalizar_gp_nome(artista_nome or slug)
    if not slug or not titulo_base_norm:
        return []

    versoes = []
    vistos = set()
    for rec in _gp_index_records():
        rec_artist = rec.get("artist_norm") or ""
        rec_title_raw = rec.get("title_raw") or rec.get("title_norm") or ""

        if rec_artist and artista_norm and rec_artist != artista_norm:
            continue

        if _normalizar_gp_nome(_titulo_base_sem_versao(rec_title_raw)) != titulo_base_norm:
            continue

        rec_slug = normalizar_slug(_limpar_titulo_gp_exibicao(rec_title_raw))
        if not rec_slug:
            continue

        destino = f"/tocador-gp4/{slug}/{rec_slug}"
        if destino in vistos:
            continue
        vistos.add(destino)

        versoes.append(
            {
                "label": _limpar_titulo_gp_exibicao(rec_title_raw),
                "url": destino,
            }
        )

    if current_url and current_url not in vistos:
        versoes.insert(
            0,
            {
                "label": _limpar_titulo_gp_exibicao(titulo_referencia),
                "url": current_url,
            },
        )

    if len(versoes) <= 1:
        return []

    return versoes


def _gp_index_file_path():
    return Path("static") / "guitarpro" / "_gp_index.txt"


def _gp_index_refresh(max_age_seconds=21600):
    import time

    base_dir = Path("static") / "guitarpro"
    idx_path = _gp_index_file_path()
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
            artista_gp, titulo_gp = stem.split(" - ", 1)
        elif "-" in stem:
            artista_gp, titulo_gp = stem.split("-", 1)
        else:
            artista_gp, titulo_gp = "", stem

        artista_norm = _normalizar_gp_nome(artista_gp)
        titulo_norm = _normalizar_gp_nome(titulo_gp)
        if not titulo_norm:
            continue

        linhas.append(
            "\t".join(
                [
                    artista_norm,
                    titulo_norm,
                    arquivo.name,
                    (artista_gp or "").strip().replace("\t", " "),
                    (titulo_gp or "").strip().replace("\t", " "),
                ]
            )
        )

    try:
        idx_path.write_text("\n".join(linhas), encoding="utf-8")
    except Exception:
        pass


def _gp_index_records():
    _gp_index_refresh()
    idx_path = _gp_index_file_path()
    if not idx_path.exists():
        return []

    records = []
    try:
        conteudo = idx_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    for linha in conteudo.splitlines():
        if not linha.strip():
            continue
        partes = linha.split("\t")
        if len(partes) < 3:
            continue

        artista_norm = (partes[0] or "").strip()
        titulo_norm = (partes[1] or "").strip()
        file_name = (partes[2] or "").strip()
        artista_raw = (partes[3] if len(partes) > 3 else "").strip()
        titulo_raw = (partes[4] if len(partes) > 4 else "").strip()

        if not titulo_norm or not file_name:
            continue

        records.append(
            {
                "artist_norm": artista_norm,
                "title_norm": titulo_norm,
                "file_name": file_name,
                "artist_raw": artista_raw,
                "title_raw": titulo_raw,
            }
        )

    return records


def buscar_tab_guitarpro(artista_nome, musica_titulo):
    artista_alvo = _normalizar_gp_nome(artista_nome)
    musica_alvo = _normalizar_gp_nome(musica_titulo)

    if not artista_alvo or not musica_alvo:
        return None

    melhor = None
    melhor_score = -1
    melhor_tamanho = -1

    for rec in _gp_index_records():
        artista_gp_norm = rec["artist_norm"]
        titulo_gp_norm = rec["title_norm"]

        if not titulo_gp_norm:
            continue

        score = 0

        if artista_gp_norm:
            if artista_gp_norm == artista_alvo:
                score += 100
            elif artista_gp_norm in artista_alvo or artista_alvo in artista_gp_norm:
                score += 50
            else:
                continue

        if titulo_gp_norm == musica_alvo:
            score += 100
        elif titulo_gp_norm in musica_alvo or musica_alvo in titulo_gp_norm:
            score += 70
        else:
            continue

        ext = Path(rec["file_name"]).suffix.lower()
        if ext == ".gp5":
            score += 3
        elif ext == ".gp4":
            score += 2
        elif ext == ".gpx":
            score += 1

        tamanho = 0
        try:
            tamanho = (Path("static") / "guitarpro" / rec["file_name"]).stat().st_size
        except Exception:
            tamanho = 0

        if score > melhor_score or (score == melhor_score and tamanho > melhor_tamanho):
            melhor_score = score
            melhor_tamanho = tamanho
            melhor = {
                "file_name": rec["file_name"],
                "artist": rec["artist_raw"] or artista_nome,
                "title": _limpar_titulo_gp_exibicao(rec["title_raw"] or musica_titulo),
            }

    return melhor


def buscar_tab_guitarpro_por_slug(artista_nome, musica_slug):
    artista_alvo = _normalizar_gp_nome(artista_nome)
    slug_alvo = (musica_slug or "").strip().lower()
    if not artista_alvo or not slug_alvo:
        return None

    for rec in _gp_index_records():
        artista_gp_norm = rec["artist_norm"]
        if artista_gp_norm and artista_gp_norm != artista_alvo:
            continue

        titulo_exibicao = _limpar_titulo_gp_exibicao(rec.get("title_raw") or "")
        if not titulo_exibicao:
            continue

        if normalizar_slug(titulo_exibicao) != slug_alvo:
            continue

        return {
            "file_name": rec["file_name"],
            "artist": rec.get("artist_raw") or artista_nome,
            "title": titulo_exibicao,
        }

    return None


@app.route("/tocador-gp4/<slug>/<uid>")
def tocador_gp4(slug, uid):
    resolved = _resolver_track_gp(slug, uid)
    if not resolved:
        return (
            header("Tocador GP4")
            + f"""
            <section class="systemPanel" style="max-width:900px;margin:28px auto;">
                <h2 style="margin-top:0;">Musica nao encontrada</h2>
                <p>Nao foi possivel resolver a musica para abrir o tocador GP4.</p>
                <a class="pageBtn" href="/artista/{slug}">Voltar para artista</a>
            </section>
            </main>
            """
        )

    file_id = resolved["uid"]
    current_version_url = f"/tocador-gp4/{slug}/{uid}"
    versoes = _listar_versoes_gp(slug, resolved.get("artist"), resolved["title"], current_version_url)
    return render_template(
        "player_gp4.html",
        file_id=file_id,
        artist_slug=slug,
        slug=slug,
        file_url=url_for("gp_media", slug=slug, uid=file_id),
        fretboard_url=url_for("gp_api_fretboard", slug=slug, uid=file_id),
        title=resolved["title"],
        artist=resolved["artist"],
        versions=versoes,
        current_version_url=current_version_url,
        filename=resolved["file_name"],
        soundfont_url=url_for("gp_soundfont", filename="FluidR3_GM.sf2"),
    )


def _resolver_track_gp(slug, uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        SELECT m.titulo, a.nome, m.uid
        FROM musicas m
        JOIN artistas a ON a.id = m.artista_id
        WHERE a.slug=? AND (m.uid=? OR m.slug=?)
        LIMIT 1
        """,
        (slug, uid, uid),
    )
    row = c.fetchone()

    c.execute("SELECT nome FROM artistas WHERE slug=? LIMIT 1", (slug,))
    artista_row = c.fetchone()
    artista_nome_slug = artista_row[0] if artista_row else slug.replace("-", " ").title()

    if not row and (uid or "").strip().lower() in {"", "undefined", "null", "none"}:
        c.execute(
            """
            SELECT m.titulo, a.nome, m.uid
            FROM musicas m
            JOIN artistas a ON a.id = m.artista_id
            WHERE a.slug=?
            ORDER BY COALESCE(m.views, 0) DESC, m.id DESC
            LIMIT 300
            """,
            (slug,),
        )
        candidatos = c.fetchall()
    else:
        candidatos = [row] if row else []

    uid_text = (uid or "").strip()

    # Prefer exact slug resolution only when URL explicitly targets a GP variant (-1, -ver-2, ...).
    if uid_text and re.search(r"-(?:ver-\d+|\d+)$", uid_text, re.IGNORECASE):
        gp_tab_exata = buscar_tab_guitarpro_por_slug(artista_nome_slug, uid_text)
        if gp_tab_exata:
            conn.close()
            return {
                "title": _limpar_titulo_gp_exibicao(gp_tab_exata.get("title") or uid_text.replace("-", " ").title()),
                "artist": gp_tab_exata.get("artist") or artista_nome_slug,
                "uid": uid_text,
                "gp_tab": gp_tab_exata,
                "file_name": gp_tab_exata.get("file_name") or f"{artista_nome_slug} - {uid_text}.gp",
            }

    for cand in candidatos:
        if not cand:
            continue
        titulo, artista_nome, uid_resolvido = cand
        gp_tab = buscar_tab_guitarpro(artista_nome, titulo)
        if gp_tab:
            conn.close()
            return {
                "title": _limpar_titulo_gp_exibicao(titulo),
                "artist": artista_nome,
                "uid": uid_resolvido,
                "gp_tab": gp_tab,
                "file_name": gp_tab.get("file_name") or f"{artista_nome} - {titulo}.gp",
            }

    # Fallback: allow direct song-slug URLs even when DB uid/slug does not match.
    # Example: /tocador-gp4/all-time-low/summer-daze-seasons-pt-2
    if uid_text:
        titulo_guess = uid_text.replace("-", " ").strip()
        gp_tab = buscar_tab_guitarpro(artista_nome_slug, titulo_guess)
        if gp_tab:
            conn.close()
            return {
                "title": _limpar_titulo_gp_exibicao(gp_tab.get("title") or titulo_guess.title()),
                "artist": gp_tab.get("artist") or artista_nome_slug,
                "uid": uid_text,
                "gp_tab": gp_tab,
                "file_name": gp_tab.get("file_name") or f"{artista_nome_slug} - {titulo_guess}.gp",
            }

    conn.close()
    return None


@app.route("/gp/media/<slug>/<uid>")
def gp_media(slug, uid):
    from pathlib import Path
    from flask import abort, send_file

    resolved = _resolver_track_gp(slug, uid)
    if not resolved:
        abort(404)

    arquivo = Path("static") / "guitarpro" / resolved["file_name"]
    if not arquivo.exists():
        abort(404)
    return send_file(str(arquivo), as_attachment=False)


@app.route("/gp/soundfonts/<path:filename>")
def gp_soundfont(filename):
    from pathlib import Path
    from flask import abort, send_from_directory

    folder = Path("static") / "soundfonts"
    if not folder.exists():
        abort(404)
    return send_from_directory(str(folder), filename)


@app.route("/gp/api/fretboard/<slug>/<uid>")
def gp_api_fretboard(slug, uid):
    from pathlib import Path
    from flask import abort

    resolved = _resolver_track_gp(slug, uid)
    if not resolved:
        abort(404)

    arquivo = Path("static") / "guitarpro" / resolved["file_name"]
    if not arquivo.exists():
        abort(404)

    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    standard_tuning = {1: 4, 2: 11, 3: 7, 4: 2, 5: 9, 6: 4}

    def note_name(string, fret):
        return note_names[(standard_tuning.get(string, 4) + fret) % 12]

    try:
        import guitarpro
    except ModuleNotFoundError:
        return jsonify(
            {
                "available": False,
                "message": "Instale PyGuitarPro para ativar o braco sincronizado.",
                "tracks": [],
            }
        )

    try:
        song = guitarpro.parse(str(arquivo))
    except Exception as exc:
        return jsonify(
            {
                "available": False,
                "message": f"Nao consegui ler as notas deste arquivo: {exc}",
                "tracks": [],
            }
        )

    tracks = []
    for track_index, track in enumerate(song.tracks):
        notes = []
        cursor = 0
        for measure in track.measures:
            measure_start = cursor
            measure_end = cursor
            for voice in measure.voices:
                voice_cursor = measure_start
                for beat in voice.beats:
                    duration = getattr(beat.duration, "time", 0) or 0
                    for note in beat.notes:
                        string = getattr(note, "string", None)
                        fret = getattr(note, "value", None)
                        if string and fret is not None and fret >= 0:
                            notes.append(
                                {
                                    "time": voice_cursor,
                                    "string": int(string),
                                    "fret": int(fret),
                                    "name": note_name(int(string), int(fret)),
                                }
                            )
                    voice_cursor += duration
                measure_end = max(measure_end, voice_cursor)
            cursor = measure_end
        tracks.append(
            {
                "index": track_index,
                "name": track.name or f"Track {track_index + 1}",
                "notes": notes,
            }
        )

    return jsonify({"available": True, "message": "", "tracks": tracks})
