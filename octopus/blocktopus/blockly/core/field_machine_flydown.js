// -*- mode: java; c-basic-offset: 2; -*-
/**
 * @license
 * @fileoverview Clickable field with flydown menu of machine getter blocks.
 * @author fturbak@wellesley.edu (Lyn Turbak)
 * @author mail@richardingham.net (Richard Ingham)
 */

'use strict';

import Blockly from './blockly';
import FieldFlydown from './field_flydown';
import {inherits} from './utils';
import {MACHINE_NAME_PREFIX} from '../constants';

/**
 * Class for a clickable global variable declaration field.
 * @param {string} text The initial parameter name in the field.
 * @extends {FieldFlydown}
 * @constructor
 */
export default function FieldMachineFlydown (name, isEditable, displayLocation, changeHandler) {
  FieldMachineFlydown.super_.call(this, name, isEditable, displayLocation,
      // rename all references to this global variable
      changeHandler)
};
inherits(FieldMachineFlydown, FieldFlydown);

FieldMachineFlydown.prototype.fieldCSSClassName = 'blocklyFieldParameter';

FieldMachineFlydown.prototype.flyoutCSSClassName = 'blocklyFieldParameterFlydown';

/**
 * Block creation menu for global variables
 * Returns a list of two XML elements: a getter block for name and a setter block for this parameter field.
 *  @return {!Array.<string>} List of two XML elements.
 **/
FieldMachineFlydown.prototype.flydownBlocksXML_ = function() {
  var name, v = this.sourceBlock_.variable_;
  if (v) {
    name = v.getDisplay() + '@@' + v.getName();
  } else {
    name = MACHINE_NAME_PREFIX + " " + this.getText(); // global name for this parameter field.
  }
  var getterSetterXML =
      '<xml>' +
        '<block type="lexical_variable_get">' +
          '<field name="VAR">' +
            name +
          '</field>' +
        '</block>' +
      '</xml>';
  return getterSetterXML;
};
