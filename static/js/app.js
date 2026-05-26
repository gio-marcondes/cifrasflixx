let currentPage = 1;
let lastSearchTerm = "";
let searchTimer = null;

function showLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (!overlay) return;
    overlay.classList.add("show");
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
}

function hideLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (!overlay) return;
    overlay.classList.remove("show");
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";
}

function navegarComEfeito(url) {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) overlay.classList.add("show");
    document.body.style.transition = "transform 0.3s ease, opacity 0.3s ease";
    document.body.style.transform = "scale(1)";
    document.body.style.opacity = "0.5";

    setTimeout(() => {
        window.location.href = url;
    }, 220);
}

document.addEventListener("click", function(e) {
    function handleClick(el) {
        if (!el) return false;
        const hrefMatch = el.getAttribute("onclick")?.match(/location\.href='(.+)'/);
        if (hrefMatch) {
            e.preventDefault();
            navegarComEfeito(hrefMatch[1]);
            return true;
        }
        return false;
    }

    if (e.target.closest(".musicRow")) return handleClick(e.target.closest(".musicRow"));
    if (e.target.closest(".list-item")) return handleClick(e.target.closest(".list-item"));

    const pageBtn = e.target.closest(".pageBtn");
    if (pageBtn) {
        e.preventDefault();
        navegarComEfeito(pageBtn.href);
        return;
    }

    const chordLink = e.target.closest("a.chord");
    if (chordLink) {
        e.preventDefault();
        navegarComEfeito(chordLink.href);
    }
});

function renderResultados(data, append = false) {
    const div = document.getElementById("resultado");
    if (!div) return;
    if (!append) div.innerHTML = "";

    if (!data.results || !data.results.length) {
        div.innerHTML = '<div class="list-item">Nenhum resultado encontrado</div>';
        return;
    }

    data.results.forEach(item => {
        div.innerHTML += `
            <div class="list-item" onclick="location.href='/artista/${item.artista}/${item.uid}'">
                <strong>${item.titulo}</strong><br>
                <span style="color:#6b7280">${item.artista_nome}</span>
            </div>
        `;
    });

    if (data.has_next) {
        div.innerHTML += `<div style="text-align:center;">
            <button type="button" onclick="proximaPagina('${lastSearchTerm}')" class="mais-btn">Mais...</button>
        </div>`;
    }
}

function executarBusca(q) {
    const div = document.getElementById("resultado");
    if (!div) return;

    if (!q) {
        div.style.display = "none";
        div.innerHTML = "";
        return;
    }

    if (q !== lastSearchTerm) {
        currentPage = 1;
        lastSearchTerm = q;
    }

    div.style.display = "block";
    div.innerHTML = '<div class="list-item">Buscando...</div>';

    fetch(`/buscar?q=${encodeURIComponent(q)}&page=${currentPage}`)
        .then(r => r.json())
        .then(data => renderResultados(data))
        .catch(() => {
            div.innerHTML = '<div class="list-item">Erro ao buscar</div>';
        });
}

function buscar() {
    const input = document.getElementById("busca");
    if (!input) return;
    const q = input.value.trim();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => executarBusca(q), 180);
}

function proximaPagina(q) {
    const div = document.getElementById("resultado");
    if (!div) return;
    currentPage += 1;
    div.querySelector(".mais-btn")?.remove();

    fetch(`/buscar?q=${encodeURIComponent(q)}&page=${currentPage}`)
        .then(r => r.json())
        .then(data => renderResultados(data, true));
}

function toggleDark() {
    document.body.classList.toggle("dark-mode");
    localStorage.setItem("theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
}

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("loginModal");
    const btn = document.getElementById("loginBtn");
    const closeBtn = document.querySelector(".close");
    const searchInput = document.getElementById("busca");
    const resultado = document.getElementById("resultado");

    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
    }

    document.querySelectorAll(".menu a").forEach(link => {
        if (link.pathname === window.location.pathname) link.classList.add("active");
    });

    if (searchInput) {
        searchInput.addEventListener("input", buscar);
        searchInput.addEventListener("keydown", event => {
            if (event.key === "Escape" && resultado) {
                resultado.style.display = "none";
                searchInput.blur();
            }
        });
    }

    if (btn && modal) btn.addEventListener("click", () => modal.style.display = "block");
    if (closeBtn && modal) closeBtn.addEventListener("click", () => modal.style.display = "none");

    document.addEventListener("click", event => {
        const container = document.querySelector(".busca-container");
        if (container && resultado && !container.contains(event.target)) {
            resultado.style.display = "none";
        }

        if (modal && event.target === modal) {
            modal.style.display = "none";
        }
    });
});
