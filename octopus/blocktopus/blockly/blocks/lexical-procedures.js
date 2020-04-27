// -*- mode: java; c-basic-offset: 2; -*-
// Copyright 2013-2014 MIT, All rights reserved
// Released under the MIT License https://raw.github.com/mit-cml/app-inventor/master/mitlicense.txt
/**
 * @license
 * @fileoverview Procedure blocks for Blockly, modified for MIT App Inventor.
 * @author mckinney@mit.edu (Andrew F. McKinney)
 * @author mail@richardingham.net (Richard Ingham)
 */

/**
 * Lyn's Change History:
 * [lyn, written 11/16-17/13, added 07/01/14]
 *   + Added freeVariables, renameFree, and renameBound to procedure declarations
 *   + Added renameVars for procedure declarations, which allows renaming multiple parameters simultaneously
 *   + Modified updateParams_ to accept optional params argument
 *   + Introduced bodyInputName field for procedure declarations ('STACK' for procedures_defnoreturn;
 *     'RETURN' for procedures_return), and use this to share more methods between the two kinds
 *     of procedure declarations.
 *   + Replaced inlined string list equality tests by new Blockly.LexicalVariable.stringListsEqual
 * [lyn, 10/28/13]
 *   + Fixed a missing change of Blockly.Procedures.rename by Blockly.AIProcedure.renameProcedure
 *   + I was wrong about re-rendering not being needed in updatedParams_!
 *     Without it, changing horizontal -> vertical params doesn't handle body slot correctly.
 *     So added it back.
 * [lyn, 10/27/13]
 *   + Fix bug in list of callers in flyout by simplifying domToMutation for procedure callers.
 *     This should never look for associated declaration, but just take arguments from given xml.
 *   + Removed render() call from updateParams. Seems unnecessary. <== I WAS WRONG. SEE 10/28/13 NOTE
 *   + Specify direction of flydowns
 *   + Replaced Blockly.Procedures.rename by Blockly.AIProcedure.renameProcedure in proc decls
 * [lyn, 10/26/13] Modify procedure parameter changeHandler to propagate name changes to caller arg labels
 *     and open mutator labels
 * [lyn, 10/25/13]
 *   + Modified procedures_defnoreturn compose method so that it doesn't call updateParams_
 *     if mutator hasn't changed parameter names. This helps avoid a situation where
 *     an attempt is made to update params of a collapsed declaration.
 *   + Modified collapsed decls to have 'to ' prefix and collapsed callers to have 'call ' prefix.
 * [lyn, 10/24/13] Allowed switching between horizontal and vertical display of arguments
 * [lyn, 10/23/13] Fixed bug in domToMutation for callers that was giving wrong args to caller blocks.
 * [lyn, 10/10-14/13]
 *   + Installed variable declaration flydowns in both types of procedure declarations.
 *   + Fixed bug: Modified onchange for procedure declarations to keep arguments_ instance
 *     variable updated when param is edited directly on declaration block.
 *   + Removed get block (still in Variable drawer; no longer needed with parameter flydowns)
 *   + Removed "do {} then-return []" block since (1) it's in Control drawer and
 *     (2) it will be superseded in the context by Michael Phox's proc_defnoreturn mutator
 *     that allows adding a DO statement.
 *   + TODO: Abstract over string labels on all blocks using constants defined in en/_messages.js
 *   + TODO: Clean up code, including refactoring to increase sharing between
 *     procedures_defnoreturn and procedures_defreturn.
 * [lyn, 11/29/12] Integrated into App Inventor blocks. Known bugs:
 *   + Reordering mutator_args in mutator_container changes references to ??? because it interprets it
 *     as removing and inserting rather than moving.
 * [lyn, 11/24/12] Implemented procedure parameter renaming:
 *   + changing a variable name in mutator_arg for procedure changes it immediately in references in body.
 *   + no duplicate names are allowed in mutator_args; alpha-renaming prevents this.
 *   + no variables can be captured by renaming; alpha-renaming prevents this.
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Field from '../core/field';
import Mutator from '../core/mutator';
import Msg from '../core/msg';
import Names from '../core/names';
import Procedures from '../core/procedures';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import FieldFlydown from '../core/field_flydown';
import FieldParameterFlydown from '../core/field_parameter_flydown';
import {PROCEDURE_CATEGORY_HUE} from '../colourscheme';

function stringListsEqual (strings1, strings2) {
  var len1 = strings1.length;
  var len2 = strings2.length;
  if (len1 !== len2) {
    return false;
  } else {
    for (var i = 0; i < len1; i++) {
      if (strings1[i] !== strings2[i]) {
        return false;
      }
    }
  }
  return true; // get here iff lists are equal
};

Blocks['procedures_defnoreturn'] = {
  // Define a procedure with no return value.
  category: 'Procedures',  // Procedures are handled specially.
  helpUrl: Msg.PROCEDURES_DEFNORETURN_HELPURL,
  bodyInputName: 'STACK',
  tooltip: Msg.PROCEDURES_DEFNORETURN_TOOLTIP,
  definesScope: true,
  init: function() {
    this.setColour(PROCEDURE_CATEGORY_HUE);
    var name = Procedures.findLegalName(
        Msg.PROCEDURES_DEFNORETURN_PROCEDURE, this);
    this.appendDummyInput('HEADER')
        .appendField(Msg.PROCEDURES_DEFNORETURN_TITLE)
        .appendField(new FieldTextInput(name, Procedures.rename), 'NAME');
    this.horizontalParameters = true; // horizontal by default
    this.appendStatementInput('STACK')
        .appendField(Msg.PROCEDURES_DEFNORETURN_DO);
    this.setMutator(new Mutator(['procedures_mutatorarg']));
    this.arguments_ = []; // List of declared local variable names; has one ("name") initially
                          // Other methods guarantee the invariant that this variable contains
                          // the list of names declared in the local declaration block.
    this.warnings = [{name:"checkEmptySockets",sockets:["STACK"]}];
  },

  // updateParams_ logic:
  // NB this is NOT a means to change the variable names.
  // This can ONLY be done by changing the textfield in the FieldParameterFlydown, or (indirectly)
  // by changing the field in the mutator which then changes the flydown field.
  //
  //  -> So all we have to do is figure out any reordering, removing or adding of fields (variables).
  //
  // (Note that this method is called by the compose() function after a workspaceChanged event in the
  // mutator workspace when a variable is renamed via the mutator textfield).

  // - fields should contain vars and ids. Compose needs to update ids on fields as well.
  //   AND - there needs to be no way to change the var names apart from the mutator UI and creation from XML.
  // - pull all vars out, and store them with ids.
  // - read new vars + ids, adding fields and renaming vars as necessary.


  updateParams_: function(opt_params) {  // make rendered block reflect the parameter names currently in this.arguments_
    //console.log("enter procedures_defnoreturn updateParams_()");
    // [lyn, 11/17/13] Added optional opt_params argument:
    //    If its falsey (null or undefined), use the existing this.arguments_ list
    //    Otherwise, replace this.arguments_ by opt_params
    // In either case, make rendered block reflect the parameter names in this.arguments_

    if (typeof opt_params !== "undefined") {
      this.arguments_ = opt_params;
    }

	// Check for duplicated arguments.
    // [lyn 10/10/13] Note that in blocks edited within AI2, duplicate parameter names should never occur
    //    because parameters are renamed to avoid duplication. But duplicates might show up
    //    in XML code hand-edited by user.
    var badArg = false;
    var hash = {};
    for (var x = 0; x < this.arguments_.length; x++) {
      if (hash['arg_' + this.arguments_[x].toLowerCase()]) {
        badArg = true;
        break;
      }
      hash['arg_' + this.arguments_[x].toLowerCase()] = true;
    }
    if (badArg) {
      this.setWarningText(Msg.LANG_PROCEDURES_DEF_DUPLICATE_WARNING);
    } else {
      this.setWarningText(null);
    }

    var procName = this.getFieldValue('NAME');
    //save the first two input lines and the last input line
    //to be re added to the block later
    // var firstInput = this.inputList[0];  // [lyn, 10/24/13] need to reconstruct first input
    var bodyInput = this.inputList[this.inputList.length - 1]; // Body of procedure

    // stop rendering until block is recreated
    var savedRendered = this.rendered;
    this.rendered = false;

    // remove first input
    // console.log("updateParams_: remove input HEADER");
    var thisBlock = this; // Grab correct object for use in thunk below
    Blockly.FieldParameterFlydown.withChangeHanderDisabled(
        // [lyn, 07/02/14] Need to disable change handler, else this will try to rename params for horizontal arg fields!
        function() {thisBlock.removeInput('HEADER');}
    );

    // [lyn, 07/02/14 fixed logic] remove all old argument inputs (if they were vertical)
    if (! this.horizontalParameters) {
      var oldArgCount = this.inputList.length - 1; // Only args and body are left
      if (oldArgCount > 0) {
        var paramInput0 = this.getInput('VAR0');
        if (paramInput0) { // Yes, they were vertical
          for (var i = 0; i < oldArgCount; i++)
          {
            try
            {
              FieldParameterFlydown.withChangeHanderDisabled(
                  // [lyn, 07/02/14] Need to disable change handler, else this will try to rename params for vertical arg fields!
                  function() {thisBlock.removeInput('VAR' + i);}
              );
            }
            catch(err)
            {
              console.log(err);
            }
          }
        }
      }
    }

    //empty the inputList then recreate it
    this.inputList = [];

    // console.log("updateParams_: create input HEADER");
    var headerInput =
        this.appendDummyInput('HEADER')
            .appendField(Msg.LANG_PROCEDURES_DEFNORETURN_DEFINE)
            .appendField(new FieldTextInput(procName, Procedures.rename), 'NAME');

    //add an input title for each argument
    //name each input after the block and where it appears in the block to reference it later
	for (var i = 0; i < this.arguments_.length; i++) {
	  var name = this.arguments_[i];

      if (this.horizontalParameters) { // horizontal case
        headerInput.appendField(' ')
                   .appendField(this.parameterFlydown(i, name), // [lyn, 10/10/13] Changed to param flydown
                                'VAR' + i); // Tag with param tag to make it easy to find later.
      } else { // vertical case
        this.appendDummyInput('VAR' + i)
             // .appendField(this.arguments_[i])
             .appendField(this.parameterFlydown(i, name, variable), 'VAR' + i)
             .setAlign(Blockly.ALIGN_RIGHT);
      }
    }

    //put the last two arguments back
    this.inputList = this.inputList.concat(bodyInput);

    this.rendered = savedRendered;
    // [lyn, 10/28/13] I thought this rerendering was unnecessary. But I was wrong!
    // Without it, get bug noticed by Andrew in which toggling horizontal -> vertical params
    // in procedure decl doesn't handle body tag appropriately!
    if (this.rendered) {
       this.render();
    }
    // console.log("exit procedures_defnoreturn updateParams_()");
  },
  // [lyn, 10/26/13] Introduced this to correctly handle renaming of [(1) caller arg labels and
  // (2) mutatorarg in open mutator] when procedure parameter flydown name is edited.
  parameterFlydown: function (paramIndex, name) { // Return a new procedure parameter flydown
    var initialParamName = name;
    var procDecl = this; // Here, "this" is the proc decl block. Name it to use in function below
    var procWorkspace = this.workspace;
    var procedureParameterChangeHandler = function (newParamName) {
      // console.log("enter procedureParameterChangeHandler");


      // Extra work that needs to be done when procedure param name is changed, in addition
      // to renaming lexical variables:
      //   1. Change all callers so label reflects new name
      //   2. If there's an open mutator, change the corresponding slot.
      // Note: this handler is invoked as method on field, so within the handler body,
      // "this" will be bound to that field and *not* the procedure declaration object!

      // Subtlety #1: within this changeHandler, procDecl.arguments_ has *not* yet been
      // updated to include newParamName. This only happens later. But since we know newParamName
      // *and* paramIndex, we know how to update procDecl.arguments_ ourselves!

      // Subtlety #2: I would have thought we would want to create local copy of
      // procedure arguments_ list rather than mutate that list, but I'd be wrong!
      // Turns out that *not* mutating list here causes trouble below in the line
      //
      //   Field.prototype.setText.call(mutatorarg.getTitle_("NAME"), newParamName);
      //
      // The reason is that this fires a change event in mutator workspace, which causes
      // a call to the proc decl compose() method, and when it detects a difference in
      // the arguments it calls proc decl updateParams_. This removes proc decl inputs
      // before adding them back, and all hell breaks loose when the procedure name field
      // and previous parameter flydown fields are disposed before an attempt is made to
      // disposed this field. At this point, the SVG element associated with the procedure name
      // is gone but the field is still in the title list. Attempting to dispose this field
      // attempts to hide the open HTML editor widget, which attempts to re-render the
      // procedure declaration block. But the null SVG for the procedure name field
      // raises an exception.
      //
      // It turns out that by mutating proc decl arguments_, when compose() is called,
      // updateParams_() is *not* called, and this prevents the above scenario.
      //  So rather than doing
      //
      //    var newArguments = [].concat(procDecl.arguments_)
      //
      // we instead do:
      var newArguments = procDecl.arguments_;
      var oldParamName = newArguments[paramIndex];

      if (newParamName === oldParamName) {
        return;
      }

      var variable = procDecl.getVariableScope().getVariable(oldParamName);
      var procName = procDecl.getFieldValue('NAME');

      if (variable) {
        variable.setName(newParamName);
        newParamName = variable.getVarName();
      }

      newArguments[paramIndex] = newParamName;

      // 1. Change all callers so label reflects new name
      Procedures.mutateCallers(procName, procWorkspace, newArguments, procDecl.paramIds_);

      // 2. If there's an open mutator, change the name in the corresponding slot.
      if (procDecl.mutator && procDecl.mutator.rootBlock_) {
        // Iterate through mutatorarg param blocks and change name of one at paramIndex
        var mutatorContainer = procDecl.mutator.rootBlock_;
        var mutatorargIndex = 0;
        var mutatorarg = mutatorContainer.getInputTargetBlock('STACK');
        while (mutatorarg && mutatorargIndex < paramIndex) {
          mutatorarg = mutatorarg.nextConnection && mutatorarg.nextConnection.targetBlock();
          mutatorargIndex++;
        }
        if (mutatorarg && mutatorargIndex == paramIndex) {
          // Subtlety #3: If call mutatorargs's setValue, its change handler will be invoked
          // several times, and on one of those times, it will find new param name in
          // the procedures arguments_ instance variable and will try to renumber it
          // (e.g. "a" -> "a2"). To avoid this, invoke the setText method of its Field s
          // superclass directly. I.e., can't do this:
          //   mutatorarg.getTitle_("NAME").setValue(newParamName);
          // so instead do this:
          Field.prototype.setText.call(mutatorarg.getField_("NAME"), newParamName);
        }
      }
      // console.log("exit procedureParameterChangeHandler");
    }
    var field = new FieldParameterFlydown(initialParamName,
      true, // name is editable
      // [lyn, 10/27/13] flydown location depends on parameter orientation
      this.horizontalParameters ? FieldFlydown.DISPLAY_BELOW
                               : FieldFlydown.DISPLAY_RIGHT,
      procedureParameterChangeHandler
    );
	return field;
  },
  setParameterOrientation: function(isHorizontal) {
    var params = this.getParameters();
    if (params.length != 0 && isHorizontal !== this.horizontalParameters) {
      this.horizontalParameters = isHorizontal;
      this.updateParams_();
    }
  },
  mutationToDom: function() {
    var container = document.createElement('mutation');
    if (!this.horizontalParameters) {
      container.setAttribute('vertical_parameters', "true"); // Only store an element for vertical
      // The absence of this attribute means horizontal.
    }
    for (var x = 0; x < this.arguments_.length; x++) {
      var parameter = document.createElement('arg');
      parameter.setAttribute('name', this.arguments_[x]);
      container.appendChild(parameter);
    }
    return container;
  },
  domToMutation: function(xmlElement) {
    var params = [], scope = this.variableScope_, name;
    var children = $(xmlElement).children();
    for (var x = 0, childNode; childNode = children[x]; x++) {
      if (childNode.nodeName.toLowerCase() == 'arg') {
        name = childNode.getAttribute('name');
        params.push(name);

        // Add variables defined in XML to scope.
        scope.addVariable(name);
      }
    }
    this.horizontalParameters = xmlElement.getAttribute('vertical_parameters') !== "true";
    this.updateParams_(params);
  },
  decompose: function(workspace) {
    var containerBlock = new Block.obtain(workspace, 'procedures_mutatorcontainer');
    containerBlock.initSvg();
    // [lyn, 11/24/12] Remember the associated procedure, so can
    // appropriately change body when update name in param block.
    containerBlock.setProcBlock(this);
    this.paramIds_ = [] // [lyn, 10/26/13] Added
    var connection = containerBlock.getInput('STACK').connection;
    for (var x = 0; x < this.arguments_.length; x++) {
      var paramBlock = new Block.obtain(workspace, 'procedures_mutatorarg');
      this.paramIds_.push(paramBlock.id); // [lyn, 10/26/13] Added
      paramBlock.initSvg();
      paramBlock.setFieldValue(this.arguments_[x], 'NAME');
	  paramBlock.variable_ = this.variableScope_.getVariable(this.arguments_[x]);
      // Store the old location.
      paramBlock.oldLocation = x;
      connection.connect(paramBlock.previousConnection);
      connection = paramBlock.nextConnection;
    }
    // [lyn, 10/26/13] Rather than passing null for paramIds, pass actual paramIds
    // and use true flag to initialize tracking.
    Procedures.mutateCallers(this.getFieldValue('NAME'),
                                     this.workspace, this.arguments_, this.paramIds_, true);
    return containerBlock;
  },
  compose: function(containerBlock) {
    //console.log("Compose: Old Param IDs", this.paramIds_, "arguments: ", this.arguments_);
    var params = [];
    this.paramIds_ = [];
    var paramBlock = containerBlock.getInputTargetBlock('STACK');
    while (paramBlock) {
      params.push(paramBlock.getFieldValue('NAME'));
      this.paramIds_.push(paramBlock.id);
      paramBlock = paramBlock.nextConnection &&
          paramBlock.nextConnection.targetBlock();
    }
	//console.log("Compose: New Param IDs", this.paramIds_, " Params: ", params);
    // console.log("enter procedures_defnoreturn compose(); prevArguments = "
    //    + prevArguments.join(',')
    //    + "; currentAguments = "
    //    + this.arguments_.join(',')
    //    + ";"
    // );
    // [lyn, 11/24/12] Note: update params updates param list in proc declaration,
    // but renameParam updates procedure body appropriately.
    if (!stringListsEqual(params, this.arguments_)) { // Only need updates if param list has changed
      this.updateParams_(params);
      Procedures.mutateCallers(this.getFieldValue('NAME'),
        this.workspace, this.arguments_, this.paramIds_);
    }
    // console.log("exit procedures_defnoreturn compose()");
  },
  dispose: function() {
    var name = this.getFieldValue('NAME');
    var editable = this.editable_;
    var workspace = this.workspace;

    // Call parent's destructor.
    Block.prototype.dispose.apply(this, arguments);

    if (editable) {
      // Dispose of any callers.
      //Procedures.disposeCallers(name, workspace);
      Procedures.removeProcedureValues(name, workspace);
    }

  },
  getProcedureDef: function() {
    // Return the name of the defined procedure,
    // a list of all its arguments,
    // and that it DOES NOT have a return value.
    return [this.getFieldValue('NAME'),
            this.arguments_,
           this.bodyInputName === 'RETURN']; // true for procedures that return values.
  },
  getVars: function() {
    var names = []
    for (var i = 0, field; field = this.getField_('VAR' + i); i++) {
      names.push(field.getValue());
    }
    return names;
  },
  declaredNames: function() { // [lyn, 10/11/13] return the names of all parameters of this procedure
     return this.getVars();
  },
  //renameVar: function(oldName, newName) {
  //  this.renameVars(Substitution.simpleSubstitution(oldName,newName));
  //},
  // [lyn, 11/24/12] return list of procedure body (if there is one)
  blocksInScope: function () {
    var body = this.getInputTargetBlock(this.bodyInputName);
    return (body && [body]) || [];
  },
  //typeblock: [{ translatedName: Msg.LANG_PROCEDURES_DEFNORETURN_PROCEDURE +
  //    ' ' + Msg.LANG_PROCEDURES_DEFNORETURN_DO }],
  customContextMenu: function (options) {
    FieldParameterFlydown.addHorizontalVerticalOption(this, options);
  },
  getParameters: function() {
    return this.arguments_;
  },
  getParameterVariables: function () {
    var scope = this.getVariableScope();
    var parameterVariables = [];
    for (var x = 0; x < this.arguments_.length; x++) {
      parameterVariables.push(scope.getVariable(this.arguments_[x]));
    }
    return parameterVariables;
  }
};

// [lyn, 01/15/2013] Edited to remove STACK (no longer necessary with DO-THEN-RETURN)
Blocks['procedures_defreturn'] = {
  // Define a procedure with a return value.
  category: 'Procedures',  // Procedures are handled specially.
  helpUrl: Msg.PROCEDURES_DEFRETURN_HELPURL,
  tooltip: Msg.PROCEDURES_DEFRETURN_TOOLTIP,
  bodyInputName: 'RETURN',
  definesScope: true,
  init: function() {
    this.setColour(PROCEDURE_CATEGORY_HUE);
    var name = Procedures.findLegalName(
        Msg.PROCEDURES_DEFRETURN_PROCEDURE, this);
    this.appendDummyInput('HEADER')
        .appendField(Msg.PROCEDURES_DEFRETURN_TITLE)
        .appendField(new FieldTextInput(name, Procedures.rename), 'NAME');
    this.horizontalParameters = true; // horizontal by default
    this.appendValueInput('RETURN')
        .appendField(Msg.PROCEDURES_DEFRETURN_RETURN);
    this.setMutator(new Mutator(['procedures_mutatorarg']));
    this.arguments_ = [];
    this.warnings = [{name:"checkEmptySockets",sockets:["RETURN"]}];
  },
  onchange: Blocks.procedures_defnoreturn.onchange,
  // [lyn, 11/24/12] return list of procedure body (if there is one)
  updateParams_: Blocks.procedures_defnoreturn.updateParams_,
  parameterFlydown: Blocks.procedures_defnoreturn.parameterFlydown,
  setParameterOrientation: Blocks.procedures_defnoreturn.setParameterOrientation,
  mutationToDom: Blocks.procedures_defnoreturn.mutationToDom,
  domToMutation: Blocks.procedures_defnoreturn.domToMutation,
  decompose: Blocks.procedures_defnoreturn.decompose,
  compose: Blocks.procedures_defnoreturn.compose,
  dispose: Blocks.procedures_defnoreturn.dispose,
  getProcedureDef: Blocks.procedures_defnoreturn.getProcedureDef,
  getVars: Blocks.procedures_defnoreturn.getVars,
  declaredNames: Blocks.procedures_defnoreturn.declaredNames,
  blocksInScope: Blocks.procedures_defnoreturn.blocksInScope,
  //typeblock: [{ translatedName: Msg.LANG_PROCEDURES_DEFRETURN_PROCEDURE +
  //    ' ' + Msg.LANG_PROCEDURES_DEFRETURN_RETURN }],
  customContextMenu: Blocks.procedures_defnoreturn.customContextMenu,
  getParameters: Blocks.procedures_defnoreturn.getParameters
};

Blocks['procedures_mutatorcontainer'] = {
  // Procedure container (for mutator dialog).
  init: function() {
    this.setColour(PROCEDURE_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(Msg.PROCEDURES_MUTATORCONTAINER_TITLE);
    this.appendStatementInput('STACK');
    this.setTooltip(Msg.PROCEDURES_MUTATORCONTAINER_TOOLTIP);
    this.contextMenu = false;
  },
  // [lyn. 11/24/12] Set procBlock associated with this container.
  setProcBlock: function (procBlock) {
    this.procBlock_ = procBlock;
  },
  // [lyn. 11/24/12] Set procBlock associated with this container.
  // Invariant: should not be null, since only created as mutator for a particular proc block.
  getProcBlock: function () {
    return this.procBlock_;
  }
};

Blocks['procedures_mutatorarg'] = {
  // Procedure argument (for mutator dialog).
  init: function() {
    this.setColour(PROCEDURE_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(Msg.PROCEDURES_MUTATORARG_TITLE)
        .appendField(new FieldTextInput('x', this.renamed.bind(this)), 'NAME');
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.setTooltip(Msg.PROCEDURES_MUTATORARG_TOOLTIP);
    this.contextMenu = false;
  },
  getContainerBlock: function () {
    this.cachedContainerBlock_ = this.getAncestor("procedures_mutatorcontainer");
    return this.cachedContainerBlock_;
  },
  // [lyn, 11/24/12] Return the procedure associated with mutator arg is in, or null if there isn't one.
  // Dynamically calculate this by walking up chain, because mutator arg might or might not
  // be in container stack.
  getProcBlock: function () {
	var container = this.getContainerBlock();
    return (container && container.getProcBlock()) || null;
  },
  getScope: function () {
    if (this.cachedScope_) return this.cachedScope_;
    var procBlock = this.getProcBlock();
    if (this.isInFlyout || !procBlock) {
      return;
    }
    var scope = procBlock.getVariableScope(true);
	this.cachedScope_ = scope;
	return scope;
  },
  renamed: function (newName) {
    if (this.variable_) {
      this.variable_.setName(newName);
	  newName = this.variable_.getVarName();
    }
	return newName;
  },
  created: function () {
    var scope = this.getScope();
    if (!scope) {
      return;
    }
    if (this.variable_) {
      this.attached_ = true;
      return;
    }
    var paramName = this.getFieldValue('NAME');
    var newName = scope.validName(paramName);
    if (newName !== paramName) {
      this.setFieldValue(newName, 'NAME');
    }
    this.attached_ = true;
    this.variable_ = scope.addVariable(newName);
  },
  disposed: function () {
    var scope = this.getScope();
    if (!scope || this.attached_) {
      return;
    }
    scope.removeVariable(this.variable_.getVarName());
    delete this.variable_;
  },
  // TODO: this could possibly all be rewritten and incorporated into the decompose() function.
  setParent: function (newParent) {
    var paramName = this.getFieldValue('NAME');
    var attached = (!this.parentBlock_ && newParent);

    Block.prototype.setParent.call(this, newParent);
    if (paramName) { // paramName is null when deleting from stack
      if (attached) {
        this.created();
      }
    }
  },
  onchange: function() {
    var paramName = this.getFieldValue('NAME');
    var oldContainer = this.cachedContainerBlock_;
    // Order is important; this must come after cachedContainer
    // since it sets cachedContainerBlock_
    var newContainer = this.getContainerBlock();

    if (paramName) { // paramName is null when deleting from stack
      if (!oldContainer && newContainer) {
        this.created();
      } else if (oldContainer && !newContainer) {
        this.attached_ = false;
      }
    }
  }
};

Blocks.procedures_mutatorarg.validator = function(newVar) {
  // Merge runs of whitespace.  Strip leading and trailing whitespace.
  // Beyond this, all names are legal.
  newVar = newVar.replace(/[\s\xa0]+/g, ' ').replace(/^ | $/g, '');
  return newVar || null;
};


Blocks['procedures_callnoreturn'] = {
  // Call a procedure with no return value.
  category: 'Procedures',  // Procedures are handled specially.
  tooltop: Msg.LANG_PROCEDURES_CALLNORETURN_TOOLTIP,
  init: function() {
    this.setHelpUrl(Msg.PROCEDURES_CALLNORETURN_HELPURL);
    this.setColour(PROCEDURE_CATEGORY_HUE);
    this.procNamesFxn = function(){return Procedures.getProcedureNames(false);};

    this.procDropDown = new FieldDropdown(this.procNamesFxn, this.onChangeProcedure);
    this.procDropDown.block = this;
    this.appendDummyInput()
        .appendField(Msg.LANG_PROCEDURES_CALLNORETURN_CALL)
        .appendField(this.procDropDown,"NAME");
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.arguments_ = [];
    this.quarkConnections_ = null;
    this.quarkArguments_ = null;
    this.errors = [{name:"checkIsInDefinition"},{name:"checkDropDownContainsValidValue",dropDowns:["NAME"]}];
    this.onChangeProcedure.call(this.getField_("NAME"),this.getField_("NAME").getValue());
  },
  onChangeProcedure: function(text) {
    var workspace = this.block.workspace;
    if (!this.block.editable_){
      //workspace = Blockly.Drawer.flyout_.workspace_;
      return;
    }

    if (text == "" || text != this.getValue()) {
      for(var i=0;this.block.getInput('ARG' + i) != null;i++){
        this.block.removeInput('ARG' + i);
      }
      //return;
    }
    this.setValue(text);
    var def = Procedures.getDefinition(text, workspace);
    if (def) {
      // [lyn, 10/27/13] Lyn sez: this causes complications (e.g., might open up mutator on collapsed procedure
      //   declaration block) and is no longer necessary with changes to setProedureParameters.
      // if(def.paramIds_ == null){
      //  def.mutator.setVisible(true);
      //  def.mutator.shouldHide = true;
      //}
      this.block.setProcedureParameters(def.arguments_, def.paramIds_, true); // It's OK if def.paramIds is null
    }
  },
  getProcedureCall: function() {
    return this.getFieldValue('NAME');
  },
  renameProcedure: function(oldName, newName) {
    if (Names.equals(oldName, this.getFieldValue('NAME'))) {
      this.setFieldValue(newName, 'NAME');
    }
  },
  // [lyn, 10/27/13] Renamed "fromChange" parameter to "startTracking", because it should be true in any situation
  // where we want caller to start tracking connections associated with paramIds. This includes when a mutator
  // is opened on a procedure declaration.
  setProcedureParameters: function(paramNames, paramIds, startTracking) {
    // Data structures for parameters on each call block:
    // this.arguments = ['x', 'y']
    //     Existing param names.
    // paramNames = ['x', 'y', 'z']
    //     New param names.
    // paramIds = ['piua', 'f8b_', 'oi.o']
    //     IDs of params (consistent for each parameter through the life of a
    //     mutator, regardless of param renaming).
    // this.quarkConnections_ {piua: null, f8b_: Connection}
    //     Look-up of paramIds to connections plugged into the call block.
    // this.quarkArguments_ = ['piua', 'f8b_']
    //     Existing param IDs.
    // Note that quarkConnections_ may include IDs that no longer exist, but
    // which might reappear if a param is reattached in the mutator.

    var input;
    var connection;
    var x;

    //fixed parameter alignment see ticket 465
    if (!paramIds) {
      // Reset the quarks (a mutator is about to open).
      this.quarkConnections_ = {};
      this.quarkArguments_ = null;
      // return;  // [lyn, 10/27/13] No, don't return yet. We still want to add paramNames to block!
      // For now, create dummy list of param ids. This needs to be cleaned up further!
      paramIds = [].concat(paramNames); // create a dummy list that's a copy of paramNames.
    }
    if (paramIds.length != paramNames.length) {
      throw 'Error: paramNames and paramIds must be the same length.';
    }
    var paramIdToParamName = {};
    for(var i=0;i<paramNames.length;i++) {
      paramIdToParamName[paramIds[i]] = paramNames[i];
    }
    if(typeof startTracking == "undefined") {
      startTracking = null;
    }

    if (!this.quarkArguments_ || startTracking) {
      // Initialize tracking for this block.
      this.quarkConnections_ = {};
      if (stringListsEqual(paramNames, this.arguments_) || startTracking) {
        // No change to the parameters, allow quarkConnections_ to be
        // populated with the existing connections.
        this.quarkArguments_ = paramIds;
      } else {
        this.quarkArguments_ = [];
      }
    }
    // Switch off rendering while the block is rebuilt.
    var savedRendered = this.rendered;
    this.rendered = false;
    // Update the quarkConnections_ with existing connections.
    for (x = 0;this.getInput('ARG' + x); x++) {
      input = this.getInput('ARG' + x);
      if (input) {
        connection = input.connection.targetConnection;
        this.quarkConnections_[this.quarkArguments_[x]] = connection;
        // Disconnect all argument blocks and remove all inputs.
        this.removeInput('ARG' + x);
      }
    }
    // Rebuild the block's arguments.
    this.arguments_ = [].concat(paramNames);
    this.quarkArguments_ = paramIds;
    for (x = 0; x < this.arguments_.length; x++) {
      input = this.appendValueInput('ARG' + x)
          .setAlign(Blockly.ALIGN_RIGHT)
          .appendField(this.arguments_[x]);
      if (this.quarkArguments_) {
        // Reconnect any child blocks.
        var quarkName = this.quarkArguments_[x];
        if (quarkName in this.quarkConnections_) {
          connection = this.quarkConnections_[quarkName];
          if (!connection || connection.targetConnection ||
              connection.sourceBlock_.workspace != this.workspace) {
            // Block no longer exists or has been attached elsewhere.
            delete this.quarkConnections_[quarkName];
          } else {
            input.connection.connect(connection);
          }
        } else if(paramIdToParamName[quarkName]){
          connection = this.quarkConnections_[paramIdToParamName[quarkName]];
          if (connection){
            input.connection.connect(connection);
          }
        }
      }
    }
    // Restore rendering and show the changes.
    this.rendered = savedRendered;
    if (this.rendered) {
      this.render();
    }
  },
  mutationToDom: function() {
    // Save the name and arguments (none of which are editable).
    var container = document.createElement('mutation');
    container.setAttribute('name', this.getFieldValue('NAME'));
    for (var x = 0; this.getInput("ARG" + x); x++) {
      var parameter = document.createElement('arg');
      parameter.setAttribute('name', this.getInput("ARG" + x).fieldRow[0].text_);
      container.appendChild(parameter);
    }
    return container;
  },
  domToMutation: function(xmlElement) {
    // Restore the name and parameters.
    var name = xmlElement.getAttribute('name');
    this.setFieldValue(name, 'NAME');
    // [lyn, 10/27/13] Significantly cleaned up this code. Always take arg names from xmlElement.
    // Do not attempt to find definition.
    this.arguments_ = [];
    var children = $(xmlElement).children();
    for (var x = 0, childNode; childNode = children[x]; x++) {
      if (childNode.nodeName.toLowerCase() == 'arg') {
        this.arguments_.push(childNode.getAttribute('name'));
      }
    }
    this.setProcedureParameters(this.arguments_, null, true);
      // [lyn, 10/27/13] Above. set tracking to true in case this is a block with argument subblocks.
      // and there's an open mutator.
  },
  /*renameVar: function(oldName, newName) {
    for (var x = 0; x < this.arguments_.length; x++) {
      if (Names.equals(oldName, this.arguments_[x])) {
        this.arguments_[x] = newName;
        this.getInput('ARG' + x).fieldRow[0].setText(newName);
      }
    }
  },*/
  procCustomContextMenu: function(options) {
    // Add option to find caller.
    var option = {enabled: true};
    option.text = Msg.LANG_PROCEDURES_HIGHLIGHT_DEF;
    var name = this.getFieldValue('NAME');
    var workspace = this.workspace;
    option.callback = function() {
      var def = Procedures.getDefinition(name, workspace);
      def && def.select();
    };
    options.push(option);
  },
  removeProcedureValue: function() {
    this.setFieldValue("none", 'NAME');
    for(var i=0;this.getInput('ARG' + i) !== null;i++) {
      this.removeInput('ARG' + i);
    }
  },
  // This generates a single generic call to 'call no return' defaulting its value
  // to the first procedure in the list. Calls for each procedure cannot be done here because the
  // blocks have not been loaded yet (they are loaded in typeblock.js)
  //typeblock: [{ translatedName: Blockly.Msg.LANG_PROCEDURES_CALLNORETURN_TRANSLATED_NAME}]
};


Blocks['procedures_callreturn'] = {
  // Call a procedure with a return value.
  category: 'Procedures',  // Procedures are handled specially.
  tooltip: Msg.PROCEDURES_CALLRETURN_TOOLTIP,
  init: function() {
    this.setHelpUrl(Msg.PROCEDURES_CALLRETURN_HELPURL);
    this.setColour(PROCEDURE_CATEGORY_HUE);
    this.procNamesFxn = function(){return Procedures.getProcedureNames(true);};

    this.procDropDown = new FieldDropdown(this.procNamesFxn, Blocks.procedures_callnoreturn.onChangeProcedure);
    this.procDropDown.block = this;
    this.appendDummyInput()
        .appendField(Msg.PROCEDURES_CALLRETURN_CALL)
        .appendField(this.procDropDown,"NAME");
    this.setOutput(true, null);
    this.arguments_ = [];
    this.quarkConnections_ = null;
    this.quarkArguments_ = null;
    this.errors = [{name:"checkIsInDefinition"},{name:"checkDropDownContainsValidValue",dropDowns:["NAME"]}];
    Blocks.procedures_callnoreturn.onChangeProcedure.call(this.getField_("NAME"),this.getField_("NAME").getValue());
  },
  getProcedureCall: Blocks.procedures_callnoreturn.getProcedureCall,
  renameProcedure: Blocks.procedures_callnoreturn.renameProcedure,
  setProcedureParameters:
      Blocks.procedures_callnoreturn.setProcedureParameters,
  mutationToDom: Blocks.procedures_callnoreturn.mutationToDom,
  domToMutation: Blocks.procedures_callnoreturn.domToMutation,
  //renameVar: Blocks.procedures_callnoreturn.renameVar,
  procCustomContextMenu: Blocks.procedures_callnoreturn.procCustomContextMenu,
  removeProcedureValue: Blocks.procedures_callnoreturn.removeProcedureValue,
  // This generates a single generic call to 'call return' defaulting its value
  // to the first procedure in the list. Calls for each procedure cannot be done here because the
  // blocks have not been loaded yet (they are loaded in typeblock.js)
  //typeblock: [{ translatedName: Msg.LANG_PROCEDURES_CALLRETURN_TRANSLATED_NAME}]
};

Blocks['procedures_namedsequence'] = {
  // Define a named sequence.
  category: 'Procedures',  // Procedures are handled specially.
  helpUrl: '', //Msg.PROCEDURES_DEFNORETURN_HELPURL,
  bodyInputName: 'STACK',
  tooltip: 'Define a named sequence', // TODO: extract Msg.PROCEDURES_DEFNORETURN_TOOLTIP,
  init: function() {
    this.setColour(PROCEDURE_CATEGORY_HUE);
    var name = Procedures.findLegalName(
        Msg.PROCEDURES_DEFNORETURN_PROCEDURE, this);
    this.appendDummyInput('HEADER')
        .appendField(Msg.PROCEDURES_DEFNORETURN_TITLE)
        .appendField(new FieldTextInput(name, Procedures.rename), 'NAME');
    this.appendStatementInput('STACK')
        .appendField(Msg.PROCEDURES_DEFNORETURN_DO);
    this.warnings = [{name:"checkEmptySockets",sockets:["STACK"]}];

	this.arguments_ = [];
	this.paramIds_ = [];
  },
  dispose: function() {
    var name = this.getFieldValue('NAME');
    var editable = this.editable_;
    var workspace = this.workspace;

    // Call parent's destructor.
      Block.prototype.dispose.apply(this, arguments);

    if (editable) {
      // Dispose of any callers.
      Procedures.removeProcedureValues(name, workspace);
    }
  },
  getProcedureDef: function() {
    // Return the name of the defined procedure,
    // a list of all its arguments,
    // and that it DOES NOT have a return value.
    return [this.getFieldValue('NAME'),
            [], // no arguments
           "sequence"]; // no return value.
  },
  // [lyn, 11/24/12] return list of procedure body (if there is one)
  blocksInScope: function () {
    var body = this.getInputTargetBlock(this.bodyInputName);
    return (body && [body]) || [];
  }
};

Blocks['procedures_callnamedsequence'] = {
  // Call a procedure with a return value.
  category: 'Procedures',  // Procedures are handled specially.
  tooltip: Msg.PROCEDURES_CALLRETURN_TOOLTIP,
  init: function() {
    this.setHelpUrl(Msg.PROCEDURES_CALLRETURN_HELPURL);
    this.setColour(PROCEDURE_CATEGORY_HUE);
    this.procNamesFxn = function(){return Procedures.getNamedSequenceNames();};

    this.procDropDown = new FieldDropdown(this.procNamesFxn,Blocks.procedures_callnoreturn.onChangeProcedure);
    this.procDropDown.block = this;
    this.appendDummyInput()
        .appendField(Msg.PROCEDURES_CALLRETURN_CALL)
        .appendField(this.procDropDown,"NAME");
    this.setPreviousStatement(true);
    this.setNextStatement(true);
    this.arguments_ = [];
    this.quarkConnections_ = null;
    this.quarkArguments_ = null;
    this.errors = [{name:"checkIsInDefinition"},{name:"checkDropDownContainsValidValue",dropDowns:["NAME"]}];
    Blocks.procedures_callnoreturn.onChangeProcedure.call(this.getField_("NAME"),this.getField_("NAME").getValue());
  },
  getProcedureCall: Blocks.procedures_callnoreturn.getProcedureCall,
  renameProcedure: Blocks.procedures_callnoreturn.renameProcedure,
  setProcedureParameters:
      Blocks.procedures_callnoreturn.setProcedureParameters,
  mutationToDom: Blocks.procedures_callnoreturn.mutationToDom,
  domToMutation: Blocks.procedures_callnoreturn.domToMutation,
  //renameVar: Blocks.procedures_callnoreturn.renameVar,
  procCustomContextMenu: Blocks.procedures_callnoreturn.procCustomContextMenu,
  removeProcedureValue: Blocks.procedures_callnoreturn.removeProcedureValue,
  // This generates a single generic call to 'call return' defaulting its value
  // to the first procedure in the list. Calls for each procedure cannot be done here because the
  // blocks have not been loaded yet (they are loaded in typeblock.js)
  //typeblock: [{ translatedName: Msg.LANG_PROCEDURES_CALLRETURN_TRANSLATED_NAME}]
};
