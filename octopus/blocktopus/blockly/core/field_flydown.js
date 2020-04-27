// -*- mode: java; c-basic-offset: 2; -*-
// Copyright 2013-2014 MIT, All rights reserved
// Released under the MIT License https://raw.github.com/mit-cml/app-inventor/master/mitlicense.txt
/**
 * @license
 * @fileoverview Field in which mouseover displays flyout-like menu of blocks
 * and mouse click edits the field name.
 * Flydowns are used in App Inventor for displaying get/set blocks for parameter names
 * and callers for procedure declarations.
 * @author fturbak@wellesley.edu (Lyn Turbak)
 */

'use strict';

/**
 * Class for a clickable parameter field.
 * @param {string} text The initial parameter name in the field.
 * @param {Function} opt_changeHandler An optional function that is called
 *     to validate any constraints on what the user entered.  Takes the new
 *     text as an argument and returns the accepted text or null to abort
 *     the change. E.g., for an associated getter/setter this could change
 *     references to names in this field.
 * @extends {Field}
 * @constructor
 */

 import Blockly from './blockly';
 import Flydown from './flydown';
 import FieldTextInput from './field_textinput';
 import FieldDropdown from './field_dropdown';
 import {Variable} from './variables';
 import Xml from './xml';
 import {inherits} from './utils';
 import {addClass_, removeClass_, bindEvent_, getSvgXY_} from './utils';


var FieldFlydown = function(name, isEditable, displayLocation, opt_changeHandler) {
  FieldFlydown.super_.call(this, name, opt_changeHandler);

  this.EDITABLE = isEditable; // This by itself does not control editability
  this.displayLocation = displayLocation; // [lyn, 10/27/13] Make flydown direction an instance variable
  // this.fieldGroup_.style.cursor = '';

  // Remove inherited field css classes ...
  removeClass_(/** @type {!Element} */ (this.fieldGroup_),
      'blocklyEditableText');
  removeClass_(/** @type {!Element} */ (this.fieldGroup_),
      'blocklyNoNEditableText');
  // ... and add new one, so that look and feel of flyout fields can be customized
  addClass_(/** @type {!Element} */ (this.fieldGroup_),
      this.fieldCSSClassName);

  // Only want one flydown object and associated svg per workspace
  if (! Blockly.mainWorkspace.FieldFlydown) {
    var flydown = new Flydown();
    // ***** [lyn, 10/05/2013] NEED TO WORRY ABOUT MULTIPLE BLOCKLIES! *****
    Blockly.mainWorkspace.FieldFlydown = flydown;
    var flydownSvg = flydown.createDom(this.flyoutCSSClassName);
    Blockly.svg.appendChild(flydownSvg); // Add flydown to top-level svg, *not* to main workspace svg
                                         // This is essential for correct positioning of flydown via translation
                                         // (If it's in workspace svg, it will be additionally translated by
                                         //  workspace svg translation relative to Blockly.svg.)
    flydown.init(Blockly.mainWorkspace, false); // false means no scrollbar
    flydown.autoClose = true; // Flydown closes after selecting a block
  }
};
inherits(FieldFlydown, FieldTextInput);
export default FieldFlydown;

/**
 * Milliseconds to wait before showing flydown after mouseover event on flydown field.
 * @type {number}
 * @const
 */
FieldFlydown.timeout = 500;

/**
 * Process ID for timer event to show flydown (scheduled by mouseover event)
 * @type {number}
 * @const
 */
FieldFlydown.showPid_ = 0;

/**
 * Which instance of FieldFlydown (or a subclass) is an open flydown attached to?
 * @type {FieldFlydown (or subclass)}
 * @private
 */
FieldFlydown.openFieldFlydown_ = null;

/**
 * Control positioning of flydown
 */
FieldFlydown.DISPLAY_BELOW = "BELOW";
FieldFlydown.DISPLAY_RIGHT = "RIGHT";
FieldFlydown.DISPLAY_LOCATION = FieldFlydown.DISPLAY_BELOW; // [lyn, 10/14/13] Make global for now, change in future

/**
 * Default CSS class name for the field itself
 * @type {String}
 * @const
 */
FieldFlydown.prototype.fieldCSSClassName = 'blocklyFieldFlydownField';

/**
 * Default CSS class name for the flydown that flies down from the field
 * @type {String}
 * @const
 */
FieldFlydown.prototype.flyoutCSSClassName = 'blocklyFieldFlydownFlydown';

// Override FieldTextInput's showEditor_ so it's only called for EDITABLE field.
FieldFlydown.prototype.showEditor_ = function() {
  if (this.EDITABLE) {
    FieldFlydown.super_.prototype.showEditor_.call(this);
  }
}

FieldFlydown.prototype.init = function(block) {
  FieldFlydown.super_.prototype.init.call(this, block);
  this.mouseOverWrapper_ =
      bindEvent_(this.fieldGroup_, 'mouseover', this, this.onMouseOver_);
  this.mouseOutWrapper_ =
      bindEvent_(this.fieldGroup_, 'mouseout', this, this.onMouseOut_);
};

FieldFlydown.prototype.onMouseOver_ = function(e) {
  // alert("FieldFlydown mouseover");
  if (this.sourceBlock_.isInFlyout) { // [lyn, 10/22/13] No flydowns in a flyout!
    return;
  }
  if (!this.sourceBlock_.isEditable()) {
    return;
  }
  FieldFlydown.showPid_ =
      window.setTimeout(this.showFlydownMaker_(), FieldFlydown.timeout);

  e.stopPropagation();
};

FieldFlydown.prototype.onMouseOut_ = function(e) {
  // Clear any pending timer event to show flydown
  window.clearTimeout(FieldFlydown.showPid_);
  var flydown = Blockly.mainWorkspace.FieldFlydown;
  e.stopPropagation();
};

/**
 * Returns a thunk that creates a Flydown block of the getter and setter blocks for receiver field.
 *  @return A thunk (zero-parameter function).
 */
FieldFlydown.prototype.showFlydownMaker_ = function() {
  var field = this; // Name receiver in variable so can close over this variable in returned thunk
  return function() {
    if (FieldFlydown.showPid_ != 0) {
      field.showFlydown_();
      FieldFlydown.showPid_ = 0;
    }
  };
};

/**
 * Creates a Flydown block of the getter and setter blocks for the parameter name in this field.
 */
FieldFlydown.prototype.showFlydown_ = function() {
  // Create XML elements from blocks and then create the blocks from the XML elements.
  // This is a bit crazy, but it's simplest that way. Otherwise, we'd have to duplicate
  // much of the code in Blockly.Flydown.prototype.show.
  // alert("FieldFlydown show Flydown");
  Blockly.hideChaff(); // Hide open context menus, dropDowns, flyouts, and other flydowns
  FieldFlydown.openFieldFlydown_ = this; // Remember field to which flydown is attached
  var flydown = Blockly.mainWorkspace.FieldFlydown;
  flydown.setCSSClass(this.flyoutCSSClassName); // This could have been changed by another field.
  var blocksXMLText = this.flydownBlocksXML_()
  var blocksDom = Xml.textToDom(blocksXMLText);

  var blocksXMLList = $(blocksDom).children(); // List of blocks for flydown
  var xy = getSvgXY_(this.borderRect_);
  var borderBBox = this.borderRect_.getBBox();
  var x = xy.x;
  var y = xy.y;
  if (this.displayLocation === FieldFlydown.DISPLAY_BELOW) {
    y = y + borderBBox.height;
  } else { // if (this.displayLocation === FieldFlydown.DISPLAY_RIGHT) {
    x = x + borderBBox.width;
  }
  Blockly.mainWorkspace.FieldFlydown.showAt(blocksXMLList, x, y);
};

/**
 * Hide the flydown menu and squash any timer-scheduled flyout creation
 */
FieldFlydown.hide = function() {
  // Clear any pending timer event to show flydown
  window.clearTimeout(FieldFlydown.showPid_);
  // Clear any displayed flydown
  var flydown = Blockly.mainWorkspace.FieldFlydown;
  if (flydown) {
    flydown.hide();
  }
  FieldDropdown.openFieldFlydown_ = null;
};

/**
 * Close the flydown and dispose of all UI.
 */
FieldFlydown.prototype.dispose = function() {
  if (FieldFlydown.openFieldFlydown_ == this) {
    FieldFlydown.hide();
  }
  // Call parent's destructor.
  FieldTextInput.prototype.dispose.call(this);
};


FieldFlydown.prototype.announceChanged = function (name) {
  var block = this.sourceBlock_;
  var variable = block && block.variable_;
  if (variable && variable.getName()) {
    block.workspace.startEmitTransaction();
    this.emit("changed", name);
    Variable.announceRenamed(variable.getName());
    block.workspace.completeEmitTransaction();
  } else {
    this.emit("changed", name);
  }
};
