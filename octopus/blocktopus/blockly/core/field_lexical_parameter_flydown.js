// -*- mode: java; c-basic-offset: 2; -*-
/**
 * @license
 * @fileoverview Clickable field with flydown menu of local parameter getter blocks.
 * @author fturbak@wellesley.edu (Lyn Turbak)
 * @author mail@richardingham.net (Richard Ingham)
 */

'use strict';

import Blockly from './blockly';
import FieldFlydown from './field_flydown';
import {inherits} from './utils';

/**
 * Class for a clickable global variable declaration field.
 * @param {string} text The initial parameter name in the field.
 * @extends {FieldFlydown}
 * @constructor
 */
export default function FieldLexicalParameterFlydown (name, isEditable, displayLocation, changeHandler) {
  FieldLexicalParameterFlydown.super_.call(this, name, isEditable, displayLocation,
      // rename all references to this global variable
      changeHandler)
};
inherits(FieldLexicalParameterFlydown, FieldFlydown);

FieldLexicalParameterFlydown.prototype.fieldCSSClassName = 'blocklyFieldParameter';

FieldLexicalParameterFlydown.prototype.flyoutCSSClassName = 'blocklyFieldParameterFlydown';

/**
 * Block creation menu for global variables
 * Returns a list of two XML elements: a getter block for name and a setter block for this parameter field.
 *  @return {!Array.<string>} List of two XML elements.
 **/
FieldLexicalParameterFlydown.prototype.flydownBlocksXML_ = function() {
  var name, v = this.sourceBlock_.variable_;
  if (v) {
    name = v.getDisplay() + '@@' + v.getName();
  } else {
    name = this.getText();
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
