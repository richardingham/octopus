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
 * @fileoverview Object representing an input (value, statement, or dummy).
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import EventEmitter from 'events';
import Blockly from './blockly';
import FieldLabel from './field_label';
import {inherits} from './utils';
import {bindEvent_, unbindEvent_, addClass_, removeClass_, getRelativeXY_} from './utils';

/**
 * Class for an input with an optional field.
 * @param {number} type The type of the input.
 * @param {string} name Language-neutral identifier which may used to find this
 *     input again.
 * @param {!Block} block The block containing this input.
 * @param {Blockly.Connection} connection Optional connection for this input.
 * @constructor
 */
export default function Input (type, name, block, connection) {
  this.type = type;
  this.name = name;
  this.sourceBlock_ = block;
  this.connection = connection;
  this.fieldRow = [];
  this.align = Blockly.ALIGN_LEFT;

  this.visible_ = true;

  EventEmitter.call(this);
};
inherits(Input, EventEmitter);

/**
 * Add an item to the end of the input's field row.
 * @param {string|!Field} field Something to add as a field.
 * @param {string} opt_name Language-neutral identifier which may used to find
 *     this field again.  Should be unique to the host block.
 * @return {!Input} The input being append to (to allow chaining).
 */
Input.prototype.appendField = function(field, opt_name) {
  return this.insertField(this.fieldRow.length, field, opt_name);
};

/**
 * Insert an item into the input's field row.
 * @param {integer} position Position to insert the field. If -1, place at the end.
 * @param {string|!Field} field Something to add as a field.
 * @param {string} opt_name Language-neutral identifier which may used to find
 *     this field again.  Should be unique to the host block.
 * @return {!Input} The input being append to (to allow chaining).
 */
Input.prototype.insertField = function(position, field, opt_name) {
  // Empty string, Null or undefined generates no field, unless field is named.
  if (!field && !opt_name) {
    return this;
  }
  // Generate a FieldLabel when given a plain text field.
  if (typeof field === 'string') {
    field = new FieldLabel(/** @type {string} */ (field));
  }
  if (this.sourceBlock_.svg_) {
    field.init(this.sourceBlock_);
  }
  field.name = opt_name;

  // Add the field to the field row.

  this.fieldRow.splice(position, 0, field);
  if (field.suffixField) {
    // Add any suffix.
    this.insertField(position + 1, field.suffixField);
  }
  if (field.prefixField) {
    // Add any prefix.
    this.insertField(position - 1, field.prefixField);
  }

  field.on("changed", function (value) {
    this.emit("field-changed", field.name, value);
  }.bind(this));

  if (this.sourceBlock_.rendered) {
    this.sourceBlock_.render();
    // Adding a field will cause the block to change shape.
    this.sourceBlock_.bumpNeighbours_();
  }
  return this;
};

/**
 * Add an item to the end of the input's field row.
 * @param {*} field Something to add as a field.
 * @param {string} opt_name Language-neutral identifier which may used to find
 *     this field again.  Should be unique to the host block.
 * @return {!Input} The input being append to (to allow chaining).
 * @deprecated December 2013
 */
Input.prototype.appendTitle = function(field, opt_name) {
  console.log('Deprecated call to appendTitle, use appendField instead.');
  return this.appendField(field, opt_name);
};

/**
 * Remove a field from this input.
 * @param {string} name The name of the field.
 * @param {boolean} opt_quiet Suppress error if field not present.
 * @throws {Error} if the field is not present.
 */
Input.prototype.removeField = function(name, opt_quiet) {
  for (var i = 0, field; field = this.fieldRow[i]; i++) {
    if (field.name === name) {
      field.removeAllListeners();
      field.dispose();
      this.fieldRow.splice(i, 1);
      if (this.sourceBlock_.rendered) {
        this.sourceBlock_.render();
        // Removing a field will cause the block to change shape.
        this.sourceBlock_.bumpNeighbours_();
      }
      return;
    }
  }
  if (!opt_quiet) {
    throw new Error('Field "' + name + '" not found.');
  }
};

/**
 * Gets whether this input is visible or not.
 * @return {boolean} True if visible.
 */
Input.prototype.isVisible = function() {
  return this.visible_;
};

/**
 * Sets whether this input is visible or not.
 * @param {boolean} visible True if visible.
 * @return {!Array.<!Block>} List of blocks to render.
 */
Input.prototype.setVisible = function(visible) {
  var renderList = [];
  if (this.visible_ == visible) {
    return renderList;
  }
  this.visible_ = visible;

  var display = visible ? 'block' : 'none';
  for (var y = 0, field; field = this.fieldRow[y]; y++) {
    field.setVisible(visible);
  }
  if (this.connection) {
    // Has a connection.
    if (visible) {
      renderList = this.connection.unhideAll();
    } else {
      this.connection.hideAll();
    }
    var child = this.connection.targetBlock();
    if (child) {
      child.svg_.getRootElement().style.display = display;
      if (!visible) {
        child.rendered = false;
      }
    }
  }
  return renderList;
};

/**
 * Change a connection's compatibility.
 * @param {string|Array.<string>|null} check Compatible value type or
 *     list of value types.  Null if all types are compatible.
 * @return {!Input} The input being modified (to allow chaining).
 */
Input.prototype.setCheck = function(check) {
  if (!this.connection) {
    throw 'This input does not have a connection.';
  }
  this.connection.setCheck(check);
  return this;
};

/**
 * Change the alignment of the connection's field(s).
 * @param {number} align One of Blockly.ALIGN_LEFT, ALIGN_CENTRE, ALIGN_RIGHT.
 *   In RTL mode directions are reversed, and ALIGN_RIGHT aligns to the left.
 * @return {!Input} The input being modified (to allow chaining).
 */
Input.prototype.setAlign = function(align) {
  this.align = align;
  if (this.sourceBlock_.rendered) {
    this.sourceBlock_.render();
  }
  return this;
};

/**
 * Initialize the fields on this input.
 */
Input.prototype.init = function() {
  for (var x = 0; x < this.fieldRow.length; x++) {
    this.fieldRow[x].init(this.sourceBlock_);
  }
};

/**
 * Sever all links to this input.
 */
Input.prototype.dispose = function() {
  for (var i = 0, field; field = this.fieldRow[i]; i++) {
    field.dispose();
  }
  if (this.connection) {
    this.connection.dispose();
  }
  this.sourceBlock_ = null;
};
