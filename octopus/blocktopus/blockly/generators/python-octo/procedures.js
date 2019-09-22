/**
 * @license
 * Visual Blocks Language
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
 * @fileoverview Generating Python for procedure blocks.
 * @author fraser@google.com (Neil Fraser)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER, STATEMENT_PREFIX, INFINITE_LOOP_TRAP, INDENT} from '../python-octo-constants';
import {getVariableName, getProcedureName, addDefinition, statementToCode, valueToCode, prefixLines, scrub} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['procedures_defreturn'] = function(block) {
  // Define a procedure with a return value.

  var funcName = getProcedureName(block.getFieldValue('NAME'));
  var branch = statementToCode(block, 'STACK');
  if (STATEMENT_PREFIX) {
    branch = prefixLines(
      STATEMENT_PREFIX.replace(/%1/g, '\'' + block.id + '\''), INDENT
    ) + branch;
  }
  if (INFINITE_LOOP_TRAP) {
    branch = INFINITE_LOOP_TRAP.replace(/%1/g, '"' + block.id + '"') + branch;
  }
  var returnValue = valueToCode(block, 'RETURN', ORDER.NONE) || '';
  if (returnValue) {
    returnValue = 'return ' + returnValue + '\n';
  } else if (!branch) {
    branch = 'pass';
  }
  var parameterVariables = block.getParameterVariables();
  var args = [];
  for (var x = 0; x < parameterVariables.length; x++) {
    args[x] = getVariableName(parameterVariables[x]);
  }
  var code = 'def ' + funcName + '(' + args.join(', ') + '):\n' +
      prefixLines(branch + returnValue, INDENT);
  code = scrub(block, code);
  addDefinition(funcName, code);
  return null;
};


// Defining a procedure without a return value uses the same generator as
// a procedure with a return value.
PythonOcto['procedures_defnoreturn'] =
    PythonOcto['procedures_defreturn'];

PythonOcto['procedures_callreturn'] = function(block) {
  // Call a procedure with a return value.
  var funcName = getProcedureName(block.getFieldValue('NAME'));
  var args = [];
  for (var x = 0; x < block.getParameters().length; x++) {
    args[x] = valueToCode(block, 'ARG' + x, ORDER.NONE) || 'None';
  }
  var code = funcName + '(' + args.join(', ') + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['procedures_callnoreturn'] = function(block) {
  // Call a procedure with no return value.
  var funcName = getProcedureName(block.getFieldValue('NAME'));
  var args = [];
  for (var x = 0; x < block.getParameters().length; x++) {
    args[x] = valueToCode(block, 'ARG' + x, ORDER.NONE) || 'None';
  }
  var code = funcName + '(' + args.join(', ') + ')';
  return code;
};

PythonOcto['procedures_ifreturn'] = function(block) {
  // Conditionally return value from a procedure.
  var condition = valueToCode(block, 'CONDITION', ORDER.NONE) || 'False';
  var code = 'if ' + condition + ':\n';
  if (block.hasReturnValue_) {
    var value = valueToCode(block, 'VALUE', ORDER.NONE) || 'None';
    code += '  return ' + value + '\n';
  } else {
    code += '  return\n';
  }
  return code;
};

PythonOcto['procedures_namedsequence'] = function(block) {
  var name = getProcedureName(block.getFieldValue('NAME'));
  var branch = statementToCode(block, 'STACK') || 'sequence()';
  if (STATEMENT_PREFIX) {
    branch = prefixLines(
      STATEMENT_PREFIX.replace(/%1/g, '\'' + block.id + '\''), INDENT
    ) + branch;
  }
  if (INFINITE_LOOP_TRAP) {
    branch = INFINITE_LOOP_TRAP.replace(/%1/g, '"' + block.id + '"') + branch;
  }
  return name + ' = ' + branch;
};

PythonOcto['procedures_callnamedsequence'] = function(block) {
  // Insert a named sequence
  var funcName = getProcedureName(block.getFieldValue('NAME'));
  return funcName;
};
