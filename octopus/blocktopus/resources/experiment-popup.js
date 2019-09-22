
(function ($, context, undefined) {

function Popup (element, options) {
  this.element = $(element);
  this.options = options;
}

Popup.prototype = {
  _events: [],
  _secondaryEvents: [],
  _applyEvents: function(evs){
    for (var i = 0, el, ch, ev; i < evs.length; i++){
      el = evs[i][0];
      if (evs[i].length === 2){
        ch = undefined;
        ev = evs[i][1];
      }
      else if (evs[i].length === 3){
        ch = evs[i][1];
        ev = evs[i][2];
      }
      el.on(ev, ch);
    }
  },
  _unapplyEvents: function(evs){
    for (var i = 0, el, ev, ch; i < evs.length; i++){
      el = evs[i][0];
      if (evs[i].length === 2){
        ch = undefined;
        ev = evs[i][1];
      }
      else if (evs[i].length === 3){
        ch = evs[i][1];
        ev = evs[i][2];
      }
      el.off(ev, ch);
    }
  },
  _buildEvents: function () {
    this._secondaryEvents = [
        [this.popup, {
          click: $.proxy(this.click, this)
        }],
        [$(window), {
          resize: $.proxy(this.place, this)
        }],
        [$(document), {
          mousedown: $.proxy(function(e){
            // Clicked outside the datepicker, hide it
            if (!(
              this.popup.is(e.target) ||
              this.popup.find(e.target).length
            )){
              this.hide();
            }
          }, this)
        }]
      ];
  },
  _attachSecondaryEvents: function(){
    this._detachSecondaryEvents();
    this._applyEvents(this._secondaryEvents);
  },
  _detachSecondaryEvents: function(){
    this._unapplyEvents(this._secondaryEvents);
  },
  build: function () {
    return $('<div>');
  },
  show: function () {
    var input, popup = $('<div>', {
      addClass: 'dropdown-menu bubble-dropdown',
      css: { display: 'none' }
    }).appendTo(document.body);

    popup.append(this.build());

    this.popup = popup;
    this.place();

    this._buildEvents();
    this._attachSecondaryEvents();
    this.popup.show();
  },
  hide: function () {
    this._detachSecondaryEvents();
    this.popup.remove();
  },
  place: function  () {
    var popupWidth = this.popup.outerWidth(),
        popupHeight = this.popup.outerHeight(),
        visualPadding = 10,
        windowWidth = $(document.body).width(),
        windowHeight = $(document.body).height(),
        scrollTop = $(document.body).scrollTop(),
        appendOffset = $(document.body).offset();

    var parentsZindex = [];
    this.element.parents().each(function(){
      var itemZIndex = $(this).css('z-index');
      if (itemZIndex !== 'auto' && itemZIndex !== 0) parentsZindex.push(parseInt(itemZIndex));
    });
    var zIndex = Math.max.apply(Math, parentsZindex) + 10;
    var offset = this.element.offset();
    var height = this.element.outerHeight(false);
    var width = this.element.outerWidth(false);
    var left = offset.left - appendOffset.left,
        top = offset.top - appendOffset.top;

    this.popup.removeClass(
      'bubble-orient-top bubble-orient-bottom '+
      'bubble-orient-right bubble-orient-left'
    );

    // auto x orientation is best-placement: if it crosses a window
    // edge, fudge it sideways
    if (offset.left < 0) {
      // component is outside the window on the left side. Move it into visible range
      this.popup.addClass('bubble-orient-left');
      left -= offset.left - visualPadding;
    } else if (left + popupWidth > windowWidth) {
      // the popup passes the widow right edge. Align it to component right side
      this.popup.addClass('bubble-orient-right');
      left = offset.left + width - popupWidth;
    } else {
      // Default to left
      this.popup.addClass('bubble-orient-left');
    }

    // auto y orientation is best-situation: top or bottom, no fudging,
    // decision based on which shows more of the popup
    var yorient, top_overflow, bottom_overflow;
    top_overflow = -scrollTop + top - popupHeight;
    bottom_overflow = scrollTop + windowHeight - (top + height + popupHeight);
    if (Math.max(top_overflow, bottom_overflow) === bottom_overflow)
      yorient = 'top';
    else
      yorient = 'bottom';

      this.popup.addClass('bubble-orient-' + yorient);
    if (yorient === 'top')
      top += height;
    else
      top -= popupHeight + parseInt(this.popup.css('padding-top'));

    /*if (this.o.rtl) {
      var right = windowWidth - (left + width);
      this.popup.css({
        top: top,
        right: right,
        zIndex: zIndex
      });
    } else {*/
    this.popup.css({
        top: top,
        left: left,
        zIndex: zIndex
      });
    //}
  }
};

function PropertyEditor (element, variable, options) {
  Popup.call(this, element, options);
  this.variable = variable;
}
PropertyEditor.prototype = new Popup();
PropertyEditor.prototype.build = function () {
  var container = $('<div>', { addClass: 'property-editor' });
  var formRow = $('<div>', { addClass: 'form-inline form-item' }).appendTo(container);
  var inputGroup = $('<div>', { addClass: 'form-group' }).appendTo(formRow);
  var buttonGroup = $('<div>', { addClass: 'form-group' }).appendTo(formRow);

  if (this.variable.options) {
    input = $('<select>').addClass('form-control input-sm').appendTo(inputGroup);
    $(this.variable.options).each(function() {
     input.append($("<option>", {
       text: this,
       value: this,
       selected: (variable.value == this)
     }));
    });
  } else if (this.variable.type == 'int' || this.variable.type == 'float') {
    input = $('<input>', {
      type: 'text',
      addClass: 'form-control input-sm',
      css: { 'width': '150px' },
      value: this.variable.value
    }).appendTo(inputGroup);
    if (this.variable.unit) {
      input.after(this.variable.unit);
    }
  } else if (this.variable.type == 'str') {
    input = $('<input>', {
      type: 'text',
      addClass: 'form-control input-sm',
      css: { 'width': '150px' },
      value: this.variable.value
    }).appendTo(inputGroup);
  }

  input.css({ 'margin-right': '3px' });

  $('<button>', {
    type: 'button',
    text: 'Update',
    addClass: 'btn btn-sm btn-primary',
    click: $.proxy(function () {
      this.options.update([{
        variable: this.variable.key,
        value: input.val()
      }]);
      this.hide();
    }, this)
  }).appendTo(buttonGroup);

  return container;
};


function GraphOptions (element, graph, options) {
  Popup.call(this, element, options);
  this.graph = graph;
}
GraphOptions.prototype = new Popup();
GraphOptions.prototype.build = function () {
  var container = $('<div class="graph-options">');
  var graph = this.graph;
  var _this = this;

  if (this.options.window) {
    var window = graph.window() / 1000;
    var divisor = window % 3600 === 0 ? 3600 : window % 60 === 0 ? 60 : 1;

    $('<div>', { addClass: 'form-row form-item' })
      .append($('<label>', { text: 'Show:' }))
      .appendTo(container);

    var row = $('<div>', { addClass: 'form-row form-item form-inline' });
    var time = $('<input>', {
      addClass: 'form-control input-sm',
      css: { width: '30%', 'margin-right': '3px' },
      type: 'number',
      value: window / divisor
    }).appendTo(row);

    var unit = $('<select>', {
      addClass: 'form-control input-sm',
      css: { width: '40%', 'margin-right': '3px' }
    }).appendTo(row);
    $('<option>', { value: 1, selected: divisor === 1, text: 'Seconds' }).appendTo(unit);
    $('<option>', { value: 60, selected: divisor === 60, text: 'Minutes' }).appendTo(unit);
    $('<option>', { value: 3600, selected: divisor === 13600, text: 'Hours' }).appendTo(unit);

    row.append($('<button>', {
      type: 'button',
      text: 'Update',
      addClass: 'btn btn-primary btn-sm',
      click: function () {
        graph.window(
          Math.max(1, parseInt(time.val()) * parseInt(unit.val())) * 1000
        );
      }
    }));

    row.appendTo(container);

    container.append($('<div class="divider">'));
  }

  if (this.options.axisTime) {
    container.append($('<div class="form-item">').append($('<button>', {
      addClass: 'btn btn-sm',
      type: 'button',
      text: 'Show ' + (graph.axisTime() == 'relative' ? 'absolute' : 'relative') + ' time',
      click: function () {
        var newMode;
        if (graph.axisTime() == 'relative') {
          newMode = graph.axisTime('absolute');
        } else {
          newMode = graph.axisTime('relative');
        }
        $(this).text('Show ' + (newMode == 'relative' ? 'absolute' : 'relative') + ' time');
      }
    })));
    container.append($('<div class="divider">'));
  }

  _.each(graph.variables(), function (variable) {
    var row = $('<div class="variable">').data('variable-key', variable.key);
    row.append($('<i>').addClass('fa fa-times-circle'));
    row.append($('<span>').append(variable.name));
    row.appendTo(container);
  });

  container.on('click', 'div.variable', function () {
    graph.removeStream($(this).data('variable-key'));
    $(this).closest('div').remove();
    _this.place();

    if (graph.streams.length === 0) {
      container.append($('<div>', {
        addClass: 'message',
        text: 'No variables in chart.'
      }));
    }
  });

  if (graph.streams.length === 0) {
    container.append($('<div>', {
      addClass: 'message',
      text: 'No variables in chart.'
    }));
  }

  return container;
};

function GraphAddStream (element, graph, variables, options) {
  Popup.call(this, element, options);
  this.graph = graph;
  this.variables = variables;
}
GraphAddStream.prototype = new Popup();
GraphAddStream.prototype.build = function () {
  var container = $('<div class="graph-options">');
  var graph = this.graph;
  var _this = this;
  var unit = graph.unit();
  var addStream = this.options.addStream;
  var filteredVariables = unit === null ?
    this.variables :
    _.filter(this.variables, function (variable) {
      return unit == variable.unit && graph.streams.indexOf(variable.key) < 0;
    });

  _.each(filteredVariables, function (variable) {
    var row = $('<div class="variable">').data('variable', variable);
    row.append($('<i>').addClass('fa fa-plus-circle'));
    row.append(variable.name);
    row.appendTo(container);
  });

  container.on('click', 'div.variable', function () {
    var variable = $(this).data('variable');
    var ok = addStream(variable);
    if (ok) {
      $(this).closest('div').remove();
      _this.place();
    }

    if ($('.variable', container).length === 0) {
      container.append($('<div>', {
        addClass: 'message',
        text: 'No variables to add.'
      }));
    }
  });

  if (filteredVariables.length === 0) {
    container.append($('<div>', {
      addClass: 'message',
      text: 'No variables to add.'
    }));
  }

  return container;
};

context.PropertyEditor = PropertyEditor;
context.GraphOptions = GraphOptions;
context.GraphAddStream = GraphAddStream;

})(jQuery, window);
