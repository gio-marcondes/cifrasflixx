import sqlite3
import re
import random
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ==========================================
# SLUGIFY
# ==========================================

def slugify(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')


def normalizar_slug(texto):
    texto = texto.lower().strip()
    texto = texto.replace(" ", "-")
    texto = re.sub(r"[^a-z0-9\-]", "", texto)
    return texto


# =====================================
# APP IMPORTADOR DE CIFRAS
# =====================================

class ImportadorCifras:

    def __init__(self, root):

        self.root = root
        self.root.title("Importador de Cifras")
        self.root.geometry("850x650")

        self.db_path = ""
        self.pasta_txt = ""

        # =====================================
        # TOPO
        # =====================================

        frame_topo = tk.Frame(root)
        frame_topo.pack(pady=10, padx=10, fill="x")

        # DB
        tk.Label(
            frame_topo,
            text="Banco SQLite:"
        ).pack(anchor="w")

        frame_db = tk.Frame(frame_topo)
        frame_db.pack(fill="x", pady=5)

        self.entry_db = tk.Entry(frame_db)
        self.entry_db.pack(side="left", fill="x", expand=True)

        tk.Button(
            frame_db,
            text="Selecionar DB",
            command=self.selecionar_db
        ).pack(side="left", padx=5)

        # Pasta TXT
        tk.Label(
            frame_topo,
            text="Pasta das cifras TXT:"
        ).pack(anchor="w")

        frame_pasta = tk.Frame(frame_topo)
        frame_pasta.pack(fill="x", pady=5)

        self.entry_pasta = tk.Entry(frame_pasta)
        self.entry_pasta.pack(side="left", fill="x", expand=True)

        tk.Button(
            frame_pasta,
            text="Selecionar Pasta",
            command=self.selecionar_pasta
        ).pack(side="left", padx=5)

        # BOTÃO IMPORTAR
        tk.Button(
            root,
            text="IMPORTAR CIFRAS",
            bg="#28a745",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            command=self.importar_txt
        ).pack(pady=15)

        # LOG
        self.log = scrolledtext.ScrolledText(
            root,
            height=30
        )

        self.log.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # =====================================
    # LOG
    # =====================================

    def escrever_log(self, texto):

        self.log.insert(tk.END, texto + "\n")
        self.log.see(tk.END)

        self.root.update()

    # =====================================
    # SELECIONAR DB
    # =====================================

    def selecionar_db(self):

        arquivo = filedialog.askopenfilename(
            title="Selecionar banco SQLite",
            filetypes=[
                ("Banco SQLite", "*.db *.sqlite *.sqlite3")
            ]
        )

        if arquivo:

            self.db_path = arquivo

            self.entry_db.delete(0, tk.END)
            self.entry_db.insert(0, arquivo)

    # =====================================
    # SELECIONAR PASTA
    # =====================================

    def selecionar_pasta(self):

        pasta = filedialog.askdirectory(
            title="Selecionar pasta das cifras"
        )

        if pasta:

            self.pasta_txt = pasta

            self.entry_pasta.delete(0, tk.END)
            self.entry_pasta.insert(0, pasta)

    # =====================================
    # IMPORTAÇÃO
    # =====================================

    def importar_txt(self):

        if not self.db_path:

            messagebox.showerror(
                "Erro",
                "Selecione o banco SQLite."
            )

            return

        if not self.pasta_txt:

            messagebox.showerror(
                "Erro",
                "Selecione a pasta das cifras."
            )

            return

        try:

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            pasta = Path(self.pasta_txt)

            if not pasta.exists():

                self.escrever_log(
                    "❌ Pasta não encontrada."
                )

                return

            # =====================================
            # LOOP ARTISTAS
            # =====================================

            for pasta_artista in pasta.iterdir():

                if pasta_artista.is_dir():

                    artista_nome = pasta_artista.name.strip()

                    artista_slug = slugify(artista_nome)

                    c.execute(
                        """
                        INSERT OR IGNORE INTO artistas
                        (nome, slug)
                        VALUES (?, ?)
                        """,
                        (
                            artista_nome,
                            artista_slug
                        )
                    )

                    c.execute(
                        """
                        SELECT id
                        FROM artistas
                        WHERE slug=?
                        """,
                        (artista_slug,)
                    )

                    artista_id = c.fetchone()[0]

                    self.escrever_log(
                        f"\n🎤 ARTISTA: {artista_nome}"
                    )

                    # =====================================
                    # LOOP MÚSICAS
                    # =====================================

                    for arquivo in pasta_artista.glob("*.txt"):

                        try:

                            with open(
                                arquivo,
                                "r",
                                encoding="utf-8",
                                errors="ignore"
                            ) as f:

                                conteudo_original = f.read()

                            linhas = conteudo_original.splitlines()

                            afinacao = ""
                            tom = ""
                            capotraste = ""

                            # =====================================
                            # TÍTULO
                            # =====================================

                            titulo = arquivo.stem.strip()

                            if linhas:

                                primeira = linhas[0]\
                                    .replace(" Cifra", "")\
                                    .strip()

                                if primeira:
                                    titulo = primeira

                            # =====================================
                            # INFORMAÇÕES
                            # =====================================

                            for linha in linhas:

                                linha_strip = linha.strip()

                                # AFINAÇÃO
                                if linha_strip.lower().startswith("afinação:"):

                                    afinacao = linha_strip\
                                        .split(":", 1)[1]\
                                        .strip()

                                # TOM
                                if linha_strip.lower().startswith("tecla:"):

                                    tom = linha_strip\
                                        .split(":", 1)[1]\
                                        .strip()

                                # CAPOTRASTE
                                if linha_strip.lower().startswith("capotraste:"):

                                    match = re.search(
                                        r"(\d+)",
                                        linha_strip
                                    )

                                    if match:
                                        capotraste = match.group(1)
                                    else:
                                        capotraste = "0"

                            # =====================================
                            # CONTEÚDO APÓS TAB:
                            # =====================================

                            match_tab = re.search(
                                r"TAB:\s*(.*)",
                                conteudo_original,
                                re.DOTALL | re.IGNORECASE
                            )

                            if match_tab:
                                conteudo = match_tab.group(1).strip()
                            else:
                                conteudo = ""

                            slug = normalizar_slug(
                                slugify(titulo)
                            )

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

                            self.escrever_log(
                                f"   ✅ {titulo}"
                            )

                            self.escrever_log(
                                f"      Tom: {tom}"
                            )

                            self.escrever_log(
                                f"      Afinação: {afinacao}"
                            )

                            self.escrever_log(
                                f"      Capotraste: {capotraste}"
                            )

                        except Exception as e:

                            self.escrever_log(
                                f"   ❌ ERRO: {arquivo.name}"
                            )

                            self.escrever_log(str(e))

            conn.commit()
            conn.close()

            self.escrever_log(
                "\n✅ IMPORTAÇÃO CONCLUÍDA!"
            )

            messagebox.showinfo(
                "Sucesso",
                "Importação concluída com sucesso."
            )

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )


# =====================================
# INICIAR APP
# =====================================

if __name__ == "__main__":

    root = tk.Tk()

    app = ImportadorCifras(root)

    root.mainloop()