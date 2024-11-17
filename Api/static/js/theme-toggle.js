document.getElementById('theme-toggle').addEventListener('click', function() {
    // Get the current theme
    let currentTheme = document.body.className;

    // Remove all theme classes
    document.body.classList.remove('light-theme', 'dark-theme', 'blue-theme');

    // Toggle to the next theme
    if (currentTheme === 'light-theme') {
        document.body.classList.add('dark-theme');
    } else if (currentTheme === 'dark-theme') {
        document.body.classList.add('blue-theme');
    } else {
        document.body.classList.add('light-theme');
    }

    // Optionally, save the theme preference to localStorage
    localStorage.setItem('theme', document.body.className);
});

// Load the theme on page load based on saved preference
window.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.body.classList.add(savedTheme);
    } else {
        // Default to light theme if no preference is saved
        document.body.classList.add('light-theme');
    }
});
