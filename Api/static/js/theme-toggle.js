document.addEventListener("DOMContentLoaded", function () {
    const themeToggle = document.getElementById("theme-toggle");
    const currentTheme = localStorage.getItem("theme") || "light";

    // Apply the saved theme and log it for debugging
    console.log("Applying saved theme:", currentTheme);
    document.documentElement.setAttribute("data-theme", currentTheme);

    // Update the button text
    themeToggle.textContent = currentTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode";

    themeToggle.addEventListener("click", function () {
        // Toggle the theme
        const newTheme = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
        console.log("Switched to new theme:", newTheme);

        // Update the button text
        themeToggle.textContent = newTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode";
    });
});
