document.addEventListener('DOMContentLoaded', () => {
    // Password Generator Logic
    const lengthRange = document.getElementById('lengthRange');
    const lengthValue = document.getElementById('lengthValue');
    const passwordOutput = document.getElementById('passwordOutput');
    const includeUppercase = document.getElementById('includeUppercase');
    const includeLowercase = document.getElementById('includeLowercase');
    const includeNumbers = document.getElementById('includeNumbers');
    const includeSymbols = document.getElementById('includeSymbols');

    if (lengthRange) {
        lengthRange.addEventListener('input', (e) => {
            lengthValue.textContent = e.target.value;
            generatePassword();
        });

        // Add event listeners to all checkboxes
        [includeUppercase, includeLowercase, includeNumbers, includeSymbols].forEach(el => {
            el.addEventListener('change', generatePassword);
        });

        // Initial generation
        generatePassword();

        // Copy to clipboard functionality
        passwordOutput.addEventListener('click', () => {
            const text = passwordOutput.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const originalText = passwordOutput.textContent;
                passwordOutput.textContent = 'Kopiert!';
                passwordOutput.style.backgroundColor = 'var(--md-sys-color-primary-container)';
                
                setTimeout(() => {
                    passwordOutput.textContent = originalText;
                    passwordOutput.style.backgroundColor = '';
                }, 1000);
            });
        });
    }
});

function generatePassword() {
    const length = document.getElementById('lengthRange').value;
    const useUpper = document.getElementById('includeUppercase').checked;
    const useLower = document.getElementById('includeLowercase').checked;
    const useNumbers = document.getElementById('includeNumbers').checked;
    const useSymbols = document.getElementById('includeSymbols').checked;

    const uppercaseChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const lowercaseChars = 'abcdefghijklmnopqrstuvwxyz';
    const numberChars = '0123456789';
    const symbolChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';

    let allChars = '';
    if (useUpper) allChars += uppercaseChars;
    if (useLower) allChars += lowercaseChars;
    if (useNumbers) allChars += numberChars;
    if (useSymbols) allChars += symbolChars;

    if (allChars === '') {
        document.getElementById('passwordOutput').textContent = 'Optionen wählen!';
        return;
    }

    let password = '';
    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * allChars.length);
        password += allChars[randomIndex];
    }

    document.getElementById('passwordOutput').textContent = password;
}
