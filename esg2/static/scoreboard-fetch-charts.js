function fetchCharts(r, h) {
    var t = 'light';
    if (currentTheme === null || currentTheme === 'dark') {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            t = 'dark';
        }
    }
    fetch("/chart/hourly/r" + r +  "h" + h + "?theme=" + t)
        .then(function(response) { return response.json(); })
        .then(function(item) { return Bokeh.embed.embed_item(item); })
    fetch('/chart/summary?theme=' + t)
        .then(function(response) { return response.json(); })
        .then(function(item) { return Bokeh.embed.embed_item(item); })
}