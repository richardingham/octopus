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
 * @fileoverview Non-editable text field.  Used for titles, labels, etc.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import BlockSvg from './block_svg';
import Field from './field';
import Tooltip from './tooltip';
import {createSvgElement} from './utils';
import {inherits} from './utils';

/**
 * Class for a non-editable field.
 * @param {string} text The initial content of the field.
 * @param {string|Array} extraClass Any additional classes to add to the field.
 * @extends {Field}
 * @constructor
 */
var FieldLabel = function(text, extraClass) {
  extraClass = extraClass || '';
  if (Array.isArray(extraClass)) {
    extraClass = extraClass.join(' ');
  }

  this.sourceBlock_ = null;
  // Build the DOM.
  this.textElement_ = createSvgElement('text',
      {'class': 'blocklyText ' + extraClass}, null);
  this.size_ = {height: 25, width: 0};
  this.setText(text);
};
inherits(FieldLabel, Field);
export default FieldLabel;

/**
 * Clone this FieldLabel.
 * @return {!FieldLabel} The result of calling the constructor again
 *   with the current values of the arguments used during construction.
 */
FieldLabel.prototype.clone = function() {
  return new FieldLabel(this.getText());
};

/**
 * Editable fields are saved by the XML renderer, non-editable fields are not.
 */
FieldLabel.prototype.EDITABLE = false;

/**
 * Install this text on a block.
 * @param {!Block} block The block containing this text.
 */
FieldLabel.prototype.init = function(block) {
  if (this.sourceBlock_) {
    throw 'Text has already been initialized once.';
  }
  this.sourceBlock_ = block;
  block.getSvgRoot().appendChild(this.textElement_);

  // Configure the field to be transparent with respect to tooltips.
  this.textElement_.tooltip = this.sourceBlock_;
  Tooltip.bindMouseEvents(this.textElement_);
};

/**
 * Dispose of all DOM objects belonging to this text.
 */
FieldLabel.prototype.dispose = function() {
  var node = this.textElement_
  if (node && node.parentNode) node.parentNode.removeChild(node);
  this.textElement_ = null;
};

/**
 * Gets the group element for this field.
 * Used for measuring the size and for positioning.
 * @return {!Element} The group element.
 */
FieldLabel.prototype.getRootElement = function() {
  return /** @type {!Element} */ (this.textElement_);
};

/**
 * Change the tooltip text for this field.
 * @param {string|!Element} newTip Text for tooltip or a parent element to
 *     link to for its tooltip.
 */
FieldLabel.prototype.setTooltip = function(newTip) {
  this.textElement_.tooltip = newTip;
};
