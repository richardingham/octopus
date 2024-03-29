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
 * @fileoverview Flyout tray containing blocks which may be created.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Block from './block';
import BlockSvg from './block_svg';
import Workspace from './workspace';
import {Scrollbar} from './scrollbar';
import Procedures from './procedures';
import Xml from './xml';

import {bindEvent_, unbindEvent_, addClass_, removeClass_, getSvgXY_, isRightButton, fireUiEvent, fireUiEventNow, createSvgElement} from './utils';
import {VARIABLES_NAME_TYPE, PROCEDURES_NAME_TYPE} from '../constants';

//var Variables = Blockly.Variables;

/**
 * Class for a flyout.
 * @constructor
 */
export default function Flyout () {
  var flyout = this;
  /**
   * @type {!Workspace}
   * @private
   */
  this.workspace_ = new Workspace(
    function () { return flyout.getMetrics_(); },
    function (ratio) { return flyout.setMetrics_(ratio); }
  );
  this.workspace_.isFlyout = true;

  /**
   * Opaque data that can be passed to removeChangeListener.
   * @type {Array.<!Array>}
   * @private
   */
  this.eventWrappers_ = [];

  /**
   * @type {number}
   * @private
   */
  this.width_ = 0;

  /**
   * @type {number}
   * @private
   */
  this.height_ = 0;

  /**
   * List of background buttons that lurk behind each block to catch clicks
   * landing in the blocks' lakes and bays.
   * @type {!Array.<!Element>}
   * @private
   */
  this.buttons_ = [];

  /**
   * List of event listeners.
   * @type {!Array.<!Array>}
   * @private
   */
  this.listeners_ = [];
};

/**
 * Does the flyout automatically close when a block is created?
 * @type {boolean}
 */
Flyout.prototype.autoClose = true;

/**
 * Corner radius of the flyout background.
 * @type {number}
 * @const
 */
Flyout.prototype.CORNER_RADIUS = 8;


/**
 * Creates the flyout's DOM.  Only needs to be called once.
 * @return {!Element} The flyout's SVG group.
 */
Flyout.prototype.createDom = function() {
  /*
  <g>
    <path class="blocklyFlyoutBackground"/>
    <g></g>
  </g>
  */
  this.svgGroup_ = createSvgElement('g', {}, null);
  this.svgBackground_ = createSvgElement('path',
      {'class': 'blocklyFlyoutBackground'}, this.svgGroup_);
  this.svgGroup_.appendChild(this.workspace_.createDom());
  return this.svgGroup_;
};

/**
 * Dispose of this flyout.
 * Unlink from all DOM elements to prevent memory leaks.
 */
Flyout.prototype.dispose = function() {
  this.hide();
  unbindEvent_(this.eventWrappers_);
  this.eventWrappers_.length = 0;
  if (this.scrollbar_) {
    this.scrollbar_.dispose();
    this.scrollbar_ = null;
  }
  this.workspace_ = null;
  if (this.svgGroup_) {
    var node = this.svgGroup_;
    if (node && node.parentNode) node.parentNode.removeChild(node);
    this.svgGroup_ = null;
  }
  this.svgBackground_ = null;
  this.targetWorkspace_ = null;
};

/**
 * Return an object with all the metrics required to size scrollbars for the
 * flyout.  The following properties are computed:
 * .viewHeight: Height of the visible rectangle,
 * .viewWidth: Width of the visible rectangle,
 * .contentHeight: Height of the contents,
 * .viewTop: Offset of top edge of visible rectangle from parent,
 * .contentTop: Offset of the top-most content from the y=0 coordinate,
 * .absoluteTop: Top-edge of view.
 * .absoluteLeft: Left-edge of view.
 * @return {Object} Contains size and position metrics of the flyout.
 * @private
 */
Flyout.prototype.getMetrics_ = function() {
  if (!this.isVisible()) {
    // Flyout is hidden.
    return null;
  }
  var viewHeight = this.height_ - 2 * this.CORNER_RADIUS;
  var viewWidth = this.width_;
  try {
    var optionBox = this.workspace_.getCanvas().getBBox();
  } catch (e) {
    // Firefox has trouble with hidden elements (Bug 528969).
    var optionBox = {height: 0, y: 0};
  }
  return {
    viewHeight: viewHeight,
    viewWidth: viewWidth,
    contentHeight: optionBox.height + optionBox.y,
    viewTop: -this.workspace_.scrollY,
    contentTop: 0,
    absoluteTop: this.CORNER_RADIUS,
    absoluteLeft: 0
  };
};

/**
 * Sets the Y translation of the flyout to match the scrollbars.
 * @param {!Object} yRatio Contains a y property which is a float
 *     between 0 and 1 specifying the degree of scrolling.
 * @private
 */
Flyout.prototype.setMetrics_ = function(yRatio) {
  var metrics = this.getMetrics_();
  // This is a fix to an apparent race condition.
  if (!metrics) {
    return;
  }
  if (typeof yRatio.y === 'number') {
    this.workspace_.scrollY =
        -metrics.contentHeight * yRatio.y - metrics.contentTop;
  }
  var y = this.workspace_.scrollY + metrics.absoluteTop;
  this.workspace_.getCanvas().setAttribute('transform',
                                           'translate(0,' + y + ')');
};

/**
 * Initializes the flyout.
 * @param {!Workspace} workspace The workspace in which to create new
 *     blocks.
 */
Flyout.prototype.init = function(workspace) {
  this.targetWorkspace_ = workspace;
  // Add scrollbar.
  this.scrollbar_ = new Scrollbar(this.workspace_, false, false);

  this.hide();

  // If the document resizes, reposition the flyout.
  this.eventWrappers_.concat(bindEvent_(window,
      "resize", this, this.position_));
  this.position_();
  this.eventWrappers_.concat(bindEvent_(this.svgGroup_,
      'wheel', this, this.wheel_));
  // Safari needs mousewheel.
  this.eventWrappers_.concat(bindEvent_(this.svgGroup_,
      'mousewheel', this, this.wheel_));
  this.eventWrappers_.concat(
      bindEvent_(this.targetWorkspace_.getCanvas(),
      'blocklyWorkspaceChange', this, this.filterForCapacity_));
  // Dragging the flyout up and down.
  this.eventWrappers_.concat(bindEvent_(this.svgGroup_,
      'mousedown', this, this.onMouseDown_));
};

/**
 * Move the toolbox to the edge of the workspace.
 * @private
 */
Flyout.prototype.position_ = function() {
  if (!this.isVisible()) {
    return;
  }
  var metrics = this.targetWorkspace_.getMetrics();
  if (!metrics) {
    // Hidden components will return null.
    return;
  }
  var edgeWidth = this.width_ - this.CORNER_RADIUS;
  if (Blockly.RTL) {
    edgeWidth *= -1;
  }
  var path = ['M ' + (Blockly.RTL ? this.width_ : 0) + ',0'];
  path.push('h', edgeWidth);
  path.push('a', this.CORNER_RADIUS, this.CORNER_RADIUS, 0, 0,
      Blockly.RTL ? 0 : 1,
      Blockly.RTL ? -this.CORNER_RADIUS : this.CORNER_RADIUS,
      this.CORNER_RADIUS);
  path.push('v', Math.max(0, metrics.viewHeight - this.CORNER_RADIUS * 2));
  path.push('a', this.CORNER_RADIUS, this.CORNER_RADIUS, 0, 0,
      Blockly.RTL ? 0 : 1,
      Blockly.RTL ? this.CORNER_RADIUS : -this.CORNER_RADIUS,
      this.CORNER_RADIUS);
  path.push('h', -edgeWidth);
  path.push('z');
  this.svgBackground_.setAttribute('d', path.join(' '));

  var x = metrics.absoluteLeft;
  if (Blockly.RTL) {
    x += metrics.viewWidth;
    x -= this.width_;
  }
  this.svgGroup_.setAttribute('transform',
      'translate(' + x + ',' + metrics.absoluteTop + ')');

  // Record the height for Flyout.getMetrics_.
  this.height_ = metrics.viewHeight;

  // Update the scrollbar (if one exists).
  if (this.scrollbar_) {
    this.scrollbar_.resize();
  }
};

/**
 * Scroll the flyout up or down.
 * @param {!Event} e Mouse wheel scroll event.
 * @private
 */
Flyout.prototype.wheel_ = function(e) {
  // Safari uses wheelDeltaY, everyone else uses deltaY.
  var delta = e.deltaY || -e.wheelDeltaY;
  if (delta) {
    // TODO
    /*if (goog.userAgent.GECKO) {
      // Firefox's deltas are a tenth that of Chrome/Safari.
      delta *= 10;
    }*/
    var metrics = this.getMetrics_();
    var y = metrics.viewTop + delta;
    y = Math.min(y, metrics.contentHeight - metrics.viewHeight);
    y = Math.max(y, 0);
    this.scrollbar_.set(y);
    // Don't scroll the page.
    e.preventDefault();
  }
};

/**
 * Is the flyout visible?
 * @return {boolean} True if visible.
 */
Flyout.prototype.isVisible = function() {
  return this.svgGroup_ && this.svgGroup_.style.display == 'block';
};

/**
 * Hide and empty the flyout.
 */
Flyout.prototype.hide = function() {
  if (!this.isVisible()) {
    return;
  }
  this.svgGroup_.style.display = 'none';
  // Delete all the event listeners.
  for (var x = 0, listen; listen = this.listeners_[x]; x++) {
    unbindEvent_(listen);
  }
  this.listeners_.length = 0;
  if (this.reflowWrapper_) {
    unbindEvent_(this.reflowWrapper_);
    this.reflowWrapper_ = null;
  }
  // Do NOT delete the blocks here.  Wait until Flyout.show.
  // https://neil.fraser.name/news/2014/08/09/
};

/**
 * Show and populate the flyout.
 * @param {!Array|string} xmlList List of blocks to show.
 *     Variables and procedures have a custom set of blocks.
 */
Flyout.prototype.show = function(xmlList) {
  this.hide();
  // Delete any blocks from a previous showing.
  var blocks = this.workspace_.getTopBlocks(false);
  for (var x = 0, block; block = blocks[x]; x++) {
    if (block.workspace == this.workspace_) {
      block.dispose(false, false);
    }
  }
  // Delete any background buttons from a previous showing.
  for (var x = 0, rect; rect = this.buttons_[x]; x++) {
    if (rect && rect.parentNode) rect.parentNode.removeChild(rect);
  }
  this.buttons_.length = 0;

  var margin = this.CORNER_RADIUS;
  this.svgGroup_.style.display = 'block';

  // Create the blocks to be shown in this flyout.
  var blocks = [];
  var gaps = [];
  //if (xmlList == VARIABLES_NAME_TYPE) {
    // Special category for variables.
    //Variables.flyoutCategory(blocks, gaps, margin,
    //    /** @type {!Workspace} */ (this.workspace_));
  //} else
  if (xmlList == PROCEDURES_NAME_TYPE) {
    // Special category for procedures.
    Procedures.flyoutCategory(blocks, gaps, margin,
        /** @type {!Workspace} */ (this.workspace_));
  } else {
    for (var i = 0, xml; xml = xmlList[i]; i++) {
      if (xml.tagName && xml.tagName.toUpperCase() == 'BLOCK') {
        var block = Xml.domToBlock(
            /** @type {!Workspace} */ (this.workspace_), xml);
        blocks.push(block);
        gaps.push(margin * 3);
      }
    }
  }

  // Lay out the blocks vertically.
  var cursorY = margin;
  for (var i = 0, block; block = blocks[i]; i++) {
    var allBlocks = block.getDescendants();
    for (var j = 0, child; child = allBlocks[j]; j++) {
      // Mark blocks as being inside a flyout.  This is used to detect and
      // prevent the closure of the flyout if the user right-clicks on such a
      // block.
      child.isInFlyout = true;
      // There is no good way to handle comment bubbles inside the flyout.
      // Blocks shouldn't come with predefined comments, but someone will
      // try this, I'm sure.  Kill the comment.
      child.setCommentText(null);
    }
    block.render();
    var root = block.getSvgRoot();
    var blockHW = block.getHeightWidth();
    var x = Blockly.RTL ? 0 : margin + BlockSvg.TAB_WIDTH;
    block.moveBy(x, cursorY);
    cursorY += blockHW.height + gaps[i];

    // Create an invisible rectangle under the block to act as a button.  Just
    // using the block as a button is poor, since blocks have holes in them.
    var rect = createSvgElement('rect', {'fill-opacity': 0}, null);
    // Add the rectangles under the blocks, so that the blocks' tooltips work.
    this.workspace_.getCanvas().insertBefore(rect, block.getSvgRoot());
    block.flyoutRect_ = rect;
    this.buttons_[i] = rect;

    if (this.autoClose) {
      this.listeners_.push(bindEvent_(root, 'mousedown', null,
          this.createBlockFunc_(block)));
    } else {
      this.listeners_.push(bindEvent_(root, 'mousedown', null,
          this.blockMouseDown_(block)));
    }
    this.listeners_.push(bindEvent_(root, 'mouseover', block.svg_,
        block.svg_.addSelect));
    this.listeners_.push(bindEvent_(root, 'mouseout', block.svg_,
        block.svg_.removeSelect));
    this.listeners_.push(bindEvent_(rect, 'mousedown', null,
        this.createBlockFunc_(block)));
    this.listeners_.push(bindEvent_(rect, 'mouseover', block.svg_,
        block.svg_.addSelect));
    this.listeners_.push(bindEvent_(rect, 'mouseout', block.svg_,
        block.svg_.removeSelect));
  }

  // IE 11 is an incompetant browser that fails to fire mouseout events.
  // When the mouse is over the background, deselect all blocks.
  var deselectAll = function(e) {
    var blocks = this.workspace_.getTopBlocks(false);
    for (var i = 0, block; block = blocks[i]; i++) {
      block.svg_.removeSelect();
    }
  };
  this.listeners_.push(bindEvent_(this.svgBackground_, 'mouseover',
      this, deselectAll));

  this.width_ = 0;
  this.reflow();

  this.filterForCapacity_();

  // Fire a resize event to update the flyout's scrollbar.
  fireUiEventNow(window, 'resize');
  this.reflowWrapper_ = bindEvent_(this.workspace_.getCanvas(),
      'blocklyWorkspaceChange', this, this.reflow);
  this.workspace_.fireChangeEvent();
};

/**
 * Compute width of flyout.  Position button under each block.
 * For RTL: Lay out the blocks right-aligned.
 */
Flyout.prototype.reflow = function() {
  var flyoutWidth = 0;
  var margin = this.CORNER_RADIUS;
  var blocks = this.workspace_.getTopBlocks(false);
  for (var x = 0, block; block = blocks[x]; x++) {
    var root = block.getSvgRoot();
    var blockHW = block.getHeightWidth();
    flyoutWidth = Math.max(flyoutWidth, blockHW.width);
  }
  flyoutWidth += margin + BlockSvg.TAB_WIDTH + margin / 2 +
                 Scrollbar.scrollbarThickness;
  if (this.width_ != flyoutWidth) {
    for (var x = 0, block; block = blocks[x]; x++) {
      var blockHW = block.getHeightWidth();
      var blockXY = block.getRelativeToSurfaceXY();
      if (Blockly.RTL) {
        // With the flyoutWidth known, right-align the blocks.
        var dx = flyoutWidth - margin - BlockSvg.TAB_WIDTH - blockXY.x;
        block.moveBy(dx, 0);
        blockXY.x += dx;
      }
      if (block.flyoutRect_) {
        block.flyoutRect_.setAttribute('width', blockHW.width);
        block.flyoutRect_.setAttribute('height', blockHW.height);
        block.flyoutRect_.setAttribute('x',
            Blockly.RTL ? blockXY.x - blockHW.width : blockXY.x);
        block.flyoutRect_.setAttribute('y', blockXY.y);
      }
    }
    // Record the width for .getMetrics_ and .position_.
    this.width_ = flyoutWidth;
    // Fire a resize event to update the flyout's scrollbar.
    fireUiEvent(window, 'resize');
  }
};

/**
 * Move a block to a specific location on the drawing surface.
 * @param {number} x Horizontal location.
 * @param {number} y Vertical location.
 */
/*Block.prototype.moveTo = function(x, y) {
  var oldXY = this.getRelativeToSurfaceXY();
  this.svg_.getRootElement().setAttribute('transform',
      'translate(' + x + ', ' + y + ')');
  this.moveConnections_(x - oldXY.x, y - oldXY.y);
};*/

/**
 * Handle a mouse-down on an SVG block in a non-closing flyout.
 * @param {!Block} block The flyout block to copy.
 * @return {!Function} Function to call when block is clicked.
 * @private
 */
Flyout.prototype.blockMouseDown_ = function(block) {
  var flyout = this;
  return function(e) {
    Blockly.terminateDrag_();
    Blockly.hideChaff();
    if (isRightButton(e)) {
      // Right-click.
      block.showContextMenu_(e);
    } else {
      // Left-click (or middle click)
      Blockly.removeAllRanges();
      Blockly.setCursorHand_(true);
      // Record the current mouse position.
      Flyout.startDownEvent_ = e;
      Flyout.startBlock_ = block;
      Flyout.startFlyout_ = flyout;
      Flyout.onMouseUpWrapper_ = bindEvent_(document,
          'mouseup', this, Blockly.terminateDrag_);
      Flyout.onMouseMoveBlockWrapper_ = bindEvent_(document,
          'mousemove', this, flyout.onMouseMoveBlock_);
    }
    // This event has been handled.  No need to bubble up to the document.
    e.stopPropagation();
  };
};

/**
 * Mouse down on the flyout background.  Start a vertical scroll drag.
 * @param {!Event} e Mouse down event.
 * @private
 */
Flyout.prototype.onMouseDown_ = function(e) {
  if (isRightButton(e)) {
    return;
  }
  Blockly.hideChaff(true);
  Flyout.terminateDrag_();
  this.startDragMouseY_ = e.clientY;
  Flyout.onMouseMoveWrapper_ = bindEvent_(document, 'mousemove',
      this, this.onMouseMove_);
  Flyout.onMouseUpWrapper_ = bindEvent_(document, 'mouseup',
      this, Flyout.terminateDrag_);
  // This event has been handled.  No need to bubble up to the document.
  e.preventDefault();
  e.stopPropagation();
};

/**
 * Handle a mouse-move to vertically drag the flyout.
 * @param {!Event} e Mouse move event.
 * @private
 */
Flyout.prototype.onMouseMove_ = function(e) {
  var dy = e.clientY - this.startDragMouseY_;
  this.startDragMouseY_ = e.clientY;
  var metrics = this.getMetrics_();
  var y = metrics.viewTop - dy;
  y = Math.min(y, metrics.contentHeight - metrics.viewHeight);
  y = Math.max(y, 0);
  this.scrollbar_.set(y);
};

/**
 * Mouse button is down on a block in a non-closing flyout.  Create the block
 * if the mouse moves beyond a small radius.  This allows one to play with
 * fields without instantiating blocks that instantly self-destruct.
 * @param {!Event} e Mouse move event.
 * @private
 */
Flyout.prototype.onMouseMoveBlock_ = function(e) {
  if (e.type == 'mousemove' && e.clientX <= 1 && e.clientY == 0 &&
      e.button == 0) {
    /* HACK:
     Safari Mobile 6.0 and Chrome for Android 18.0 fire rogue mousemove events
     on certain touch actions. Ignore events with these signatures.
     This may result in a one-pixel blind spot in other browsers,
     but this shouldn't be noticable. */
    e.stopPropagation();
    return;
  }
  Blockly.removeAllRanges();
  var dx = e.clientX - Flyout.startDownEvent_.clientX;
  var dy = e.clientY - Flyout.startDownEvent_.clientY;
  // Still dragging within the sticky DRAG_RADIUS.
  var dr = Math.sqrt(Math.pow(dx, 2) + Math.pow(dy, 2));
  if (dr > Blockly.DRAG_RADIUS) {
    // Create the block.
    Flyout.startFlyout_.createBlockFunc_(Flyout.startBlock_)(
        Flyout.startDownEvent_);
  }
};

/**
 * Create a copy of this block on the workspace.
 * @param {!Block} originBlock The flyout block to copy.
 * @return {!Function} Function to call when block is clicked.
 * @private
 */
Flyout.prototype.createBlockFunc_ = function(originBlock) {
  var flyout = this;
  return function(e) {
    if (isRightButton(e)) {
      // Right-click.  Don't create a block, let the context menu show.
      return;
    }
    if (originBlock.disabled) {
      // Beyond capacity.
      return;
    }
    // Create the new block by cloning the block in the flyout (via XML).
    var xml = Xml.blockToDom_(originBlock);
    var block = Xml.domToBlock(flyout.targetWorkspace_, xml);
    // Place it in the same spot as the flyout copy.
    var svgRootOld = originBlock.getSvgRoot();
    if (!svgRootOld) {
      throw 'originBlock is not rendered.';
    }
    var xyOld = getSvgXY_(svgRootOld);
    var svgRootNew = block.getSvgRoot();
    if (!svgRootNew) {
      throw 'block is not rendered.';
    }
    var xyNew = getSvgXY_(svgRootNew);
    block.moveBy(xyOld.x - xyNew.x, xyOld.y - xyNew.y);
    if (flyout.autoClose) {
      flyout.hide();
    } else {
      flyout.filterForCapacity_();
    }
    // Start a dragging operation on the new block.
    block.onMouseDown_(e);
    // Make sure the position is reported.
    Block.dragMode_ = 2;
  };
};

/**
 * Filter the blocks on the flyout to disable the ones that are above the
 * capacity limit.
 * @private
 */
Flyout.prototype.filterForCapacity_ = function() {
  var remainingCapacity = this.targetWorkspace_.remainingCapacity();
  var blocks = this.workspace_.getTopBlocks(false);
  for (var i = 0, block; block = blocks[i]; i++) {
    var allBlocks = block.getDescendants();
    var disabled = allBlocks.length > remainingCapacity;
    block.setDisabled(disabled);
  }
};

/**
 * Stop binding to the global mouseup and mousemove events.
 * @private
 */
Flyout.terminateDrag_ = function() {
  if (Flyout.onMouseUpWrapper_) {
    unbindEvent_(Flyout.onMouseUpWrapper_);
    Flyout.onMouseUpWrapper_ = null;
  }
  if (Flyout.onMouseMoveBlockWrapper_) {
    unbindEvent_(Flyout.onMouseMoveBlockWrapper_);
    Flyout.onMouseMoveBlockWrapper_ = null;
  }
  if (Flyout.onMouseMoveWrapper_) {
    unbindEvent_(Flyout.onMouseMoveWrapper_);
    Flyout.onMouseMoveWrapper_ = null;
  }
  if (Flyout.onMouseUpWrapper_) {
    unbindEvent_(Flyout.onMouseUpWrapper_);
    Flyout.onMouseUpWrapper_ = null;
  }
  Flyout.startDownEvent_ = null;
  Flyout.startBlock_ = null;
  Flyout.startFlyout_ = null;
};
