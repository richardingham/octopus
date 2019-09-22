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
 * @fileoverview Utility functions for handling procedures.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Blocks from './blocks';
import Block from './block';
import Workspace from './workspace';
import Names from './names';

var Procedures = {};
export default Procedures;

/**
 * Find all user-created procedure definitions.
 * @return {!Array.<!Array.<!Array>>} Pair of arrays, the
 *     first contains procedures without return variables, the second with.
 *     Each procedure is defined by a three-element list of name, parameter
 *     list, and return value boolean.
 */
Procedures.allProcedures = function() {
  var blocks = Blockly.mainWorkspace.getAllBlocks();
  var sequencesReturn = [];
  var proceduresReturn = [];
  var proceduresNoReturn = [];
  for (var x = 0; x < blocks.length; x++) {
    var func = blocks[x].getProcedureDef;
    if (func) {
      var tuple = func.call(blocks[x]);
      if (tuple) {
        if (tuple[2] == "sequence") {
          sequencesReturn.push(tuple);
        } else if (tuple[2]) {
          proceduresReturn.push(tuple);
        } else {
          proceduresNoReturn.push(tuple);
        }
      }
    }
  }

  proceduresNoReturn.sort(Procedures.procTupleComparator_);
  proceduresReturn.sort(Procedures.procTupleComparator_);
  return [proceduresNoReturn, proceduresReturn, sequencesReturn];
};

/**
 * Comparison function for case-insensitive sorting of the first element of
 * a tuple.
 * @param {!Array} ta First tuple.
 * @param {!Array} tb Second tuple.
 * @return {number} -1, 0, or 1 to signify greater than, equality, or less than.
 * @private
 */
Procedures.procTupleComparator_ = function(ta, tb) {
  var a = ta[0].toLowerCase();
  var b = tb[0].toLowerCase();
  if (a > b) {
    return 1;
  }
  if (a < b) {
    return -1;
  }
  return 0;
};

/**
 * Ensure two identically-named procedures don't exist.
 * @param {string} name Proposed procedure name.
 * @param {!Block} block Block to disambiguate.
 * @return {string} Non-colliding name.
 */
Procedures.findLegalName = function(name, block) {
  if (block.isInFlyout) {
    // Flyouts can have multiple procedures called 'procedure'.
    return name;
  }
  while (!Procedures.isLegalName(name, block.workspace, block)) {
    // Collision with another procedure.
    var r = name.match(/^(.*?)(\d+)$/);
    if (!r) {
      name += '2';
    } else {
      name = r[1] + (parseInt(r[2], 10) + 1);
    }
  }
  return name;
};

/**
 * Does this procedure have a legal name?  Illegal names include names of
 * procedures already defined.
 * @param {string} name The questionable name.
 * @param {!Workspace} workspace The workspace to scan for collisions.
 * @param {Block} opt_exclude Optional block to exclude from
 *     comparisons (one doesn't want to collide with oneself).
 * @return {boolean} True if the name is legal.
 */
Procedures.isLegalName = function(name, workspace, opt_exclude) {
  var blocks = workspace.getAllBlocks();
  // Iterate through every block and check the name.
  for (var x = 0; x < blocks.length; x++) {
    if (blocks[x] == opt_exclude) {
      continue;
    }
    var func = blocks[x].getProcedureDef;
    if (func) {
      var procName = func.call(blocks[x]);
      if (Names.equals(procName[0], name)) {
        return false;
      }
    }
  }
  return true;
};

/**
 * Rename a procedure.  Called by the editable field.
 * @param {string} text The proposed new name.
 * @return {string} The accepted name.
 * @this {!FieldVariable}
 */
Procedures.rename = function(text) {
  // Strip leading and trailing whitespace.  Beyond this, all names are legal.
  text = text.replace(/^[\s\xa0]+|[\s\xa0]+$/g, '');

  // Ensure two identically-named procedures don't exist.
  text = Procedures.findLegalName(text, this.sourceBlock_);
  // Rename any callers.
  var blocks = this.sourceBlock_.workspace.getAllBlocks();
  for (var x = 0; x < blocks.length; x++) {
    var func = blocks[x].renameProcedure;
    if (func) {
      func.call(blocks[x], this.text_, text);
    }
  }
  return text;
};

/**
 * Construct the blocks required by the flyout for the procedure category.
 * @param {!Array.<!Block>} blocks List of blocks to show.
 * @param {!Array.<number>} gaps List of widths between blocks.
 * @param {number} margin Standard margin width for calculating gaps.
 * @param {!Workspace} workspace The flyout's workspace.
 */
Procedures.flyoutCategory = function(blocks, gaps, margin, workspace) {
  var defaultBlocks = ['procedures_defnoreturn', 'procedures_defreturn', 'procedures_ifreturn', 'procedures_namedsequence'];
  for (var x = 0; x < defaultBlocks.length; x++) {
    if (Blocks[defaultBlocks[x]]) {
      var block = Block.obtain(workspace, defaultBlocks[x]);
      block.initSvg();
      blocks.push(block);
      gaps.push(margin * 2);
    }
  }
  if (gaps.length) {
    // Add slightly larger gap between system blocks and user calls.
    gaps[gaps.length - 1] = margin * 3;
  }

  function populateProcedures(procedureList, templateName) {
    for (var x = 0; x < procedureList.length; x++) {
      var block = Block.obtain(workspace, templateName);
      block.setFieldValue(procedureList[x][0], 'NAME');
      var tempIds = [];
      for (var t = 0; t < procedureList[x][1].length; t++) {
        tempIds[t] = 'ARG' + t;
      }
      block.setProcedureParameters(procedureList[x][1], tempIds);
      block.initSvg();
      blocks.push(block);
      gaps.push(margin * 2);
    }
  }

  var tuple = Procedures.allProcedures();
  populateProcedures(tuple[0], 'procedures_callnoreturn');
  populateProcedures(tuple[1], 'procedures_callreturn');
  populateProcedures(tuple[2], 'procedures_callnamedsequence');
};

/**
 * Find all the callers of a named procedure.
 * @param {string} name Name of procedure.
 * @param {!Workspace} workspace The workspace to find callers in.
 * @return {!Array.<!Block>} Array of caller blocks.
 */
Procedures.getCallers = function(name, workspace) {
  var callers = [];
  var blocks = workspace.getAllBlocks();
  // Iterate through every block and check the name.
  for (var x = 0; x < blocks.length; x++) {
    var func = blocks[x].getProcedureCall;
    if (func) {
      var procName = func.call(blocks[x]);
      // Procedure name may be null if the block is only half-built.
      if (procName && Names.equals(procName, name)) {
        callers.push(blocks[x]);
      }
    }
  }
  return callers;
};

/**
 * When a procedure definition is disposed of, find and dispose of all its
 *     callers.
 * @param {string} name Name of deleted procedure definition.
 * @param {!Workspace} workspace The workspace to delete callers from.
 */
Procedures.disposeCallers = function(name, workspace) {
  var callers = Procedures.getCallers(name, workspace);
  for (var x = 0; x < callers.length; x++) {
    callers[x].dispose(true, false);
  }
};

/**
 * When a procedure definition changes its parameters, find and edit all its
 * callers.
 * @param {string} name Name of edited procedure definition.
 * @param {!Workspace} workspace The workspace to delete callers from.
 * @param {!Array.<string>} paramNames Array of new parameter names.
 * @param {!Array.<string>} paramIds Array of unique parameter IDs.
 */
Procedures.mutateCallers = function(name, workspace, paramNames, paramIds, startTracking) {
  var callers = Procedures.getCallers(name, workspace);
  for (var x = 0; x < callers.length; x++) {
    callers[x].setProcedureParameters(paramNames, paramIds, startTracking);
  }
};

/**
 * Find the definition block for the named procedure.
 * @param {string} name Name of procedure.
 * @param {!Workspace} workspace The workspace to search.
 * @return {Block} The procedure definition block, or null not found.
 */
Procedures.getDefinition = function(name, workspace) {
  var blocks = workspace.getAllBlocks();
  for (var x = 0; x < blocks.length; x++) {
    var func = blocks[x].getProcedureDef;
    if (func) {
      var tuple = func.call(blocks[x]);
      if (tuple && Names.equals(tuple[0], name)) {
        return blocks[x];
      }
    }
  }
  return null;
};

Procedures.getProcedureNames = function(returnValue) {
  var topBlocks = Blockly.mainWorkspace.getTopBlocks();
  var procNameArray = [["","none"]];
  for(var i=0;i<topBlocks.length;i++){
    var procName = topBlocks[i].getFieldValue('NAME')
    if(topBlocks[i].type == "procedures_defnoreturn" && !returnValue) {
      procNameArray.push([procName,procName]);
    } else if (topBlocks[i].type == "procedures_defreturn" && returnValue) {
      procNameArray.push([procName,procName]);
    }
  }
  if(procNameArray.length > 1 ){
    procNameArray.splice(0,1);
  }
  return procNameArray;
};

Procedures.getNamedSequenceNames = function () {
  var topBlocks = Blockly.mainWorkspace.getTopBlocks();
  var procNameArray = [["","none"]];
  for(var i=0;i<topBlocks.length;i++){
    var procName = topBlocks[i].getFieldValue('NAME')
    if (topBlocks[i].type == "procedures_namedsequence") {
      procNameArray.push([procName,procName]);
    }
  }
  if(procNameArray.length > 1 ){
    procNameArray.splice(0,1);
  }
  return procNameArray;
};

Procedures.removeProcedureValues = function(name, workspace) {
  if (workspace  // [lyn, 04/13/14] ensure workspace isn't undefined
      && workspace === Blockly.mainWorkspace) {
    var blockArray = workspace.getAllBlocks();
    for(var i=0;i<blockArray.length;i++){
      var block = blockArray[i];
      if(block.type == "procedures_callreturn" || block.type == "procedures_callnoreturn") {
        if(block.getFieldValue('NAME') == name) {
          block.removeProcedureValue();
        }
      }
    }
  }
};
