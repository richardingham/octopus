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
 * @fileoverview Generating Python-Octo for logic blocks.
 * @author q.neutron@gmail.com (Quynh Neutron)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER} from '../python-octo-constants';
import {valueToCode} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['logic_compare'] = function(block) {
  // Comparison operator.
  var OPERATORS = {
    'EQ': '==',
    'NEQ': '!=',
    'LT': '<',
    'LTE': '<=',
    'GT': '>',
    'GTE': '>='
  };
  var operator = OPERATORS[block.getFieldValue('OP')];
  var order = ORDER.RELATIONAL;
  var argument0 = valueToCode(block, 'A', order) || '0';
  var argument1 = valueToCode(block, 'B', order) || '0';
  var code = argument0 + ' ' + operator + ' ' + argument1;
  return [code, order];
};

PythonOcto['logic_operation'] = function(block) {
  // Operations 'and', 'or'.
  var operator = (block.getFieldValue('OP') == 'AND') ? 'and' : 'or';
  var order = (operator == 'and') ? ORDER.LOGICAL_AND : ORDER.LOGICAL_OR;
  var argument0 = valueToCode(block, 'A', order);
  var argument1 = valueToCode(block, 'B', order);
  if (!argument0 && !argument1) {
    // If there are no arguments, then the return value is false.
    argument0 = 'False';
    argument1 = 'False';
  } else {
    // Single missing arguments have no effect on the return value.
    var defaultArgument = (operator == 'and') ? 'True' : 'False';
    if (!argument0) {
      argument0 = defaultArgument;
    }
    if (!argument1) {
      argument1 = defaultArgument;
    }
  }
  var code = argument0 + ' ' + operator + ' ' + argument1;
  return [code, order];
};

PythonOcto['logic_negate'] = function(block) {
  // Negation.
  var argument0 = valueToCode(block, 'BOOL', ORDER.LOGICAL_NOT) || 'True';
  var code = 'False == ' + argument0;
  return [code, ORDER.RELATIONAL];
};

PythonOcto['logic_boolean'] = function(block) {
  // Boolean values true and false.
  var code = (block.getFieldValue('BOOL') == 'TRUE') ? 'True' : 'False';
  return [code, ORDER.ATOMIC];
};

PythonOcto['logic_null'] = function(block) {
  // Null data type.
  return ['None', ORDER.ATOMIC];
};

PythonOcto['logic_ternary'] = function(block) {
  // Ternary operator.
  var value_if = valueToCode(block, 'IF', ORDER.CONDITIONAL) || 'False';
  var value_then = valueToCode(block, 'THEN', ORDER.CONDITIONAL) || 'None';
  var value_else = valueToCode(block, 'ELSE', ORDER.CONDITIONAL) || 'None';
  var code = value_then + ' if ' + value_if + ' else ' + value_else;
  return [code, ORDER.CONDITIONAL];
};
