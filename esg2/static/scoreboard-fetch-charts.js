function fetchCharts(r, h, t) {
    fetch("/chart/hourly/r" + r +  "h" + h + "?theme=" + t)
        .then(function(response) { return response.json(); })
        .then(function(item) { return Bokeh.embed.embed_item(item); })
    fetch('/chart/summary?theme=' + t)
        .then(function(response) { return response.json(); })
        .then(function(item) { return Bokeh.embed.embed_item(item); })
}

var scoreboardPage = true;