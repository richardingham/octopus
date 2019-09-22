import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Msg from '../core/msg';
import Names from '../core/names';
import {GlobalScope} from '../core/variables';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import FieldLexicalVariable from '../core/field_lexical_variable';
import FieldFlydown from '../core/field_flydown';
import FieldGlobalFlydown from '../core/field_global_flydown';
import {withVariableDropdown, withVariableDefinition} from './mixins.js';
import {VARIABLES_CATEGORY_HUE} from '../colourscheme';

/**
 * Prototype bindings for a global variable declaration block
 */
Blocks['global_declaration'] = {
  // Global var defn
  category: 'Variables',
  //helpUrl: Msg.LANG_VARIABLES_GLOBAL_DECLARATION_HELPURL,
  init: function() {
    this.fieldName_ = withVariableDefinition(
      this, FieldGlobalFlydown,
      FieldFlydown.DISPLAY_BELOW,
      'name', //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_NAME,
      true
    );

    this.setColour(VARIABLES_CATEGORY_HUE);
    this.appendValueInput('VALUE')
        .appendField('initialise global') //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_TITLE_INIT)
        .appendField(this.fieldName_, 'NAME')
        .appendField('to'); //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_TO);
    this.setTooltip('Declare a global variable'); //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_TOOLTIP);
  }
};


/**
 * Prototype bindings for a variable getter block
 */
Blocks['lexical_variable_get'] = {
  // Variable getter.
  category: 'Variables',
  //helpUrl: Msg.LANG_VARIABLES_GET_HELPURL,
  init: function() {
    this.setColour(VARIABLES_CATEGORY_HUE);
    this.fieldVar_ = new FieldLexicalVariable(" ");
    this.fieldVar_.setBlock(this);
    this.appendDummyInput()
        .appendField('get') //Msg.LANG_VARIABLES_GET_TITLE_GET)
        .appendField(this.fieldVar_, 'VAR');
    this.setOutput(true, null);
    this.setTooltip(''); //Msg.LANG_VARIABLES_GET_TOOLTIP);

    withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  },
  variableChanged_: function (variable) {
    this.changeOutput(variable.getType());
  }
};


/**
 * Prototype bindings for a variable setter block
 */
Blocks['lexical_variable_set'] = {
  // Variable setter.
  category: 'Variables',
  //helpUrl: Msg.LANG_VARIABLES_SET_HELPURL,
  init: function() {
    this.setColour(VARIABLES_CATEGORY_HUE);
    this.fieldVar_ = new FieldLexicalVariable(" ", { readonly: false });
    this.fieldVar_.setBlock(this);
    this.appendValueInput('VALUE')
        .appendField('set') //Msg.LANG_VARIABLES_SET_TITLE_SET)
        .appendField(this.fieldVar_, 'VAR')
        .appendField('to') //Msg.LANG_VARIABLES_SET_TITLE_TO);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setTooltip(''); //Msg.LANG_VARIABLES_SET_TOOLTIP);

	  withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  },
  variableChanged_: function (variable) {
    this.getInput('VALUE').setCheck(variable.getType());
  }
};


/**
 * Prototype bindings for a variable setter block
 */
Blocks['lexical_variable_set_to'] = {
  // Variable setter.
  category: 'Variables',
  //helpUrl: Msg.LANG_VARIABLES_SET_TO_HELPURL,
  init: function() {
    this.setColour(VARIABLES_CATEGORY_HUE);
    this.fieldVar_ = new FieldLexicalVariable(" ", { readonly: false });
    this.fieldVar_.setBlock(this);
    this.appendDummyInput('INPUT')
        .appendField('set') //Msg.LANG_VARIABLES_SET_TITLE_SET)
        .appendField(this.fieldVar_, 'VAR')
        .appendField('to') //Msg.LANG_VARIABLES_SET_TITLE_TO);
        .appendField('...', 'UNIT');
    this.appendDummyInput('BLANK')
        .appendField(new FieldTextInput(''), 'VALUE')
        .setVisible(false);
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setTooltip(''); //Msg.LANG_VARIABLES_SET_TOOLTIP);

	  withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  },
  variableChanged_: function (variable) {
    var input = this.getInput('INPUT');
    var value = this.getFieldValue('VALUE');
    var type = variable.getType();
    var field, options;

    this.removeInput('BLANK', true);
    input.removeField('VALUE', true);
    input.removeField('UNIT', true);

    // Drop-down menu
    if (variable.flags.options) {
      options = [];
      for (var i = 0; i < variable.flags.options.length; i++) {
        options.push([variable.flags.options[i], variable.flags.options[i]]);
      }

      field = input.appendField(new FieldDropdown(options), 'VALUE');

      if (variable.flags.options.indexOf(value) >= 0) {
        this.setFieldValue(value, 'VALUE');
      }

    // Number field
    } else if (type == "Number") {
      value = parseFloat(value);
      field = input.appendField(new FieldTextInput(
        isNaN(value) ? '0' : String(value),
        FieldTextInput.numberValidator
      ), 'VALUE');

    // Boolean field
    } else if (type == "Boolean") {
      options = [
        [Msg.LOGIC_BOOLEAN_TRUE, 'TRUE'],
        [Msg.LOGIC_BOOLEAN_FALSE, 'FALSE']
      ];

      field = input.appendField(new FieldDropdown(options), 'VALUE');

      if (value) {
        this.setFieldValue('TRUE', 'VALUE');
      }

    // Text field
    } else {
      field = input.appendField(new FieldTextInput(
        String(value)
      ), 'VALUE');
    }

    // Unit
    if (variable.flags.unit) {
      input.appendField(variable.flags.unit, 'UNIT');
    }
  }
};
