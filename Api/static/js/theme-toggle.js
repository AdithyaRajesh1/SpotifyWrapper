// Load the theme on page load based on saved preference
window.addEventListener('DOMContentLoaded', function () {
    const savedTheme = localStorage.getItem('theme');

    // Remove all existing theme classes first
    document.body.classList.remove('light-theme', 'dark-theme', 'blue-theme');

    if (savedTheme) {
        // Apply saved theme
        document.body.classList.add(savedTheme);
    } else {
        // Default to light theme if no preference is saved
        document.body.classList.add('light-theme');
    }
});

// Toggle theme logic
document.getElementById('theme-toggle').addEventListener('click', function () {
    // Get the current theme from classList
    let currentTheme = Array.from(document.body.classList).find(cls =>
        ['light-theme', 'dark-theme', 'blue-theme'].includes(cls)
    );

    // Remove all theme classes
    document.body.classList.remove('light-theme', 'dark-theme', 'blue-theme');

    // Cycle to the next theme
    if (currentTheme === 'light-theme') {
        document.body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark-theme');
    } else if (currentTheme === 'dark-theme') {
        document.body.classList.add('blue-theme');
        localStorage.setItem('theme', 'blue-theme');
    } else {
        document.body.classList.add('light-theme'); // Default to light
        localStorage.setItem('theme', 'light-theme');
    }
});