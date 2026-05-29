import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import jsonify, render_template, request, url_for
from werkzeug.utils import secure_filename


SEPARADOR_ROOT = Path("static") / "separacoes"
UPLOAD_ROOT = SEPARADOR_ROOT / "uploads"
OUTPUT_ROOT = SEPARADOR_ROOT / "jobs"
SEPARADOR_PYTHON = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python310" / "python.exe"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
CHORD_NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CHORD_MAP_BEMOL = {
    "A#": "Bb",
    "C#": "Db",
    "D#": "Eb",
    "F#": "Gb",
    "G#": "Ab",
}
CHORD_PERFIS = {
    "": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    "m": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    "7": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
}
STEM_LABELS = {
    "vocals": "Vocais",
    "vocal": "Vocais",
    "no_vocals": "Instrumental",
    "instrumental": "Instrumental",
    "drums": "Bateria",
    "drum": "Bateria",
    "bass": "Baixo",
    "other": "Outros",
}
JOBS = {}
JOBS_LOCK = threading.Lock()


def _ensure_separador_dirs():
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _extensao_valida(nome_arquivo):
    return Path(nome_arquivo).suffix.lower() in ALLOWED_EXTENSIONS


def _label_para_faixa(nome_arquivo):
    base = Path(nome_arquivo).stem.lower().strip()
    for chave, label in STEM_LABELS.items():
        if chave in base:
            return label
    return Path(nome_arquivo).stem.replace("_", " ").replace("-", " ").title()


def _ajustar_nome_acorde(acorde):
    for chave, valor in CHORD_MAP_BEMOL.items():
        if acorde.startswith(chave):
            return acorde.replace(chave, valor, 1)
    return acorde


def _separar_tom_qualidade(acorde):
    if acorde == "N":
        return "N", ""

    tom = acorde[:1]
    qualidade = acorde[1:]

    if len(acorde) > 1 and acorde[1] in {"#", "b"}:
        tom = acorde[:2]
        qualidade = acorde[2:]

    return tom, qualidade


def _suavizar_acordes(lista_acordes):
    if not lista_acordes:
        return []

    acordes_suavizados = []
    for indice in range(len(lista_acordes)):
        janela = lista_acordes[max(0, indice - 2) : min(len(lista_acordes), indice + 3)]
        candidatos = [item["acorde"] for item in janela]
        acorde_mais_frequente = max(set(candidatos), key=candidatos.count)
        base = next((item for item in janela if item["acorde"] == acorde_mais_frequente), janela[0])
        acordes_suavizados.append(base)

    return acordes_suavizados


def _detectar_acorde_do_chroma(chroma):
    import numpy as np

    chroma = np.asarray(chroma, dtype=float)
    chroma = chroma / (np.linalg.norm(chroma) + 1e-6)

    melhor_score = -1.0
    melhor_acorde = "N"

    for indice, nota in enumerate(CHORD_NOTAS):
        for sufixo, perfil in CHORD_PERFIS.items():
            perfil_shift = np.roll(np.asarray(perfil, dtype=float), indice)
            perfil_shift = perfil_shift / (np.linalg.norm(perfil_shift) + 1e-6)
            score = float(np.dot(chroma, perfil_shift))

            if score > melhor_score:
                melhor_score = score
                melhor_acorde = _ajustar_nome_acorde(f"{nota}{sufixo}")

    tom, qualidade = _separar_tom_qualidade(melhor_acorde)
    return {
        "acorde": melhor_acorde,
        "tom": tom,
        "qualidade": qualidade,
    }


def _normalizar_bpm(valor, padrao=120.0):
    try:
        bpm = float(valor)
    except Exception:
        return float(padrao)

    if not (bpm > 0):
        return float(padrao)

    # Evita leituras em metade/dobro do BPM real (muito comum em detecao automatica).
    while bpm < 70:
        bpm *= 2
    while bpm > 190:
        bpm /= 2

    return round(bpm, 2)


def _extrair_tom_inicial(segmentos):
    for segmento in segmentos or []:
        tom = (segmento.get("tom") or "").strip()
        if tom and tom.upper() != "N":
            return tom
    return "C"


def _nota_para_semitom(nota):
    mapa = {
        "C": 0,
        "B#": 0,
        "C#": 1,
        "DB": 1,
        "D": 2,
        "D#": 3,
        "EB": 3,
        "E": 4,
        "FB": 4,
        "E#": 5,
        "F": 5,
        "F#": 6,
        "GB": 6,
        "G": 7,
        "G#": 8,
        "AB": 8,
        "A": 9,
        "A#": 10,
        "BB": 10,
        "B": 11,
        "CB": 11,
    }
    return mapa.get((nota or "").upper())


def _semitom_para_nota(semitom):
    notas = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    return notas[int(semitom) % 12]


def _raiz_de_acorde(acorde):
    if not acorde:
        return None

    m = re.match(r"^([A-G](?:#|b)?)", str(acorde).strip())
    if not m:
        return None
    return m.group(1)


def _detectar_tonalidade_por_segmentos(segmentos):
    if not segmentos:
        return None, 0.0

    pesos_por_raiz = {}
    total = 0.0
    for seg in segmentos:
        raiz = _raiz_de_acorde(seg.get("acorde"))
        semitom = _nota_para_semitom(raiz)
        if semitom is None:
            continue

        peso = float(seg.get("duracao") or 0.0)
        if peso <= 0:
            peso = 0.25

        total += peso
        pesos_por_raiz[semitom] = pesos_por_raiz.get(semitom, 0.0) + peso

    if not pesos_por_raiz or total <= 0:
        return None, 0.0

    graus_maior = {0, 2, 4, 5, 7, 9, 11}
    graus_menor = {0, 2, 3, 5, 7, 8, 10}

    melhor_tonica = 0
    melhor_score = -1e9
    segundo_score = -1e9

    for tonica in range(12):
        score_maior = 0.0
        score_menor = 0.0
        for semitom, peso in pesos_por_raiz.items():
            grau = (semitom - tonica) % 12
            score_maior += peso if grau in graus_maior else (-0.30 * peso)
            score_menor += peso if grau in graus_menor else (-0.30 * peso)

        score = max(score_maior, score_menor)
        if score > melhor_score:
            segundo_score = melhor_score
            melhor_score = score
            melhor_tonica = tonica
        elif score > segundo_score:
            segundo_score = score

    confianca = max(0.0, melhor_score - segundo_score)
    return _semitom_para_nota(melhor_tonica), float(confianca)


def _detectar_tonalidade_global(y, sr):
    import librosa
    import numpy as np

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    if chroma is None or chroma.size == 0:
        return "C", 0.0

    perfil = np.mean(chroma, axis=1)
    norma = np.linalg.norm(perfil)
    if norma <= 1e-8:
        return "C", 0.0

    perfil = perfil / norma

    # Perfis de Krumhansl-Schmuckler para tonalidade maior/menor.
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88], dtype=float)
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17], dtype=float)

    major_profile = major_profile / np.linalg.norm(major_profile)
    minor_profile = minor_profile / np.linalg.norm(minor_profile)

    melhor_nota = "C"
    melhor_score = -1e9
    segundo_score = -1e9

    for indice, nota in enumerate(CHORD_NOTAS):
        major_shift = np.roll(major_profile, indice)
        minor_shift = np.roll(minor_profile, indice)

        score_major = float(np.dot(perfil, major_shift))
        score_minor = float(np.dot(perfil, minor_shift))
        score = max(score_major, score_minor)

        if score > melhor_score:
            segundo_score = melhor_score
            melhor_score = score
            melhor_nota = nota
        elif score > segundo_score:
            segundo_score = score

    confianca = max(0.0, melhor_score - segundo_score)
    return _ajustar_nome_acorde(melhor_nota), float(confianca)


def _analisar_acordes_audio(audio_path):
    try:
        import librosa
        import numpy as np
    except Exception:
        return {
            "segmentos": [],
            "bpm_base": 120.0,
            "tom_base": "C",
        }

    y, sr = librosa.load(str(audio_path), mono=True)
    if y.size == 0:
        return {
            "segmentos": [],
            "bpm_base": 120.0,
            "tom_base": "C",
        }

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempos = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    if tempos is not None and len(tempos) > 0:
        bpm_estimado = float(np.median(tempos))
    else:
        bpm_estimado = float(tempo)

    bpm_base = _normalizar_bpm(bpm_estimado, padrao=120.0)
    tom_global, confianca_global = _detectar_tonalidade_global(y, sr)

    if beats is None or len(beats) < 2:
        duracao = max(float(librosa.get_duration(y=y, sr=sr)), 0.1)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        media = np.mean(chroma, axis=1)
        acorde = _detectar_acorde_do_chroma(media)
        segmentos = [
            {
                "inicio": 0.0,
                "fim": round(duracao, 3),
                "duracao": round(duracao, 3),
                **acorde,
            }
        ]
        tom_segmentos, _ = _detectar_tonalidade_por_segmentos(segmentos)
        tom_base = tom_global if confianca_global >= 0.18 else (tom_segmentos or tom_global)

        return {
            "segmentos": segmentos,
            "bpm_base": bpm_base,
            "tom_base": tom_base,
        }

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    duracao_audio = float(librosa.get_duration(y=y, sr=sr))

    segmentos = []
    for indice in range(len(beats) - 1):
        inicio = float(librosa.frames_to_time(beats[indice], sr=sr))
        fim = float(librosa.frames_to_time(beats[indice + 1], sr=sr))
        if fim <= inicio:
            continue

        inicio_frame = max(0, int(beats[indice]))
        fim_frame = max(inicio_frame + 1, int(beats[indice + 1]))
        media = np.mean(chroma[:, inicio_frame:fim_frame], axis=1)
        acorde = _detectar_acorde_do_chroma(media)
        segmentos.append(
            {
                "inicio": round(inicio, 3),
                "fim": round(fim, 3),
                "duracao": round(fim - inicio, 3),
                **acorde,
            }
        )

    if not segmentos:
        media = np.mean(chroma, axis=1)
        acorde = _detectar_acorde_do_chroma(media)
        segmentos = [
            {
                "inicio": 0.0,
                "fim": round(max(duracao_audio, 0.1), 3),
                "duracao": round(max(duracao_audio, 0.1), 3),
                **acorde,
            }
        ]
        tom_segmentos, _ = _detectar_tonalidade_por_segmentos(segmentos)
        tom_base = tom_global if confianca_global >= 0.18 else (tom_segmentos or tom_global)

        return {
            "segmentos": segmentos,
            "bpm_base": bpm_base,
            "tom_base": tom_base,
        }

    ultimo_fim = segmentos[-1]["fim"]
    if ultimo_fim < duracao_audio:
        ultimo_segmento = dict(segmentos[-1])
        ultimo_segmento["inicio"] = round(ultimo_fim, 3)
        ultimo_segmento["fim"] = round(duracao_audio, 3)
        ultimo_segmento["duracao"] = round(max(duracao_audio - ultimo_fim, 0.1), 3)
        segmentos.append(
            ultimo_segmento
        )

    segmentos = _suavizar_acordes(segmentos)
    tom_segmentos, confianca_segmentos = _detectar_tonalidade_por_segmentos(segmentos)

    if tom_segmentos and (confianca_segmentos >= 0.2 or confianca_global < 0.18):
        tom_base = tom_segmentos
    else:
        tom_base = tom_global

    return {
        "segmentos": segmentos,
        "bpm_base": bpm_base,
        "tom_base": tom_base,
    }


def _extrair_percentual_linha(linha):
    correspondencias = re.findall(r"(\d{1,3})%", linha or "")
    if not correspondencias:
        return None

    for bruto in reversed(correspondencias):
        try:
            valor = int(bruto)
        except ValueError:
            continue
        if 0 <= valor <= 100:
            return valor
    return None


def _atualizar_job(job_id, **campos):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(campos)
        job["updated_at"] = time.time()


def _obter_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return None
        return dict(job)


def _montar_comandos_demucs(arquivo_entrada, modo, formato, pasta_saida):
    python_exe = SEPARADOR_PYTHON if SEPARADOR_PYTHON.exists() else Path(sys.executable)
    base = [str(python_exe), "-m", "demucs", "-o", str(pasta_saida)]
    if formato == "mp3":
        base.append("--mp3")

    arquivo_entrada = str(arquivo_entrada)
    pasta_saida = str(pasta_saida)

    if modo == "2":
        return [
            base + ["--two-stems", "vocals", arquivo_entrada],
            base + ["--two-stems=vocals", arquivo_entrada],
        ]

    return [
        [str(python_exe), "-m", "demucs", "-o", pasta_saida, "-n", "htdemucs"]
        + (["--mp3"] if formato == "mp3" else [])
        + [arquivo_entrada],
        [str(python_exe), "-m", "demucs", "-o", pasta_saida, "--htdemucs"]
        + (["--mp3"] if formato == "mp3" else [])
        + [arquivo_entrada],
    ]


def _executar_demucs(arquivo_entrada, modo, formato, pasta_saida, progresso_callback=None):
    ultimo_erro = None
    processo_env = os.environ.copy()
    processo_env["PYTHONNOUSERSITE"] = "1"
    comandos = _montar_comandos_demucs(arquivo_entrada, modo, formato, pasta_saida)

    for indice, comando in enumerate(comandos, start=1):
        if progresso_callback:
            progresso_callback(8, f"Iniciando separacao (tentativa {indice}/{len(comandos)})...")

        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=processo_env,
            bufsize=1,
        )

        linhas = []
        percentual_reportado = 8
        percentual_suavizado = 8
        ultima_suavizacao = time.time()

        if processo.stdout:
            for linha in processo.stdout:
                linhas.append(linha)
                percentual_linha = _extrair_percentual_linha(linha)

                if percentual_linha is not None:
                    percentual_reportado = max(percentual_reportado, min(95, percentual_linha))

                agora = time.time()
                if percentual_reportado > percentual_suavizado:
                    percentual_suavizado = percentual_reportado
                    ultima_suavizacao = agora
                elif agora - ultima_suavizacao >= 2 and percentual_suavizado < 92:
                    percentual_suavizado += 1
                    ultima_suavizacao = agora

                if progresso_callback:
                    progresso_callback(percentual_suavizado, "Separando audio...")

        retorno = processo.wait()
        saida = "".join(linhas)

        if retorno == 0:
            if progresso_callback:
                progresso_callback(98, "Separacao concluida. Organizando faixas...")
            return saida

        ultimo_erro = saida

    raise RuntimeError(
        ultimo_erro.strip()
        or "Nao foi possivel executar a separacao. Verifique se o ambiente cifrasflix-separador esta pronto."
    )


def _descobrir_faixas(pasta_saida):
    base_static = Path("static").resolve()
    audio_exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

    arquivos = [
        arquivo
        for arquivo in pasta_saida.rglob("*")
        if arquivo.is_file() and arquivo.suffix.lower() in audio_exts
    ]

    arquivos.sort(key=lambda arquivo: (len(arquivo.parts), arquivo.name.lower()))

    faixas = []
    for arquivo in arquivos:
        try:
            relatorio = arquivo.resolve().relative_to(base_static).as_posix()
        except Exception:
            continue

        url_publica = f"/static/{relatorio}"

        faixas.append(
            {
                "nome": arquivo.name,
                "titulo": _label_para_faixa(arquivo.name),
                "url": url_publica,
            }
        )

    return faixas


def _processar_job(job_id, input_path, modo, formato, output_dir, arquivo_original):
    try:
        _atualizar_job(job_id, status="running", progresso=3, mensagem="Preparando separacao...")

        def callback(progresso, mensagem):
            _atualizar_job(job_id, status="running", progresso=min(99, max(0, int(progresso))), mensagem=mensagem)

        _executar_demucs(input_path, modo, formato, output_dir, progresso_callback=callback)
        faixas = _descobrir_faixas(output_dir)

        if not faixas:
            raise RuntimeError("A separacao terminou, mas nenhuma faixa de saida foi encontrada.")

        _atualizar_job(job_id, progresso=96, mensagem="Analisando acordes do audio...")
        analise_musical = _analisar_acordes_audio(input_path)
        acordes = analise_musical.get("segmentos", [])
        bpm_base = float(analise_musical.get("bpm_base", 120.0) or 120.0)
        tom_base = str(analise_musical.get("tom_base", "C") or "C")

        _atualizar_job(
            job_id,
            status="completed",
            progresso=100,
            mensagem="Separacao concluida.",
            resultado={
                "job_id": job_id,
                "arquivo_original": arquivo_original,
                "modo": modo,
                "formato": formato,
                "faixas": faixas,
                "acordes": acordes,
                "bpm_base": bpm_base,
                "tom_base": tom_base,
            },
            erro="",
        )
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            progresso=100,
            mensagem="Falha ao separar audio.",
            erro=str(exc),
        )


@app.route("/separar-audio/status/<job_id>", methods=["GET"])
def separar_audio_status(job_id):
    job = _obter_job(job_id)
    if not job:
        return jsonify({"ok": False, "erro": "Job nao encontrado."}), 404

    return jsonify(
        {
            "ok": True,
            "job_id": job_id,
            "status": job.get("status", "queued"),
            "progresso": int(job.get("progresso", 0)),
            "mensagem": job.get("mensagem", ""),
            "erro": job.get("erro", ""),
            "redirect_url": url_for("separar_audio_route", job=job_id),
        }
    )


@app.route("/separar-audio", methods=["GET", "POST"])
def separar_audio_route():
    _ensure_separador_dirs()

    job_id_param = (request.args.get("job") or "").strip()
    contexto = {
        "erro": "",
        "resultado": None,
        "modo": "2",
        "formato": "wav",
        "processando": False,
        "job_id": "",
        "progresso": 0,
        "mensagem_status": "Aguardando arquivo",
    }

    if request.method == "GET" and job_id_param:
        job = _obter_job(job_id_param)
        if not job:
            contexto["erro"] = "Job nao encontrado. Envie o arquivo novamente."
            return render_template("separador_audio.html", **contexto)

        contexto["job_id"] = job_id_param
        contexto["modo"] = job.get("modo", contexto["modo"])
        contexto["formato"] = job.get("formato", contexto["formato"])
        contexto["progresso"] = int(job.get("progresso", 0))
        contexto["mensagem_status"] = job.get("mensagem", "Processando...")

        status = job.get("status")
        if status == "completed":
            contexto["resultado"] = job.get("resultado")
            contexto["mensagem_status"] = "Separacao concluida"
        elif status == "failed":
            contexto["erro"] = job.get("erro") or "Falha ao separar o audio."
            contexto["mensagem_status"] = "Falha na separacao"
            contexto["progresso"] = 100
        else:
            contexto["processando"] = True

        return render_template("separador_audio.html", **contexto)

    if request.method == "POST":
        arquivo = request.files.get("arquivo_audio")
        modo = (request.form.get("modo") or "2").strip()
        formato = (request.form.get("formato") or "wav").strip().lower()

        contexto["modo"] = modo if modo in {"2", "full"} else "2"
        contexto["formato"] = formato if formato in {"wav", "mp3"} else "wav"

        if not arquivo or not arquivo.filename:
            contexto["erro"] = "Selecione um arquivo de audio para separar."
            return render_template("separador_audio.html", **contexto)

        if not _extensao_valida(arquivo.filename):
            contexto["erro"] = "Use um arquivo MP3, WAV, FLAC, M4A ou OGG."
            return render_template("separador_audio.html", **contexto)

        job_id = uuid.uuid4().hex
        job_dir = OUTPUT_ROOT / job_id
        input_dir = job_dir / "input"
        output_dir = job_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        nome_seguro = secure_filename(arquivo.filename) or f"audio_{job_id}.mp3"
        if not _extensao_valida(nome_seguro):
            nome_seguro = f"audio_{job_id}.mp3"

        input_path = input_dir / nome_seguro
        arquivo.save(input_path)

        try:
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "status": "queued",
                    "progresso": 0,
                    "mensagem": "Job criado. Aguardando processamento...",
                    "erro": "",
                    "resultado": None,
                    "modo": contexto["modo"],
                    "formato": contexto["formato"],
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }

            thread = threading.Thread(
                target=_processar_job,
                args=(job_id, input_path, contexto["modo"], contexto["formato"], output_dir, arquivo.filename),
                daemon=True,
            )
            thread.start()

            contexto["job_id"] = job_id
            contexto["processando"] = True
            contexto["progresso"] = 0
            contexto["mensagem_status"] = "Processamento iniciado..."
        except Exception as exc:
            contexto["erro"] = str(exc)

    return render_template("separador_audio.html", **contexto)