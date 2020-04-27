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
 * @fileoverview Object representing a code comment.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Icon from './icon';
import Bubble from './bubble';
import Warning from './warning';
import {inherits} from './utils';
import {bindEvent_, unbindEvent_, createSvgElement} from './utils';

/**
 * Class for a comment.
 * @param {!Block} block The block associated with this comment.
 * @extends {Icon}
 * @constructor
 */
var Comment = function(block) {
  Comment.super_.call(this, block);
  this.createIcon_();
};
inherits(Comment, Icon);
export default Comment;


/**
 * Comment text (if bubble is not visible).
 * @private
 */
Comment.prototype.text_ = '';

/**
 * Width of bubble.
 * @private
 */
Comment.prototype.width_ = 160;

/**
 * Height of bubble.
 * @private
 */
Comment.prototype.height_ = 80;

/**
 * Create the icon on the block.
 * @private
 */
Comment.prototype.createIcon_ = function() {
  Icon.prototype.createIcon_.call(this);
  /* Here's the markup that will be generated:
  <circle class="blocklyIconShield" r="8" cx="8" cy="8"/>
  <text class="blocklyIconMark" x="8" y="13">?</text>
  */
  var iconShield = createSvgElement('circle',
      {'class': 'blocklyIconShield',
       'r': Icon.RADIUS,
       'cx': Icon.RADIUS,
       'cy': Icon.RADIUS}, this.iconGroup_);
  this.iconMark_ = createSvgElement('text',
      {'class': 'blocklyIconMark',
       'x': Icon.RADIUS,
       'y': 2 * Icon.RADIUS - 3}, this.iconGroup_);
  this.iconMark_.appendChild(document.createTextNode('?'));
};

/**
 * Create the editor for the comment's bubble.
 * @return {!Element} The top-level node of the editor.
 * @private
 */
Comment.prototype.createEditor_ = function() {
  /* Create the editor.  Here's the markup that will be generated:
    <foreignObject x="8" y="8" width="164" height="164">
      <body xmlns="http://www.w3.org/1999/xhtml" class="blocklyMinimalBody">
        <textarea xmlns="http://www.w3.org/1999/xhtml"
            class="blocklyCommentTextarea"
            style="height: 164px; width: 164px;"></textarea>
      </body>
    </foreignObject>
  */
  this.foreignObject_ = createSvgElement('foreignObject',
      {'x': Bubble.BORDER_WIDTH, 'y': Bubble.BORDER_WIDTH},
      null);
  var body = document.createElementNS(Blockly.HTML_NS, 'body');
  body.setAttribute('xmlns', Blockly.HTML_NS);
  body.className = 'blocklyMinimalBody';
  this.textarea_ = document.createElementNS(Blockly.HTML_NS, 'textarea');
  this.textarea_.className = 'blocklyCommentTextarea';
  this.textarea_.setAttribute('dir', Blockly.RTL ? 'RTL' : 'LTR');
  body.appendChild(this.textarea_);
  this.foreignObject_.appendChild(body);
  bindEvent_(this.textarea_, 'mouseup', this, this.textareaFocus_);
  bindEvent_(this.textarea_, 'blur', this, this.saveComment_);
  return this.foreignObject_;
};

/**
 * Add or remove editability of the comment.
 * @override
 */
Comment.prototype.updateEditable = function() {
  if (this.isVisible()) {
    // Toggling visibility will force a rerendering.
    this.setVisible(false);
    this.setVisible(true);
  }
  // Allow the icon to update.
  Icon.prototype.updateEditable.call(this);
};

/**
 * Callback function triggered when the bubble has resized.
 * Resize the text area accordingly.
 * @private
 */
Comment.prototype.resizeBubble_ = function() {
  var size = this.bubble_.getBubbleSize();
  var doubleBorderWidth = 2 * Bubble.BORDER_WIDTH;
  this.foreignObject_.setAttribute('width', size.width - doubleBorderWidth);
  this.foreignObject_.setAttribute('height', size.height - doubleBorderWidth);
  this.textarea_.style.width = (size.width - doubleBorderWidth - 4) + 'px';
  this.textarea_.style.height = (size.height - doubleBorderWidth - 4) + 'px';
};

var _foreignObjectSupported = (
  typeof document !== "undefined" &&
  typeof document.implementation !== "undefined" &&
  document.implementation.hasFeature("http://www.w3.org/TR/SVG11/feature#Extensibility","1.1")
);

/**
 * Show or hide the comment bubble.
 * @param {boolean} visible True if the bubble should be visible.
 */
Comment.prototype.setVisible = function(visible) {
  if (visible == this.isVisible()) {
    // No change.
    return;
  }
  if ((!this.block_.isEditable() && !this.textarea_) || !_foreignObjectSupported) {
    // Steal the code from warnings to make an uneditable text bubble.
    // MSIE does not support foreignobject; textareas are impossible.
    // http://msdn.microsoft.com/en-us/library/hh834675%28v=vs.85%29.aspx
    // Always treat comments in IE as uneditable.
    Warning.prototype.setVisible.call(this, visible);
    return;
  }
  // Save the bubble stats before the visibility switch.
  var text = this.getText();
  var size = this.getBubbleSize();
  if (visible) {
    // Create the bubble.
    this.bubble_ = new Bubble(
        /** @type {!Workspace} */ (this.block_.workspace),
        this.createEditor_(), this.block_.svg_.svgPath_,
        this.iconX_, this.iconY_,
        this.width_, this.height_);
    this.bubble_.registerResizeEvent(this, this.resizeBubble_);
    this.updateColour();
    this.text_ = null;
  } else {
    // Dispose of the bubble.
    this.bubble_.dispose();
    this.bubble_ = null;
    this.textarea_ = null;
    this.foreignObject_ = null;
  }
  // Restore the bubble stats after the visibility switch.
  this.setText(text);
  this.setBubbleSize(size.width, size.height);
};

/**
 * Bring the comment to the top of the stack when clicked on.
 * @param {!Event} e Mouse up event.
 * @private
 */
Comment.prototype.textareaFocus_ = function(e) {
  // Ideally this would be hooked to the focus event for the comment.
  // However doing so in Firefox swallows the cursor for unknown reasons.
  // So this is hooked to mouseup instead.  No big deal.
  this.bubble_.promote_();
  // Since the act of moving this node within the DOM causes a loss of focus,
  // we need to reapply the focus.
  this.textarea_.focus();
};

/**
 * Emit event to save comment value.
 * @private
 */
Comment.prototype.saveComment_ = function() {
  this.block_.workspaceEmit("block-set-comment", { id: this.block_.id, value: this.getText() });
  if (this.block_.rendered) {
    this.block_.render();
  }
};

/**
 * Get the dimensions of this comment's bubble.
 * @return {!Object} Object with width and height properties.
 */
Comment.prototype.getBubbleSize = function() {
  if (this.isVisible()) {
    return this.bubble_.getBubbleSize();
  } else {
    return {width: this.width_, height: this.height_};
  }
};

/**
 * Size this comment's bubble.
 * @param {number} width Width of the bubble.
 * @param {number} height Height of the bubble.
 */
Comment.prototype.setBubbleSize = function(width, height) {
  if (this.textarea_) {
    this.bubble_.setBubbleSize(width, height);
  } else {
    this.width_ = width;
    this.height_ = height;
  }
};

/**
 * Returns this comment's text.
 * @return {string} Comment text.
 */
Comment.prototype.getText = function() {
  return this.textarea_ ? this.textarea_.value : this.text_;
};

/**
 * Set this comment's text.
 * @param {string} text Comment text.
 */
Comment.prototype.setText = function(text) {
  if (this.textarea_) {
    this.textarea_.value = text;
  } else {
    this.text_ = text;
  }
};

/**
 * Dispose of this comment.
 */
Comment.prototype.dispose = function() {
  this.block_.comment = null;
  this.block_.workspaceEmit("block-set-comment", { id: this.block_.id, value: "" });
  Icon.prototype.dispose.call(this);
};
