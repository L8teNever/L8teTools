const toolsData = [
    { name: "Passwort Generator", url: "/tools/password-generator", icon: "password", keywords: ["sicherheit", "crypto", "pw", "login", "key", "safe", "secure", "passwort"] },
    { name: "QR-Code Generator", url: "/tools/qr-generator", icon: "qr_code_2", keywords: ["scan", "link", "url", "2d code", "share", "quick", "response"] },
    { name: "Datei Konverter", url: "/tools/file-converter", icon: "transform", keywords: ["bild", "pdf", "jpg", "png", "umwandeln", "format", "konvertieren", "convert", "image"] },
    { name: "Glücksrad", url: "/tools/wheel-of-fortune", icon: "autorenew", keywords: ["random", "zufall", "entscheidung", "spiel", "rad", "wheel", "luck"] },
    { name: "Würfel", url: "/tools/dice-roller", icon: "casino", keywords: ["dice", "spiel", "zahl", "zufall", "board", "game", "würfeln"] },
    { name: "Punktezähler", url: "/tools/score-tracker", icon: "scoreboard", keywords: ["score", "spiel", "track", "punkte", "zählen", "sport", "game"] },
    { name: "Farbwähler", url: "/tools/color-picker", icon: "palette", keywords: ["hex", "rgb", "hsl", "color", "design", "css", "farbe", "picker", "web"] },
    { name: "URL Shortener", url: "/tools/shortlinks", icon: "link", keywords: ["link", "kürzen", "short", "bitly", "tiny", "url", "adresse"] },
    { name: "HTML/CSS Playground", url: "/tools/playground", icon: "code", keywords: ["code", "html", "css", "test", "web", "entwicklung", "dev", "editor"] },
    { name: "Einheiten-Umrechner", url: "/tools/unit-converter", icon: "straighten", keywords: ["cm", "m", "kg", "celsius", "fahrenheit", "umrechnen", "maße", "zoll", "feet", "inch"] },
    { name: "Diff-Checker", url: "/tools/diff-checker", icon: "difference", keywords: ["vergleich", "unterschied", "text", "git", "diff", "compare", "code"] },
    { name: "Case Converter", url: "/tools/case-converter", icon: "text_fields", keywords: ["gross", "klein", "camelcase", "text", "upper", "lower", "snake", "kebab"] },
    { name: "Word Counter", url: "/tools/word-counter", icon: "segment", keywords: ["wörter", "zählen", "zeichen", "länge", "count", "text", "analyse"] },
    { name: "Exif-Daten Entferner", url: "/tools/exif-remover", icon: "perm_camera_mic", keywords: ["meta", "daten", "foto", "privatsphäre", "gps", "remove", "clean", "exif", "image"] },
    { name: "IP Info", url: "/tools/my-ip", icon: "public", keywords: ["adresse", "netzwerk", "internet", "wifi", "ip", "public", "location"] },
    { name: "Whois Lookup", url: "/tools/whois", icon: "domain_verification", keywords: ["domain", "besitzer", "dns", "lookup", "whois", "registar"] },
    { name: "MAC Finder", url: "/tools/mac-lookup", icon: "lan", keywords: ["vendor", "hersteller", "hardware", "mac", "address", "network"] },
    { name: "BMI Rechner", url: "/tools/bmi-calculator", icon: "monitor_weight", keywords: ["gesundheit", "gewicht", "größe", "körper", "bmi", "index", "mass"] },
    { name: "Text Sorter", url: "/tools/text-sorter", icon: "sort_by_alpha", keywords: ["liste", "alphabet", "sortieren", "ordnen", "a-z", "unique", "duplikate"] },
    { name: "Regex Replacer", url: "/tools/regex-replacer", icon: "find_replace", keywords: ["suchen", "ersetzen", "pattern", "code", "regex", "regular", "expression"] },
    { name: "Listen Vergleicher", url: "/tools/list-comparator", icon: "compare_arrows", keywords: ["vergleich", "unterschied", "listen", "diff", "common", "unique"] },
    { name: "Morsecode", url: "/tools/morse-code", icon: "graphic_eq", keywords: ["code", "übersetzung", "funk", "sos", "morse", "sound", "signal"] },
    { name: "Arbeitstage", url: "/tools/workday-calculator", icon: "event_available", keywords: ["urlaub", "tage", "datum", "arbeit", "wochenende", "feiertage", "calc"] },
    { name: "Prefix/Suffix", url: "/tools/prefix-suffix", icon: "format_quote", keywords: ["programmieren", "text", "zeilen", "edit", "prefix", "suffix", "add"] },
    { name: "Notizen", url: "/tools/notes", icon: "edit_note", keywords: ["schreiben", "text", "gedanken", "speichern", "notiz", "notes", "memo"] },
    { name: "Wiki", url: "/tools/wiki", icon: "library_books", keywords: ["wissen", "linux", "befehle", "help", "cheat", "sheet", "wiki", "docs"] },
];

function toggleSearch() {
    const wrapper = document.getElementById('searchWrapper');
    const input = document.getElementById('globalSearch');

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
    const q = query.toLowerCase().trim();

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
