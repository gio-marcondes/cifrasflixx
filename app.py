"""Ponto de entrada do CifrasFlix.

O app original foi dividido em módulos por responsabilidade. Eles são
carregados no mesmo namespace para preservar o comportamento das rotas e
helpers que ainda compartilham muitos globals.
"""
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODULE_DIR = BASE_DIR / "modules"

MODULES = (
    "config.py",
    "layout.py",
    "ui_helpers.py",
    "routes_main.py",
    "routes_admin.py",
    "routes_albums.py",
    "routes_lyrics.py",
)


for module_name in MODULES:
    module_path = MODULE_DIR / module_name
    code = compile(module_path.read_text(encoding="utf-8"), str(module_path), "exec")
    exec(code, globals())


if __name__ == "__main__":
    app.run(debug=True)
