// -*- mode: java; c-basic-offset: 2; -*-
// Copyright 2013-2014 MIT, All rights reserved
// Released under the MIT License https://raw.github.com/mit-cml/app-inventor/master/mitlicense.txt
/**
 * @license
 * @fileoverview Clickable field with flydown menu of global getter and setter blocks.
 * @author fturbak@wellesley.edu (Lyn Turbak)
 */

'use strict';

import Blockly from './blockly';
import FieldFlydown from './field_flydown';
import {inherits} from './utils';
import {GLOBAL_NAME_PREFIX} from '../constants';

/**
 * Class for a clickable global variable declaration field.
 * @param {string} text The initial parameter name in the field.
 * @extends {Field}
 * @constructor
 */
var FieldGlobalFlydown = function(name, isEditable, displayLocation, changeHandler) {
  FieldGlobalFlydown.super_.call(this, name, isEditable, displayLocation, changeHandler);
};
inherits(FieldGlobalFlydown, FieldFlydown);
export default FieldGlobalFlydown;

FieldGlobalFlydown.prototype.fieldCSSClassName = 'blocklyFieldParameter';

FieldGlobalFlydown.prototype.flyoutCSSClassName = 'blocklyFieldParameterFlydown';

/**
 * Block creation menu for global variables
 * Returns a list of two XML elements: a getter block for name and a setter block for this parameter field.
 *  @return {!Array.<string>} List of two XML elements.
 **/
FieldGlobalFlydown.prototype.flydownBlocksXML_ = function() {
  var name, v = this.sourceBlock_.variable_;
  if (v) {
    name = v.getDisplay() + '@@' + v.getName();
  } else {
    name = GLOBAL_NAME_PREFIX + " " + this.getText(); // global name for this parameter field.
  }
  var getterSetterXML =
      '<xml>' +
        '<block type="lexical_variable_get">' +
          '<field name="VAR">' +
            name +
          '</field>' +
        '</block>' +
        '<block type="lexical_variable_set">' +
          '<field name="VAR">' +
            name +
          '</field>' +
        '</block>' +
      '</xml>';
  return getterSetterXML;
};
