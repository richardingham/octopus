
var _graphCounter = 0;

function Graph (element, options) {
  var window = 1000 * 60 * 5;
  var unit = null;
  var graphId = _graphCounter++;

  var streams = [];
  this.streams = [];

  var duration = 1000,
      now = new Date(),
      start = new Date(now - window);

  var margin = {top: 5, right: 20, bottom: 40, left: 60};

  this.addData = function (payload) {
    var i, j, k, m = payload.length, n = streams.length, l;
    var last, streamData, newData;

    for (i = 0; i < m; i++) {
      for (j = 0; j < n; j++) {
        if (payload[i].name == streams[j].key) {
          newData = payload[i].data;
          streamData = streams[j].data;
          last = streamData.length && streamData[streamData.length - 1];

          // Inserting old data
          if (last && payload[i].data[0][0] < last[0]) {
            Array.prototype.push.apply(streamData, payload[i].data);
            streamData.sort(function (a, b) { return a[0] - b[0]; });

          // The graph is empty currently
          } else if (streamData.length < 2) {
            Array.prototype.push.apply(streamData, payload[i].data);

          // Inserting new data - avoid runs of the same number.
          } else {
            for (k = 0, l = newData.length; k < l; k++) {
              if (newData[k][0] == last[0]) {
                continue;
              } else if (newData[k][1] == last[1] && streamData[streamData.length - 2][1] == last[1]) {
                last[0] = newData[k][0];
              } else {
                streamData.push(newData[k]);
                last = newData[k];
              }
            }
          }
        }
      }
    }

    if (options.static) {
      draw();
    }
  };

  this.addStream = function (variable) {
    for (var i = 0; i < streams.length; i++)
      if (variable.key == streams[i].key)
        return false;

    if (unit === null) {
      unit = variable.unit;
      ylabel.text(unit);
    } else if (unit !== variable.unit) {
      console.log("mismatched units: ", this.unit, variable);
      return false;
    }

    var now = new Date(),
        start = new Date(now - window);

    streams.push({
      variable: variable,
      key: variable.key,
      data: [] //[[start, 0], [now, 0]]
    });

    this.streams = _.map(streams, 'key');

    // Request data for added stream.
    if (options.static) {
      options.requestData.call(this, [variable.key]);
    } else {
      options.requestData.call(this, [variable.key], start, now);
    }

    makeLegend();

    return true;
  };

  this.removeStream = function (key) {
    for (var i = 0; i < streams.length; i++) {
      if (key == streams[i].key) {
        streams.splice(i, 1);
        this.streams = _.map(streams, 'key');
        makeLegend();
        draw();

        if (streams.length === 0) {
          unit = null;
        }
        return true;
      }
    }

    return false;
  };

  this.variables = function () {
    return _.map(streams, 'variable');
  };

  this.unit = function () {
    return unit;
  };

  this.setSize = function () {
    var el = $(element);
    var width = el.width();
    var height = el.height();

    $('svg', el).attr({ width: width, height: height });

    width -= (margin.right + margin.left);
    height -= (margin.top + margin.bottom);

    x.range([0, width]);
    y.range([height, 0]);

    $('#graph' + graphId + '-clip rect', el).attr({ width: width, height: height });

    xaxis.attr("transform", "translate(0," + height + ")");

    xlabel.attr("x", width)
      .attr("y", height - 6);

    if (options.static) {
      draw();
    }
  };

  this.window = function (newWindow) {
    if (typeof newWindow === 'undefined') {
      return window;
    }

    window = newWindow;
    var start = new Date(new Date() - window);
    var end = d3.max(streams, function(s) { return d3.min(s.data, function(v) { return v[0]; }); });

    options.requestData(_.map(streams, 'key'), start, end);
  };

  var axisTimeMode = 'absolute';
  this.axisTime = function (mode) {
    if (typeof mode === 'undefined') {
      return axisTimeMode;
    }
    if (mode == 'relative' && options.timezero) {
      axisTimeMode = 'relative';
    } else {
      axisTimeMode = 'absolute';
    }
    if (options.static) {
      draw();
    }
    return axisTimeMode;
  };

  var x = d3.scaleTime()
      .domain([start, now]);

  var y = d3.scaleLinear()
      .domain([0, 1]);

  var line = d3.line()
      .x(function(d, i) { return x(d[0]); })
      .y(function(d, i) { return y(d[1]); });

  var svg = d3.select(element).append("svg")
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  svg.append("defs").append("clipPath")
      .attr("id", "graph" + graphId + "-clip")
      .append("rect");

  var xaxis = svg.append("g")
      .attr("class", "x axis")
      .call(x.axis = d3.axisBottom().scale(x));

  var yaxis = svg.append("g")
      .attr("class", "y axis")
      .call(y.axis = d3.axisLeft().scale(y));

  var xlabel = svg.append("text")
    .attr("class", "x label")
    .attr("text-anchor", "end")
    .text("Time");

  var ylabel = svg.append("text")
    .attr("class", "y label")
    .attr("text-anchor", "end")
    .attr("y", 6)
    .attr("dy", ".75em")
    .attr("transform", "rotate(-90)");

  var color = d3.scaleOrdinal(d3.schemeCategory10);

  var cliparea = svg.append("g")
      .attr('clip-path', 'url(#graph' + graphId + '-clip)');
  var chartarea = cliparea.append("g");

  var legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", "translate(20, 15)")
      .style("font-size", "12px");

  this.setSize();

  function _fetch (fn, i) {
    return function(s) { return fn(s.data, function(v) { return v[i]; }); };
  }

  if (options.timezero) {
    // Round to nearest second.
    options.timezero = Math.round(options.timezero / 1000) * 1000;
  }

  function relativeTickFormat (date) {
    d = (+date - options.timezero) / 1000;

    var result = [];
    var days   = Math.floor(d / 86400);
    d -= days * 86400;

    var hours = Math.floor(d / 3600);
    if (hours > 0) result.push(hours);
    d -= hours * 3600;

    var minutes = Math.floor(d / 60);
    if (minutes > 0) {
      result.push((result.length !== 0 && minutes < 10 ? '0' : '') + minutes);
    }

    var seconds = d - (minutes * 60);
    seconds = Math.round(seconds * 100) / 100;

    if (result.length === 0) {
      result.push(seconds + 's');
    } else if (seconds > 0) {
      result.push((seconds < 10 ? '0' : '') + seconds);
    }

    result = result.join(':');
    if (days > 0) {
      return days + 'd ' + result;
    }

    return result;
  }

  var absoluteTickFormat = x.tickFormat();

  function draw () {
    var now = new Date();

    // update the domains
    if (options.static) {
      x.domain([
        d3.min(streams, _fetch(d3.min, 0)),
        d3.max(streams, _fetch(d3.max, 0))
      ]);
    } else {
      x.domain([now - window, now]);
    }

    y.domain([
      d3.min(streams, _fetch(d3.min, 1)),
      1.01 * d3.max(streams, _fetch(d3.max, 1))
    ]);

    // Remove old data
    if (!options.static) {
      var data;
      for (var s = 0, n = streams.length; s < n; s++) {
        data = streams[s].data;
        if (data.length && data[0][0] < now - (window * 2)) {
          var i, earliest_data = now - window;
          for (i = 0, m = data.length; i < m; i++) {
            if (data[i][0] > earliest_data)
                break;
          }
          if (i - 2 > data.length / 3) {
            data.splice(0, i - 2);
          }
        }
      }
    }

    // redraw the lines
    var update = chartarea.selectAll('.stream').data(streams, function (d) { return d.key; });
    update.enter().append('g')
      .attr('class', 'stream')
      .append('path')
      .attr('data-legend', function (d) { return d.variable.name; })
      .attr('class', 'line')
      .style('stroke', function (d) { return color(d.key); });

    update.exit().remove();

    chartarea.selectAll('.stream').select('.line')
      .attr('d', function (d) { return line(d.data); });

    // slide the x-axis left
    xaxis.call(x.axis.tickFormat(axisTimeMode == 'relative' ? relativeTickFormat : absoluteTickFormat));
    yaxis.call(y.axis);

    // slide the line left
    if (!options.static) {
      chartarea.attr('transform', 'translate(0,0)');
      chartarea.transition()
        .attr("transform", "translate(" + (x(now - duration) - x(now)) + ")");
    }
  }

  if (options.static) {
    draw();
  } else {
    var transition = d3.select({}).transition()
        .duration(duration)
        .ease(d3.easeLinear);

    (function tick () {
      transition = transition.each(draw).transition().on("start", tick);
    })();
  }

  // https://gist.github.com/ZJONSSON/3918369
  function makeLegend () {
    var g = legend,
        legendPadding = 5;

    g.style('display', streams.length ? 'block' : 'none');

    var items = _.map(streams, function (stream) {
      return {
        key: stream.key,
        name: stream.variable.name,
        color: color(stream.key)
      };
    });

    g.selectAll(".legend-box").data([true])
      .enter().append("rect").classed("legend-box", true);

    g.selectAll(".legend-items").data([true])
        .enter().append("g").classed("legend-items", true);

    var li = g.selectAll(".legend-items"),
        lb = g.selectAll(".legend-box");

    var text = li.selectAll("text")
        .data(items, function(d) { return d.key; });

    text.exit().remove();
    text.enter().append("text")
        .attr("y", function (d, i) { return i + "em"; })
        .attr("x", "1em")
        .text(function(d) { return d.name; });

    var circles = li.selectAll("circle")
        .data(items, function (d) { return d.key; });

    circles.exit().remove();
    circles.enter().append("circle")
        .attr("cy", function (d, i) { return i - 0.25 + "em"; })
        .attr("cx", 0)
        .attr("r", "0.4em")
        .style("fill", function (d) { return d.color; });

    var lbbox = li.nodes()[0].getBBox()

    lb.attr("x", (lbbox.x - legendPadding))
        .attr("y", (lbbox.y - legendPadding))
        .attr("height", (lbbox.height + 2 * legendPadding))
        .attr("width", (lbbox.width + 2 * legendPadding));
  }
}
