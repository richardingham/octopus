// -*- mode: java; c-basic-offset: 2; -*-
// Copyright 2013-2014 MIT, All rights reserved
// Released under the MIT License https://raw.github.com/mit-cml/app-inventor/master/mitlicense.txt
/**
 * @license
 * @fileoverview Drop-down chooser of variables in the current lexical scope for App Inventor
 * @author fturbak@wellesley.com (Lyn Turbak)
 * @author mail@richardingham.net (Richard Ingham)
 */

'use strict';

import Blockly from './blockly';
import BlockSvg from './block_svg';
import FieldDropdown from './field_dropdown';
import Tooltip from './tooltip';
import WidgetDiv from './widgetdiv';
import {GlobalScope} from './variables';
import {inherits} from './utils';
import {getAbsoluteXY_, createSvgElement} from './utils';

/**
 * Class for a variable's dropdown field.
 * @param {!string} varname The default name for the variable.  If null,
 *     a unique variable name will be generated.
 * @extends FieldDropdown
 * @constructor
 */
export default function FieldLexicalVariable (varname, filter, noVariablesMessage) {
  this.menuGenerator_ = FieldLexicalVariable.dropdownCreate;
  this.arrow_ = createSvgElement("tspan", {}, null);
  this.arrow_.appendChild(document.createTextNode(Blockly.RTL ? FieldDropdown.ARROW_CHAR + " " : " " + FieldDropdown.ARROW_CHAR));

  this.noVariablesMessage = noVariablesMessage || 'No variables defined';

  FieldDropdown.super_.call(this, " ")

  this.setText(varname);

  this.filter_ = filter || {};
};
inherits(FieldLexicalVariable, FieldDropdown);

/**
 * Get the variable's name (use a variableDB to convert into a real name).
 * Unline a regular dropdown, variables are literal and have no neutral value.
 * @return {string} Current text.
 */
FieldLexicalVariable.prototype.getValue = function() {
  return (this.value_ && this.value_.trim()) ? this.text_ + '@@' + this.value_ : this.text_;
};

FieldLexicalVariable.prototype.getFullVariableName = function() {
  return this.value_;
};

FieldLexicalVariable.prototype.getVariableName = function() {
  return this.value_.split('::').slice(0, 2).join('::');
};

FieldLexicalVariable.prototype.getAttributeName = function() {
  return this.value_.split('::').slice(2, 3).join('');
};

/**
 * Set the variable name.
 * @param {string} text New text.
 */
FieldLexicalVariable.prototype.setValue = function (variable) {
  if (this.block_ && this.block_.isInFlyout) {
    var i1 = variable.indexOf('::');
    var i2 = variable.indexOf('@@');
    if (i1 >= 0 && i2 >= 0 && i2 < i1) {
      this.value_ = variable.substring(2 + i2);
      this.setText(variable.substring(0, i2));
      return this.value_;
    }
    this.value_ = variable;
    this.setText(variable);
    return this.value_;
  }
  if (typeof variable === "string" && this.block_) {
    var i1 = variable.indexOf('::');
    var i2 = variable.indexOf('@@');
    if (i1 >= 0 && i2 >= 0 && i2 < i1) {
      this.value_ = variable.substring(2 + i2);
      this.setText(variable.substring(0, i2));
      return this.value_;
    } else {
      var scope = this.block_.getVariableScope();
      var scopedVariable = scope.getScopedVariable(variable);
      if (scopedVariable) {
        variable = scopedVariable;
      }
    }
  }
  if (!variable || typeof variable === "string") {
    this.value_ = variable || "";
    this.setText(variable || "");
    return this.value_;
  }
  if (this.block_.variableChanged_) {
    this.block_.variableChanged_(variable);
  }
  this.value_ = variable.getName();
  this.setText(variable.getDisplay());

  return this.value_;
  // Blockly.WarningHandler.checkErrors.call(this.sourceBlock_);
};


/**
 * Get the block holding this drop-down variable chooser
 * @return {string} Block holding this drop-down variable chooser.
 */
FieldLexicalVariable.prototype.getBlock = function() {
  return this.block_;
};

/**
 * Set the block holding this drop-down variable chooser. Also initializes the cachedParent.
 * @param {string} block Block holding this drop-down variable chooser
 */
FieldLexicalVariable.prototype.setBlock = function(block) {
  this.block_ = block;
  this.setCachedParent(block.getParent());
};

/**
 * Get the cached parent of the block holding this drop-down variable chooser
 * @return {string} Cached parent of the block holding this drop-down variable chooser.
 */
FieldLexicalVariable.prototype.getCachedParent = function() {
  return this.cachedParent_;
};

/**
 * Set the cached parent of the block holding this drop-down variable chooser.
 * This is used for detecting when the parent has changed in the onchange event handler.
 * @param {string} Parent of the block holding this drop-down variable chooser
 */
FieldLexicalVariable.prototype.setCachedParent = function(parent) {
  this.cachedParent_ = parent;
};

/**
 * @this A FieldLexicalVariable instance
 * @returns {list} A list of all global and lexical names in scope at the point of the getter/setter
 *   block containing this FieldLexicalVariable instance. Global names are listed in sorted
 *   order before lexical names in sorted order.
 */
// [lyn, 12/24/12] Clean up of name prefixes; most work done earlier by paulmw
// [lyn, 11/29/12] Now handle params in control constructs
// [lyn, 11/18/12] Clarified structure of namespaces
// [lyn, 11/17/12]
// * Now handle event params.
// * Commented out loop params because AI doesn't handle loop variables correctly yet.
// [lyn, 11/10/12]
// Returns the names of all names in lexical scope for the block associated with this menu.
// including global variable names.
// * Each global name is prefixed with "global "
// * If Blockly.showPrefixToUser is false, non-global names are not prefixed.
// * If Blockly.showPrefixToUser is true, non-global names are prefixed with labels
//   specified in blocklyeditor.js

FieldLexicalVariable.prototype.getNamesInScope = function () {
  return FieldLexicalVariable.getNamesInScope.call(this, this.block_);
}

function _compareVariables (a, b) {
  if (a.subScope_ < b.subScope_) {
    return -1;
  }
  if (a.subScope_ > b.subScope_) {
    return 1;
  }
  if (a.varName_ < b.varName_) {
    return -1;
  }
  if (a.varName_ > b.varName_) {
    return 1;
  }
  // a must be equal to b
  return 0;
}

/**
 * @param block
 * @returns {list} A list of all global and lexical names in scope at the given block.
 *   Global names are listed in sorted order before lexical names in sorted order.
 */
FieldLexicalVariable.getNamesInScope = function (block) {

  var variables = GlobalScope.getVariables().slice();
  variables.sort(_compareVariables);

  if (block) {
    var allLexicalNames = block.getVariableScope().getVariablesInScope();
    if (allLexicalNames.length > 0) {
      if (variables.length > 0) {
        variables.push("separator");
      }
      variables = variables.concat(allLexicalNames);
    }
  }

  return variables;
}

/**
 * Return a sorted list of variable names for variable dropdown menus.
 * @return {!Array.<string>} Array of variable names.
 * @this {!FieldLexicalVariable}
 */
FieldLexicalVariable.dropdownCreate = function() {
  return this.getNamesInScope();
};


/**
 * Create a dropdown menu under the text. This dropdown menu allows submenus
 * for selecting machine components, and disabled / enabled states for
 * getters / setters.
 * @private
 */
FieldLexicalVariable.prototype.showEditor_ = function() {
  WidgetDiv.show(this, function () {
    thisField.menu.closemenu();
  });
  var thisField = this;
  var selected = this.value_;
  var filter = this.filter_;
  var noVariablesMessage = this.noVariablesMessage;

  function callback(value) {
    if (thisField.changeHandler_) {
      // Call any change handler, and allow it to override.
      var override = thisField.changeHandler_(value);
      if (override !== undefined) {
        value = override;
      }
    }
    if (value !== null) {
      thisField.setValue(value);
      thisField.emit("changed", value.getName());
    }
    WidgetDiv.hideIfOwner(thisField);
  }

  function contains (a, o) {
    for (var i = 0, m = a.length; i < m; i++) {
        if (a[i] === o) {
            return true;
        }
    }
    return false;
  }

  function enabled (variable) {
    if (typeof filter.readonly !== "undefined" && !filter.readonly && variable.readonly) {
      return false;
    }
    if (typeof filter.type !== "undefined" && variable.getType()) {
      if (Array.isArray(filter.type) && !contains(variable.getType())) {
        return false;
      } else if (filter.type !== variable.getType()) {
        return false;
      }
    }
    for (var flag in filter) {
      if (filter.hasOwnProperty(flag) && flag != 'type' && flag != 'readonly') {
        if (!variable.flags[flag]) {
          return false;
        }
      }
    }
    return true;
  }

  // Build a menu or submenu
  function build (options, subMenu) {
    // If a submenu item is checked, all parent items will be checked.
    // This value is returned by build() to enable this.
    var menu = [];
    var checked = false;
    var option, menuItem;

    if (!subMenu && options.length === 0) {
      menu.push({
      text: "No variables defined",
      enabled: false,
       });
      options = [];
    }

    for (var x = 0; x < options.length; x++) {
      option = options[x];

      // Separators are allowed.
      if (option === "separator") {
        menuItem = { divider: true };
      }

      // Everything else will be a Blockly.Variable.
      else if (option.getName) {
        menuItem = {
          text: option.getMenu(),  // Human-readable text.
          value: option, // Language-neutral value.
          enabled: enabled(option)
        };
        var attributes = option.getAttributes();

        // If a submenu is required
        if (attributes.length) {
          var children = build(attributes, true);

          if (children.length) {
            menuItem.children = children;

            // If one of the child items is checked, the parent is checked.
            if (menuItem.children.isChecked) {
              menuItem.selected = true;
              checked = true;
            }
          }

          //menuItem.enabled = true;
          menuItem.children = build(attributes, true);
          var subChecked = menuItem.children.isChecked;

          // Unless the parent menu item is disabled, add an entry
          // to allow the parent to be selected.
          /*if (menuItem.enabled) {
            var same = (option.getName() === selected);
            menuItem.children = [{
                text: menuItem.text,
                value: menuItem.value,
                selected: same
              }, {
                divider: true
              }].concat(menuItem.children);
            subChecked |= same;
          }*/

          // If one of the child items is checked, the parent is checked.
          if (subChecked) {
            menuItem.selected = true;
          }
          checked |= subChecked;
        }

        // Just a regular menu item.
        if (!menuItem.children) {
          var same = (option.getName() === selected);
          menuItem.selected = same;
          checked |= same;
        }
      }

      // "disabled" items are not added to the menu.
      if (menuItem.enabled || (menuItem.children && menuItem.children.length)) {
        menu.push(menuItem);
      }
    }

    if (!subMenu && menu.length === 0 ) {
      menu.push({
        text: noVariablesMessage,
        enabled: false
      });
      options = [];
    }

    menu.isChecked = checked;
    return menu;
  }

  var options = this.getOptions_();
  this.menu = new ContextMenu(build(options), callback, { selectable: true });

  var xy = getAbsoluteXY_(/** @type {!Element} */ (this.borderRect_));
  var borderBBox = this.borderRect_.getBBox();
  this.menu.showForBox(xy, borderBBox);
};


/**
 * Split name into digit suffix and prefix before it.
 * Return two-element list of prefix and suffix strings. Suffix is empty if no digits.
 * @param {string} name Input string
 * @return {string list} Two-element list of prefix and suffix
 */
FieldLexicalVariable.prefixSuffix = function(name) {
  var prefix = name;
  var suffix = "";
  var matchResult = name.match(/^(.*?)(\d+)$/);
  if (matchResult)
    return [matchResult[1], matchResult[2]]; // List of prefix and suffix
  else
    return [name, ""];
}
