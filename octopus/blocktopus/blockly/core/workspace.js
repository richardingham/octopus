/**
 * @license
 * Visual Blocks Editor
 *
 * Copyright 2012 Google Inc.
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
 * @fileoverview Object representing a workspace.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import EventEmitter from 'events';
import Blockly from './blockly';
import Block from './block';
import {ConnectionDB} from './connection';
import {ScrollbarPair} from './scrollbar';
import Trashcan from './trashcan';
import Xml from './xml';
import {bindEvent_, unbindEvent_, fireUiEvent, createSvgElement} from './utils';

import {inherits} from './utils';

/**
 * Class for a workspace.
 * @param {Function} getMetrics A function that returns size/scrolling metrics.
 * @param {Function} setMetrics A function that sets size/scrolling metrics.
 * @constructor
 */
export default function Workspace (getMetrics, setMetrics) {
  this.getMetrics = getMetrics;
  this.setMetrics = setMetrics;

  /** @type {boolean} */
  this.isFlyout = false;

  /**
   * @type {!Array.<!Block>}
   * @private
   */
  this.topBlocks_ = [];

  /**
   * @type {!Array.<!Block>}
   * @private
   */
  this.allBlocks_ = [];

  /** @type {number} */
  this.maxBlocks = Infinity;

  this.emitTransaction_ = [];
  this.inEmitTransaction_ = 0;

  ConnectionDB.init(this);

  EventEmitter.call(this);
};
inherits(Workspace, EventEmitter);

/**
 * Angle away from the horizontal to sweep for blocks.  Order of execution is
 * generally top to bottom, but a small angle changes the scan to give a bit of
 * a left to right bias (reversed in RTL).  Units are in degrees.
 * See: http://tvtropes.org/pmwiki/pmwiki.php/Main/DiagonalBilling.
 */
Workspace.SCAN_ANGLE = 3;

/**
 * Can this workspace be dragged around (true) or is it fixed (false)?
 * @type {boolean}
 */
Workspace.prototype.dragMode = false;

/**
 * Current horizontal scrolling offset.
 * @type {number}
 */
Workspace.prototype.scrollX = 0;

/**
 * Current vertical scrolling offset.
 * @type {number}
 */
Workspace.prototype.scrollY = 0;

/**
 * The workspace's trashcan (if any).
 * @type {Trashcan}
 */
Workspace.prototype.trashcan = null;

/**
 * PID of upcoming firing of a change event.  Used to fire only one event
 * after multiple changes.
 * @type {?number}
 * @private
 */
Workspace.prototype.fireChangeEventPid_ = null;

/**
 * This workspace's scrollbars, if they exist.
 * @type {ScrollbarPair}
 */
Workspace.prototype.scrollbar = null;

/**
 * Create the trash can elements.
 * @return {!Element} The workspace's SVG group.
 */
Workspace.prototype.createDom = function() {
  /*
  <g>
    [Trashcan may go here]
    <g></g>
    <g></g>
  </g>
  */
  this.svgGroup_ = createSvgElement('g', {}, null);
  this.svgBlockCanvas_ = createSvgElement('g', {}, this.svgGroup_);
  this.svgBubbleCanvas_ = createSvgElement('g', {}, this.svgGroup_);
  this.fireChangeEvent();
  return this.svgGroup_;
};

/**
 * Dispose of this workspace.
 * Unlink from all DOM elements to prevent memory leaks.
 */
Workspace.prototype.dispose = function() {
  // Remove all elements
  this.clear();

  if (this.svgGroup_) {
    var node = this.svgGroup_;
    if (node && node.parentNode) node.parentNode.removeChild(node);
    this.svgGroup_ = null;
  }
  this.svgBlockCanvas_ = null;
  this.svgBubbleCanvas_ = null;
  if (this.trashcan) {
    this.trashcan.dispose();
    this.trashcan = null;
  }

  // Prevent any further change events trying to update deleted
  // svg element or workspace. This is required to prevent errors.
  if (this.fireChangeEventPid_) {
    window.clearTimeout(this.fireChangeEventPid_);
  }
};

/**
 * Add a trashcan.
 */
Workspace.prototype.addTrashcan = function() {
  if (Blockly.hasTrashcan && !Blockly.readOnly) {
    this.trashcan = new Trashcan(this);
    var svgTrashcan = this.trashcan.createDom();
    this.svgGroup_.insertBefore(svgTrashcan, this.svgBlockCanvas_);
    this.trashcan.init();
  }
};

/**
 * Get the SVG element that forms the drawing surface.
 * @return {!Element} SVG element.
 */
Workspace.prototype.getCanvas = function() {
  return this.svgBlockCanvas_;
};

/**
 * Get the SVG element that forms the bubble surface.
 * @return {!SVGGElement} SVG element.
 */
Workspace.prototype.getBubbleCanvas = function() {
  return this.svgBubbleCanvas_;
};

/**
 * Add a block to the list of blocks.
 * @param {!Block} block Block to add.
 */
Workspace.prototype.addBlock = function(block) {
  this.allBlocks_.push(block);
};

/**
 * Remove a block from the list of blocks.
 * @param {!Block} block Block to remove.
 */
Workspace.prototype.removeBlock = function(block) {
  var blocks = this.allBlocks_;
  for (var i = blocks.length - 1; i >= 0; i--) {
    if (blocks[i] === block) {
      blocks.splice(i, 1);
      break;
    }
  }
};

/**
 * Add a block to the list of top blocks.
 * @param {!Block} block Block to add.
 */
Workspace.prototype.addTopBlock = function(block) {
  this.topBlocks_.push(block);
  this.fireChangeEvent();
};

/**
 * Remove a block from the list of top blocks.
 * @param {!Block} block Block to remove.
 */
Workspace.prototype.removeTopBlock = function(block) {
  var found = false;
  for (var child, x = 0; child = this.topBlocks_[x]; x++) {
    if (child == block) {
      this.topBlocks_.splice(x, 1);
      found = true;
      break;
    }
  }
  if (!found) {
    throw 'Block not present in workspace\'s list of top-most blocks.';
  }

  this.fireChangeEvent();
};

/**
 * Finds the top-level blocks and returns them.  Blocks are optionally sorted
 * by position; top to bottom (with slight LTR or RTL bias).
 * @param {boolean} ordered Sort the list if true.
 * @return {!Array.<!Block>} The top-level block objects.
 */
Workspace.prototype.getTopBlocks = function(ordered) {
  // Copy the topBlocks_ list.
  var blocks = [].concat(this.topBlocks_);
  if (ordered && blocks.length > 1) {
    var offset = Math.sin(Workspace.SCAN_ANGLE / 180 * Math.PI);
    if (Blockly.RTL) {
      offset *= -1;
    }
    blocks.sort(function(a, b) {
      var aXY = a.getRelativeToSurfaceXY();
      var bXY = b.getRelativeToSurfaceXY();
      return (aXY.y + offset * aXY.x) - (bXY.y + offset * bXY.x);
    });
  }
  return blocks;
};

/**
 * Find all blocks in workspace.  No particular order.
 * @return {!Array.<!Block>} Array of blocks.
 */
Workspace.prototype.getAllBlocks = function() {
  var blocks = this.getTopBlocks(false);
  for (var x = 0; x < blocks.length; x++) {
    blocks.push.apply(blocks, blocks[x].getChildren());
  }
  return blocks;
};

/**
 * Dispose of all blocks in workspace.
 */
Workspace.prototype.clear = function() {
  Blockly.hideChaff();
  this.startEmitTransaction();
  while (this.topBlocks_.length) {
    this.topBlocks_[0].dispose();
  }
  this.completeEmitTransaction();
};

/**
 * Render all blocks in workspace.
 */
Workspace.prototype.render = function() {
  var renderList = this.getAllBlocks();
  for (var x = 0, block; block = renderList[x]; x++) {
    if (!block.getChildren().length) {
      block.render();
    }
  }
};

/**
 * Finds the block with the specified ID in this workspace.
 * @param {string} id ID of block to find.
 * @return {Block} The matching block, or null if not found.
 */
Workspace.prototype.getBlockById = function(id) {
  // If this O(n) function fails to scale well, maintain a hash table of IDs.
  var blocks = this.getAllBlocks();
  for (var x = 0, block; block = blocks[x]; x++) {
    if (block.id == id) {
      return block;
    }
  }
  return null;
};

/**
 * Turn the visual trace functionality on or off.
 * @param {boolean} armed True if the trace should be on.
 */
Workspace.prototype.traceOn = function(armed) {
  this.traceOn_ = armed;
  if (this.traceWrapper_) {
    unbindEvent_(this.traceWrapper_);
    this.traceWrapper_ = null;
  }
  if (armed) {
    this.traceWrapper_ = bindEvent_(this.svgBlockCanvas_,
        'blocklySelectChange', this, function() {this.traceOn_ = false});
  }
};

/**
 * Highlight a block in the workspace.
 * @param {?string} id ID of block to find.
 */
Workspace.prototype.highlightBlock = function(id) {
  if (this.traceOn_ && Block.dragMode_ != 0) {
    // The blocklySelectChange event normally prevents this, but sometimes
    // there is a race condition on fast-executing apps.
    this.traceOn(false);
  }
  if (!this.traceOn_) {
    return;
  }
  var block = null;
  if (id) {
    block = this.getBlockById(id);
    if (!block) {
      return;
    }
  }
  // Temporary turn off the listener for selection changes, so that we don't
  // trip the monitor for detecting user activity.
  this.traceOn(false);
  // Select the current block.
  if (block) {
    block.select();
  } else if (Blockly.selected) {
    Blockly.selected.unselect();
  }
  // Restore the monitor for user activity after the selection event has fired.
  var thisWorkspace = this;
  setTimeout(function() {thisWorkspace.traceOn(true);}, 1);
};

/**
 * Fire a change event for this workspace.  Changes include new block, dropdown
 * edits, mutations, connections, etc.  Groups of simultaneous changes (e.g.
 * a tree of blocks being deleted) are merged into one event.
 * Applications may hook workspace changes by listening for
 * 'blocklyWorkspaceChange' on Blockly.mainWorkspace.getCanvas().
 */
Workspace.prototype.fireChangeEvent = function() {
  if (this.fireChangeEventPid_) {
    window.clearTimeout(this.fireChangeEventPid_);
  }
  var canvas = this.svgBlockCanvas_;
  if (canvas) {
    this.fireChangeEventPid_ = window.setTimeout(function() {
        fireUiEvent(canvas, 'blocklyWorkspaceChange');
      }, 0);
  }
};

/**
 * Paste the provided block onto the workspace.
 * @param {!Element} xmlBlock XML block element.
 */
Workspace.prototype.paste = function(xmlBlock) {
  if (xmlBlock.getElementsByTagName('block').length >=
      this.remainingCapacity()) {
    return;
  }
  var block = Xml.domToBlock(this, xmlBlock);
  // Move the duplicate to original position.
  var blockX = parseInt(xmlBlock.getAttribute('x'), 10);
  var blockY = parseInt(xmlBlock.getAttribute('y'), 10);
  if (!isNaN(blockX) && !isNaN(blockY)) {
    if (Blockly.RTL) {
      blockX = -blockX;
    }
    // Offset block until not clobbering another block.
    do {
      var collide = false;
      var allBlocks = this.getAllBlocks();
      for (var x = 0, otherBlock; otherBlock = allBlocks[x]; x++) {
        var otherXY = otherBlock.getRelativeToSurfaceXY();
        if (Math.abs(blockX - otherXY.x) <= 1 &&
            Math.abs(blockY - otherXY.y) <= 1) {
          if (Blockly.RTL) {
            blockX -= Blockly.SNAP_RADIUS;
          } else {
            blockX += Blockly.SNAP_RADIUS;
          }
          blockY += Blockly.SNAP_RADIUS * 2;
          collide = true;
        }
      }
    } while (collide);
    block.moveBy(blockX, blockY);
  }
  block.select();
};

/**
 * The number of blocks that may be added to the workspace before reaching
 *     the maxBlocks.
 * @return {number} Number of blocks left.
 */
Workspace.prototype.remainingCapacity = function() {
  if (this.maxBlocks == Infinity) {
    return Infinity;
  }
  return this.maxBlocks - this.getAllBlocks().length;
};



Workspace.prototype.startEmitTransaction = function () {
  this.inEmitTransaction_++;
};
Workspace.prototype.completeEmitTransaction = function () {
  this.inEmitTransaction_--;
  if (this.inEmitTransaction_ === 0) {
    this.emit("block-transaction", { events: this.emitTransaction_ });
    this.emitTransaction_ = [];
  }
};
Workspace.prototype.discardEmitTransaction = function () {
  if (this.inEmitTransaction_ !== 1) {
    throw new Error("Cannot discard inner transaction");
  }
  this.inEmitTransaction_ = 0;
  this.emitTransaction_ = [];
};
var _emit = Workspace.prototype.emit;
Workspace.prototype.emit = function(event, data) {
  if (this.inEmitTransaction_ > 0) {
    this.emitTransaction_.push({ event: event, data: data });
  } else {
    _emit.call(this, event, data);
  }
};
