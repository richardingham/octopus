import Blockly from '../core/blockly';
import Block from '../core/block';
import Blocks from '../core/blocks';
import Mutator from '../core/mutator';
import Names from '../core/names';
import {GlobalScope} from '../core/variables';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';

export function extend (defaults, options) {
    var extended = {};
    var prop;
    for (prop in defaults) {
        if (Object.prototype.hasOwnProperty.call(defaults, prop)) {
            extended[prop] = defaults[prop];
        }
    }
    for (prop in options) {
        if (Object.prototype.hasOwnProperty.call(options, prop)) {
            extended[prop] = options[prop];
        }
    }
    return extended;
};

export function withVariableDefinition (block, fieldClass, fieldFlydownLocation, defaultVariableName, isGlobal, createVariableFunction) {
  var field = new fieldClass(
    defaultVariableName, //Msg.LANG_VARIABLES_GLOBAL_DECLARATION_NAME,
    true, // isEditable
    fieldFlydownLocation,
    renameVariable
  );

  if (isGlobal) {
    var scope = GlobalScope;
  } else {
    scope = block.getVariableScope();
  }

  if (!block.isInFlyout) {
    block.variable_ = (createVariableFunction || createVariable)();
    field.setValue(block.variable_.getVarName());
  }

  function renameVariable (newName) {
    var oldName = field.getValue();

    if (block.variable_) {
      if (oldName === newName) {
        return newName;
      }

      block.variable_.setName(newName);
      return block.variable_.getVarName();
    }
  };

  function createVariable () {
    return scope.addVariable(defaultVariableName);
  };

  block.getVars = function () {
    return [field.getValue()];
  };

  block.getVariable = function () {
    return block.variable_;
  };

  block.disposed = function () {
    if (block.variable_) {
      block.variable_.getScope().removeVariable(this.variable_.getVarName());
      block.variable_ = null;
    }
  }

  return field;
}

// withLexicalVariable
export function withVariableDropdown (field, fieldName) {
  /**
   * Get the variable currently referenced by this block,
   * accounting for scope.
   * @return {Variable} variable The variable.
   * @this Block
   */
  this.getVariable = function getVariable () {
    var scope = this.getVariableScope();
    return scope && scope.getScopedVariable(field.getFullVariableName());
  };

  /**
   * Return all variables referenced by this block.
   * @return {!Array.<string>} List of variable names.
   * @this Block
   */
  this.getVars = function getVars () {
    return [field.getFullVariableName()];
  };

  function changeParent_ () {
    var val = field.getFullVariableName();
    var scope = this.getVariableScope();
    var newVar = scope && scope.getScopedVariable(field.getFullVariableName());
    if (newVar) {
      field.setValue(newVar);
    }
  };

  this.on("parent-changed", changeParent_);

  /**
   * Emit an event that this variable's name has changed
   * @param {string} name New (full) name of variable.
   * @this Block
   */
  this.announceRename = function announceRename (name) {
    if (Names.equals(name, field.getVariableName())) {
      var attributeName = field.getAttributeName();
      if (attributeName !== '') {
        name += '::' + attributeName;
      }
      this.workspaceEmit("block-set-field-value", { id: this.id, field: fieldName, value: name });
    }
  };

  /**
   * Notification that a variable is renaming.
   * If the name matches one of this block's variables, rename it.
   * @param {string} oldName Previous name of variable.
   * @param {string} newName Renamed variable.
   * @param {Variable} variable The variable in question.
   * @this Block
   */
  this.renameVar = function renameVar (oldName, newName, variable) {
    if (Names.equals(oldName, field.getFullVariableName())) {
      field.setValue(variable);
    }
  };
}

export function addUnitDropdown (block, input, variable, currentUnitSelection) {
  // Unit
  if (variable.flags.unit) {
    if (typeof variable.flags.unit === 'object') {
      var unitOptions = variable.flags.unit.options.map(o => o[1]);

      input.appendField(new FieldDropdown(variable.flags.unit.options), 'UNIT');

      if (currentUnitSelection && unitOptions.indexOf(currentUnitSelection) !== -1) {
        block.setFieldValue(currentUnitSelection, 'UNIT');
      } else if (variable.flags.unit.default) {
        block.setFieldValue(variable.flags.unit.default, 'UNIT');
      }
    } else {
      input.appendField(variable.flags.unit, 'UNIT');
    }
  } else {
    input.appendField('', 'UNIT');
  }
}

export function withMagicVariableValue (callAlso) {
  this.variableChanged_ = function (variable) {
    var input = this.getInput('INPUT');
    var value = this.getFieldValue('VALUE');
    var type = variable.getType();
    var field, options;

    var currentUnitSelection = this.getFieldValue('UNIT');

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
    addUnitDropdown(this, input, variable, currentUnitSelection);

    if (callAlso) {
      callAlso(variable);
    }
  }
}

export function withMutation (mutationOptions) {
  this.mutation_ = {};
  var defaultMutation = {};

  var mutationParts = mutationOptions.parts || [];
  var mutationTypeMap = {};
  var preUpdate = mutationOptions.preUpdate || function () {};
  var postUpdate = mutationOptions.postUpdate || function () {};

  var part;

  // Create this.mutation_, initially with defaults.
  var editorBlocks = [];
  for (var i = 0, m = mutationParts.length; i < m; i++) {
    part = mutationParts[i];
    this.mutation_[part.name] = 0;
    defaultMutation[part.name] = part.default;

    if (!Array.isArray(part.input)) {
      part.input = [part.input];
    }

    part.counterStart = parseInt(part.counterStart) || 0;

    part.editor.block = part.editor.block || this.type + '_mut_item_' + part.name;
    mutationTypeMap[part.editor.block] = i;
    editorBlocks.push(part.editor.block);
  }

  mutationOptions.editor.block = mutationOptions.editor.block || this.type + '_mut_container';

  // Create mutation editor blocks
  if (typeof Blocks[mutationOptions.editor.block] === 'undefined') {
    Blocks[mutationOptions.editor.block] = mutator_stack(
      this.getColour(),
      mutationOptions.editor.text || '',
      mutationOptions.editor.tooltip || ''
    );

    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];

      Blocks[part.editor.block] = mutator_child(
        this.getColour(),
        part.editor.text || '',
        part.editor.tooltip || '',
        part.isFinal
      );
    }
  }

  // Set up mutator
  this.setMutator(new Mutator(editorBlocks));

  // Function to check whether the mutation has changed from
  // the defaults. Used in mutationToDom()
  function mutationDefault () {
    var part;
    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];
      if (this.mutation_[part.name] !== part.default) {
        return false;
      }
    }
    return true;
  }

  /**
   * Create JSON to represent the number of test inputs.
   * @return {String} JSON representation of mutation.
   * @this Block
   */
  this.mutationToJSON = function mutationToJSON () {
    return JSON.stringify(this.mutation_);
  };

  /**
   * Parse JSON to restore the dependents inputs.
   * @param {!String} JSON representation of mutation.
   * @this Block
   */
  this.JSONToMutation = function JSONToMutation (obj) {
    var mutation = {};
    for (var key in this.mutation_) {
      if (typeof this.mutation_[key] === "number") {
        mutation[key] = obj[key] && parseInt(obj[key], 10) || 0;
      } else {
        mutation[key] = obj[key] || "";
      }
    }
    this.update(mutation);
  };

  /**
   * Create XML to represent the number of dependents inputs.
   * @return {Element} XML storage element.
   * @this Block
   */
  this.mutationToDom = function mutationToDom () {
    if (mutationDefault.call(this)) {
      return null;
    }
    var container = document.createElement('mutation');
    for (var key in this.mutation_) {
      container.setAttribute(key, this.mutation_[key]);
    }
    return container;
  };

  /**
   * Parse XML to restore the dependents inputs.
   * @param {!Element} xmlElement XML storage element.
   * @this Block
   */
  this.domToMutation = function domToMutation (xmlElement) {
    var mutation = {};
    for (var key in this.mutation_) {
      if (typeof this.mutation_[key] === "number") {
        mutation[key] = parseInt(xmlElement.getAttribute(key), 10) || 0;
      } else {
        mutation[key] = xmlElement.getAttribute(key) || "";
      }
    }
    this.update(mutation);
  };

  function getInputName (name, part, number) {
    return name + (part.isFinal ? '' : number + part.counterStart);
  }

  function updatePart (mutation, part, newConnections) {
    var newCount = mutation[part.name];
    var input, inputOptions;

    // Add / remove inputs as necessary
    if (newCount > this.mutation_[part.name]) {
      for (var x = this.mutation_[part.name]; x < newCount; x++) {
        for (var i = 0, m = part.input.length; i < m; i++) {
          inputOptions = part.input[i];

          if (inputOptions.type === 'statement') {
            input = this.appendStatementInput(getInputName(inputOptions.name, part, x));
          } else {
            input = this.appendValueInput(getInputName(inputOptions.name, part, x));
            if (inputOptions.check) {
              input.setCheck(inputOptions.check);
            }
          }
          if (inputOptions.align) {
            input.setAlign(inputOptions.align);
          }
          if (inputOptions.text) {
            input.appendField(inputOptions.text);
          }
        }
      }
    } else {
      for (var x = this.mutation_[part.name]; x > newCount; x--) {
        for (var i = 0, m = part.input.length; i < m; i++) {
          this.removeInput(getInputName(part.input[i].name, part, x - 1));
        }
      }
    }

    if (newConnections) {
      var inputName, connect = {};

      // Disconnections
      for (var x = 0; x < newCount; x++) {
        for (var i = 0, m = part.input.length; i < m; i++) {
          inputOptions = part.input[i];
          inputName = getInputName(inputOptions.name, part, x)
          if (newConnections[inputName] != this.connections_[inputName]) {
            input = this.getInput(inputName);
            if (input && input.connection.targetConnection) {
              input.connection.targetBlock().setParent();
            }
            connect[inputName] = newConnections[inputName];
          }
        }
      }

      // Connections.
      var targetConnection;
      for (var inputName in connect) {
        targetConnection = connect[inputName];
        input = this.getInput(inputName);
        input && targetConnection && input.connection.connect(targetConnection);
      }
    }
  }

  this.update = function (mutation, newConnections) {
    var oldMutation = this.mutation_;
    preUpdate.call(this, mutation, oldMutation);

    var part;
    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];
      updatePart.call(this, mutation, part, newConnections);
    }
    this.mutation_ = mutation;

    postUpdate.call(this, mutation, oldMutation);
  };

  /**
   * Populate the mutator's dialog with this block's components.
   * @param {!Workspace} workspace Mutator's workspace.
   * @return {!Block} Root block in mutator.
   * @this Block
   */
  this.decompose = function (workspace) {
    var containerBlock = Block.obtain(
      workspace,
      mutationOptions.editor.block
    );
    containerBlock.initSvg();
    var connection = containerBlock.getInput('STACK').connection;

    var part;
    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];

      for (var x = 0; x < this.mutation_[part.name]; x++) {
        var itemBlock = Block.obtain(workspace, part.editor.block);
        itemBlock.initSvg();
        connection.connect(itemBlock.previousConnection);
        connection = itemBlock.nextConnection;
      }
    }

    return containerBlock;
  };

  /**
   * Reconfigure this block based on the mutator dialog's components.
   * @param {!Block} containerBlock Root block in mutator.
   * @this Block
   */
  this.compose = function(containerBlock) {
    var clauseBlock = containerBlock.getInputTargetBlock('STACK');
    var mutation = {}, connections = {};
    var part;

    // Set empty mutation, store types map.
    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];
      mutation[part.name] = 0;
    }

    // Calculate changes
    while (clauseBlock) {
      if (typeof mutationTypeMap[clauseBlock.type] === 'undefined') {
        throw 'Unknown block type.';
      }
      part = mutationParts[mutationTypeMap[clauseBlock.type]];

      for (var i = 0, m = part.input.length; i < m; i++) {
        if (clauseBlock.connection_) {
          connections[getInputName(
            part.input[i].name,
            part,
            mutation[part.name]
          )] = clauseBlock.connection_[part.input[i].name];
        }
      }
      mutation[part.name]++;

      clauseBlock = clauseBlock.nextConnection &&
          clauseBlock.nextConnection.targetBlock();
    }

    this.update(mutation, connections);
  };

  /**
   * Store pointers to any connected child blocks.
   * @param {!Block} containerBlock Root block in mutator.
   * @this Block
   */
  this.saveConnections = function (containerBlock) {
    var part, input, inputName, inputOptions;
    var counters = {}

    this.connections_ = {};

    // Store types map.
    for (var i = 0, m = mutationParts.length; i < m; i++) {
      part = mutationParts[i];
      counters[part.name] = 0;
    }

    var clauseBlock = containerBlock.getInputTargetBlock('STACK');
    while (clauseBlock) {
      part = mutationParts[mutationTypeMap[clauseBlock.type]];

      if (!part) {
        throw 'Unknown block type.';
      }

      clauseBlock.connection_ = {};
      for (var i = 0, m = part.input.length; i < m; i++) {
        inputOptions = part.input[i];
        inputName = getInputName(inputOptions.name, part, counters[part.name]);
        input = this.getInput(inputName);
        clauseBlock.connection_[inputOptions.name] = input && input.connection.targetConnection;
        this.connections_[inputName] = clauseBlock.connection_[inputOptions.name];
      }
      counters[part.name]++;

      clauseBlock = clauseBlock.nextConnection &&
        clauseBlock.nextConnection.targetBlock();
    }
  };

  // Create default mutation
  this.JSONToMutation(defaultMutation);
}

function mutator_stack (colour, text, tooltip) {
  return {
    init: function() {
      this.setColour(colour);
      this.appendDummyInput()
          .appendField(text);
      this.appendStatementInput('STACK');

      if (tooltip) {
        this.setTooltip(tooltip);
      }

      this.contextMenu = false;
    }
  };
}

function mutator_child (colour, text, tooltip, isFinal) {
  return {
    init: function() {
      this.setColour(colour);
      this.appendDummyInput()
          .appendField(text);
      this.setPreviousStatement(true);

      if (!isFinal) {
        this.setNextStatement(true);
      }

      if (tooltip) {
        this.setTooltip(tooltip);
      }

      this.contextMenu = false;
    }
  };
}
