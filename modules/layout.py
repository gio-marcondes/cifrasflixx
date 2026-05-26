def header(titulo="CifrasFlix"):
    template_path = BASE_DIR / "templates" / "header.html"
    html = template_path.read_text(encoding="utf-8")
    return html.replace("{{ titulo }}", str(titulo))

