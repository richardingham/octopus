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
 * @fileoverview The class representing one block.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import EventEmitter from 'events';
import {inherits, _extend, assert} from './utils';

import Blockly from './blockly';
import Blocks from './blocks';
import BlockSvg from './block_svg';
import Xml from './xml';
import Field from './field';
import FieldLabel from './field_label';
import Comment from './comment';
import Warning from './warning';
import Input from './input';
import Mutator from './mutator';
import {VariableScope, GlobalScope} from './variables';
import {Connection} from './connection';
import ContextMenu from './contextmenu';
import {bindEvent_, unbindEvent_, removeClass_, addClass_, isRightButton, fireUiEvent, getRelativeXY_} from './utils';


/**
 * Unique ID counter for created blocks.
 * @private
 */
var uidCounter_ = 0;

/**
 * Update the uidCounter_
 * @param {number} val The min value to set the counter to.
 */
function updateUidCounter (val) {
  val = parseInt(val, 10) + 1;
  uidCounter_ = val > uidCounter_ ? val : uidCounter_;
};

/**
 * Generate a unique id.  This will be locally or globally unique, depending on
 * whether we are in single user or realtime collaborative mode.
 * @return {string}
 */
function genUid () {
  return (++uidCounter_).toString();
};

/**
* Class for one block.
* @constructor
*/
var Block = function () {
  // We assert this here because there may be users of the previous form of
  // this constructor, which took arguments.
  assert(arguments.length === 0, 'Please use Block.obtain.');

  EventEmitter.call(this);
};
inherits(Block, EventEmitter);
export default Block;

/**
 * Obtain a newly created block.
 * @param {!Workspace} workspace The block's workspace.
 * @param {?string} prototypeName Name of the language object containing
 *     type-specific functions for this block.
 * @return {!Block} The created block
 */
Block.obtain = function(workspace, prototypeName, id) {
  var newBlock = new Block();
  newBlock.initialize(workspace, prototypeName, id);
  return newBlock;
};

/**
 * Initialization for one block.
 * @param {!Workspace} workspace The new block's workspace.
 * @param {?string} prototypeName Name of the language object containing
 *     type-specific functions for this block.
 */
Block.prototype.initialize = function(workspace, prototypeName, id) {
  if (typeof id !== "undefined") {
    this.id = id;
    updateUidCounter(id);
  } else {
    this.id = genUid();
  }
  workspace.addTopBlock(this);
  this.fill(workspace, prototypeName);
  // Bind an onchange function, if it exists.
  if (typeof this.onchange === 'function') {
    bindEvent_(workspace.getCanvas(), 'blocklyWorkspaceChange', this,
        this.onchange);
  }
};

Block.prototype.workspaceEmit = function() {};

/**
 * Fill a block with initial values.
 * @param {!Workspace} workspace The workspace to use.
 * @param {string} prototypeName The typename of the block.
 */
Block.prototype.fill = function(workspace, prototypeName) {
  this.outputConnection = null;
  this.nextConnection = null;
  this.previousConnection = null;
  this.inputList = [];
  this.inputsInline = false;
  this.rendered = false;
  this.disabled = false;
  this.tooltip = '';
  this.contextMenu = true;

  this.parentBlock_ = null;
  this.childBlocks_ = [];
  this.deletable_ = true;
  this.movable_ = true;
  this.editable_ = true;
  this.collapsed_ = false;

  this.workspace = workspace;
  this.isInFlyout = workspace.isFlyout;

  self.runningState_ = "ready";

  // Copy the type-specific functions and data from the prototype.
  if (prototypeName) {
    this.type = prototypeName;
    var prototype = Blocks[prototypeName];
    assert(typeof prototype === 'object' && prototype !== null,
        'Error: "' + prototypeName + '" is an unknown language block.');
    _extend(this, prototype);
  }

  // Create a VariableScope object if necessary
  if (this.definesScope) {
    this.variableScope_ = new VariableScope(this);
  }

  // Call an initialization function, if it exists.
  if (typeof this.init === 'function') {
    this.init();
  }

  if (this.workspace) {
    this.workspace.addBlock(this);
  }

  var input, field, fields = {};
  for (var x = 0, max_x = this.inputList.length; x < max_x; x++) {
    input = this.inputList[x];
    for (var y = 0, max_y = input.fieldRow.length; y < max_y; y++) {
      field = input.fieldRow[y];
      if (field.name && field.EDITABLE) {
        fields[field.name] = field.getValue();
      }
    }
  }

  this.workspaceEmit = function(event, data) {
    if (this.workspace) {
      this.workspace.emit(event, data);
    }
  };
  this.workspaceEmit("block-created", { id: this.id, type: prototypeName, fields: fields });

  // Call the created() function if necessary
  if (typeof this.created === 'function') {
    this.created();
  }
};

/**
 * Set the block's running state.
 * @param {String} state One of "READY", "RUNNING", "PAUSED", "COMPLETE", "CANCELLED" or "ERROR"
 */
Block.prototype.setRunningState = function(state) {
  var oldState = this.runningState_;
  state = state.toLowerCase();
  this.runningState_ = state;

  removeClass_(this.svg_.svgGroup_, 'state-' + oldState);
  addClass_(this.svg_.svgGroup_, 'state-' + state);
};

/**
 * Get an existing block.
 * @param {string} id The block's id.
 * @param {!Workspace} workspace The block's workspace.
 * @return {Block} The found block, or null if not found.
 */
Block.getById = function(id, workspace) {
  return workspace.getBlockById(id);
};

/**
 * Pointer to SVG representation of the block.
 * @type {BlockSvg}
 * @private
 */
Block.prototype.svg_ = null;

/**
 * Block's mutator icon (if any).
 * @type {Mutator}
 */
Block.prototype.mutator = null;

/**
 * Block's comment icon (if any).
 * @type {Comment}
 */
Block.prototype.comment = null;

/**
 * Block's warning icon (if any).
 * @type {Warning}
 */
Block.prototype.warning = null;

/**
 * Returns a list of mutator, comment, and warning icons.
 * @return {!Array} List of icons.
 */
Block.prototype.getIcons = function() {
  var icons = [];
  if (this.mutator) {
    icons.push(this.mutator);
  }
  if (this.comment) {
    icons.push(this.comment);
  }
  if (this.warning) {
    icons.push(this.warning);
  }
  return icons;
};

/**
 * Create and initialize the SVG representation of the block.
 */
Block.prototype.initSvg = function() {
  this.svg_ = new BlockSvg(this);
  this.svg_.init();
  if (!Blockly.readOnly) {
    bindEvent_(this.svg_.getRootElement(), 'mousedown', this,
                       this.onMouseDown_);
  }
  this.workspace.getCanvas().appendChild(this.svg_.getRootElement());
};

/**
 * Return the root node of the SVG or null if none exists.
 * @return {Element} The root SVG node (probably a group).
 */
Block.prototype.getSvgRoot = function() {
  return this.svg_ && this.svg_.getRootElement();
};

/**
 * Is the mouse dragging a block?
 * 0 - No drag operation.
 * 1 - Still inside the sticky DRAG_RADIUS.
 * 2 - Freely draggable.
 * @private
 */
Block.dragMode_ = 0;

/**
 * Wrapper function called when a mouseUp occurs during a drag operation.
 * @type {Array.<!Array>}
 * @private
 */
Block.onMouseUpWrapper_ = null;

/**
 * Wrapper function called when a mouseMove occurs during a drag operation.
 * @type {Array.<!Array>}
 * @private
 */
Block.onMouseMoveWrapper_ = null;

/**
 * Stop binding to the global mouseup and mousemove events.
 * @private
 */
Block.terminateDrag_ = function() {
  if (Block.onMouseUpWrapper_) {
    unbindEvent_(Block.onMouseUpWrapper_);
    Block.onMouseUpWrapper_ = null;
  }
  if (Block.onMouseMoveWrapper_) {
    unbindEvent_(Block.onMouseMoveWrapper_);
    Block.onMouseMoveWrapper_ = null;
  }
  var selected = Blockly.selected;
  if (Block.dragMode_ == 2) {
    // Terminate a drag operation.
    if (selected) {
      // Update the connection locations.
      var xy = selected.getRelativeToSurfaceXY();
      var dx = xy.x - selected.startDragX;
      var dy = xy.y - selected.startDragY;
      selected.moveConnections_(dx, dy);
      delete selected.draggedBubbles_;
      selected.setDragging_(false);
      selected.render();
      selected.workspaceEmit("block-set-position", { id: selected.id, x: xy.x, y: xy.y, manual: true });
      window.setTimeout(
          selected.bumpNeighbours_.bind(selected), Blockly.BUMP_DELAY);
      // Fire an event to allow scrollbars to resize.
      fireUiEvent(window, 'resize');
    }
  }
  if (selected && selected.workspace) {
    selected.workspace.fireChangeEvent();
  }
  Block.dragMode_ = 0;
};

/**
 * Select this block.  Highlight it visually.
 */
Block.prototype.select = function() {
  assert(typeof this.svg_ === 'object' && this.svg_ !== null, 'Block is not rendered.');
  if (Blockly.selected) {
    // Unselect any previously selected block.
    Blockly.selected.unselect();
  }
  Blockly.selected = this;
  this.svg_.addSelect();
  fireUiEvent(this.workspace.getCanvas(), 'blocklySelectChange');
};

/**
 * Unselect this block.  Remove its highlighting.
 */
Block.prototype.unselect = function() {
  assert(typeof this.svg_ === 'object' && this.svg_ !== null, 'Block is not rendered.');
  Blockly.selected = null;
  this.svg_.removeSelect();
  fireUiEvent(this.workspace.getCanvas(), 'blocklySelectChange');
};

/**
 * Dispose of this block.
 * @param {boolean} healStack If true, then try to heal any gap by connecting
 *     the next statement with the previous statement.  Otherwise, dispose of
 *     all children of this block.
 * @param {boolean} animate If true, show a disposal animation and sound.
 * @param {boolean} opt_dontRemoveFromWorkspace If true, don't remove this
 *     block from the workspace's list of top blocks.
 */
Block.prototype.dispose = function(healStack, animate,
                                           opt_dontRemoveFromWorkspace) {
  // Switch off rerendering.
  this.rendered = false;
  this.unplug(healStack, false);

  if (animate && this.svg_) {
    this.svg_.disposeUiEffect();
  }

  if (this.workspace) {
    this.workspace.startEmitTransaction();
    this.workspace.removeBlock(this);

    // This block is now at the top of the workspace.
    // Remove this block from the workspace's list of top-most blocks.
    if (!opt_dontRemoveFromWorkspace) {
      this.workspace.removeTopBlock(this);
    }
  }

  // Just deleting this block from the DOM would result in a memory leak as
  // well as corruption of the connection database.  Therefore we must
  // methodically step through the blocks and carefully disassemble them.

  if (Blockly.selected == this) {
    Blockly.selected = null;
    // If there's a drag in-progress, unlink the mouse events.
    Blockly.terminateDrag_();
  }

  // If this block has a context menu open, close it.
  if (ContextMenu.currentBlock == this) {
    ContextMenu.hide();
  }

  // First, dispose of all my children.
  for (var x = this.childBlocks_.length - 1; x >= 0; x--) {
    this.childBlocks_[x].dispose(false);
  }
  // Then dispose of myself.
  var icons = this.getIcons();
  for (var x = 0; x < icons.length; x++) {
    icons[x].dispose();
  }
  // Dispose of all inputs and their fields.
  for (var x = 0, input; input = this.inputList[x]; x++) {
    input.dispose();
  }
  this.inputList = [];
  // Dispose of any remaining connections (next/previous/output).
  var connections = this.getConnections_(true);
  for (var x = 0; x < connections.length; x++) {
    var connection = connections[x];
    if (connection.targetConnection) {
      connection.disconnect();
    }
    connections[x].dispose();
  }
  // Dispose of the SVG and break circular references.
  if (this.svg_) {
    this.svg_.dispose();
    this.svg_ = null;
  }

  // Call disposed function if defined
  if (typeof this.disposed === 'function') {
    this.disposed();
  }

  if (this.workspace) {
    if (!opt_dontRemoveFromWorkspace) {
      this.workspaceEmit("block-disposed", { id: this.id });
    }
    this.workspace.completeEmitTransaction();
    if (!opt_dontRemoveFromWorkspace) {
      this.workspace = null;
    }
  }
};

/**
 * Unplug this block from its superior block.  If this block is a statement,
 * optionally reconnect the block underneath with the block on top.
 * @param {boolean} healStack Disconnect child statement and reconnect stack.
 * @param {boolean} bump Move the unplugged block sideways a short distance.
 */
Block.prototype.unplug = function(healStack, bump) {
  bump = bump && !!this.getParent();
  if (this.outputConnection) {
    if (this.outputConnection.targetConnection) {
      // Disconnect from any superior block.
      this.setParent(null);
    }
  } else {
    var previousTarget = null;
    if (this.previousConnection && this.previousConnection.targetConnection) {
      // Remember the connection that any next statements need to connect to.
      previousTarget = this.previousConnection.targetConnection;
      // Detach this block from the parent's tree.
      this.setParent(null);
    }
    var nextBlock = this.getNextBlock();
    if (healStack && nextBlock) {
      // Disconnect the next statement.
      var nextTarget = this.nextConnection.targetConnection;
      nextBlock.setParent(null);
      if (previousTarget && previousTarget.checkType_(nextTarget)) {
        // Attach the next statement to the previous statement.
        previousTarget.connect(nextTarget);
      }
    }
  }
  if (bump) {
    // Bump the block sideways.
    var dx = Blockly.SNAP_RADIUS * (Blockly.RTL ? -1 : 1);
    var dy = Blockly.SNAP_RADIUS * 2;
    this.moveBy(dx, dy);
  }
};

/**
 * Return the coordinates of the top-left corner of this block relative to the
 * drawing surface's origin (0,0).
 * @return {!Object} Object with .x and .y properties.
 */
Block.prototype.getRelativeToSurfaceXY = function() {
  var x = 0;
  var y = 0;
  if (this.svg_) {
    var element = this.svg_.getRootElement();
    do {
      // Loop through this block and every parent.
      var xy = getRelativeXY_(element);
      x += xy.x;
      y += xy.y;
      element = element.parentNode;
    } while (element && element != this.workspace.getCanvas());
  }
  return {x: x, y: y};
};

/**
 * Move a block by a relative offset.
 * @param {number} dx Horizontal offset.
 * @param {number} dy Vertical offset.
 * @param {boolean} manual Should be true if the block was moved by the user.
 */
Block.prototype.moveBy = function(dx, dy, manual) {
  var xy = this.getRelativeToSurfaceXY();
  this.svg_.getRootElement().setAttribute('transform',
      'translate(' + (xy.x + dx) + ', ' + (xy.y + dy) + ')');
  this.moveConnections_(dx, dy);
  this.workspaceEmit("block-set-position", {
    id: this.id,
    x: xy.x + dx,
    y: xy.y + dy,
    manual: !!manual
  });
};

/**
 * Move a block to an absolute offset.
 * @param {number} dx Horizontal offset.
 * @param {number} dy Vertical offset.
 * @param {boolean} manual Should be true if the block was moved by the user.
 */
Block.prototype.moveTo = function(x, y, manual) {
  var xy = this.getRelativeToSurfaceXY();
  this.svg_.getRootElement().setAttribute('transform',
      'translate(' + x + ', ' + y + ')');
  this.moveConnections_(x - xy.x, y - xy.y);
  this.workspaceEmit("block-set-position", {
    id: this.id,
    x: x,
    y: y,
    manual: !!manual
  });
};

/**
 * Returns a bounding box describing the dimensions of this block
 * and any blocks stacked below it.
 * @return {!Object} Object with height and width properties.
 */
Block.prototype.getHeightWidth = function() {
  var height = this.svg_.height;
  var width = this.svg_.width;
  // Recursively add size of subsequent blocks.
  var nextBlock = this.getNextBlock();
  if (nextBlock) {
    var nextHeightWidth = nextBlock.getHeightWidth();
    height += nextHeightWidth.height - 4;  // Height of tab.
    width = Math.max(width, nextHeightWidth.width);
  }
  return {height: height, width: width};
};

/**
 * Handle a mouse-down on an SVG block.
 * @param {!Event} e Mouse down event.
 * @private
 */
Block.prototype.onMouseDown_ = function(e) {
  if (this.isInFlyout) {
    return;
  }
  // Update Blockly's knowledge of its own location.
  Blockly.svgResize();
  Blockly.terminateDrag_();
  this.select();
  Blockly.hideChaff();
  if (isRightButton(e)) {
    // Right-click.
    this.showContextMenu_(e);
  } else if (!this.isMovable()) {
    // Allow unmovable blocks to be selected and context menued, but not
    // dragged.  Let this event bubble up to document, so the workspace may be
    // dragged instead.
    return;
  } else {
    // Left-click (or middle click)
    Blockly.removeAllRanges();
    Blockly.setCursorHand_(true);
    // Look up the current translation and record it.
    var xy = this.getRelativeToSurfaceXY();
    this.startDragX = xy.x;
    this.startDragY = xy.y;
    // Record the current mouse position.
    this.startDragMouseX = e.clientX;
    this.startDragMouseY = e.clientY;
    Block.dragMode_ = 1;
    Block.onMouseUpWrapper_ = bindEvent_(document,
        'mouseup', this, this.onMouseUp_);
    Block.onMouseMoveWrapper_ = bindEvent_(document,
        'mousemove', this, this.onMouseMove_);
    // Build a list of bubbles that need to be moved and where they started.
    this.draggedBubbles_ = [];
    var descendants = this.getDescendants();
    for (var x = 0, descendant; descendant = descendants[x]; x++) {
      var icons = descendant.getIcons();
      for (var y = 0; y < icons.length; y++) {
        var data = icons[y].getIconLocation();
        data.bubble = icons[y];
        this.draggedBubbles_.push(data);
      }
    }
  }
  // This event has been handled.  No need to bubble up to the document.
  e.stopPropagation();
};

/**
 * Handle a mouse-up anywhere in the SVG pane.  Is only registered when a
 * block is clicked.  We can't use mouseUp on the block since a fast-moving
 * cursor can briefly escape the block before it catches up.
 * @param {!Event} e Mouse up event.
 * @private
 */
Block.prototype.onMouseUp_ = function(e) {
  var this_ = this;
  Blockly.doCommand(function() {
    Blockly.terminateDrag_();
    if (Blockly.selected && Blockly.highlightedConnection_) {
      // Connect two blocks together.
      Blockly.localConnection_.connect(Blockly.highlightedConnection_);
      if (this_.svg_) {
        // Trigger a connection animation.
        // Determine which connection is inferior (lower in the source stack).
        var inferiorConnection;
        if (Blockly.localConnection_.isSuperior()) {
          inferiorConnection = Blockly.highlightedConnection_;
        } else {
          inferiorConnection = Blockly.localConnection_;
        }
        inferiorConnection.sourceBlock_.svg_.connectionUiEffect();
      }
      if (this_.workspace.trashcan && this_.workspace.trashcan.isOpen) {
        // Don't throw an object in the trash can if it just got connected.
        this_.workspace.trashcan.close();
      }
    } else if (this_.workspace && this_.workspace.trashcan && this_.workspace.trashcan.isOpen) {
      var trashcan = this_.workspace.trashcan;
      window.setTimeout(trashcan.close.bind(trashcan), 100);
      Blockly.selected.dispose(false, true);
      // Dropping a block on the trash can will usually cause the workspace to
      // resize to contain the newly positioned block.  Force a second resize
      // now that the block has been deleted.
      fireUiEvent(window, 'resize');
    }
    if (Blockly.highlightedConnection_) {
      Blockly.highlightedConnection_.unhighlight();
      Blockly.highlightedConnection_ = null;
    }
  });
};

/**
 * Load the block's help page in a new window.
 * @private
 */
Block.prototype.showHelp_ = function() {
  var url = typeof this.helpUrl === 'function' ? this.helpUrl() : this.helpUrl;
  if (url) {
    window.open(url);
  }
};

/**
 * Duplicate this block and its children.
 * @return {!Block} The duplicate.
 * @private
 */
Block.prototype.duplicate_ = function() {
  // Create a duplicate via XML.
  var xmlBlock = Xml.blockToDom_(this);
  Xml.deleteNext(xmlBlock);
  var newBlock = Xml.domToBlock(
      /** @type {!Workspace} */ (this.workspace), xmlBlock);
  // Move the duplicate next to the old block.
  var xy = this.getRelativeToSurfaceXY();
  if (Blockly.RTL) {
    xy.x -= Blockly.SNAP_RADIUS;
  } else {
    xy.x += Blockly.SNAP_RADIUS;
  }
  xy.y += Blockly.SNAP_RADIUS * 2;
  newBlock.moveBy(xy.x, xy.y);
  newBlock.select();
  return newBlock;
};

/**
 * Send a cancel message to the server for this block.
 * @private
 */
Block.prototype.sendCancelMessage_ = function() {
  if (this.runningState_ === "running" || this.runningState_ === "paused") {
    this.workspaceEmit("block-cancel", { id: this.id });
  }
};

/**
 * Show the context menu for this block.
 * @param {!Event} e Mouse event.
 * @private
 */
Block.prototype.showContextMenu_ = function(e) {
  if (Blockly.readOnly || !this.contextMenu) {
    return;
  }
  // Save the current block in a variable for use in closures.
  var block = this;
  var options = [];

  if (this.runningState_ === "running" || this.runningState_ === "paused") {
    var cancelOption = {
      text: 'Cancel', // Blockly.Msg.CANCEL_BLOCK,
      enabled: true,
      callback: function() {
        block.sendCancelMessage_();
      }
    };
    options.push(cancelOption);
  }

  if (this.isDeletable() && this.isMovable() && !block.isInFlyout) {
    // Option to duplicate this block.
    var duplicateOption = {
      text: Blockly.Msg.DUPLICATE_BLOCK,
      enabled: true,
      callback: function() {
        block.duplicate_();
      }
    };
    if (this.getDescendants().length > this.workspace.remainingCapacity()) {
      duplicateOption.enabled = false;
    }
    options.push(duplicateOption);

    if (this.isEditable() && !this.collapsed_ && Blockly.comments) {
      // Option to add/remove a comment.
      var commentOption = {enabled: true};
      if (this.comment) {
        commentOption.text = Blockly.Msg.REMOVE_COMMENT;
        commentOption.callback = function() {
          block.setCommentText(null);
        };
      } else {
        commentOption.text = Blockly.Msg.ADD_COMMENT;
        commentOption.callback = function() {
          block.setCommentText('');
        };
      }
      options.push(commentOption);
    }

    // Option to make block inline.
    if (!this.collapsed_) {
      for (var i = 0; i < this.inputList.length; i++) {
        if (this.inputList[i].type == Blockly.INPUT_VALUE) {
          // Only display this option if there is a value input on the block.
          var inlineOption = {enabled: true};
          inlineOption.text = this.inputsInline ? Blockly.Msg.EXTERNAL_INPUTS :
                                                  Blockly.Msg.INLINE_INPUTS;
          inlineOption.callback = function() {
            block.setInputsInline(!block.inputsInline);
          };
          options.push(inlineOption);
          break;
        }
      }
    }

    if (Blockly.collapse) {
      // Option to collapse/expand block.
      if (this.collapsed_) {
        var expandOption = {enabled: true};
        expandOption.text = Blockly.Msg.EXPAND_BLOCK;
        expandOption.callback = function() {
          block.setCollapsed(false);
        };
        options.push(expandOption);
      } else {
        var collapseOption = {enabled: true};
        collapseOption.text = Blockly.Msg.COLLAPSE_BLOCK;
        collapseOption.callback = function() {
          block.setCollapsed(true);
        };
        options.push(collapseOption);
      }
    }

    if (Blockly.disable) {
      // Option to disable/enable block.
      var disableOption = {
        text: this.disabled ?
            Blockly.Msg.ENABLE_BLOCK : Blockly.Msg.DISABLE_BLOCK,
        enabled: !this.getInheritedDisabled(),
        callback: function() {
          block.setDisabled(!block.disabled);
        }
      };
      options.push(disableOption);
    }

    // Option to delete this block.
    // Count the number of blocks that are nested in this block.
    var descendantCount = this.getDescendants().length;
    var nextBlock = this.getNextBlock();
    if (nextBlock) {
      // Blocks in the current stack would survive this block's deletion.
      descendantCount -= nextBlock.getDescendants().length;
    }
    var deleteOption = {
      text: descendantCount == 1 ? Blockly.Msg.DELETE_BLOCK :
          Blockly.Msg.DELETE_X_BLOCKS.replace('%1', String(descendantCount)),
      enabled: true,
      callback: function() {
        block.dispose(true, true);
      }
    };
    options.push(deleteOption);
  }

  // Option to get help.
  var url = typeof this.helpUrl === 'function' ? this.helpUrl() : this.helpUrl;
  var helpOption = {enabled: !!url};
  helpOption.text = Blockly.Msg.HELP;
  helpOption.callback = function() {
    block.showHelp_();
  };
  options.push(helpOption);

  // Allow the block to add or modify options.
  if (this.customContextMenu && !block.isInFlyout) {
    this.customContextMenu(options);
  }

  ContextMenu.show(e, options);
  ContextMenu.currentBlock = this;
};

/**
 * Returns all connections originating from this block.
 * @param {boolean} all If true, return all connections even hidden ones.
 *     Otherwise return those that are visible.
 * @return {!Array.<!Blockly.Connection>} Array of connections.
 * @private
 */
Block.prototype.getConnections_ = function(all) {
  var myConnections = [];
  if (all || this.rendered) {
    if (this.outputConnection) {
      myConnections.push(this.outputConnection);
    }
    if (this.nextConnection) {
      myConnections.push(this.nextConnection);
    }
    if (this.previousConnection) {
      myConnections.push(this.previousConnection);
    }
    if (all || !this.collapsed_) {
      for (var x = 0, input; input = this.inputList[x]; x++) {
        if (input.connection) {
          myConnections.push(input.connection);
        }
      }
    }
  }
  return myConnections;
};

/**
 * Move the connections for this block and all blocks attached under it.
 * Also update any attached bubbles.
 * @param {number} dx Horizontal offset from current location.
 * @param {number} dy Vertical offset from current location.
 * @private
 */
Block.prototype.moveConnections_ = function(dx, dy) {
  if (!this.rendered) {
    // Rendering is required to lay out the blocks.
    // This is probably an invisible block attached to a collapsed block.
    return;
  }
  var myConnections = this.getConnections_(false);
  for (var x = 0; x < myConnections.length; x++) {
    myConnections[x].moveBy(dx, dy);
  }
  var icons = this.getIcons();
  for (var x = 0; x < icons.length; x++) {
    icons[x].computeIconLocation();
  }

  // Recurse through all blocks attached under this one.
  for (var x = 0; x < this.childBlocks_.length; x++) {
    this.childBlocks_[x].moveConnections_(dx, dy);
  }
};

/**
 * Recursively adds or removes the dragging class to this node and its children.
 * @param {boolean} adding True if adding, false if removing.
 * @private
 */
Block.prototype.setDragging_ = function(adding) {
  if (adding) {
    this.svg_.addDragging();
  } else {
    this.svg_.removeDragging();
  }
  // Recurse through all blocks attached under this one.
  for (var x = 0; x < this.childBlocks_.length; x++) {
    this.childBlocks_[x].setDragging_(adding);
  }
};

/**
 * Drag this block to follow the mouse.
 * @param {!Event} e Mouse move event.
 * @private
 */
Block.prototype.onMouseMove_ = function(e) {
  var this_ = this;
  Blockly.doCommand(function() {
    if (e.type == 'mousemove' && e.clientX <= 1 && e.clientY == 0 &&
        e.button == 0) {
      /* HACK:
       Safari Mobile 6.0 and Chrome for Android 18.0 fire rogue mousemove
       events on certain touch actions. Ignore events with these signatures.
       This may result in a one-pixel blind spot in other browsers,
       but this shouldn't be noticeable. */
      e.stopPropagation();
      return;
    }
    Blockly.removeAllRanges();
    var dx = e.clientX - this_.startDragMouseX;
    var dy = e.clientY - this_.startDragMouseY;
    if (Block.dragMode_ == 1) {
      // Still dragging within the sticky DRAG_RADIUS.
      var dr = Math.sqrt(Math.pow(dx, 2) + Math.pow(dy, 2));
      if (dr > Blockly.DRAG_RADIUS) {
        // Switch to unrestricted dragging.
        Block.dragMode_ = 2;
        // Push this block to the very top of the stack.
        this_.setParent(null);
        this_.setDragging_(true);
      }
    }
    if (Block.dragMode_ == 2) {
      // Unrestricted dragging.
      var x = this_.startDragX + dx;
      var y = this_.startDragY + dy;
      this_.svg_.getRootElement().setAttribute('transform',
          'translate(' + x + ', ' + y + ')');
      // Drag all the nested bubbles.
      for (var i = 0; i < this_.draggedBubbles_.length; i++) {
        var commentData = this_.draggedBubbles_[i];
        commentData.bubble.setIconLocation(commentData.x + dx,
            commentData.y + dy);
      }

      // Check to see if any of this block's connections are within range of
      // another block's connection.
      var myConnections = this_.getConnections_(false);
      var closestConnection = null;
      var localConnection = null;
      var radiusConnection = Blockly.SNAP_RADIUS;
      for (var i = 0; i < myConnections.length; i++) {
        var myConnection = myConnections[i];
        var neighbour = myConnection.closest(radiusConnection, dx, dy);
        if (neighbour.connection) {
          closestConnection = neighbour.connection;
          localConnection = myConnection;
          radiusConnection = neighbour.radius;
        }
      }

      // Remove connection highlighting if needed.
      if (Blockly.highlightedConnection_ &&
          Blockly.highlightedConnection_ != closestConnection) {
        Blockly.highlightedConnection_.unhighlight();
        Blockly.highlightedConnection_ = null;
        Blockly.localConnection_ = null;
      }
      // Add connection highlighting if needed.
      if (closestConnection &&
          closestConnection != Blockly.highlightedConnection_) {
        closestConnection.highlight();
        Blockly.highlightedConnection_ = closestConnection;
        Blockly.localConnection_ = localConnection;
      }
      // Flip the trash can lid if needed.
      if (this_.workspace.trashcan && this_.isDeletable()) {
        this_.workspace.trashcan.onMouseMove(e);
      }
    }
    // This event has been handled.  No need to bubble up to the document.
    e.stopPropagation();
  });
};

/**
 * Bump unconnected blocks out of alignment.  Two blocks which aren't actually
 * connected should not coincidentally line up on screen.
 * @private
 */
Block.prototype.bumpNeighbours_ = function() {
  if (Block.dragMode_ != 0) {
    // Don't bump blocks during a drag.
    return;
  }
  var rootBlock = this.getRootBlock();
  if (rootBlock.isInFlyout) {
    // Don't move blocks around in a flyout.
    return;
  }
  // Loop though every connection on this block.
  var myConnections = this.getConnections_(false);
  for (var x = 0; x < myConnections.length; x++) {
    var connection = myConnections[x];
    // Spider down from this block bumping all sub-blocks.
    if (connection.targetConnection && connection.isSuperior()) {
      connection.targetBlock().bumpNeighbours_();
    }

    var neighbours = connection.neighbours_(Blockly.SNAP_RADIUS);
    for (var y = 0; y < neighbours.length; y++) {
      var otherConnection = neighbours[y];
      // If both connections are connected, that's probably fine.  But if
      // either one of them is unconnected, then there could be confusion.
      if (!connection.targetConnection || !otherConnection.targetConnection) {
        // Only bump blocks if they are from different tree structures.
        if (otherConnection.sourceBlock_.getRootBlock() != rootBlock) {
          // Always bump the inferior block.
          if (connection.isSuperior()) {
            otherConnection.bumpAwayFrom_(connection);
          } else {
            connection.bumpAwayFrom_(otherConnection);
          }
        }
      }
    }
  }
};

/**
 * Return the parent block or null if this block is at the top level.
 * @return {Block} The block that holds the current block.
 */
Block.prototype.getParent = function() {
  // Look at the DOM to see if we are nested in another block.
  return this.parentBlock_;
};

/**
 * Return the parent block that surrounds the current block, or null if this
 * block has no surrounding block.  A parent block might just be the previous
 * statement, whereas the surrounding block is an if statement, while loop, etc.
 * @return {Block} The block that surrounds the current block.
 */
Block.prototype.getSurroundParent = function() {
  var block = this;
  while (true) {
    do {
      var prevBlock = block;
      block = block.getParent();
      if (!block) {
        // Ran off the top.
        return null;
      }
    } while (block.getNextBlock() == prevBlock);
    // This block is an enclosing parent, not just a statement in a stack.
    return block;
  }
};

/**
 * Return the first parent block of a particular block type,
 * or null if none is found.
 * @param {string} type New parent block.
 * @return {Block} The ancestor block.
 */
Block.prototype.getAncestor = function(type) {
  var block = this;
  do {
    block = block.getParent();
  } while (block && block.type !== type);
  return block || null;
};

/**
 * Return the first parent block of the desired type that surrounds the current
 * block, or null if none is found. A parent block might just be the previous
 * statement, whereas the surrounding block is an if statement, while loop, etc.
 * @return {Block} The block that surrounds the current block.
 */
Block.prototype.getSurroundAncestor = function(type) {
  var block = this;
  do {
    var prevBlock = block;
    block = block.getAncestor(type);
    if (!block) {
      // Ran off the top.
      return null;
    }
  } while (block.getNextBlock() == prevBlock);
  // This block is an enclosing parent, not just a statement in a stack.
  return block;
};

/**
 * Return the next statement block directly connected to this block.
 * @return {Block} The next statement block or null.
 */
Block.prototype.getNextBlock = function() {
  return this.nextConnection && this.nextConnection.targetBlock();
};

/**
 * Return the top-most block in this block's tree.
 * This will return itself if this block is at the top level.
 * @return {!Block} The root block.
 */
Block.prototype.getRootBlock = function() {
  var rootBlock;
  var block = this;
  do {
    rootBlock = block;
    block = rootBlock.parentBlock_;
  } while (block);
  return rootBlock;
};

/**
 * Find all the blocks that are directly nested inside this one.
 * Includes value and block inputs, as well as any following statement.
 * Excludes any connection on an output tab or any preceding statement.
 * @return {!Array.<!Block>} Array of blocks.
 */
Block.prototype.getChildren = function() {
  return this.childBlocks_;
};

/**
 * Set parent of this block to be a new block or null.
 * @param {Block} newParent New parent block.
 */
Block.prototype.setParent = function(newParent) {
  if (!this.onChangeParent_) {
    this.onChangeParent_ = function () { this.emit("parent-changed") }.bind(this);
  }

  if (this.parentBlock_) {
    // Remove this block from the old parent's child list.
    var children = this.parentBlock_.childBlocks_;
    for (var child, x = 0; child = children[x]; x++) {
      if (child == this) {
        children.splice(x, 1);
        break;
      }
    }
    // Move this block up the DOM.  Keep track of x/y translations.
    var xy = this.getRelativeToSurfaceXY();
    this.workspace.getCanvas().appendChild(this.svg_.getRootElement());
    this.svg_.getRootElement().setAttribute('transform',
        'translate(' + xy.x + ', ' + xy.y + ')');

    this.parentBlock_.removeListener("parent-changed", this.onChangeParent_);

    // Disconnect from superior blocks.
    this.parentBlock_ = null;
    if (this.previousConnection && this.previousConnection.targetConnection) {
      this.previousConnection.disconnect();
    }
    if (this.outputConnection && this.outputConnection.targetConnection) {
      this.outputConnection.disconnect();
    }
    // This block hasn't actually moved on-screen, so there's no need to update
    // its connection locations.
  } else {
    // Remove this block from the workspace's list of top-most blocks.
    // Note that during realtime sync we sometimes create child blocks that are
    // not top level so we check first before removing.
    if (this.workspace.getTopBlocks(false).indexOf(this) !== -1) {
      this.workspace.removeTopBlock(this);
    }
  }

  this.parentBlock_ = newParent;
  if (newParent) {
    // Add this block to the new parent's child list.
    newParent.childBlocks_.push(this);

    var oldXY = this.getRelativeToSurfaceXY();
    if (newParent.svg_ && this.svg_) {
      newParent.svg_.getRootElement().appendChild(this.svg_.getRootElement());
    }
    var newXY = this.getRelativeToSurfaceXY();

    newParent.on("parent-changed", this.onChangeParent_);

    // Move the connections to match the child's new position.
    this.moveConnections_(newXY.x - oldXY.x, newXY.y - oldXY.y);
  } else {
    this.workspace.addTopBlock(this);
  }

  this.emit("parent-changed");
};

/**
 * Find all the blocks that are directly or indirectly nested inside this one.
 * Includes this block in the list.
 * Includes value and block inputs, as well as any following statements.
 * Excludes any connection on an output tab or any preceding statements.
 * @return {!Array.<!Block>} Flattened array of blocks.
 */
Block.prototype.getDescendants = function() {
  var blocks = [this];
  for (var child, x = 0; child = this.childBlocks_[x]; x++) {
    blocks.push.apply(blocks, child.getDescendants());
  }
  return blocks;
};

/**
 * Get whether this block is deletable or not.
 * @return {boolean} True if deletable.
 */
Block.prototype.isDeletable = function() {
  return this.deletable_ && !Blockly.readOnly;
};

/**
 * Set whether this block is deletable or not.
 * @param {boolean} deletable True if deletable.
 */
Block.prototype.setDeletable = function(deletable) {
  this.deletable_ = deletable;
  this.workspaceEmit("block-set-deletable", { id: this.id, value: deletable });
  this.svg_ && this.svg_.updateMovable();
};

/**
 * Get whether this block is movable or not.
 * @return {boolean} True if movable.
 */
Block.prototype.isMovable = function() {
  return this.movable_ && !Blockly.readOnly;
};

/**
 * Set whether this block is movable or not.
 * @param {boolean} movable True if movable.
 */
Block.prototype.setMovable = function(movable) {
  this.movable_ = movable;
  this.workspaceEmit("block-set-movable", { id: this.id, change: "movable", value: movable });
};

/**
 * Get whether this block is editable or not.
 * @return {boolean} True if editable.
 */
Block.prototype.isEditable = function() {
  return this.editable_ && !Blockly.readOnly;
};

/**
 * Set whether this block is editable or not.
 * @param {boolean} editable True if editable.
 */
Block.prototype.setEditable = function(editable) {
  this.editable_ = editable;
  for (var x = 0, input; input = this.inputList[x]; x++) {
    for (var y = 0, field; field = input.fieldRow[y]; y++) {
      field.updateEditable();
    }
  }
  var icons = this.getIcons();
  for (var x = 0; x < icons.length; x++) {
    icons[x].updateEditable();
  }
  this.workspaceEmit("block-set-editable", { id: this.id, value: editable });
};

/**
 * Set the URL of this block's help page.
 * @param {string|Function} url URL string for block help, or function that
 *     returns a URL.  Null for no help.
 */
Block.prototype.setHelpUrl = function(url) {
  this.helpUrl = url;
  this.workspaceEmit("block-set-help-url", { id: this.id, url: url });
};

/**
 * Get the colour of a block.
 * @return {number} HSV hue value.
 */
Block.prototype.getColour = function() {
  return this.colourHue_;
};

/**
 * Change the colour of a block.
 * @param {number} colourHue HSV hue value.
 */
Block.prototype.setColour = function(colourHue) {
  this.colourHue_ = colourHue;
  if (this.svg_) {
    this.svg_.updateColour();
  }
  var icons = this.getIcons();
  for (var x = 0; x < icons.length; x++) {
    icons[x].updateColour();
  }
  if (this.rendered) {
    // Bump every dropdown to change its colour.
    for (var x = 0, input; input = this.inputList[x]; x++) {
      for (var y = 0, field; field = input.fieldRow[y]; y++) {
        field.setText(null);
      }
    }
    this.render();
  }
  this.workspaceEmit("block-set-colour", { id: this.id, colour: colourHue });
};

/**
 * Returns the named field from a block.
 * @param {string} name The name of the field.
 * @return {Field} Named field, or null if field does not exist.
 * @private
 */
Block.prototype.getField_ = function(name) {
  for (var x = 0, input; input = this.inputList[x]; x++) {
    for (var y = 0, field; field = input.fieldRow[y]; y++) {
      if (field.name === name) {
        return field;
      }
    }
  }
  return null;
};

/**
 * Returns the language-neutral value from the field of a block.
 * @param {string} name The name of the field.
 * @return {?string} Value from the field or null if field does not exist.
 */
Block.prototype.getFieldValue = function(name) {
  var field = this.getField_(name);
  if (field) {
    return field.getValue();
  }
  return null;
};

/**
 * Returns the language-neutral value from the field of a block.
 * @param {string} name The name of the field.
 * @return {?string} Value from the field or null if field does not exist.
 * @deprecated December 2013
 */
Block.prototype.getTitleValue = function(name) {
  console.log('Deprecated call to getTitleValue, use getFieldValue instead.');
  return this.getFieldValue(name);
};

/**
 * Change the field value for a block (e.g. 'CHOOSE' or 'REMOVE').
 * @param {string} newValue Value to be the new field.
 * @param {string} name The name of the field.
 */
Block.prototype.setFieldValue = function(newValue, name, options) {
  var field = this.getField_(name);
  var options = options || {};
  assert(typeof field === 'object' && field !== null, 'Field "' + name + '" not found.');
  var changed = field.setValue(newValue);
  if (changed) newValue = changed;
  if (options.emit) {
    this.workspaceEmit("block-set-field-value", { id: this.id, field: name, value: newValue });
  }
};

/**
 * Change the field value for a block (e.g. 'CHOOSE' or 'REMOVE').
 * @param {string} newValue Value to be the new field.
 * @param {string} name The name of the field.
 * @deprecated December 2013
 */
Block.prototype.setTitleValue = function(newValue, name) {
  console.log('Deprecated call to setTitleValue, use setFieldValue instead.');
  this.setFieldValue(newValue, name);
};

/**
 * Change the tooltip text for a block.
 * @param {string|!Function} newTip Text for tooltip or a parent element to
 *     link to for its tooltip.  May be a function that returns a string.
 */
Block.prototype.setTooltip = function(newTip) {
  this.tooltip = newTip;
};

/**
 * Set whether this block can chain onto the bottom of another block.
 * @param {boolean} newBoolean True if there can be a previous statement.
 * @param {string|Array.<string>|null} opt_check Statement type or list of
 *     statement types.  Null or undefined if any type could be connected.
 */
Block.prototype.setPreviousStatement = function(newBoolean, opt_check) {
  if (this.previousConnection) {
    assert(!this.previousConnection.targetConnection,
        'Must disconnect previous statement before removing connection.');
    this.previousConnection.dispose();
    this.previousConnection = null;
  }
  if (newBoolean) {
    assert(!this.outputConnection,
        'Remove output connection prior to adding previous connection.');
    if (opt_check === undefined) {
      opt_check = null;
    }
    this.previousConnection =
        new Connection(this, Blockly.PREVIOUS_STATEMENT);
    this.previousConnection.setCheck(opt_check);
  }
  if (this.rendered) {
    this.render();
    this.bumpNeighbours_();
  }
};

/**
 * Set whether another block can chain onto the bottom of this block.
 * @param {boolean} newBoolean True if there can be a next statement.
 * @param {string|Array.<string>|null} opt_check Statement type or list of
 *     statement types.  Null or undefined if any type could be connected.
 */
Block.prototype.setNextStatement = function(newBoolean, opt_check) {
  if (this.nextConnection) {
    assert(!this.nextConnection.targetConnection,
        'Must disconnect next statement before removing connection.');
    this.nextConnection.dispose();
    this.nextConnection = null;
  }
  if (newBoolean) {
    if (opt_check === undefined) {
      opt_check = null;
    }
    this.nextConnection =
        new Connection(this, Blockly.NEXT_STATEMENT);
    this.nextConnection.setCheck(opt_check);
    this.nextConnection.on("connect", function (child, parent) {
      this.workspaceEmit("block-connected", { id: child.id, parent: parent.id, connection: "previous" });
    }.bind(this));
    this.nextConnection.on("disconnect", function (child, parent) {
      this.workspaceEmit("block-disconnected", { id: child.id, parent: parent.id, connection: "previous" });
    }.bind(this));
  }
  if (this.rendered) {
    this.render();
    this.bumpNeighbours_();
  }
};

/**
 * Set whether this block returns a value.
 * @param {boolean} newBoolean True if there is an output.
 * @param {string|Array.<string>|null} opt_check Returned type or list of
 *     returned types.  Null or undefined if any type could be returned
 *     (e.g. variable get).
 */
Block.prototype.setOutput = function(newBoolean, opt_check) {
  if (this.outputConnection) {
    assert(!this.outputConnection.targetConnection,
        'Must disconnect output value before removing connection.');
    this.outputConnection.dispose();
    this.outputConnection = null;
  }
  if (newBoolean) {
    assert(!this.previousConnection,
        'Remove previous connection prior to adding output connection.');
    if (opt_check === undefined) {
      opt_check = null;
    }
    this.outputConnection =
        new Connection(this, Blockly.OUTPUT_VALUE);
    this.outputConnection.setCheck(opt_check);
  }
  if (this.rendered) {
    this.render();
    this.bumpNeighbours_();
  }
};

/**
 * Change the output type on a block.
 * @param {string|Array.<string>|null} check Returned type or list of
 *     returned types.  Null or undefined if any type could be returned
 *     (e.g. variable get).  It is fine if this is the same as the old type.
 * @throws {AssertionError} if the block did not already have an
 *     output.
 */
Block.prototype.changeOutput = function(check) {
  assert(this.outputConnection,
      'Only use changeOutput() on blocks that already have an output.');
  this.outputConnection.setCheck(check);
};

/**
 * Set whether value inputs are arranged horizontally or vertically.
 * @param {boolean} newBoolean True if inputs are horizontal.
 */
Block.prototype.setInputsInline = function(newBoolean) {
  this.inputsInline = newBoolean;
  if (this.rendered) {
    this.render();
    this.bumpNeighbours_();
    this.workspace.fireChangeEvent();
    this.workspaceEmit("block-set-inputs-inline", { id: this.id, value: newBoolean });
  }
};

/**
 * Set whether the block is disabled or not.
 * @param {boolean} disabled True if disabled.
 */
Block.prototype.setDisabled = function(disabled) {
  if (this.disabled == disabled) {
    return;
  }
  this.disabled = disabled;
  this.svg_.updateDisabled();
  this.workspace.fireChangeEvent();
  this.workspaceEmit("block-set-disabled", { id: this.id, value: disabled });
};

/**
 * Get whether the block is disabled or not due to parents.
 * The block's own disabled property is not considered.
 * @return {boolean} True if disabled.
 */
Block.prototype.getInheritedDisabled = function() {
  var block = this;
  while (true) {
    block = block.getSurroundParent();
    if (!block) {
      // Ran off the top.
      return false;
    } else if (block.disabled) {
      return true;
    }
  }
};

/**
 * Get whether the block is collapsed or not.
 * @return {boolean} True if collapsed.
 */
Block.prototype.isCollapsed = function() {
  return this.collapsed_;
};

/**
 * Set whether the block is collapsed or not.
 * @param {boolean} collapsed True if collapsed.
 */
Block.prototype.setCollapsed = function(collapsed) {
  if (this.collapsed_ == collapsed) {
    return;
  }
  this.collapsed_ = collapsed;
  var renderList = [];
  // Show/hide the inputs.
  for (var x = 0, input; input = this.inputList[x]; x++) {
    renderList.push.apply(renderList, input.setVisible(!collapsed));
  }

  var COLLAPSED_INPUT_NAME = '_TEMP_COLLAPSED_INPUT';
  if (collapsed) {
    var icons = this.getIcons();
    for (var x = 0; x < icons.length; x++) {
      icons[x].setVisible(false);
    }
    var text = this.toString(Blockly.COLLAPSE_CHARS);
    this.appendDummyInput(COLLAPSED_INPUT_NAME).appendField(text);
  } else {
    this.removeInput(COLLAPSED_INPUT_NAME);
  }

  if (!renderList.length) {
    // No child blocks, just render this block.
    renderList[0] = this;
  }
  if (this.rendered) {
    for (var x = 0, block; block = renderList[x]; x++) {
      block.render();
    }
    this.bumpNeighbours_();
  }

  this.workspaceEmit("block-set-collapsed", { id: this.id, value: collapsed });
};

/**
 * Create a human-readable text representation of this block and any children.
 * @param {?number} opt_maxLength Truncate the string to this length.
 * @return {string} Text of block.
 */
Block.prototype.toString = function(opt_maxLength) {
  var text = [];
  for (var x = 0, input; input = this.inputList[x]; x++) {
    for (var y = 0, field; field = input.fieldRow[y]; y++) {
      text.push(field.getText());
    }
    if (input.connection) {
      var child = input.connection.targetBlock();
      if (child) {
        text.push(child.toString());
      } else {
        text.push('?');
      }
    }
  }
  text = text.join(' ').trim() || '???';
  if (opt_maxLength) {
    // TODO: Improve truncation so that text from this block is given priority.
    // TODO: Handle FieldImage better.
    text = Blockly.string.truncate(text, opt_maxLength);
  }
  return text;
};

/**
 * Shortcut for appending a value input row.
 * @param {string} name Language-neutral identifier which may used to find this
 *     input again.  Should be unique to this block.
 * @return {!Input} The input object created.
 */
Block.prototype.appendValueInput = function(name) {
  return this.appendInput_(Blockly.INPUT_VALUE, name);
};

/**
 * Shortcut for appending a statement input row.
 * @param {string} name Language-neutral identifier which may used to find this
 *     input again.  Should be unique to this block.
 * @return {!Input} The input object created.
 */
Block.prototype.appendStatementInput = function(name) {
  return this.appendInput_(Blockly.NEXT_STATEMENT, name);
};

/**
 * Shortcut for appending a dummy input row.
 * @param {string} opt_name Language-neutral identifier which may used to find
 *     this input again.  Should be unique to this block.
 * @return {!Input} The input object created.
 */
Block.prototype.appendDummyInput = function(opt_name) {
  return this.appendInput_(Blockly.DUMMY_INPUT, opt_name || '');
};

/**
 * Interpolate a message string, creating fields and inputs.
 * @param {string} msg The message string to parse.  %1, %2, etc. are symbols
 *     for value inputs or for Fields, such as an instance of
 *     FieldDropdown, which would be placed as a field in either the
 *     following value input or a dummy input.  The newline character forces
 *     the creation of an unnamed dummy input if any fields need placement.
 *     Note that '%10' would be interpreted as a reference to the tenth
 *     argument.  To show the first argument followed by a zero, use '%1 0'.
 *     (Spaces around tokens are stripped.)  To display a percentage sign
 *     followed by a number (e.g., "%123"), put that text in a
 *     FieldLabel (as described below).
 * @param {!Array.<?string|number|Array.<string>|Field>|number} var_args
 *     A series of tuples that each specify the value inputs to create.  Each
 *     tuple has at least two elements.  The first is its name; the second is
 *     its type, which can be any of:
 *     - A string (such as 'Number'), denoting the one type allowed in the
 *       corresponding socket.
 *     - An array of strings (such as ['Number', 'List']), denoting the
 *       different types allowed in the corresponding socket.
 *     - null, denoting that any type is allowed in the corresponding socket.
 *     - Field, in which case that field instance, such as an
 *       instance of FieldDropdown, appears (instead of a socket).
 *     If the type is any of the first three options (which are legal arguments
 *     to setCheck()), there should be a third element in the tuple, giving its
 *     alignment.
 *     The final parameter is not a tuple, but just an alignment for any
 *     trailing dummy inputs.  This last parameter is mandatory; there may be
 *     any number of tuples (though the number of tuples must match the symbols
 *     in msg).
 */
Block.prototype.interpolateMsg = function(msg, var_args) {
  /**
   * Add a field to this input.
   * @this !Input
   * @param {Field|Array.<string|Field>} field
   *     This is either a Field or a tuple of a name and a Field.
   */
  function addFieldToInput(field) {
    if (field instanceof Field) {
      this.appendField(field);
    } else {
      assert(Array.isArray(field));
      this.appendField(field[1], field[0]);
    }
  }

  // Validate the msg at the start and the dummy alignment at the end,
  // and remove the latter.
  assert(typeof msg === 'string');
  var dummyAlign = arguments[arguments.length - 1];
  assert(
      dummyAlign === Blockly.ALIGN_LEFT ||
      dummyAlign === Blockly.ALIGN_CENTRE ||
      dummyAlign === Blockly.ALIGN_RIGHT,
      'Illegal final argument "' + dummyAlign + '" is not an alignment.');
  arguments.length = arguments.length - 1;

  var tokens = msg.split(this.interpolateMsg.SPLIT_REGEX_);
  var fields = [];
  for (var i = 0; i < tokens.length; i += 2) {
    var text = tokens[i].trim();
    var input = undefined;
    if (text) {
      fields.push(new FieldLabel(text));
    }
    var symbol = tokens[i + 1];
    if (symbol && symbol.charAt(0) == '%') {
      // Numeric field.
      var number = parseInt(symbol.substring(1), 10);
      var tuple = arguments[number];
      assert(Array.isArray(tuple),
          'Message symbol "' + symbol + '" is out of range.');
      if (tuple[1] instanceof Field) {
        fields.push([tuple[0], tuple[1]]);
      } else {
        input = this.appendValueInput(tuple[0])
            .setCheck(tuple[1])
            .setAlign(tuple[2]);
      }
      arguments[number] = null;  // Inputs may not be reused.
    } else if (symbol == '\n' && fields.length) {
      // Create a dummy input.
      input = this.appendDummyInput();
    }
    // If we just added an input, hang any pending fields on it.
    if (input && fields.length) {
      fields.forEach(addFieldToInput, input);
      fields = [];
    }
  }
  // If any fields remain, create a trailing dummy input.
  if (fields.length) {
    var input = this.appendDummyInput()
        .setAlign(dummyAlign);
    fields.forEach(addFieldToInput, input);
  }

  // Verify that all inputs were used.
  for (var i = 1; i < arguments.length - 1; i++) {
    assert(arguments[i] === null,
        'Input "' + i + '" not used in message: "' + msg + '"');
  }
  // Make the inputs inline unless there is only one input and
  // no text follows it.
  this.setInputsInline(!msg.match(this.interpolateMsg.INLINE_REGEX_));
};

Block.prototype.interpolateMsg.SPLIT_REGEX_ = /(%\d+|\n)/;
Block.prototype.interpolateMsg.INLINE_REGEX_ = /%1\s*$/;


/**
 * Add a value input, statement input or local variable to this block.
 * @param {number} type Either Blockly.INPUT_VALUE or Blockly.NEXT_STATEMENT or
 *     Blockly.DUMMY_INPUT.
 * @param {string} name Language-neutral identifier which may used to find this
 *     input again.  Should be unique to this block.
 * @return {!Input} The input object created.
 * @private
 */
Block.prototype.appendInput_ = function(type, name) {
  var connection = null;
  if (type == Blockly.INPUT_VALUE || type == Blockly.NEXT_STATEMENT) {
    connection = new Connection(this, type);
  }
  if (type == Blockly.INPUT_VALUE) {
   connection.on("connect", function (child, parent) {
        this.workspaceEmit("block-connected", { id: child.id, parent: parent.id, connection: "input-value", input: name });
    }.bind(this));
    connection.on("disconnect", function (child, parent) {
      this.workspaceEmit("block-disconnected", { id: child.id, parent: parent.id, connection: "input-value", input: name });
    }.bind(this));
  }
  if (type == Blockly.NEXT_STATEMENT) {
    connection.on("connect", function (child, parent) {
      this.workspaceEmit("block-connected", { id: child.id, parent: parent.id, connection: "input-statement", input: name });
    }.bind(this));
    connection.on("disconnect", function (child, parent) {
      this.workspaceEmit("block-disconnected", { id: child.id, parent: parent.id, connection: "input-statement", input: name });
    }.bind(this));
  }
  var input = new Input(type, name, this, connection);
  input.on("field-changed", function (fieldName, value) {
    this.workspaceEmit("block-set-field-value", { id: this.id, field: fieldName, value: value });
  }.bind(this));
  // Append input to list.
  this.inputList.push(input);
  if (this.rendered) {
    this.render();
    // Adding an input will cause the block to change shape.
    this.bumpNeighbours_();
  }
  this.workspaceEmit("block-add-input", { id: this.id, type: type, input: name });
  return input;
};

/**
 * Move a named input to a different location on this block.
 * @param {string} name The name of the input to move.
 * @param {?string} refName Name of input that should be after the moved input,
 *   or null to be the input at the end.
 */
Block.prototype.moveInputBefore = function(name, refName) {
  if (name == refName) {
    return;
  }
  // Find both inputs.
  var inputIndex = -1;
  var refIndex = refName ? -1 : this.inputList.length;
  for (var x = 0, input; input = this.inputList[x]; x++) {
    if (input.name == name) {
      inputIndex = x;
      if (refIndex != -1) {
        break;
      }
    } else if (refName && input.name == refName) {
      refIndex = x;
      if (inputIndex != -1) {
        break;
      }
    }
  }
  assert(inputIndex !== -1, 'Named input "' + name + '" not found.');
  assert(refIndex !== -1, 'Reference input "' + refName + '" not found.');
  this.moveNumberedInputBefore(inputIndex, refIndex);
};

/**
 * Move a numbered input to a different location on this block.
 * @param {number} inputIndex Index of the input to move.
 * @param {number} refIndex Index of input that should be after the moved input.
 */
Block.prototype.moveNumberedInputBefore = function(
    inputIndex, refIndex) {
  // Validate arguments.
  assert(inputIndex != refIndex, 'Can\'t move input to itself.');
  assert(inputIndex < this.inputList.length,
                      'Input index ' + inputIndex + ' out of bounds.');
  assert(refIndex <= this.inputList.length,
                      'Reference input ' + refIndex + ' out of bounds.');
  // Remove input.
  var input = this.inputList[inputIndex];
  this.inputList.splice(inputIndex, 1);
  if (inputIndex < refIndex) {
    refIndex--;
  }
  // Reinsert input.
  this.inputList.splice(refIndex, 0, input);
  if (this.rendered) {
    this.render();
    // Moving an input will cause the block to change shape.
    this.bumpNeighbours_();
  }
  this.workspaceEmit("block-move-input", { id: this.id, input: inputIndex, before: refIndex });
};

/**
 * Remove an input from this block.
 * @param {string} name The name of the input.
 * @param {boolean} opt_quiet True to prevent error if input is not present.
 * @throws {AssertionError} if the input is not present and
 *     opt_quiet is not true.
 */
Block.prototype.removeInput = function(name, opt_quiet) {
  for (var x = 0, input; input = this.inputList[x]; x++) {
    if (input.name == name) {
      if (input.connection && input.connection.targetConnection) {
        // Disconnect any attached block.
        input.connection.targetBlock().setParent(null);
      }
      input.removeAllListeners();
      input.dispose();
      this.inputList.splice(x, 1);
      if (this.rendered) {
        this.render();
        // Removing an input will cause the block to change shape.
        this.bumpNeighbours_();
      }
      this.workspaceEmit("block-remove-input", { id: this.id, input: name });
      return;
    }
  }
  if (!opt_quiet) {
    assert.fail(null, null, 'Input "' + name + '" not found.');
  }
};

/**
 * Fetches the named input object.
 * @param {string} name The name of the input.
 * @return {Object} The input object, or null of the input does not exist.
 */
Block.prototype.getInput = function(name) {
  for (var x = 0, input; input = this.inputList[x]; x++) {
    if (input.name == name) {
      return input;
    }
  }
  // This input does not exist.
  return null;
};

/**
 * Fetches the block attached to the named input.
 * @param {string} name The name of the input.
 * @return {Block} The attached value block, or null if the input is
 *     either disconnected or if the input does not exist.
 */
Block.prototype.getInputTargetBlock = function(name) {
  var input = this.getInput(name);
  return input && input.connection && input.connection.targetBlock();
};

/**
 * Give this block a mutator dialog.
 * @param {Mutator} mutator A mutator dialog instance or null to remove.
 */
Block.prototype.setMutator = function(mutator) {
  if (this.mutator && this.mutator !== mutator) {
    this.mutator.dispose();
  }
  if (mutator) {
    mutator.block_ = this;
    this.mutator = mutator;
    if (this.svg_) {
      mutator.createIcon();
    }
  }
};

/**
 * Returns the comment on this block (or '' if none).
 * @return {string} Block's comment.
 */
Block.prototype.getCommentText = function() {
  if (this.comment) {
    var comment = this.comment.getText();
    // Trim off trailing whitespace.
    return comment.replace(/\s+$/, '').replace(/ +\n/g, '\n');
  }
  return '';
};

/**
 * Set this block's comment text.
 * @param {?string} text The text, or null to delete.
 */
Block.prototype.setCommentText = function(text) {
  var changedState = false;
  if (typeof text === 'string') {
    if (!this.comment) {
      this.comment = new Comment(this);
      changedState = true;
    }
    this.comment.setText(/** @type {string} */ (text));
    this.workspaceEmit("block-set-comment", { id: this.id, value: text });
  } else {
    if (this.comment) {
      this.comment.dispose();
      changedState = true;
    }
  }
  if (this.rendered) {
    this.render();
    if (changedState) {
      // Adding or removing a comment icon will cause the block to change shape.
      this.bumpNeighbours_();
    }
  }
};

/**
 * Set this block's warning text.
 * @param {?string} text The text, or null to delete.
 */
Block.prototype.setWarningText = function(text) {
  if (this.isInFlyout) {
    text = null;
  }
  var changedState = false;
  if (typeof text === 'string') {
    if (!this.warning) {
      this.warning = new Warning(this);
      changedState = true;
    }
    this.warning.setText(/** @type {string} */ (text));
  } else {
    if (this.warning) {
      this.warning.dispose();
      changedState = true;
    }
  }
  if (changedState && this.rendered) {
    this.render();
    // Adding or removing a warning icon will cause the block to change shape.
    this.bumpNeighbours_();
  }
};

/**
 * Render the block.
 * Lays out and reflows a block based on its contents and settings.
 */
Block.prototype.render = function() {
  assert(typeof this.svg_ === 'object' && this.svg_ !== null,
      'Uninitialized block cannot be rendered.  Call block.initSvg()');
  this.svg_.render();
};

/**
 * Return the variable scope of this block. i.e. the scope of the first
 * surrounding ancestor of this that has a scope, unless thisBlockOnly
 * is true, in which case null is returned if this block does not have
 * a scope.
 * @param {boolean} thisBlockOnly Only consider this block.
 * @return {VariableScope} The variable scope.
 */
Block.prototype.getVariableScope = function(thisBlockOnly) {
  if (thisBlockOnly) {
    return this.variableScope_ || null;
  }

  var parent = this.getSurroundParent();
  return this.variableScope_ || (parent && parent.getVariableScope()) || GlobalScope;
};

/**
 * Return all variables referenced by this block or its children.
 * @return {!Array.string} Array of variable names.
 */
Block.prototype.getVars = function () {
  return Array.prototype.concat.apply([], this.getChildren().map(function (block) {
    return block.getVars();
  }));
};
