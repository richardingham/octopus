/**
 * @license
 * Visual Blocks Editor
 *
 * Copyright 2011 Google Inc.
 * https://github.com/google/blockly
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @fileoverview Functionality for the right-click context menus.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Xml from './xml';
import WidgetDiv from './widgetdiv';

var Menu = {};
export default Menu;

/**
 * Which block is the context menu attached to?
 * @type {Blockly.Block}
 */
Menu.currentBlock = null;

/**
 * Construct the menu based on the list of options and show the menu.
 * @param {!Event} e Mouse event.
 * @param {!Array.<!Object>} options Array of menu options.
 */
Menu.show = function(e, options) {
  WidgetDiv.show(Menu, function () {
    if (this.menu) {
      this.menu.closemenu();
    }
  }.bind(this));

  if (!options.length) {
    Menu.hide();
    return;
  }

  this.menu = new ContextMenu(options);
  this.menu.showAtEvent(e);

  /* Here's what one option object looks like:
    {text: 'Make It So',
     enabled: true,
     callback: Blockly.MakeItSo}
  */

/* ???
  menu.setAllowAutoFocus(true);
  // 1ms delay is required for focusing on context menus because some other
  // mouse event is still waiting in the queue and clears focus.
  setTimeout(function() {menuDom.focus();}, 1);*/

  Menu.currentBlock = null;  // May be set by Blockly.Block.

};

/**
 * Hide the context menu.
 */
Menu.hide = function() {
  if (this.menu) {
    this.menu.closemenu();
  }
  this.menu = null;
  WidgetDiv.hideIfOwner(Menu);
  Menu.currentBlock = null;
};

/**
 * Create a callback function that creates and configures a block,
 *   then places the new block next to the original.
 * @param {!Blockly.Block} block Original block.
 * @param {!Element} xml XML representation of new block.
 * @return {!Function} Function that creates a block.
 */
Menu.callbackFactory = function(block, xml) {
  return function() {
    var newBlock = Xml.domToBlock(block.workspace, xml);
    // Move the new block next to the old block.
    var xy = block.getRelativeToSurfaceXY();
    if (Blockly.RTL) {
      xy.x -= Blockly.SNAP_RADIUS;
    } else {
      xy.x += Blockly.SNAP_RADIUS;
    }
    xy.y += Blockly.SNAP_RADIUS * 2;
    newBlock.moveBy(xy.x, xy.y);
    newBlock.select();
  };
};
