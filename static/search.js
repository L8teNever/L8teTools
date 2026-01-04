const toolsData = [
    { name: "Passwort Generator", url: "/tools/password-generator", icon: "password", category: "security", keywords: ["sicherheit", "crypto", "pw", "login", "key", "safe", "secure", "passwort"] },
    { name: "QR-Code Generator", url: "/tools/qr-generator", icon: "qr_code_2", category: "images", keywords: ["scan", "link", "url", "2d code", "share", "quick", "response"] },
    { name: "Datei Konverter", url: "/tools/file-converter", icon: "transform", category: "images", keywords: ["bild", "pdf", "jpg", "png", "umwandeln", "format", "konvertieren", "convert", "image"] },
    { name: "Glücksrad", url: "/tools/wheel-of-fortune", icon: "autorenew", category: "games", keywords: ["random", "zufall", "entscheidung", "spiel", "rad", "wheel", "luck"] },
    { name: "Würfel", url: "/tools/dice-roller", icon: "casino", category: "games", keywords: ["dice", "spiel", "zahl", "zufall", "board", "game", "würfeln"] },
    { name: "Punktezähler", url: "/tools/score-tracker", icon: "scoreboard", category: "games", keywords: ["score", "spiel", "track", "punkte", "zählen", "sport", "game"] },
    { name: "Farbwähler", url: "/tools/color-picker", icon: "palette", category: "design", keywords: ["hex", "rgb", "hsl", "color", "design", "css", "farbe", "picker", "web"] },
    { name: "URL Shortener", url: "/tools/shortlinks", icon: "link", category: "network", keywords: ["link", "kürzen", "short", "bitly", "tiny", "url", "adresse"] },
    { name: "HTML/CSS Playground", url: "/tools/playground", icon: "code", category: "dev", keywords: ["code", "html", "css", "test", "web", "entwicklung", "dev", "editor"] },
    { name: "Einheiten-Umrechner", url: "/tools/unit-converter", icon: "straighten", category: "calc", keywords: ["cm", "m", "kg", "celsius", "fahrenheit", "umrechnen", "maße", "zoll", "feet", "inch"] },
    { name: "Diff-Checker", url: "/tools/diff-checker", icon: "difference", category: "dev", keywords: ["vergleich", "unterschied", "text", "git", "diff", "compare", "code"] },
    { name: "Case Converter", url: "/tools/case-converter", icon: "text_fields", category: "text", keywords: ["gross", "klein", "camelcase", "text", "upper", "lower", "snake", "kebab"] },
    { name: "Word Counter", url: "/tools/word-counter", icon: "segment", category: "text", keywords: ["wörter", "zählen", "zeichen", "länge", "count", "text", "analyse"] },
    { name: "Exif-Daten Entferner", url: "/tools/exif-remover", icon: "perm_camera_mic", category: "images", keywords: ["meta", "daten", "foto", "privatsphäre", "gps", "remove", "clean", "exif", "image"] },
    { name: "IP Info", url: "/tools/my-ip", icon: "public", category: "network", keywords: ["adresse", "netzwerk", "internet", "wifi", "ip", "public", "location"] },
    { name: "Whois Lookup", url: "/tools/whois", icon: "domain_verification", category: "network", keywords: ["domain", "besitzer", "dns", "lookup", "whois", "registar"] },
    { name: "MAC Finder", url: "/tools/mac-lookup", icon: "lan", category: "network", keywords: ["vendor", "hersteller", "hardware", "mac", "address", "network"] },
    { name: "BMI Rechner", url: "/tools/bmi-calculator", icon: "monitor_weight", category: "calc", keywords: ["gesundheit", "gewicht", "größe", "körper", "bmi", "index", "mass"] },
    { name: "Text Sorter", url: "/tools/text-sorter", icon: "sort_by_alpha", category: "text", keywords: ["liste", "alphabet", "sortieren", "ordnen", "a-z", "unique", "duplikate"] },
    { name: "Regex Replacer", url: "/tools/regex-replacer", icon: "find_replace", category: "dev", keywords: ["suchen", "ersetzen", "pattern", "code", "regex", "regular", "expression"] },
    { name: "Listen Vergleicher", url: "/tools/list-comparator", icon: "compare_arrows", category: "text", keywords: ["vergleich", "unterschied", "listen", "diff", "common", "unique"] },
    { name: "Morsecode", url: "/tools/morse-code", icon: "graphic_eq", category: "text", keywords: ["code", "übersetzung", "funk", "sos", "morse", "sound", "signal"] },
    { name: "Arbeitstage", url: "/tools/workday-calculator", icon: "event_available", category: "calc", keywords: ["urlaub", "tage", "datum", "arbeit", "wochenende", "feiertage", "calc"] },
    { name: "Prefix/Suffix", url: "/tools/prefix-suffix", icon: "format_quote", category: "dev", keywords: ["programmieren", "text", "zeilen", "edit", "prefix", "suffix", "add"] },
    { name: "Notizen", url: "/tools/notes", icon: "edit_note", category: "text", keywords: ["schreiben", "text", "gedanken", "speichern", "notiz", "notes", "memo"] },
    { name: "Wiki", url: "/tools/wiki", icon: "library_books", category: "dev", keywords: ["wissen", "linux", "befehle", "help", "cheat", "sheet", "wiki", "docs"] },
];

function toggleSearch() {
    const wrapper = document.getElementById('searchWrapper');
    const input = document.getElementById('globalSearch');

    // Close related menu if open
    const related = document.getElementById('relatedToolsWrapper');
    if (related && !related.classList.contains('hidden')) toggleRelatedTools();

    if (wrapper.classList.contains('hidden')) {
        wrapper.classList.remove('hidden');
        // Trigger reflow
        void wrapper.offsetWidth;
        wrapper.classList.remove('w-0', 'opacity-0');
        wrapper.classList.add('w-[300px]', 'opacity-100');
        input.focus();
    } else {
        wrapper.classList.remove('w-[300px]', 'opacity-100');
        wrapper.classList.add('w-0', 'opacity-0');
        setTimeout(() => {
            wrapper.classList.add('hidden');
            document.getElementById('searchResults').classList.add('hidden');
            input.value = '';
        }, 300);
    }
}

function closeSearchWithDelay() {
    setTimeout(() => {
        // Check if focus moved to results
        if (!document.activeElement.closest('#searchResults')) {
            toggleSearch();
        }
    }, 200);
}

function performSearch(query) {
    const resultsDiv = document.getElementById('searchResults');
    const dashboardGrid = document.getElementById('dashboard-grid');
    const q = query.toLowerCase().trim();

    // --- DASHBOARD MODE ---
    if (dashboardGrid) {
        // Hide dropdown if it was somehow shown
        if (!resultsDiv.classList.contains('hidden')) {
            resultsDiv.classList.add('hidden');
        }

        const cards = Array.from(dashboardGrid.children);

        // Reset if empty query
        if (q.length === 0) {
            cards.forEach(card => {
                card.classList.remove('hidden');
                card.style.order = 'initial';
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            });
            return;
        }

        let hasMatches = false;

        cards.forEach(card => {
            const href = card.getAttribute('href');
            // Remove potential query params
            const toolUrl = href ? href.split('?')[0] : '';

            // Find tool data
            const tool = toolsData.find(t => t.url === toolUrl) || { name: "", keywords: [] };

            // Fallback: search in text content if no tool data found (robustness)
            const textContent = card.innerText.toLowerCase();

            let score = 0;

            // 1. Data-based scoring
            if (tool.name) {
                if (tool.name.toLowerCase() === q) score += 100;
                else if (tool.name.toLowerCase().startsWith(q)) score += 80;
                else if (tool.name.toLowerCase().includes(q)) score += 60;

                tool.keywords.forEach(k => {
                    if (k === q) score += 50;
                    else if (k.startsWith(q)) score += 30;
                    else if (k.includes(q)) score += 10;

                    if (q.length > 3 && Math.abs(k.length - q.length) <= 1) {
                        if (getEditDistance(q, k) <= 1) score += 20;
                    }
                });
            }

            // 2. Text-content fallback (if tool data might be missing or generic search)
            if (textContent.includes(q)) score += 5;

            if (score > 0) {
                card.classList.remove('hidden');
                // Invert score for order (smaller order = first)
                // Max score around maybe 500? 
                // We use a large negative offset to ensure sorted order
                card.style.order = -score;
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
                hasMatches = true;
            } else {
                card.classList.add('hidden');
                card.style.order = '9999';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
            }
        });

        return;
    }

    // --- GLOBAL DROPDOWN MODE (Non-Dashboard) ---
    if (q.length < 2) {
        resultsDiv.classList.add('hidden');
        resultsDiv.innerHTML = '';
        return;
    }

    const scored = toolsData.map(tool => {
        let score = 0;

        // Exact title match priority
        if (tool.name.toLowerCase() === q) score += 100;
        else if (tool.name.toLowerCase().startsWith(q)) score += 80;
        else if (tool.name.toLowerCase().includes(q)) score += 60;

        // Keyword matching
        tool.keywords.forEach(k => {
            if (k === q) score += 50;
            else if (k.startsWith(q)) score += 30;
            else if (k.includes(q)) score += 10;

            // Simple typo tolerance (levenshtein-ish for shorts)
            if (q.length > 3 && Math.abs(k.length - q.length) <= 1) {
                if (getEditDistance(q, k) <= 1) score += 20;
            }
        });

        return { ...tool, score };
    });

    const results = scored.filter(tool => tool.score > 0).sort((a, b) => b.score - a.score);

    if (results.length > 0) {
        resultsDiv.innerHTML = results.slice(0, 5).map(tool => `
            <a href="${tool.url}" class="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-0">
                <span class="material-icons-round text-gray-500 bg-gray-100 dark:bg-gray-700 p-2 rounded-lg">${tool.icon}</span>
                <div>
                    <div class="font-bold text-sm text-gray-800 dark:text-gray-200">${tool.name}</div>
                    <div class="text-xs text-gray-400">Match: ${tool.score > 80 ? 'Volltreffer' : 'Relevantes Tool'}</div>
                </div>
            </a>
        `).join('');
        resultsDiv.classList.remove('hidden');
    } else {
        resultsDiv.innerHTML = `<div class="p-4 text-center text-gray-400 text-sm">Kein passendes Tool gefunden.</div>`;
        resultsDiv.classList.remove('hidden');
    }
}

// Simple Levenshtein distance for typos
function getEditDistance(a, b) {
    if (a.length === 0) return b.length;
    if (b.length === 0) return a.length;

    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, Math.min(matrix[i][j - 1] + 1, matrix[i - 1][j] + 1));
            }
        }
    }
    return matrix[b.length][a.length];
}

// --- RELATED TOOLS FEATURE ---

function toggleRelatedTools() {
    const wrapper = document.getElementById('relatedToolsWrapper');
    const btn = document.getElementById('relatedToolsBtn');

    if (wrapper.classList.contains('hidden')) {
        wrapper.classList.remove('hidden');
        // Small delay to allow transition
        setTimeout(() => {
            wrapper.style.maxHeight = '500px';
            wrapper.style.opacity = '1';
        }, 10);
        btn.classList.add('bg-blue-100', 'dark:bg-blue-900', 'text-blue-700');
    } else {
        wrapper.style.maxHeight = '0px';
        wrapper.style.opacity = '0';
        btn.classList.remove('bg-blue-100', 'dark:bg-blue-900', 'text-blue-700');
        setTimeout(() => {
            wrapper.classList.add('hidden');
        }, 300);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on a tool page
    const header = document.querySelector('.page-header');
    if (!header) return; // Not a tool page (or dashboard different struct)

    // Check if dashboard link exists in header (indicator of tool page)
    const backBtn = header.querySelector('a[href*="dashboard"]');
    if (!backBtn) return;

    // Identify current tool
    const currentPath = window.location.pathname;
    const currentTool = toolsData.find(t => t.url.split('?')[0] === currentPath);

    if (!currentTool || !currentTool.category) return;

    // Find Related Tools
    const related = toolsData.filter(t => t.category === currentTool.category && t.url.split('?')[0] !== currentPath);

    if (related.length === 0) return;

    // Inject Button
    const btnContainer = document.createElement('div');
    btnContainer.className = "relative ml-2";

    const btn = document.createElement('button');
    btn.id = "relatedToolsBtn";
    btn.onclick = toggleRelatedTools;
    btn.className = "p-4 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors relative";
    btn.title = "Ähnliche Tools";
    btn.innerHTML = `<span class="material-icons-round text-2xl text-gray-600 dark:text-gray-300">category</span>`;

    // Inject Dropdown Container
    const dropdown = document.createElement('div');
    dropdown.id = "relatedToolsWrapper";
    dropdown.className = "hidden absolute top-16 left-0 bg-white dark:bg-gray-800 shadow-xl rounded-xl border border-gray-200 dark:border-gray-700 z-50 w-72 overflow-hidden transition-all duration-300 opacity-0";
    dropdown.style.maxHeight = "0px";

    let html = `<div class="p-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700 text-xs font-bold text-gray-500 uppercase tracking-widest">
        Kategorie: ${currentTool.category.toUpperCase()}
    </div>`;

    related.forEach(tool => {
        html += `
        <a href="${tool.url}" class="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-0">
            <span class="material-icons-round text-gray-500 bg-gray-100 dark:bg-gray-700 p-2 rounded-lg text-lg">${tool.icon}</span>
            <div class="text-sm font-medium text-gray-800 dark:text-gray-200">${tool.name}</div>
        </a>`;
    });

    dropdown.innerHTML = html;

    btnContainer.appendChild(btn);
    btnContainer.appendChild(dropdown);

    // Insert after back button. 
    backBtn.parentNode.insertBefore(btnContainer, backBtn.nextSibling);
});
