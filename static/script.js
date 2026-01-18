function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// SPA Navigation & Scroll Memory
let scrollPositions = {};

function initSPA() {
    // Intercept all internal links
    document.addEventListener('click', e => {
        const link = e.target.closest('a');
        if (link && link.href && link.href.startsWith(window.location.origin) &&
            !link.target && !link.hasAttribute('download') && !link.href.includes('#')) {

            // Don't intercept if it's a "logout" or specific non-SPA links if any
            if (link.href.includes('/logout')) return;

            e.preventDefault();
            navigateTo(link.href);
        }
    });

    // Handle back/forward buttons
    window.addEventListener('popstate', e => {
        loadPage(window.location.href, false);
    });

    // Save scroll position of dashboard
    if (window.location.pathname === '/dashboard') {
        window.addEventListener('scroll', () => {
            if (window.location.pathname === '/dashboard') {
                scrollPositions['/dashboard'] = window.scrollY;
            }
        });
    }
}

async function navigateTo(url) {
    // Save current scroll position before leaving
    scrollPositions[window.location.pathname] = window.scrollY;

    history.pushState(null, '', url);
    await loadPage(url, true);
}

async function loadPage(url, isForward = true) {
    const main = document.querySelector('.main-content');
    const loadingBar = document.getElementById('loadingBar');

    // Start transition
    main.classList.add('page-transitioning');
    loadingBar.style.width = '30%';

    try {
        const response = await fetch(url);
        loadingBar.style.width = '70%';
        const html = await response.text();

        // Parse the new content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newContent = doc.querySelector('.main-content').innerHTML;
        const newTitle = doc.title;

        // Wait a bit for the fade out
        setTimeout(() => {
            main.innerHTML = newContent;
            document.title = newTitle;
            main.classList.remove('page-transitioning');
            loadingBar.style.width = '100%';

            // Restore scroll position or top
            if (scrollPositions[new URL(url).pathname]) {
                window.scrollTo({
                    top: scrollPositions[new URL(url).pathname],
                    behavior: isForward ? 'instant' : 'smooth'
                });
            } else {
                window.scrollTo(0, 0);
            }

            // Re-run scripts if necessary (especially for tools)
            executeScripts(doc);

            // Hide loading bar
            setTimeout(() => {
                loadingBar.style.width = '0%';
            }, 300);
        }, 200);

    } catch (e) {
        console.error('SPA Load Error:', e);
        window.location.href = url; // Fallback to normal load
    }
}

function executeScripts(doc) {
    // Find scripts in the new content
    const actualScripts = doc.querySelectorAll('.main-content script');

    actualScripts.forEach(oldScript => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
        document.body.appendChild(newScript);
        // Clean up
        setTimeout(() => newScript.remove(), 1000);
    });

    // Re-init global features from search.js if loaded
    if (typeof initRelatedTools === 'function') initRelatedTools();
}

// Extract the initialization logic from search.js into a callable function
function initRelatedTools() {
    // Check if we are on a tool page
    const header = document.querySelector('.page-header');
    if (!header) return;

    const backBtn = header.querySelector('a[href*="dashboard"]');
    if (!backBtn) return;

    // Avoid double buttons
    if (document.getElementById('relatedToolsBtn')) return;

    const currentPath = window.location.pathname;
    const currentTool = toolsData.find(t => t.url.split('?')[0] === currentPath);
    if (!currentTool || !currentTool.category) return;

    const related = toolsData.filter(t => t.category === currentTool.category && t.url.split('?')[0] !== currentPath);
    if (related.length === 0) return;

    const btnContainer = document.createElement('div');
    btnContainer.className = "relative ml-2";
    const btn = document.createElement('button');
    btn.id = "relatedToolsBtn";
    btn.onclick = toggleRelatedTools;
    btn.className = "p-4 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors relative";
    btn.innerHTML = `<span class="material-icons-round text-2xl text-gray-600 dark:text-gray-300">category</span>`;

    const dropdown = document.createElement('div');
    dropdown.id = "relatedToolsWrapper";
    dropdown.className = "hidden absolute top-16 left-0 bg-white dark:bg-gray-800 shadow-xl rounded-xl border border-gray-200 dark:border-gray-700 z-50 w-72 overflow-hidden transition-all duration-300 opacity-0";
    dropdown.style.maxHeight = "0px";

    let html = `<div class="p-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700 text-xs font-bold text-gray-500 uppercase tracking-widest">Kategorie: ${currentTool.category.toUpperCase()}</div>`;
    related.forEach(tool => {
        html += `<a href="${tool.url}" class="flex items-center gap-3 p-3 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-0"><span class="material-icons-round text-gray-500 bg-gray-100 dark:bg-gray-700 p-2 rounded-lg text-lg">${tool.icon}</span><div class="text-sm font-medium text-gray-800 dark:text-gray-200">${tool.name}</div></a>`;
    });
    dropdown.innerHTML = html;
    btnContainer.appendChild(btn);
    btnContainer.appendChild(dropdown);
    backBtn.parentNode.insertBefore(btnContainer, backBtn.nextSibling);
}
