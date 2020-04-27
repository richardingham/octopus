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
 * @fileoverview Text blocks for Blockly.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import FieldLabel from '../core/field_label';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import FieldLexicalVariable from '../core/field_lexical_variable';
import {withMutation, withVariableDropdown} from './mixins.js';
import {TEXT_CATEGORY_HUE} from '../colourscheme';

/**
 * Create an image of an open or closed quote.
 * @param {boolean} open True if open quote, false if closed.
 * @return {!FieldImage} The field image of the quote.
 * @private
 */
function newQuote_ (open) {
  var label = (open == Blockly.RTL) ? '\uf10e' : '\uf10d';
  return new FieldLabel(label, 'fa quote');
}

Blocks['text'] = {
  /**
   * Block for text value.
   * @this Block
   */
  init: function() {
    this.fieldText_ = new FieldTextInput('');
    this.setHelpUrl(Msg.TEXT_TEXT_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(newQuote_(true))
        .appendField(this.fieldText_, 'TEXT')
        .appendField(newQuote_(false));
    this.setOutput(true, 'String');
    this.setTooltip(Msg.TEXT_TEXT_TOOLTIP);
  },

};

Blocks['text_join'] = {
  /**
   * Block for creating a string made up of any number of elements of any type.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.TEXT_JOIN_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.setOutput(true, 'String');
    this.setTooltip(Msg.TEXT_JOIN_TOOLTIP);

    this.mutationConfig = {
      parts: [{
        name: 'items',
        default: 2,
        input: {
          name: 'ADD',
          type: 'value'
        },
        editor: {
          //block: 'text_create_join_item',
          text: Msg.TEXT_CREATE_JOIN_ITEM_TITLE_ITEM,
          tooltip: Msg.TEXT_CREATE_JOIN_ITEM_TOOLTIP
        }
      }],
      editor: {
        //block: 'text_create_join_container',
        text: Msg.TEXT_CREATE_JOIN_TITLE_JOIN,
        tooltip: Msg.TEXT_CREATE_JOIN_TOOLTIP
      },
      postUpdate: function (newMutation, oldMutation) {
        var wasEmpty = (oldMutation.items === 0);

        if (newMutation.items === 0 && !wasEmpty) {
          this.appendDummyInput('EMPTY')
              .appendField(newQuote_(true))
              .appendField(newQuote_(false));
        } else if (newMutation.items > 0 && wasEmpty) {
          this.removeInput('EMPTY', true);
          this.getInput('ADD0').insertField(0, Msg.TEXT_JOIN_TITLE_CREATEWITH);
        }
      }
    };
    withMutation.call(this, this.mutationConfig);
  },
};


Blocks['text_append'] = {
  /**
   * Block for appending to a variable in place.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.TEXT_APPEND_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.fieldVar_ = new FieldLexicalVariable(" ");
    this.fieldVar_.setBlock(this);
    this.appendValueInput('TEXT')
        .appendField(Msg.TEXT_APPEND_TO)
        .appendField(this.fieldVar_, 'VAR')
        .appendField(Msg.TEXT_APPEND_APPENDTEXT);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      return Msg.TEXT_APPEND_TOOLTIP.replace('%1',
          thisBlock.getFieldValue('VAR'));
    });

    withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  },
};

Blocks['text_length'] = {
  /**
   * Block for string length.
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.TEXT_LENGTH_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.interpolateMsg(Msg.TEXT_LENGTH_TITLE,
                        ['VALUE', ['String', 'Array'], Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setOutput(true, 'Number');
    this.setTooltip(Msg.TEXT_LENGTH_TOOLTIP);
  }
};

Blocks['text_isEmpty'] = {
  /**
   * Block for is the string null?
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.TEXT_ISEMPTY_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.interpolateMsg(Msg.TEXT_ISEMPTY_TITLE,
                        ['VALUE', ['String', 'Array'], Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setOutput(true, 'Boolean');
    this.setTooltip(Msg.TEXT_ISEMPTY_TOOLTIP);
  }
};

Blocks['text_indexOf'] = {
  /**
   * Block for finding a substring in the text.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.TEXT_INDEXOF_OPERATOR_FIRST, 'FIRST'],
         [Msg.TEXT_INDEXOF_OPERATOR_LAST, 'LAST']];
    this.setHelpUrl(Msg.TEXT_INDEXOF_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('VALUE')
        .setCheck('String')
        .appendField(Msg.TEXT_INDEXOF_INPUT_INTEXT);
    this.appendValueInput('FIND')
        .setCheck('String')
        .appendField(new FieldDropdown(OPERATORS), 'END');
    if (Msg.TEXT_INDEXOF_TAIL) {
      this.appendDummyInput().appendField(Msg.TEXT_INDEXOF_TAIL);
    }
    this.setInputsInline(true);
    this.setTooltip(Msg.TEXT_INDEXOF_TOOLTIP);
  }
};

Blocks['text_charAt'] = {
  /**
   * Block for getting a character from the string.
   * @this Block
   */
  init: function() {
    this.WHERE_OPTIONS =
        [[Msg.TEXT_CHARAT_FROM_START, 'FROM_START'],
         [Msg.TEXT_CHARAT_FROM_END, 'FROM_END'],
         [Msg.TEXT_CHARAT_FIRST, 'FIRST'],
         [Msg.TEXT_CHARAT_LAST, 'LAST'],
         [Msg.TEXT_CHARAT_RANDOM, 'RANDOM']];
    this.setHelpUrl(Msg.TEXT_CHARAT_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.setOutput(true, 'String');
    this.appendValueInput('VALUE')
        .setCheck('String')
        .appendField(Msg.TEXT_CHARAT_INPUT_INTEXT);
    this.appendDummyInput('AT');
    this.setInputsInline(true);
    this.updateAt_(true);
    this.setTooltip(Msg.TEXT_CHARAT_TOOLTIP);
  },
  /**
   * Create XML to represent whether there is an 'AT' input.
   * @return {Element} XML storage element.
   * @this Block
   */
  mutationToDom: function() {
    var container = document.createElement('mutation');
    var isAt = this.getInput('AT').type == Blockly.INPUT_VALUE;
    container.setAttribute('at', isAt);
    return container;
  },
  /**
   * Parse XML to restore the 'AT' input.
   * @param {!Element} xmlElement XML storage element.
   * @this Block
   */
  domToMutation: function(xmlElement) {
    // Note: Until January 2013 this block did not have mutations,
    // so 'at' defaults to true.
    var isAt = (xmlElement.getAttribute('at') != 'false');
    this.updateAt_(isAt);
  },
  /**
   * Create or delete an input for the numeric index.
   * @param {boolean} isAt True if the input should exist.
   * @private
   * @this Block
   */
  updateAt_: function(isAt) {
    // Destroy old 'AT' and 'ORDINAL' inputs.
    this.removeInput('AT');
    this.removeInput('ORDINAL', true);
    // Create either a value 'AT' input or a dummy input.
    if (isAt) {
      this.appendValueInput('AT').setCheck('Number');
      if (Msg.ORDINAL_NUMBER_SUFFIX) {
        this.appendDummyInput('ORDINAL')
            .appendField(Msg.ORDINAL_NUMBER_SUFFIX);
      }
    } else {
      this.appendDummyInput('AT');
    }
    if (Msg.TEXT_CHARAT_TAIL) {
      this.removeInput('TAIL', true);
      this.appendDummyInput('TAIL')
          .appendField(Msg.TEXT_CHARAT_TAIL);
    }
    var menu = new FieldDropdown(this.WHERE_OPTIONS, function(value) {
      var newAt = (value == 'FROM_START') || (value == 'FROM_END');
      // The 'isAt' variable is available due to this function being a closure.
      if (newAt != isAt) {
        var block = this.sourceBlock_;
        block.updateAt_(newAt);
        // This menu has been destroyed and replaced.  Update the replacement.
        block.setFieldValue(value, 'WHERE');
        return null;
      }
      return undefined;
    });
    this.getInput('AT').appendField(menu, 'WHERE');
  }
};

Blocks['text_getSubstring'] = {
  /**
   * Block for getting substring.
   * @this Block
   */
  init: function() {
    this.WHERE_OPTIONS_1 =
        [[Msg.TEXT_GET_SUBSTRING_START_FROM_START, 'FROM_START'],
         [Msg.TEXT_GET_SUBSTRING_START_FROM_END, 'FROM_END'],
         [Msg.TEXT_GET_SUBSTRING_START_FIRST, 'FIRST']];
    this.WHERE_OPTIONS_2 =
        [[Msg.TEXT_GET_SUBSTRING_END_FROM_START, 'FROM_START'],
         [Msg.TEXT_GET_SUBSTRING_END_FROM_END, 'FROM_END'],
         [Msg.TEXT_GET_SUBSTRING_END_LAST, 'LAST']];
    this.setHelpUrl(Msg.TEXT_GET_SUBSTRING_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.appendValueInput('STRING')
        .setCheck('String')
        .appendField(Msg.TEXT_GET_SUBSTRING_INPUT_IN_TEXT);
    this.appendDummyInput('AT1');
    this.appendDummyInput('AT2');
    if (Msg.TEXT_GET_SUBSTRING_TAIL) {
      this.appendDummyInput('TAIL')
          .appendField(Msg.TEXT_GET_SUBSTRING_TAIL);
    }
    this.setInputsInline(true);
    this.setOutput(true, 'String');
    this.updateAt_(1, true);
    this.updateAt_(2, true);
    this.setTooltip(Msg.TEXT_GET_SUBSTRING_TOOLTIP);
  },
  /**
   * Create XML to represent whether there are 'AT' inputs.
   * @return {Element} XML storage element.
   * @this Block
   */
  mutationToDom: function() {
    var container = document.createElement('mutation');
    var isAt1 = this.getInput('AT1').type == Blockly.INPUT_VALUE;
    container.setAttribute('at1', isAt1);
    var isAt2 = this.getInput('AT2').type == Blockly.INPUT_VALUE;
    container.setAttribute('at2', isAt2);
    return container;
  },
  /**
   * Parse XML to restore the 'AT' inputs.
   * @param {!Element} xmlElement XML storage element.
   * @this Block
   */
  domToMutation: function(xmlElement) {
    var isAt1 = (xmlElement.getAttribute('at1') == 'true');
    var isAt2 = (xmlElement.getAttribute('at2') == 'true');
    this.updateAt_(1, isAt1);
    this.updateAt_(2, isAt2);
  },
  /**
   * Create or delete an input for a numeric index.
   * This block has two such inputs, independant of each other.
   * @param {number} n Specify first or second input (1 or 2).
   * @param {boolean} isAt True if the input should exist.
   * @private
   * @this Block
   */
  updateAt_: function(n, isAt) {
    // Create or delete an input for the numeric index.
    // Destroy old 'AT' and 'ORDINAL' inputs.
    this.removeInput('AT' + n);
    this.removeInput('ORDINAL' + n, true);
    // Create either a value 'AT' input or a dummy input.
    if (isAt) {
      this.appendValueInput('AT' + n).setCheck('Number');
      if (Msg.ORDINAL_NUMBER_SUFFIX) {
        this.appendDummyInput('ORDINAL' + n)
            .appendField(Msg.ORDINAL_NUMBER_SUFFIX);
      }
    } else {
      this.appendDummyInput('AT' + n);
    }
    // Move tail, if present, to end of block.
    if (n == 2 && Msg.TEXT_GET_SUBSTRING_TAIL) {
      this.removeInput('TAIL', true);
      this.appendDummyInput('TAIL')
          .appendField(Msg.TEXT_GET_SUBSTRING_TAIL);
    }
    var menu = new FieldDropdown(this['WHERE_OPTIONS_' + n],
        function(value) {
      var newAt = (value == 'FROM_START') || (value == 'FROM_END');
      // The 'isAt' variable is available due to this function being a closure.
      if (newAt != isAt) {
        var block = this.sourceBlock_;
        block.updateAt_(n, newAt);
        // This menu has been destroyed and replaced.  Update the replacement.
        block.setFieldValue(value, 'WHERE' + n);
        return null;
      }
      return undefined;
    });
    this.getInput('AT' + n)
        .appendField(menu, 'WHERE' + n);
    if (n == 1) {
      this.moveInputBefore('AT1', 'AT2');
    }
  }
};

Blocks['text_changeCase'] = {
  /**
   * Block for changing capitalization.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.TEXT_CHANGECASE_OPERATOR_UPPERCASE, 'UPPERCASE'],
         [Msg.TEXT_CHANGECASE_OPERATOR_LOWERCASE, 'LOWERCASE'],
         [Msg.TEXT_CHANGECASE_OPERATOR_TITLECASE, 'TITLECASE']];
    this.setHelpUrl(Msg.TEXT_CHANGECASE_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.appendValueInput('TEXT')
        .setCheck('String')
        .appendField(new FieldDropdown(OPERATORS), 'CASE');
    this.setOutput(true, 'String');
    this.setTooltip(Msg.TEXT_CHANGECASE_TOOLTIP);
  }
};

Blocks['text_trim'] = {
  /**
   * Block for trimming spaces.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.TEXT_TRIM_OPERATOR_BOTH, 'BOTH'],
         [Msg.TEXT_TRIM_OPERATOR_LEFT, 'LEFT'],
         [Msg.TEXT_TRIM_OPERATOR_RIGHT, 'RIGHT']];
    this.setHelpUrl(Msg.TEXT_TRIM_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.appendValueInput('TEXT')
        .setCheck('String')
        .appendField(new FieldDropdown(OPERATORS), 'MODE');
    this.setOutput(true, 'String');
    this.setTooltip(Msg.TEXT_TRIM_TOOLTIP);
  }
};

Blocks['controls_log'] = {
  /**
   * Block for print statement.
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.TEXT_PRINT_HELPURL);
    this.setColour(TEXT_CATEGORY_HUE);
    this.interpolateMsg(Msg.TEXT_PRINT_TITLE,
                        ['TEXT', null, Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setTooltip('Log a message to the experiment history'); //Msg.TEXT_PRINT_TOOLTIP);
  }
};
