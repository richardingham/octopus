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
 * @fileoverview Logic blocks for Blockly.
 * @author q.neutron@gmail.com (Quynh Neutron)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import FieldDropdown from '../core/field_dropdown';
import {LOGIC_CATEGORY_HUE} from '../colourscheme';

Blocks['logic_compare'] = {
  /**
   * Block for comparison operator.
   * @this Block
   */
  init: function() {
    var OPERATORS = Blockly.RTL ? [
          ['=', 'EQ'],
          ['\u2260', 'NEQ'],
          ['>', 'LT'],
          ['\u2265', 'LTE'],
          ['<', 'GT'],
          ['\u2264', 'GTE']
        ] : [
          ['=', 'EQ'],
          ['\u2260', 'NEQ'],
          ['<', 'LT'],
          ['\u2264', 'LTE'],
          ['>', 'GT'],
          ['\u2265', 'GTE']
        ];
    this.setHelpUrl(Msg.LOGIC_COMPARE_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.setOutput(true, 'Boolean');
    this.appendValueInput('A');
    this.appendValueInput('B')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    this.setInputsInline(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var op = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'EQ': Msg.LOGIC_COMPARE_TOOLTIP_EQ,
        'NEQ': Msg.LOGIC_COMPARE_TOOLTIP_NEQ,
        'LT': Msg.LOGIC_COMPARE_TOOLTIP_LT,
        'LTE': Msg.LOGIC_COMPARE_TOOLTIP_LTE,
        'GT': Msg.LOGIC_COMPARE_TOOLTIP_GT,
        'GTE': Msg.LOGIC_COMPARE_TOOLTIP_GTE
      };
      return TOOLTIPS[op];
    });
  }
};

Blocks['logic_operation'] = {
  /**
   * Block for logical operations: 'and', 'or'.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.LOGIC_OPERATION_AND, 'AND'],
         [Msg.LOGIC_OPERATION_OR, 'OR']];
    this.setHelpUrl(Msg.LOGIC_OPERATION_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.setOutput(true, 'Boolean');
    this.appendValueInput('A')
        .setCheck('Boolean');
    this.appendValueInput('B')
        .setCheck('Boolean')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    this.setInputsInline(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var op = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'AND': Msg.LOGIC_OPERATION_TOOLTIP_AND,
        'OR': Msg.LOGIC_OPERATION_TOOLTIP_OR
      };
      return TOOLTIPS[op];
    });
  }
};

Blocks['logic_negate'] = {
  /**
   * Block for negation.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.LOGIC_NEGATE_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.setOutput(true, 'Boolean');
    this.interpolateMsg(Msg.LOGIC_NEGATE_TITLE,
                        ['BOOL', 'Boolean', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setTooltip(Msg.LOGIC_NEGATE_TOOLTIP);
  }
};

Blocks['logic_boolean'] = {
  /**
   * Block for boolean data type: true and false.
   * @this Block
   */
  init: function() {
    var BOOLEANS =
        [[Msg.LOGIC_BOOLEAN_TRUE, 'TRUE'],
         [Msg.LOGIC_BOOLEAN_FALSE, 'FALSE']];
    this.setHelpUrl(Msg.LOGIC_BOOLEAN_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.setOutput(true, 'Boolean');
    this.appendDummyInput()
        .appendField(new FieldDropdown(BOOLEANS), 'BOOL');
    this.setTooltip(Msg.LOGIC_BOOLEAN_TOOLTIP);
  }
};

Blocks['logic_null'] = {
  /**
   * Block for null data type.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.LOGIC_NULL_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.setOutput(true);
    this.appendDummyInput()
        .appendField(Msg.LOGIC_NULL);
    this.setTooltip(Msg.LOGIC_NULL_TOOLTIP);
  }
};

Blocks['logic_ternary'] = {
  /**
   * Block for ternary operator.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.LOGIC_TERNARY_HELPURL);
    this.setColour(LOGIC_CATEGORY_HUE);
    this.appendValueInput('IF')
        .setCheck('Boolean')
        .appendField(Msg.LOGIC_TERNARY_CONDITION);
    this.appendValueInput('THEN')
        .appendField(Msg.LOGIC_TERNARY_IF_TRUE);
    this.appendValueInput('ELSE')
        .appendField(Msg.LOGIC_TERNARY_IF_FALSE);
    this.setOutput(true);
    this.setTooltip(Msg.LOGIC_TERNARY_TOOLTIP);
  }
};
