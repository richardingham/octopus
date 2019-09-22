
jQuery(function ($) {

  Blockly.inject($('#blockly')[0], {
      path: '/resources/blockly/'
  });

  var loaded = false;
  toolboxPopulate();

  function updateCode () {
    if (!$('#editor').hasClass('code')) {
      return;
    }

    $('#code pre').html(prettyPrintOne(
      PythonOctoGenerator.workspaceToCode(
        Blockly.getMainWorkspace().getTopBlocks(true)
      ),
      'python'
    ));
  }
  Blockly.addWorkspaceChangeListener(updateCode);

  // Sketch / Experiment
  var sketchId = $('#blockly').data('sketch');
  var experimentState = '';
  var experimentId = '';

  function setExperimentState (state) {
    experimentState = state;
    $('#toolbar').attr('experiment-state', state);
  }

  setExperimentState('ready');

  // Socket communications
  var socket = new WebSocket($('#blockly').data('websocket'), 'octopus');
  var socketOpen = false;

  socket.onopen = function () {
    console.log("Socket open");
    socketOpen = true;
    _socketSend("sketch", "load", {
      sketch: sketchId
    });
  };

  socket.onclose = function (reason) {
    console.log('Connection Closed: ', reason);
    alert('Connection to server was lost. Please refresh the page.');
    socketOpen = false;
  };

  socket.onmessage = function (e) {
    var data = JSON.parse(e.data);
    //console.log('socket message', data);

    var protocol = data.protocol;
    var command = data.command;
    var payload = data.payload;

    if (protocol === 'sketch' && payload.sketch == sketchId) {
      if (command === 'load') {
        if (payload.state !== 'ready') {
          setExperimentState(payload.state);
          experimentId = payload.experiment;
        }

        var message, messages = payload['log-messages'] || [];
        for (var i = 0, m = messages.length; i < m; i++) {
          message = messages[i];
          addLogMessage(message.experiment, message.level, message.message, new Date(message.time * 1000));
        }

        return sketchLoaded(payload);
      }

      if (command === 'renamed') {
        return sketchRenamed(payload.title);
      }
    }

    if (protocol === 'block' && payload.sketch == sketchId) {
      return blockChanged(command, payload);
    }

    if (protocol === 'experiment' && payload.sketch == sketchId) {
      if (command === 'state-started') {
        experimentId = payload.experiment;
        setExperimentState('running');
        addLogMessage(payload.experiment, 'status', 'Experiment running', new Date());
      } else if (command === 'state-stopped') {
        experimentId = null;
        setExperimentState('ready');
        addLogMessage(payload.experiment, 'status', 'Experiment complete', new Date());
      } else if (command === 'state-paused') {
        setExperimentState('paused');
        addLogMessage(payload.experiment, 'status', 'Experiment paused', new Date());
      } else if (command === 'state-resumed') {
        setExperimentState('running');
        addLogMessage(payload.experiment, 'status', 'Experiment resumed', new Date());
      } else if (command === 'state-error') {
        setExperimentState('error');
        addLogMessage(payload.experiment, 'error', 'Experiment error: ' + payload.error, new Date());
      }

      else if (command === 'log' && payload.experiment == experimentId) {
        addLogMessage(payload.experiment, payload.level, payload.message, new Date(payload.time * 1000));
      }
    }

    if (command === 'error' && payload.sketch == sketchId) {
      console.error(protocol, payload);
    }
  };

  function _socketSend (protocol, command, payload) {
    if (!socketOpen) {
      return;
    }

    var data = { protocol: protocol, command: command, payload: payload };

    console.log("Socket send", data);
    socket.send(JSON.stringify(data));
  }

  function blockEvent (event) {
    event.data.sketch = sketchId;

    // Remove "block-" from each event in a transaction.
    if (event.eventType === "transaction") {
      event.data.events = event.data.events.map(function (event) {
        if (event.event.substring(0, 6) === "block-") {
          event.event = event.event.substring(6);
        }
        return event;
      });
    }

    _socketSend("block", event.eventType, event.data);
  }

  function changeTitle (title) {
    _socketSend("sketch", "rename", {
      sketch: sketchId,
      title: title
    });
  }

  function experimentAction (action) {
    _socketSend("experiment", action, {
      sketch: sketchId
    });
  }


  // Received initial load data from the server
  function sketchLoaded (sketch) {
      sketchRenamed(sketch.title);

      var workspace = Blockly.getMainWorkspace();
      var moveBlocks = {};

      var event, data, block, input;
      for (var i in sketch.events) {
          event = sketch.events[i];
          data = event.data;
          if (event.type === "AddBlock") {
              block = Blockly.createBlock(workspace, data.type, data.id);

              for (var field in data.fields) {
                  block.setFieldValue(data.fields[field], field);
              }

              block.initSvg();

          } else if (event.type === "SetBlockPosition") {
              block = workspace.getBlockById(data.id);
              block.moveTo(data.x, data.y);

          } else if (event.type === "SetBlockInputsInline") {
              block = workspace.getBlockById(data.id);
              block.setInputsInline(data.value);

          } else if (event.type === "SetBlockDisabled") {
              block = workspace.getBlockById(data.id);
              block.setDisabled(data.value);

          } else if (event.type === "SetBlockCollapsed") {
              block = workspace.getBlockById(data.id);
              block.setCollapsed(data.value);

          } else if (event.type === "SetBlockComment") {
              block = workspace.getBlockById(data.id);
              block.setCommentText(data.value);

          } else if (event.type === "SetBlockMutation") {
              block = workspace.getBlockById(data.id);
              block.JSONToMutation(JSON.parse(data.mutation));

          } else if (event.type === "ConnectBlock") {
              block = workspace.getBlockById(data.id);
              var parent = workspace.getBlockById(data.parent);

              if (data.connection === "input-value") {
                  input = parent.getInput(data.input);
                  if (input) {
                      input.connection.connect(block.outputConnection);
                  }
              } else if (data.connection === "input-statement") {
                  input = parent.getInput(data.input);
                  if (input) {
                      input.connection.connect(block.previousConnection);
                  }
              } else if (data.connection === "previous") {
                  parent.nextConnection.connect(block.previousConnection);
              }
          }
      }

      // Force re-evaluation of variable names upon loading.
      var topBlocks = workspace.getTopBlocks();
      for (i = 0, m = topBlocks.length; i < m; i++) {
          topBlocks[i].setParent(null);
      }

      workspace.render();

      // Set block running states
      var states = sketch['block-states'];
      for (var id in states) {
          workspace.getBlockById(id).setRunningState(states[id]);
      }

      var blockEvents = [
          "created", "disposed", "connected", "disconnected",
          "set-position", "set-field-value", "set-disabled",
          "set-inputs-inline", "add-input", "remove-input",
          "set-comment", "set-collapsed",
          "set-mutation", "transaction", "cancel"
      ];

      blockEvents.forEach(function (type) {
          Blockly.addEventListener("block-" + type, function (data) {
              blockEvent({
                  eventType: type,
                  data: data
              });
          });
      });
  }

  function sketchRenamed (title) {
    $('#experiment-title').val(title);
    document.title = title + " | Edit Sketch";
  }

  function blockChanged (command, payload) {
    var workspace = Blockly.getMainWorkspace();
    var block;

    if (command === "transaction") {
      return console.log("transaction", payload);
    }
    if (command === "created") {
      workspace.startEmitTransaction();

      block = Blockly.createBlock(workspace, payload.type, payload.id);
      block.initSvg();
      block.render();

      block.moveBy(payload.x, payload.y);

      for (var field in payload.fields) {
        block.setFieldValue(payload.fields[field], field);
      }

      workspace.discardEmitTransaction();
      return;
    }
    if (command === "state") {
      block = workspace.getBlockById(payload.block);
      if (block) {
        return block.setRunningState(payload.state);
      }
    }

    block = workspace.getBlockById(payload.id);
    if (!block) {
      return;
    }

    workspace.startEmitTransaction();
    switch (command) {
      case "set-position":
        block.moveTo(payload.x, payload.y);
        break;
      case "set-field-value":
        block.setFieldValue(payload.value, payload.field);
        break;
      case "set-disabled":
        block.setDisabled(payload.value);
        break;
      case "set-inputs-inline":
        block.setInputsInline(payload.value);
        break;
      case "set-collapsed":
        block.setCollapsed(payload.value);
        break;
      case "set-comment":
        block.setCommentText(payload.value);
        break;
      case "set-mutation":
        block.JSONToMutation(JSON.parse(payload.mutation));
        break;
      case "disposed":
        block.dispose();
        break;
      case "connected":
        var parent = workspace.getBlockById(payload.parent);
        if (payload.connection === "input-value") {
          parent.getInput(payload.input).connection.connect(block.outputConnection);
        } else if (payload.connection === "input-statement") {
          parent.getInput(payload.input).connection.connect(block.previousConnection);
        } else if (payload.connection === "previous") {
          parent.nextConnection.connect(block.previousConnection);
        }
        break;
      case "disconnected":
        var connection, parentConnection;
        if (payload.connection === "input-value") {
          connection = block.outputConnection;
        } else if (payload.connection === "input-statement") {
          connection = block.previousConnection;
        } else if (payload.connection === "previous") {
          connection = block.previousConnection;
        }
        parentConnection = connection.targetConnection;
        block.setParent(null);
        connection.bumpAwayFrom_(parentConnection);
        break;
    }

    workspace.discardEmitTransaction();
  }

  function clearBlockStates () {
    Blockly.getMainWorkspace().getAllBlocks().forEach(function (block) {
      block.setRunningState("ready");
    });
  }

  // Log messages
  var closedExperiments = [];

  function addLogMessage (experimentId, level, message, time) {
    var container = $('#experiments-log > [data-experiment=' + experimentId + ']');

    if (container.length === 0) {
      if (closedExperiments.indexOf(experimentId) !== -1) {
        return;
      }

      container = $('<div>', {
        addClass: 'experiment',
        'data-experiment': experimentId
      });
      container.append('<div class="experiment-link">');
      $('.experiment-link', container).append($('<a>', {
        href: '/experiment/' + experimentId,
        text: 'Show Experiment',
        target: '_blank'
      }));
      container.append($('<i>', {
        addClass: 'cancel fa fa-times-circle',
        click: function () {
          var exptlog = $(this).closest('.experiment');
          closedExperiments.push(exptlog.data('experiment'));
          exptlog.remove();
        }
      }));
      container.append('<ul>');
      container.appendTo('#experiments-log');
    }

    $('<li>', {
      text: '[' + formatLogTime(time) + '] ' + message
    }).prepend($('<i>', {
      addClass: 'fa fa-lg fa-' + levelToIcon(level),
      css: {
        color: levelToIconColour(level)
      }
    })).appendTo($('ul', container));
  }

  function formatLogTime (date) {
    function pad (n) { return ("0" + n).slice(-2); }
    return [date.getHours(), pad(date.getMinutes()), pad(date.getSeconds())].join(":");
  }
  function levelToIcon (level) {
    if (level === "status") return "circle";
    if (level === "warning") return "exclamation-triangle";
    if (level === "error") return "exclamation-circle";
    return "info-circle";
  }
  function levelToIconColour (level) {
    if (level === "status") return "#0D7C38";
    if (level === "warning") return "#FFC200";
    if (level === "error") return "#CB0909";
    return "#526E9C";
  }



  // Toolbox actions

  function toolboxPopulate () {
    // Iterate over each category.
    var toolbox = $('#toolbox');

    function filterChildNodesByTag (node, name) {
      return node.childNodes.array().filter(function (node) {
        return node.tagName && node.tagName.toLowerCase() == name;
      });
    }

    $('#toolbox-categories > category').each(function () {
      var node = $(this);
      var custom = node.attr('custom');
      var blocks = custom ? custom : node.children('block');

      $("<li><i></i>" + node.attr('name') + "</li>")
        .data('blocks', blocks)
        .find('i').addClass('fa fa-' + (node.attr('icon') || 'cog'))
        .end().appendTo(toolbox);
    });
  }

  $('#toolbox').on('mousedown', 'li', function () {
    var item = $(this);
    var activate = !item.is('.active');

    $('#toolbox .active').removeClass('active');
    Blockly.hideToolbox();

    if (activate) {
      item.addClass('active');
      Blockly.showToolbox(item.data('blocks'));
    }
  });

  Blockly.addEventListener("hide-toolbox", function () {
    // If the toolbar is closed by Blockly (e.g. by clicking in the svg area)
    // deselect the menu item.
    $('#toolbox .active').removeClass('active');
  });


  // Toolbar actions

  $('#btn-run').click(function () {
    clearBlockStates();
    experimentAction("run");
  });

  $('#btn-pause').click(function () {
    experimentAction("pause");
  });

  $('#btn-resume').click(function () {
    experimentAction("resume");
  });

  $('#btn-stop').click(function (e) {
    experimentAction("stop");
  });

  $('#experiment-title').change(function () {
    changeTitle($(this).val());
  });

  $('#btn-upload').click(function () {
    var modal;
    if (!this._modal) {
      // Create an <input> element to select a file.
      modal = $('<div class="modal"><div class="modal-dialog"><div class="modal-content"></div></div></div>');
      modal.appendTo(document.body);

      modal.find('.modal-content')
        .append($('<div class="modal-header"><h4 class="modal-title">Select blocks file to insert</h4></div>'))
        .append($('<div class="modal-body"><input type="file"></div>'))
        .append($('<div class="modal-footer"><button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button><button type="button" class="btn btn-primary">Load</button></div>'));

      this._modal = modal;
      modal.modal();
    } else {
      modal = this._modal;
      modal.modal('show');
    }

    function insertXMLFragmentBlock (text) {
      var block, blockY, blockH, maxY = 0;
      var workspace = Blockly.getMainWorkspace();
      var topBlocks = workspace.getTopBlocks();

      for (var i = 0, m = topBlocks.length; i < m; i++) {
        block = topBlocks[i];
        blockY = block.getRelativeToSurfaceXY().y;
        blockH = block.svg_.svgGroup_.getBBox().height;
        maxY = Math.max(maxY, blockY + blockH + 10);
      }
      try {
        var dom = Blockly.xmlTextToDom(text);
        $(dom).children('block').each(function () {
          block = Blockly.Xml.domToBlock(workspace, this);
          block.moveTo(0, maxY);

          blockY = block.getRelativeToSurfaceXY().y;
          blockH = block.svg_.svgGroup_.getBBox().height;
          maxY = Math.max(maxY, blockY + blockH + 10);
        });
      } catch (e) {
        workspace.discardEmitTransaction();

        alert('The uploaded file did not contain a valid block tree.');
        console.log(e);
      }
    }

    $('button.btn-primary', modal).one('click', function () {
      file = $('input[type=file]', modal)[0].files[0];

      if (file) {
        var reader = new FileReader();
        reader.onloadend = function (e) {
          insertXMLFragmentBlock(e.target.result);
          modal.modal('hide');
        };
        reader.readAsText(file);
      } else {
        modal.modal('hide');
      }
    });
  });

  $('#btn-download').on('click', function () {
    var workspace = Blockly.getMainWorkspace();
    var xmlText = Blockly.exportWorkspaceToXml(workspace);

    // Create an <a> element to contain the download.
    var a = window.document.createElement('a');
    a.href = window.URL.createObjectURL(new Blob([xmlText], {type: 'text/xml'}));

    // Give the download an appropriate name.
    a.download =
      'experiment__' +
      $('#experiment-title').val().trim()
      .replace(/[^a-z0-9]/ig, '_') + '__' +
      (new Date().toJSON().substring(0, 19)
          .replace('T', '_').replace(/:/g, '-')
      ) + '.xml';

    // Append anchor to body.
    document.body.appendChild(a);
    a.click();

    // Remove anchor from body
    document.body.removeChild(a);
  });

  $('#btn-code').on('click', function () {
    var visible = $(this).toggleClass('active').is('.active');

    $('#editor').toggleClass('code', visible);

    if (visible) {
      updateCode();
    }

    Blockly.getMainWorkspace().render();
  });

  $('#btn-lock').on('click', function (e) {
    var workspace = Blockly.getMainWorkspace();
    var locked = $(this).toggleClass('active').is('.active');
    $('#editor').toggleClass('locked', locked);
    $('i', this)
      .toggleClass('fa-lock', locked)
      .toggleClass('fa-unlock', !locked);

    if (locked) {
      Blockly.hideChaff();
      workspace.getAllBlocks().forEach(function (block) {
        block.setEditable(false);
        block.setMovable(false);
      });
    } else {
      workspace.getAllBlocks().forEach(function (block) {
        block.setEditable(true);
        block.setMovable(true);
      });
    }
    workspace.render();
  });
});
