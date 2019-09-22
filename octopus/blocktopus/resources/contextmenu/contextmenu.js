
(function($) {

  'use strict';

  /* CONTEXTMENU CLASS DEFINITION
   * ============================ */

  /*
  items = [{text: 'Make It So',
   value: val,
   callback: Blockly.MakeItSo,
   enabled: true,
   selected: true,
   [children: [...]]
  }]

  callback receives value if set, or text if not.
  callback is not called if item callback is set.
  */
  var ContextMenu = function (items, callback, options) {
    this.$menu = generate(items, options);
    this.callback = callback;
  };

  var menuContainerSelector = "#menu-container";

  var generate = function (spec, options) {
    var a, row, item, menu = $(document.createElement('ul')).addClass('dropdown-menu').attr('role', 'menu');
    options = options || {};
    if (options.selectable) {
      menu.addClass("selectable");
    }
    for (var i = 0, len = spec.length; i < len; i++) {
      row = spec[i];
      item = $(document.createElement('li')).appendTo(menu);

      if (row.divider) {
        item.addClass("divider");
        continue;
      }

      a = $(document.createElement('a')).appendTo(item).attr('tabindex', -1).text(row.text);
      if (row.enabled === false) {
        item.addClass('disabled');
      }
      if (row.selected && options.selectable) {
        item.addClass('selected');
      }
      if (typeof row.value !== "undefined") {
        item.data('value', row.value);
      }
      if (typeof row.callback !== "undefined") {
        item.data('callback', row.callback);
      }
      if (row.children) {
        item.addClass('dropdown-submenu');
        item.append(generate(row.children, options));
      }
    }

    // Stops context menu being shown for drop-up menus.
    menu.on('contextmenu', function (e) {
      e.preventDefault();
      return false;
    });

    return menu;
  };

  ContextMenu.prototype = {

    constructor: ContextMenu
    ,showAtEvent: function (e) {
      this.show({x: e.clientX, y: e.clientY}, {width: 0, height: 0});
      e.preventDefault();
    }

    ,showForBox: function (point, size) {
      // Add some space under drop-up menus for shadow.
      point.y -= 5;
      size.height += 5;

      this.show(point, size);
    }

    ,show: function(point, size) {

      var $menu = this.$menu
        , evt
        , items = 'li:not(.divider)'
        , relatedTarget = { relatedTarget: this };

      $(menuContainerSelector).empty().append($menu);

      $menu.trigger(evt = $.Event('show.bs.context', relatedTarget));
      $menu.find('.dropdown-submenu-positioned').removeClass('dropdown-submenu-positioned');

      $menu.attr('style', '')
        .css(this.getPosition(point, size, $menu))
        .addClass('open')
        .on('click.context.data-api', items, $.proxy(this.onItem, this))
        .on('mouseover.context.data-api', items, $.proxy(this.layoutSubmenu, this))
        .trigger('shown.bs.context', relatedTarget);

      $(menuContainerSelector).addClass('open');

      // Delegating the `closemenu` only on the currently opened menu.
      // This prevents other opened menus from closing.
      var self = this;
      window.setTimeout(function () {
      $('html')
        .on('click.context.data-api', $menu.selector, $.proxy(self.closemenu, self));
      }, 1);

      return false;
    }

    ,layoutSubmenu: function (e) {
      var parent = $(e.currentTarget);
      if (!parent.is('.dropdown-submenu') || parent.is('.dropdown-submenu-positioned')) {
        return;
      }
      parent.removeClass("pull-left dropup");
      var child = parent.children('.dropdown-menu');
      var childOffset = child.offset();

      if (childOffset.left + child.outerWidth() > $(window).width() - 5) {
        parent.addClass("pull-left");
      }
      if (childOffset.top + child.outerHeight() > $(window).height() - 5) {
        parent.addClass("dropup");
      }
      parent.addClass('dropdown-submenu-positioned');
    }

    ,closemenu: function(e) {
      var $menu = this.$menu
        , evt
        , items = 'li:not(.divider)'
        , relatedTarget;

      relatedTarget = { relatedTarget: this };
      $menu.trigger(evt = $.Event('hide.bs.context', relatedTarget));

      $menu.removeClass('open')
        .off('click.context.data-api', items)
        .off('mouseover.context.data-api', items)
        .trigger('hidden.bs.context', relatedTarget);

      $('html')
        .off('click.context.data-api', $menu.selector);
      // Don't propagate click event so other currently
      // opened menus won't close.
      $(menuContainerSelector).removeClass('open').empty();

      return false;
    }

    ,onItem: function (e) {
      var target = $(e.currentTarget),
      callback = target.data('callback'),
      value = target.data('value');
      if (target.hasClass('disabled')) {
        e.stopPropagation();
        return;
      }
      if (callback) {
        callback(value);
      } else if (this.callback) {
        this.callback(typeof value === "undefined" ? target.children('a').text() : value);
      }
      e.stopPropagation();
      this.closemenu();
    }

    ,getPosition: function(point, size, $menu) {
      var position = { x: point.x, y: point.y + size.height }
        , boundsX = $(window).width()
        , boundsY = $(window).height()
        , menuWidth = $menu.outerWidth()
        , menuHeight = $menu.outerHeight()
        , tp = {"position":"absolute","z-index":9999}
        , Y, X, parentOffset;

      if (position.y + menuHeight > boundsY) {
        Y = {"top": point.y - menuHeight + $(window).scrollTop()};
      } else {
        Y = {"top": position.y + $(window).scrollTop()};
      }

      if ((position.x + menuWidth > boundsX) && ((position.x - menuWidth) > 0)) {
        X = {"left": position.x + size.width - menuWidth + $(window).scrollLeft()};
      } else {
        X = {"left": position.x + $(window).scrollLeft()};
      }

      // If context-menu's parent is positioned using absolute or relative positioning,
      // the calculated mouse position will be incorrect.
      // Adjust the position of the menu by its offset parent position.
      parentOffset = $menu.offsetParent().offset();
      X.left = X.left - parentOffset.left;
      Y.top = Y.top - parentOffset.top;

      return $.extend(tp, Y, X);
    }

  };

  window.ContextMenu = ContextMenu;

}(jQuery));
