/**
 * @license
 * Visual Blocks Editor
 *
 * Copyright 2013 Google Inc.
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
 * @fileoverview Object representing an icon on a block.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import BlockSvg from './block_svg';
import {bindEvent_, unbindEvent_, addClass_, removeClass_, getRelativeXY_, createSvgElement} from './utils';

/**
 * Class for an icon.
 * @param {Block} block The block associated with this icon.
 * @constructor
 */
export default function Icon (block) {
  this.block_ = block;
};

/**
 * Radius of icons.
 */
Icon.RADIUS = 8;

/**
 * Bubble UI (if visible).
 * @type {Bubble}
 * @private
 */
Icon.prototype.bubble_ = null;

/**
 * Absolute X coordinate of icon's center.
 * @private
 */
Icon.prototype.iconX_ = 0;

/**
 * Absolute Y coordinate of icon's centre.
 * @private
 */
Icon.prototype.iconY_ = 0;

/**
 * Create the icon on the block.
 * @private
 */
Icon.prototype.createIcon_ = function() {
  /* Here's the markup that will be generated:
  <g class="blocklyIconGroup"></g>
  */
  this.iconGroup_ = createSvgElement('g', {}, null);
  this.block_.getSvgRoot().appendChild(this.iconGroup_);
  bindEvent_(this.iconGroup_, 'mouseup', this, this.iconClick_);
  this.updateEditable();
};

/**
 * Dispose of this icon.
 */
Icon.prototype.dispose = function() {
  // Dispose of and unlink the icon.
  var node = this.iconGroup_;
  if (node && node.parentNode) node.parentNode.removeChild(node);
  this.iconGroup_ = null;
  // Dispose of and unlink the bubble.
  this.setVisible(false);
  this.block_ = null;
};

/**
 * Add or remove the UI indicating if this icon may be clicked or not.
 */
Icon.prototype.updateEditable = function() {
  if (!this.block_.isInFlyout) {
    addClass_(/** @type {!Element} */ (this.iconGroup_),
                      'blocklyIconGroup');
  } else {
    removeClass_(/** @type {!Element} */ (this.iconGroup_),
                         'blocklyIconGroup');
  }
};

/**
 * Is the associated bubble visible?
 * @return {boolean} True if the bubble is visible.
 */
Icon.prototype.isVisible = function() {
  return !!this.bubble_;
};

/**
 * Clicking on the icon toggles if the bubble is visible.
 * @param {!Event} e Mouse click event.
 * @private
 */
Icon.prototype.iconClick_ = function(e) {
  if (!this.block_.isInFlyout) {
    this.setVisible(!this.isVisible());
  }
};

/**
 * Change the colour of the associated bubble to match its block.
 */
Icon.prototype.updateColour = function() {
  if (this.isVisible()) {
    var hexColour = Blockly.makeColour(this.block_.getColour());
    this.bubble_.setColour(hexColour);
  }
};

/**
 * Render the icon.
 * @param {number} cursorX Horizontal offset at which to position the icon.
 * @return {number} Horizontal offset for next item to draw.
 */
Icon.prototype.renderIcon = function(cursorX) {
  if (this.block_.isCollapsed()) {
    this.iconGroup_.setAttribute('display', 'none');
    return cursorX;
  }
  this.iconGroup_.setAttribute('display', 'block');

  var TOP_MARGIN = 5;
  var diameter = 2 * Icon.RADIUS;
  if (Blockly.RTL) {
    cursorX -= diameter;
  }
  this.iconGroup_.setAttribute('transform',
      'translate(' + cursorX + ', ' + TOP_MARGIN + ')');
  this.computeIconLocation();
  if (Blockly.RTL) {
    cursorX -= BlockSvg.SEP_SPACE_X;
  } else {
    cursorX += diameter + BlockSvg.SEP_SPACE_X;
  }
  return cursorX;
};

/**
 * Notification that the icon has moved.  Update the arrow accordingly.
 * @param {number} x Absolute horizontal location.
 * @param {number} y Absolute vertical location.
 */
Icon.prototype.setIconLocation = function(x, y) {
  this.iconX_ = x;
  this.iconY_ = y;
  if (this.isVisible()) {
    this.bubble_.setAnchorLocation(x, y);
  }
};

/**
 * Notification that the icon has moved, but we don't really know where.
 * Recompute the icon's location from scratch.
 */
Icon.prototype.computeIconLocation = function() {
  // Find coordinates for the centre of the icon and update the arrow.
  var blockXY = this.block_.getRelativeToSurfaceXY();
  var iconXY = getRelativeXY_(this.iconGroup_);
  var newX = blockXY.x + iconXY.x + Icon.RADIUS;
  var newY = blockXY.y + iconXY.y + Icon.RADIUS;
  if (newX !== this.iconX_ || newY !== this.iconY_) {
    this.setIconLocation(newX, newY);
  }
};

/**
 * Returns the center of the block's icon relative to the surface.
 * @return {!Object} Object with x and y properties.
 */
Icon.prototype.getIconLocation = function() {
  return {x: this.iconX_, y: this.iconY_};
};
