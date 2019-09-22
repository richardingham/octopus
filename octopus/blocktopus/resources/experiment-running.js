jQuery(function ($) {

  var experiment = {
    sketch: $('#viewer').data('sketch'),
    id: $('#viewer').data('experiment'),
    title: $('#viewer').data('title'),
    timeZero: $('#viewer').data('timezero') * 1000,
    variables: []
  };

  var properties = [];
  var streams = { length: 0 };

  var socketOpen = false;
  var socketUrl = $('#viewer').data('url');
  var socket = new WebSocket(socketUrl, "octopus");

  properties.updateFrequency = 1000;
  streams.updateFrequency = 1000;

  socket.onopen = function () {
    console.log("Socket open");
    socketOpen = true;
    _socketSend("experiment", "load", {});
  };

  socket.onmessage = function (e) {
    var data = JSON.parse(e.data);

    var protocol = data.protocol;
    var command = data.command;
    var payload = data.payload;

    if (!(protocol === "experiment" && payload.sketch === experiment.sketch && payload.experiment === experiment.id)) {
      return;
    }

    if (command === "load") {
      experiment.variables = payload.variables.sort(function (a, b) {
        if (a.name < b.name) return -1;
        if (a.name > b.name) return 1;
        return 0;
      });
      experiment.title = payload.title;
      refreshVariableList();
      return;
    }

    if (command === "variable-added") {
      return; // self.fire("experiment-variable-added", payload);
    }

    if (command === "variable-removed") {
      return; // self.fire("experiment-variable-removed", payload);
    }

    if (command === "streams") {

      // Add time zero to each data point
      var i, m, a, p, z = payload.zero;
      for (var key in payload.data) {
        a = payload.data[key].data;
        for (i = 0, m = a.length; i < m; i++) {
          p = a[i];
          p[0] = new Date((p[0] + z) * 1000);
        }
      }

      // Insert data into graphs
      for (i = 0, m = graphs.length; i < m; i++) {
        graphs[i].addData(payload.data);
      }

      // Schedule next request
      if (!payload.oneoff) {
        window.clearTimeout(streams.updateTimer);
        streams.updateTimer = window.setTimeout(
          streams.request,
          streams.updateFrequency
        );
      }
      return;
    }

    if (command === "properties") {
      var variablesData = payload.data;

      $('#data .property-container').each(function () {
        var variable = $(this).data('variable');

        if (typeof variable !== 'undefined' && typeof variable.key !== 'undefined' && typeof variablesData[variable.key] !== 'undefined') {
          variable.value = variablesData[variable.key];

          if (variable.type == 'Image') {
            $('img', this).attr('src', variable.value);
          } else {
            $('span.value', this).text(variable.value);
          }
        }
      });

      window.clearTimeout(properties.updateTimer);
      properties.updateTimer = window.setTimeout(
        properties.request,
        properties.updateFrequency
      );
      return;
    }

    console.log("socket message", data);
  };

  socket.onclose = function (reason) {
    console.log("Connection Closed: ", reason);
    self.open = false;
  };

  properties.add = function (name) {
    for (var i = 0, m = properties.length; i < m; i++) {
      if (properties[i] === name) {
        return;
      }
    }
    properties.push(name);
    properties.changed();
  };

  properties.remove = function (name) {
    for (var i = 0, m = properties.length; i < m; i++) {
      if (properties[i] === name) {
        properties.splice(i, 1);
      }
    }
    properties.changed();
  };

  properties.changed = function () {
    _socketSend("experiment", "choose-properties", {
      properties: properties
    });

    properties.request();
  };

  properties.request = function () {
    if (properties.length > 0) {
      _socketSend("experiment", "get-properties", {});
    }
  };

  streams.changed = function () {
    var streamNames = _(graphs).map('streams').flatten().uniq().value();

    _socketSend("experiment", "choose-streams", {
      streams: streamNames
    });

    streams.length = streamNames.length;
    streams.request();
  };

  streams.request = function () {
    var start;

    if (!streams.lastRequest) {
      start = +(new Date()) - 60 * 1000;
      streams.lastRequest = start;
    } else {
      start = streams.lastRequest;
      streams.lastRequest = +(new Date());
    }

    if (streams.length > 0) {
      _socketSend("experiment", "get-streams", { start: start / 1000 });
    }
  };

  function _socketSend (protocol, command, payload) {
    if (!socketOpen) {
      return;
    }

    payload.sketch = experiment.sketch;
    payload.experiment = experiment.id;

    var data = { protocol: protocol, command: command, payload: payload };

    //console.log("Socket send", data);
    socket.send(JSON.stringify(data));
  }

  var graphs = [];

  var _itemIndex = 0;

  function refreshVariableList () {
    $.each(experiment.variables, function (i, variable) {
      $('#variables').append($('<li>', {
        'data-id': variable.key,
        'text': variable.name
      }));
    });
  }
  refreshVariableList();

  var grid = $('<div>')
    .addClass('grid-stack')
    .appendTo('#data')
    .gridstack({
      cell_height: 50,
      width: 12,
      float: true,
      handle: '.grid-stack-item-handle'
    })
    .data('gridstack');

  function addProperty (variable) {
    var container = $('<div>', {
      addClass: 'property-container grid-stack-item',
    }).data('variable', variable);

    var content = $('<div class="grid-stack-item-content">').appendTo(container);
    var handle = $('<div class="grid-stack-item-handle">').appendTo(content);

    handle.append(variable.name);

    $('<i class="remove fa fa-times-circle">').appendTo(handle);

    if (variable.type == 'int' || variable.type == 'float') {
      $('<i class="expand fa fa-area-chart">').appendTo(handle);
    }

    if (variable.edit) {
      $('<i class="edit fa fa-pencil-square-o">').appendTo(handle);
    }

    var el = $('<div class="property">').appendTo(content);

    if (variable.type == 'Image') {
      $('<img>', {
        src: variable.value
      }).appendTo(el);
    } else {
      $('<span>', {
        addClass: 'value',
        text: variable.value
      }).appendTo(el);

      if (variable.unit !== '') {
        $('<span>', {
          addClass: 'unit',
          text: variable.unit
        }).appendTo(el);
      }
    }

    properties.add(variable.key);
    grid.add_widget(container, 0, 0, 2, 1);
  }


  function addGraph (graphInfo) {
    var container = $('<div class="chart-container grid-stack-item">');
    var content = $('<div class="grid-stack-item-content">').appendTo(container);
    var handle = $('<div class="grid-stack-item-handle">').appendTo(content);

    $('<i class="remove fa fa-times-circle">').appendTo(handle);
    $('<i class="options fa fa-cog">').appendTo(handle);
    $('<i class="add fa fa-plus-circle">').appendTo(handle);

    var graphEl = $('<div class="chart">').appendTo(content);
    grid.add_widget(container, 0, 0, 6, 5);

    var graph = new Graph(graphEl[0], {
      timezero: experiment.timeZero,
      requestData: function (streams, start, end) {
        _socketSend("experiment", "get-streams", {
          start: start / 1000,
          end: end / 1000,
          streams: streams,
          oneoff: true
        });
      }
    });
    graph.addStream(graphInfo.stream);
    graphs.push(graph);
    container.data('graph', graph);

    streams.changed();

    return true;
  }

  // Resize chart on box resize
  $('.grid-stack').on('resizestop', _.debounce(function (event) {
      //var grid = this;
      var element = $(event.target);
      if (element.is('.chart-container')) {
        element.data('graph').setSize();
      }
  }, 500));

  // Property toolbar actions
  $('#data').on('click', '.property-container i.remove', function () {
    $(this).closest('.property-container').remove();
  });

  $('#data').on('click', '.property-container i.expand', function () {
    var container = $(this).closest('.property-container');
    var variable = container.data('variable');
    var graphAdded = addGraph({
      index: _itemIndex++,
      stream: variable
    });
    // TODO: expand + replace contents of container in place.
    if (graphAdded) {
      container.remove();
    }
  });

  $('#data').on('click', '.property-container i.edit', function () {
    var container = $(this).closest('.property-container');
    var variable = container.data('variable');
    var editor = new PropertyEditor(container, variable, {
      update: function (variables) {
        $.each(variables, function (i, variable) {
          _socketSend('experiment', 'set-property', variable);
        });
      }
    });
    editor.show();
  });

  // Chart toolbar actions
  $('#data').on('click', '.chart-container i.remove', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    container.remove();

    for (i = 0, m = graphs.length; i < m; i++) {
      if (graphs[i] == graph) {
        graphs.splice(i, 1);
      }
    }

    streams.changed();
  });

  $('#data').on('click', '.chart-container i.options', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    var editor = new GraphOptions(container, graph, {
      window: true,
      axisTime: true
    });
    editor.show();
  });

  $('#data').on('click', '.chart-container i.add', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    var editor = new GraphAddStream(container, graph, experiment.variables, {
      addStream: function (variable) {
        var ok = graph.addStream(variable);
        streams.changed();
        return ok;
      }
    });
    editor.show();
  });

  // Add a property watch by clicking on a variables entry
  $('#variables').on('click', 'li', function () {
    var id = $(this).data('id');

    if (id) {
      // Find id in variables.
      for (var i = 0, m = experiment.variables.length; i < m; i++) {
        if (experiment.variables[i].key === id) {
          addProperty(experiment.variables[i]);
          return;
        }
      }
    }
  });

});
