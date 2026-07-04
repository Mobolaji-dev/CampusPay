// Show and Hide password sign-up

document.addEventListener('DOMContentLoaded', () => {
    // Select the input and the button
    const passwordInput = document.getElementById('signup-password');
    const toggleButton = document.querySelector('.toggle-password');

    toggleButton.addEventListener('click', () => {
        // Check current input type and toggle it
        const isPassword = passwordInput.type === 'password';
        passwordInput.type = isPassword ? 'text' : 'password';

        // Update accessibility label
        toggleButton.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');

        // Optional: Swap the SVG icon to show an "eye-off" when the password is visible
        if (isPassword) {
            // Eye-off icon (password visible)
            toggleButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
            `;
        } else {
            // Original Eye icon (password hidden)
            toggleButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                </svg>
            `;
        }
    });
});


// remove any special character

const fullName = document.getElementById("fullName");

fullName.addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/[^a-zA-Z\s]/g, "")
})


