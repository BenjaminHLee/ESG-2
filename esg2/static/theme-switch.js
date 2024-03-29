var currentTheme = localStorage.getItem('theme');
if (currentTheme === null) {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark')
    }
} else {
    document.documentElement.setAttribute('data-theme', currentTheme);
}

window.onload = function () {
    const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
    if (currentTheme) {
            document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark') {
            toggleSwitch.checked = true;
        }
    }

    function switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            currentTheme = 'dark';
        }
        else {        
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            currentTheme = 'light';
        }    

        try {
            if (scoreboardPage == true) {
                document.getElementById('hourly-chart').innerHTML = "";
                document.getElementById('summary-chart').innerHTML = "";
                fetchCharts(r, h, currentTheme);
            }
        } catch {
            ;
        }
    }

    toggleSwitch.addEventListener('change', switchTheme, false);
}