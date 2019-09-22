jQuery(function ($) {

  var timezero = parseInt($('#viewer').data('timezero')) * 1000;
  var timeend = parseInt($('#viewer').data('timeend')) * 1000;
  var variables = $('#viewer').data('variables');
  var dataurl = $('#viewer').data('url');

  var graphs = [];

  $.each(variables, function (i, variable) {
    $('#variables').append($('<li>', {
      'data-id': variable.key,
      'text': variable.name
    }));
  });

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

  function requestData (streams, start, end) {
    var graph = this;

    var data = {
      var: streams
    };

    if (start) {
      data.start = +start / 1000;
    }
    if (end) {
      data.end = +end / 1000;
    }

    $.get(
      dataurl,
      data,
      function (payload) {
        var i, j, m, n, data, point, zero = timezero;
        for (i = 0, m = payload.length; i < m; i++) {
          data = payload[i].data;
          for (j = 0, n = data.length; j < n; j++) {
            point = data[j];
            point[0] = new Date(point[0] * 1000 + zero);
          }
        }

        graph.addData(payload);
      },
      'json'
    );
  }

  function addGraph (variable) {
    var container = $('<div class="chart-container grid-stack-item">');
    var content = $('<div class="grid-stack-item-content">').appendTo(container);
    var handle = $('<div class="grid-stack-item-handle">').appendTo(content);

    $('<i class="remove fa fa-times-circle">').appendTo(handle);
    $('<i class="options fa fa-cog">').appendTo(handle);
    $('<i class="add fa fa-plus-circle">').appendTo(handle);

    var graphEl = $('<div class="chart">').appendTo(content);
    grid.add_widget(container, 0, 0, 6, 5);

    var graph = new Graph(graphEl[0], {
      timezero: timezero,
      static: true,
      requestData: requestData
    });
    graph.addStream(variable);
    graphs.push(graph);
    container.data('graph', graph);

    return true;
  }

  $('.grid-stack').on('resizestop', _.debounce(function (event) {
      //var grid = this;
      var element = $(event.target);
      if (element.is('.chart-container')) {
        element.data('graph').setSize();
      }
  }, 500));

  // Chart toolbar options
  $('#data').on('click', '.chart-container i.remove', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    container.remove();

    for (i = 0, m = graphs.length; i < m; i++) {
      if (graphs[i] == graph) {
        graphs.splice(i, 1);
      }
    }
  });

  $('#data').on('click', '.chart-container i.options', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    var editor = new GraphOptions(container, graph, {
      axisTime: true
    });
    editor.show();
  });

  $('#data').on('click', '.chart-container i.add', function () {
    var container = $(this).closest('.chart-container');
    var graph = container.data('graph');
    var editor = new GraphAddStream(container, graph, variables, {
      addStream: function (variable) {
        return graph.addStream(variable);
      }
    });
    editor.show();
  });

  // Add a chart by clicking on a variables entry
  $('#variables').on('click', 'li', function () {
    var id = $(this).data('id');

    if (id) {
      // Find id in variables.
      for (var i = 0, m = variables.length; i < m; i++) {
        if (variables[i].key === id) {
          return addGraph(variables[i]);
        }
      }
    }
  });
});
