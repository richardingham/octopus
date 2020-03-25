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
 * @fileoverview Math blocks for Blockly.
 * @author q.neutron@gmail.com (Quynh Neutron)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import Names from '../core/names';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import FieldLexicalVariable from '../core/field_lexical_variable';
import {withVariableDropdown, addUnitDropdown} from './mixins.js';
import {MATH_CATEGORY_HUE} from '../colourscheme';
import {numberValidator} from '../core/validators';

Blocks['math_number'] = {
  /**
   * Block for numeric value.
   * @this Block
   */
  init: function() {
    this.fieldNumber_ = new FieldTextInput('0', numberValidator);
    this.setHelpUrl(Msg.MATH_NUMBER_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(this.fieldNumber_, 'NUM');
    this.setOutput(true, 'Number');
    this.setTooltip(Msg.MATH_NUMBER_TOOLTIP);
  }
};

Blocks['math_arithmetic'] = {
  /**
   * Block for basic arithmetic operator.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.MATH_ADDITION_SYMBOL, 'ADD'],
         [Msg.MATH_SUBTRACTION_SYMBOL, 'MINUS'],
         [Msg.MATH_MULTIPLICATION_SYMBOL, 'MULTIPLY'],
         [Msg.MATH_DIVISION_SYMBOL, 'DIVIDE'],
         [Msg.MATH_POWER_SYMBOL, 'POWER']];
    this.setHelpUrl(Msg.MATH_ARITHMETIC_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('A')
        .setCheck('Number');
    this.appendValueInput('B')
        .setCheck('Number')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    this.setInputsInline(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'ADD': Msg.MATH_ARITHMETIC_TOOLTIP_ADD,
        'MINUS': Msg.MATH_ARITHMETIC_TOOLTIP_MINUS,
        'MULTIPLY': Msg.MATH_ARITHMETIC_TOOLTIP_MULTIPLY,
        'DIVIDE': Msg.MATH_ARITHMETIC_TOOLTIP_DIVIDE,
        'POWER': Msg.MATH_ARITHMETIC_TOOLTIP_POWER
      };
      return TOOLTIPS[mode];
    });
  }
};

Blocks['math_single'] = {
  /**
   * Block for advanced math operators with single operand.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.MATH_SINGLE_OP_ROOT, 'ROOT'],
         [Msg.MATH_SINGLE_OP_ABSOLUTE, 'ABS'],
         ['-', 'NEG'],
         ['ln', 'LN'],
         ['log10', 'LOG10'],
         ['e^', 'EXP'],
         ['10^', 'POW10']];
    this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.interpolateMsg('%1 %2',
        ['OP', new FieldDropdown(OPERATORS)],
        ['NUM', 'Number', Blockly.ALIGN_RIGHT],
        Blockly.ALIGN_RIGHT);
    this.setInputsInline(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'ROOT': Msg.MATH_SINGLE_TOOLTIP_ROOT,
        'ABS': Msg.MATH_SINGLE_TOOLTIP_ABS,
        'NEG': Msg.MATH_SINGLE_TOOLTIP_NEG,
        'LN': Msg.MATH_SINGLE_TOOLTIP_LN,
        'LOG10': Msg.MATH_SINGLE_TOOLTIP_LOG10,
        'EXP': Msg.MATH_SINGLE_TOOLTIP_EXP,
        'POW10': Msg.MATH_SINGLE_TOOLTIP_POW10
      };
      return TOOLTIPS[mode];
    });
  }
};

Blocks['math_trig'] = {
  /**
   * Block for trigonometry operators.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.MATH_TRIG_SIN, 'SIN'],
         [Msg.MATH_TRIG_COS, 'COS'],
         [Msg.MATH_TRIG_TAN, 'TAN'],
         [Msg.MATH_TRIG_ASIN, 'ASIN'],
         [Msg.MATH_TRIG_ACOS, 'ACOS'],
         [Msg.MATH_TRIG_ATAN, 'ATAN']];
    this.setHelpUrl(Msg.MATH_TRIG_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('NUM')
        .setCheck('Number')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'SIN': Msg.MATH_TRIG_TOOLTIP_SIN,
        'COS': Msg.MATH_TRIG_TOOLTIP_COS,
        'TAN': Msg.MATH_TRIG_TOOLTIP_TAN,
        'ASIN': Msg.MATH_TRIG_TOOLTIP_ASIN,
        'ACOS': Msg.MATH_TRIG_TOOLTIP_ACOS,
        'ATAN': Msg.MATH_TRIG_TOOLTIP_ATAN
      };
      return TOOLTIPS[mode];
    });
  }
};

Blocks['math_constant'] = {
  /**
   * Block for constants: PI, E, the Golden Ratio, sqrt(2), 1/sqrt(2), INFINITY.
   * @this Block
   */
  init: function() {
    var CONSTANTS =
        [['\u03c0', 'PI'],
         ['e', 'E'],
         ['\u03c6', 'GOLDEN_RATIO'],
         ['sqrt(2)', 'SQRT2'],
         ['sqrt(\u00bd)', 'SQRT1_2'],
         ['\u221e', 'INFINITY']];
    this.setHelpUrl(Msg.MATH_CONSTANT_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendDummyInput()
        .appendField(new FieldDropdown(CONSTANTS), 'CONSTANT');
    this.setTooltip(Msg.MATH_CONSTANT_TOOLTIP);
  }
};

Blocks['math_number_property'] = {
  /**
   * Block for checking if a number is even, odd, prime, whole, positive,
   * negative or if it is divisible by certain number.
   * @this Block
   */
  init: function() {
    var PROPERTIES =
        [[Msg.MATH_IS_EVEN, 'EVEN'],
         [Msg.MATH_IS_ODD, 'ODD'],
         [Msg.MATH_IS_WHOLE, 'WHOLE'],
         [Msg.MATH_IS_POSITIVE, 'POSITIVE'],
         [Msg.MATH_IS_NEGATIVE, 'NEGATIVE'],
         [Msg.MATH_IS_DIVISIBLE_BY, 'DIVISIBLE_BY']];
    this.setColour(MATH_CATEGORY_HUE);
    this.appendValueInput('NUMBER_TO_CHECK')
        .setCheck('Number');
    var dropdown = new FieldDropdown(PROPERTIES, function(option) {
      var divisorInput = (option == 'DIVISIBLE_BY');
      this.sourceBlock_.updateShape_(divisorInput);
    });
    this.appendDummyInput()
        .appendField(dropdown, 'PROPERTY');
    this.setInputsInline(true);
    this.setOutput(true, 'Boolean');
    this.setTooltip(Msg.MATH_IS_TOOLTIP);
  },
  /**
   * Create XML to represent whether the 'divisorInput' should be present.
   * @return {Element} XML storage element.
   * @this Block
   */
  mutationToDom: function() {
    var container = document.createElement('mutation');
    var divisorInput = (this.getFieldValue('PROPERTY') == 'DIVISIBLE_BY');
    container.setAttribute('divisor_input', divisorInput);
    return container;
  },
  /**
   * Parse XML to restore the 'divisorInput'.
   * @param {!Element} xmlElement XML storage element.
   * @this Block
   */
  domToMutation: function(xmlElement) {
    var divisorInput = (xmlElement.getAttribute('divisor_input') == 'true');
    this.updateShape_(divisorInput);
  },
  /**
   * Modify this block to have (or not have) an input for 'is divisible by'.
   * @param {boolean} divisorInput True if this block has a divisor input.
   * @private
   * @this Block
   */
  updateShape_: function(divisorInput) {
    // Add or remove a Value Input.
    var inputExists = this.getInput('DIVISOR');
    if (divisorInput) {
      if (!inputExists) {
        this.appendValueInput('DIVISOR')
            .setCheck('Number');
      }
    } else if (inputExists) {
      this.removeInput('DIVISOR');
    }
  }
};

Blocks['math_change'] = {
  /**
   * Block for adding to a variable in place.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.MATH_CHANGE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.fieldVar_ = new FieldLexicalVariable(" ", { readonly: false, type: "Number" });
    this.fieldVar_.setBlock(this);
    this.appendDummyInput('VARIABLE')
		.appendField(new FieldDropdown([
			['increment', 'INCREMENT'],
			['decrement', 'DECREMENT']
		]), 'MODE')
        .appendField(this.fieldVar_, 'VAR');
    this.appendDummyInput('_UNIT').appendField('...', 'UNIT').setVisible(false);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      // TODO: new tooltips
      return Msg.MATH_CHANGE_TOOLTIP.replace('%1',
          thisBlock.getFieldValue('VAR'));
    });

    // TODO: need to filter only number variables in dropdown.
    withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  },
  variableChanged_: function (variable) {
    var input = this.getInput('VARIABLE');
    var currentUnitSelection = this.getFieldValue('UNIT');

    input.removeField('BY', true);
    input.removeField('UNIT', true);

    // Unit
    if (variable.flags.unit) {
      input.appendField('by 1', 'BY');
    }
    addUnitDropdown(this, input, variable, currentUnitSelection);
  }
};

Blocks['math_round'] = {
  /**
   * Block for rounding functions.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.MATH_ROUND_OPERATOR_ROUND, 'ROUND'],
         [Msg.MATH_ROUND_OPERATOR_ROUNDUP, 'ROUNDUP'],
         [Msg.MATH_ROUND_OPERATOR_ROUNDDOWN, 'ROUNDDOWN']];
    this.setHelpUrl(Msg.MATH_ROUND_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('NUM')
        .setCheck('Number')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    this.setTooltip(Msg.MATH_ROUND_TOOLTIP);
  }
};

Blocks['math_on_list'] = {
  /**
   * Block for evaluating a list of numbers to return sum, average, min, max,
   * etc.  Some functions also work on text (min, max, mode, median).
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.MATH_ONLIST_OPERATOR_SUM, 'SUM'],
         [Msg.MATH_ONLIST_OPERATOR_MIN, 'MIN'],
         [Msg.MATH_ONLIST_OPERATOR_MAX, 'MAX'],
         [Msg.MATH_ONLIST_OPERATOR_AVERAGE, 'AVERAGE'],
         [Msg.MATH_ONLIST_OPERATOR_MEDIAN, 'MEDIAN'],
         [Msg.MATH_ONLIST_OPERATOR_MODE, 'MODE'],
         [Msg.MATH_ONLIST_OPERATOR_STD_DEV, 'STD_DEV'],
         [Msg.MATH_ONLIST_OPERATOR_RANDOM, 'RANDOM']];
    // Assign 'this' to a variable for use in the closure below.
    var thisBlock = this;
    this.setHelpUrl(Msg.MATH_ONLIST_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    var dropdown = new FieldDropdown(OPERATORS, function(newOp) {
      if (newOp == 'MODE') {
        thisBlock.outputConnection.setCheck('Array');
      } else {
        thisBlock.outputConnection.setCheck('Number');
      }
    });
    this.appendValueInput('LIST')
        .setCheck('Array')
        .appendField(dropdown, 'OP');
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'SUM': Msg.MATH_ONLIST_TOOLTIP_SUM,
        'MIN': Msg.MATH_ONLIST_TOOLTIP_MIN,
        'MAX': Msg.MATH_ONLIST_TOOLTIP_MAX,
        'AVERAGE': Msg.MATH_ONLIST_TOOLTIP_AVERAGE,
        'MEDIAN': Msg.MATH_ONLIST_TOOLTIP_MEDIAN,
        'MODE': Msg.MATH_ONLIST_TOOLTIP_MODE,
        'STD_DEV': Msg.MATH_ONLIST_TOOLTIP_STD_DEV,
        'RANDOM': Msg.MATH_ONLIST_TOOLTIP_RANDOM
      };
      return TOOLTIPS[mode];
    });
  }
};

Blocks['math_modulo'] = {
  /**
   * Block for remainder of a division.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.MATH_MODULO_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.interpolateMsg(Msg.MATH_MODULO_TITLE,
                        ['DIVIDEND', 'Number', Blockly.ALIGN_RIGHT],
                        ['DIVISOR', 'Number', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setInputsInline(true);
    this.setTooltip(Msg.MATH_MODULO_TOOLTIP);
  }
};

Blocks['math_constrain'] = {
  /**
   * Block for constraining a number between two limits.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.MATH_CONSTRAIN_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.interpolateMsg(Msg.MATH_CONSTRAIN_TITLE,
                        ['VALUE', 'Number', Blockly.ALIGN_RIGHT],
                        ['LOW', 'Number', Blockly.ALIGN_RIGHT],
                        ['HIGH', 'Number', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setInputsInline(true);
    this.setTooltip(Msg.MATH_CONSTRAIN_TOOLTIP);
  }
};

Blocks['math_random_int'] = {
  /**
   * Block for random integer between [X] and [Y].
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.MATH_RANDOM_INT_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.interpolateMsg(Msg.MATH_RANDOM_INT_TITLE,
                        ['FROM', 'Number', Blockly.ALIGN_RIGHT],
                        ['TO', 'Number', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setInputsInline(true);
    this.setTooltip(Msg.MATH_RANDOM_INT_TOOLTIP);
  }
};

Blocks['math_random_float'] = {
  /**
   * Block for random fraction between 0 and 1.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.MATH_RANDOM_FLOAT_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendDummyInput()
        .appendField(Msg.MATH_RANDOM_FLOAT_TITLE_RANDOM);
    this.setTooltip(Msg.MATH_RANDOM_FLOAT_TOOLTIP);
  }
};

Blocks['math_framed'] = {
  /**
   * Block for max value over a timeframe.
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_NUMBER_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);

    var OPERATORS =
        [['Maximum of', 'MAX'],
         ['Minimum of', 'MIN'],
         ['Average of', 'AVERAGE'],
         ['Change in', 'CHANGE']];

    this.fieldNumber_ = new FieldTextInput(
      '0',
      FieldTextInput.nonnegativeNumberValidator
    );

    this.appendValueInput('INPUT')
        .appendField(new FieldDropdown(OPERATORS), 'OP')
        .setCheck('Number');
    this.appendDummyInput()
        .appendField('over')
        .appendField(this.fieldNumber_, 'TIME')
        .appendField('seconds');
    this.setOutput(true, 'Number');

    /*var thisBlock = this;
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var TOOLTIPS = {
        'ADD': Msg.MATH_ARITHMETIC_TOOLTIP_ADD,
        'MINUS': Msg.MATH_ARITHMETIC_TOOLTIP_MINUS,
        'MULTIPLY': Msg.MATH_ARITHMETIC_TOOLTIP_MULTIPLY,
        'DIVIDE': Msg.MATH_ARITHMETIC_TOOLTIP_DIVIDE,
        'POWER': Msg.MATH_ARITHMETIC_TOOLTIP_POWER
      };
      return TOOLTIPS[mode];
    });*/
  }
};

Blocks['math_throttle'] = {
  /**
   * Block for throttling data (reducing change event frequency)
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_NUMBER_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);

    var OPERATORS =
        [['Maximum value', 'MAX'],
         ['Minimum value', 'MIN'],
         ['Average value', 'AVERAGE'],
         ['Latest value', 'LATEST']];

    this.fieldNumber_ = new FieldTextInput(
      '0',
      FieldTextInput.nonnegativeNumberValidator
    );

    this.appendValueInput('INPUT')
        .appendField('Throttle')
        .setCheck('Number');
    this.appendDummyInput()
        .appendField('and return')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
    this.appendDummyInput()
        .appendField('every')
        .appendField(this.fieldNumber_, 'TIME')
        .appendField('seconds');
    this.setOutput(true, 'Number');

    var thisBlock = this;
    this.setTooltip(function() {
      var mode = thisBlock.getFieldValue('OP');
      var text = 'Throttle the data generation rate, producing a new value once at the end of each time window. ';
      var TOOLTIPS = {
        'MAX': 'The maximum value during the time window is returned.',
        'MIN': 'The minimum value during the time window is returned.',
        'AVERAGE': 'The average value across the time window is returned.',
        'LATEST': 'The current value is returned at the end of each time window.',
      };
      return TOOLTIPS[mode];
    });
  }
};
