document.addEventListener('DOMContentLoaded', () => {
    const lengthSlider = document.getElementById('lengthSlider');
    const lengthVal = document.getElementById('lengthVal');
    const passwordOutput = document.getElementById('passwordOutput');
    const includeUpper = document.getElementById('includeUpper');
    const includeNumbers = document.getElementById('includeNumbers');
    const includeSymbols = document.getElementById('includeSymbols');

    if (lengthSlider) {
        lengthSlider.addEventListener('input', (e) => {
            lengthVal.textContent = e.target.value;
            generatePassword();
        });

        // Add change events to switches
        [includeUpper, includeNumbers, includeSymbols].forEach(el => {
            if (el) el.addEventListener('change', generatePassword);
        });

        // Initial generation
        generatePassword();
    }
});

function generatePassword() {
    const output = document.getElementById('passwordOutput');
    if (!output) return;

    const length = document.getElementById('lengthSlider').value;
    const useUpper = document.getElementById('includeUpper').checked;
    const useNumbers = document.getElementById('includeNumbers').checked;
    const useSymbols = document.getElementById('includeSymbols').checked;

    const lowercaseChars = 'abcdefghijklmnopqrstuvwxyz';
    const uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const numberChars = '0123456789';
    const symbolChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';

    let charSet = lowercaseChars;
    if (useUpper) charSet += uppercaseChars;
    if (useNumbers) charSet += numberChars;
    if (useSymbols) charSet += symbolChars;

    let password = '';
    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * charSet.length);
        password += charSet[randomIndex];
    }

    // Dynamic font resizing for stability
    if (length > 48) {
        output.style.fontSize = '1.0rem';
    } else if (length > 32) {
        output.style.fontSize = '1.2rem';
    } else if (length > 16) {
        output.style.fontSize = '1.4rem';
    } else {
        output.style.fontSize = '1.8rem';
    }

    output.textContent = password;
}

function copyToClipboard() {
    const output = document.getElementById('passwordOutput');
    if (!output) return;

    const text = output.textContent;
    if (text.includes("Klicke 'Erstellen'")) return;

    navigator.clipboard.writeText(text).then(() => {
        showToast();

        // Visual feedback on display
        const originalBg = output.style.backgroundColor;
        output.style.backgroundColor = 'var(--m3-primary-container)';
        setTimeout(() => {
            output.style.backgroundColor = originalBg;
        }, 300);
    });
}

function showToast() {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}
