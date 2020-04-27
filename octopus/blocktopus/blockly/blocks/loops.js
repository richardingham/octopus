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
 * @fileoverview Loop blocks for Blockly.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import Names from '../core/names';
import FieldLexicalParameterFlydown from '../core/field_lexical_parameter_flydown';
import FieldDropdown from '../core/field_dropdown';
import FieldFlydown from '../core/field_flydown';
import FieldTextInput from '../core/field_textinput';
import {withVariableDefinition} from './mixins.js';
import {CONTROL_CATEGORY_HUE} from '../colourscheme';

Blocks['controls_repeat'] = {
  /**
   * Block for repeat n times (internal number).
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.CONTROLS_REPEAT_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(Msg.CONTROLS_REPEAT_TITLE_REPEAT)
        .appendField(new FieldTextInput('10',
            FieldTextInput.nonnegativeIntegerValidator), 'TIMES')
        .appendField(Msg.CONTROLS_REPEAT_TITLE_TIMES);
    this.appendStatementInput('DO')
        .appendField(Msg.CONTROLS_REPEAT_INPUT_DO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setTooltip(Msg.CONTROLS_REPEAT_TOOLTIP);
  }
};

Blocks['controls_repeat_ext'] = {
  /**
   * Block for repeat n times (external number).
   * @this Block
   */
  init: function() {
    this.setHelpUrl(Msg.CONTROLS_REPEAT_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.interpolateMsg(Msg.CONTROLS_REPEAT_TITLE,
                        ['TIMES', 'Number', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.appendStatementInput('DO')
        .appendField(Msg.CONTROLS_REPEAT_INPUT_DO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setInputsInline(true);
    this.setTooltip(Msg.CONTROLS_REPEAT_TOOLTIP);
  }
};

Blocks['controls_whileUntil'] = {
  /**
   * Block for 'do while/until' loop.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.CONTROLS_WHILEUNTIL_OPERATOR_WHILE, 'WHILE'],
         [Msg.CONTROLS_WHILEUNTIL_OPERATOR_UNTIL, 'UNTIL']];
    this.setHelpUrl(Msg.CONTROLS_WHILEUNTIL_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.appendValueInput('BOOL')
        .setCheck('Boolean')
        .appendField(new FieldDropdown(OPERATORS), 'MODE');
    this.appendStatementInput('DO')
        .appendField(Msg.CONTROLS_WHILEUNTIL_INPUT_DO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var op = thisBlock.getFieldValue('MODE');
      var TOOLTIPS = {
        'WHILE': Msg.CONTROLS_WHILEUNTIL_TOOLTIP_WHILE,
        'UNTIL': Msg.CONTROLS_WHILEUNTIL_TOOLTIP_UNTIL
      };
      return TOOLTIPS[op];
    });
  }
};

Blocks['controls_for'] = {
  /**
   * Block for 'for' loop.
   * @this Block
   */
  definesScope: true,
  init: function() {
    var variableField = withVariableDefinition(this,
      FieldLexicalParameterFlydown,
      FieldFlydown.DISPLAY_BELOW,
      'name', //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_NAME
    );
    this.variable_.setReadonly(true);

    this.setHelpUrl(Msg.CONTROLS_FOR_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(Msg.CONTROLS_FOR_INPUT_WITH)
        .appendField(variableField, 'VAR');
    this.interpolateMsg(Msg.CONTROLS_FOR_INPUT_FROM_TO_BY,
                        ['FROM', 'Number', Blockly.ALIGN_RIGHT],
                        ['TO', 'Number', Blockly.ALIGN_RIGHT],
                        ['BY', 'Number', Blockly.ALIGN_RIGHT],
                        Blockly.ALIGN_RIGHT);
    this.appendStatementInput('DO')
        .appendField(Msg.CONTROLS_FOR_INPUT_DO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setInputsInline(true);

    this.setTooltip(function() {
      return Msg.CONTROLS_FOR_TOOLTIP.replace('%1', variableField.getValue());
    });
  },
};

Blocks['controls_forEach'] = {
  /**
   * Block for 'for each' loop.
   * @this Block
   */
  definesScope: true,
  init: function() {
    var variableField = withVariableDefinition(this,
      FieldLexicalParameterFlydown,
      FieldFlydown.DISPLAY_BELOW,
      'name', //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_NAME
    );
    this.variable_.setReadonly(true);

    this.setHelpUrl(Msg.CONTROLS_FOREACH_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.appendValueInput('LIST')
        .setCheck('Array')
        .appendField(Msg.CONTROLS_FOREACH_INPUT_ITEM)
        .appendField(variableField, 'VAR')
        .appendField(Msg.CONTROLS_FOREACH_INPUT_INLIST);
    if (Msg.CONTROLS_FOREACH_INPUT_INLIST_TAIL) {
      this.appendDummyInput()
          .appendField(Msg.CONTROLS_FOREACH_INPUT_INLIST_TAIL);
      this.setInputsInline(true);
    }
    this.appendStatementInput('DO')
        .appendField(Msg.CONTROLS_FOREACH_INPUT_DO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);

    this.setTooltip(function() {
      return Msg.CONTROLS_FOREACH_TOOLTIP.replace('%1', variableField.getValue());
    });
  }
};

Blocks['controls_flow_statements'] = {
  /**
   * Block for flow statements: continue, break.
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [[Msg.CONTROLS_FLOW_STATEMENTS_OPERATOR_BREAK, 'BREAK'],
         [Msg.CONTROLS_FLOW_STATEMENTS_OPERATOR_CONTINUE, 'CONTINUE']];
    this.setHelpUrl(Msg.CONTROLS_FLOW_STATEMENTS_HELPURL);
    this.setColour(CONTROL_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(new FieldDropdown(OPERATORS), 'FLOW');
    this.setPreviousStatement(true);
    // Assign 'this' to a variable for use in the tooltip closure below.
    var thisBlock = this;
    this.setTooltip(function() {
      var op = thisBlock.getFieldValue('FLOW');
      var TOOLTIPS = {
        'BREAK': Msg.CONTROLS_FLOW_STATEMENTS_TOOLTIP_BREAK,
        'CONTINUE': Msg.CONTROLS_FLOW_STATEMENTS_TOOLTIP_CONTINUE
      };
      return TOOLTIPS[op];
    });
  },
  /**
   * Called whenever anything on the workspace changes.
   * Add warning if this flow block is not nested inside a loop.
   * @this Block
   */
  onchange: function() {
    if (!this.workspace) {
      // Block has been deleted.
      return;
    }
    var legal = false;
    // Is the block nested in a control statement?
    var block = this;
    do {
      if (block.type == 'controls_repeat' ||
          block.type == 'controls_repeat_ext' ||
          block.type == 'controls_forEach' ||
          block.type == 'controls_for' ||
          block.type == 'controls_whileUntil') {
        legal = true;
        break;
      }
      block = block.getSurroundParent();
    } while (block);
    if (legal) {
      this.setWarningText(null);
    } else {
      this.setWarningText(Msg.CONTROLS_FLOW_STATEMENTS_WARNING);
    }
  }
};
