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
 * @fileoverview Generating Python for math blocks.
 * @author q.neutron@gmail.com (Quynh Neutron)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER, FUNCTION_NAME_PLACEHOLDER_} from '../python-octo-constants';
import {getVariableName, addReservedWords, provideFunction, addDefinition, statementToCode, valueToCode, prefixLines, scrub, quote} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';
import {numberValidator} from '../../core/validators';


// If any new block imports any library, add that library name here.
addReservedWords('math,random');

PythonOcto['math_number'] = function(block) {
  // Numeric value.
  var code = numberValidator(block.getFieldValue('NUM')) || 0;
  var order = parseFloat(code) < 0 ? ORDER.UNARY_SIGN :
              ORDER.ATOMIC;
  return [code, order];
};

PythonOcto['math_arithmetic'] = function(block) {
  // Basic arithmetic operators, and power.
  var OPERATORS = {
    'ADD': [' + ', ORDER.ADDITIVE],
    'MINUS': [' - ', ORDER.ADDITIVE],
    'MULTIPLY': [' * ', ORDER.MULTIPLICATIVE],
    'DIVIDE': [' / ', ORDER.MULTIPLICATIVE],
    'POWER': [' ** ', ORDER.EXPONENTIATION]
  };
  var tuple = OPERATORS[block.getFieldValue('OP')];
  var operator = tuple[0];
  var order = tuple[1];
  var argument0 = valueToCode(block, 'A', order) || '0';
  var argument1 = valueToCode(block, 'B', order) || '0';
  var code = argument0 + operator + argument1;
  return [code, order];
  // In case of 'DIVIDE', division between integers returns different results
  // in Python 2 and 3. However, is not an issue since Blockly does not
  // guarantee identical results in all languages.  To do otherwise would
  // require every operator to be wrapped in a function call.  This would kill
  // legibility of the generated code.  See:
  // http://code.google.com/p/blockly/wiki/Language
};

PythonOcto['math_single'] = function(block) {
  // Math operators with single operand.
  var operator = block.getFieldValue('OP');
  var code;
  var arg;
  if (operator == 'NEG') {
    // Negation is a special case given its different operator precedence.
    var code = valueToCode(block, 'NUM', ORDER.UNARY_SIGN) || '0';
    return ['-' + code, ORDER.UNARY_SIGN];
  }
  addDefinition('import_math', 'import math');
  if (operator == 'SIN' || operator == 'COS' || operator == 'TAN') {
    arg = valueToCode(block, 'NUM', ORDER.MULTIPLICATIVE) || '0';
  } else {
    arg = valueToCode(block, 'NUM', ORDER.NONE) || '0';
  }
  // First, handle cases which generate values that don't need parentheses
  // wrapping the code.
  switch (operator) {
    case 'ABS':
      code = 'math.fabs(' + arg + ')';
      break;
    case 'ROOT':
      code = 'math.sqrt(' + arg + ')';
      break;
    case 'LN':
      code = 'math.log(' + arg + ')';
      break;
    case 'LOG10':
      code = 'math.log10(' + arg + ')';
      break;
    case 'EXP':
      code = 'math.exp(' + arg + ')';
      break;
    case 'POW10':
      code = 'math.pow(10,' + arg + ')';
      break;
    case 'ROUND':
      code = 'round(' + arg + ')';
      break;
    case 'ROUNDUP':
      code = 'math.ceil(' + arg + ')';
      break;
    case 'ROUNDDOWN':
      code = 'math.floor(' + arg + ')';
      break;
    case 'SIN':
      code = 'math.sin(' + arg + ' / 180.0 * math.pi)';
      break;
    case 'COS':
      code = 'math.cos(' + arg + ' / 180.0 * math.pi)';
      break;
    case 'TAN':
      code = 'math.tan(' + arg + ' / 180.0 * math.pi)';
      break;
  }
  if (code) {
    return [code, ORDER.FUNCTION_CALL];
  }
  // Second, handle cases which generate values that may need parentheses
  // wrapping the code.
  switch (operator) {
    case 'ASIN':
      code = 'math.asin(' + arg + ') / math.pi * 180';
      break;
    case 'ACOS':
      code = 'math.acos(' + arg + ') / math.pi * 180';
      break;
    case 'ATAN':
      code = 'math.atan(' + arg + ') / math.pi * 180';
      break;
    default:
      throw 'Unknown math operator: ' + operator;
  }
  return [code, ORDER.MULTIPLICATIVE];
};

PythonOcto['math_constant'] = function(block) {
  // Constants: PI, E, the Golden Ratio, sqrt(2), 1/sqrt(2), INFINITY.
  var CONSTANTS = {
    'PI': ['math.pi', ORDER.MEMBER],
    'E': ['math.e', ORDER.MEMBER],
    'GOLDEN_RATIO': ['(1 + math.sqrt(5)) / 2', ORDER.MULTIPLICATIVE],
    'SQRT2': ['math.sqrt(2)', ORDER.MEMBER],
    'SQRT1_2': ['math.sqrt(1.0 / 2)', ORDER.MEMBER],
    'INFINITY': ['float(\'inf\')', ORDER.ATOMIC]
  };
  var constant = block.getFieldValue('CONSTANT');
  if (constant != 'INFINITY') {
    addDefinition('import_math', 'import math');
  }
  return CONSTANTS[constant];
};

PythonOcto['math_number_property'] = function(block) {
  // Check if a number is even, odd, prime, whole, positive, or negative
  // or if it is divisible by certain number. Returns true or false.
  var number_to_check = valueToCode(block, 'NUMBER_TO_CHECK',
      ORDER.MULTIPLICATIVE) || '0';
  var dropdown_property = block.getFieldValue('PROPERTY');
  var code;
  switch (dropdown_property) {
    case 'EVEN':
      code = number_to_check + ' % 2 == 0';
      break;
    case 'ODD':
      code = number_to_check + ' % 2 == 1';
      break;
    case 'WHOLE':
      code = number_to_check + ' % 1 == 0';
      break;
    case 'POSITIVE':
      code = number_to_check + ' > 0';
      break;
    case 'NEGATIVE':
      code = number_to_check + ' < 0';
      break;
    case 'DIVISIBLE_BY':
      var divisor = valueToCode(block, 'DIVISOR', ORDER.MULTIPLICATIVE);
      // If 'divisor' is some code that evals to 0, Python will raise an error.
      if (!divisor || divisor == '0') {
        return ['False', ORDER.ATOMIC];
      }
      code = number_to_check + ' % ' + divisor + ' == 0';
      break;
  }
  return [code, ORDER.RELATIONAL];
};

PythonOcto['math_change'] = function(block) {
  // Add to a variable in place.
  var increment = block.getFieldValue('MODE') === 'INCREMENT';
  var name = getVariableName(block.getVariable());
  return (increment ? 'in' : 'de') + 'crement(' + name + ')';
};

// Rounding functions have a single operand.
PythonOcto['math_round'] = PythonOcto['math_single'];
// Trigonometry functions have a single operand.
PythonOcto['math_trig'] = PythonOcto['math_single'];

PythonOcto['math_on_list'] = function(block) {
  // Math functions for lists.
  var func = block.getFieldValue('OP');
  var list = valueToCode(block, 'LIST', ORDER.NONE) || '[]';
  var code;
  switch (func) {
    case 'SUM':
      code = 'sum(' + list + ')';
      break;
    case 'MIN':
      code = 'min(' + list + ')';
      break;
    case 'MAX':
      code = 'max(' + list + ')';
      break;
    case 'AVERAGE':
      var functionName = provideFunction(
          'math_mean',
          // This operation excludes null and values that aren't int or float:',
          // math_mean([null, null, "aString", 1, 9]) == 5.0.',
          ['def ' + FUNCTION_NAME_PLACEHOLDER_ + '(myList):',
           '  localList = [e for e in myList if type(e) in (int, float, long)]',
           '  if not localList: return',
           '  return float(sum(localList)) / len(localList)']);
      code = functionName + '(' + list + ')';
      break;
    case 'MEDIAN':
      var functionName = provideFunction(
          'math_median',
          // This operation excludes null values:
          // math_median([null, null, 1, 3]) == 2.0.
          ['def ' + FUNCTION_NAME_PLACEHOLDER_ + '(myList):',
           '  localList = sorted([e for e in myList ' +
               'if type(e) in (int, float, long)])',
           '  if not localList: return',
           '  if len(localList) % 2 == 0:',
           '    return (localList[len(localList) / 2 - 1] + ' +
               'localList[len(localList) / 2]) / 2.0',
           '  else:',
           '    return localList[(len(localList) - 1) / 2]']);
      code = functionName + '(' + list + ')';
      break;
    case 'MODE':
      var functionName = provideFunction(
          'math_modes',
          // As a list of numbers can contain more than one mode,
          // the returned result is provided as an array.
          // Mode of [3, 'x', 'x', 1, 1, 2, '3'] -> ['x', 1].
          ['def ' + FUNCTION_NAME_PLACEHOLDER_ + '(some_list):',
           '  modes = []',
           '  # Using a lists of [item, count] to keep count rather than dict',
           '  # to avoid "unhashable" errors when the counted item is ' +
               'itself a list or dict.',
           '  counts = []',
           '  maxCount = 1',
           '  for item in some_list:',
           '    found = False',
           '    for count in counts:',
           '      if count[0] == item:',
           '        count[1] += 1',
           '        maxCount = max(maxCount, count[1])',
           '        found = True',
           '    if not found:',
           '      counts.append([item, 1])',
           '  for counted_item, item_count in counts:',
           '    if item_count == maxCount:',
           '      modes.append(counted_item)',
           '  return modes']);
      code = functionName + '(' + list + ')';
      break;
    case 'STD_DEV':
      addDefinition('import_math', 'import math');
      var functionName = provideFunction(
          'math_standard_deviation',
          ['def ' + FUNCTION_NAME_PLACEHOLDER_ + '(numbers):',
           '  n = len(numbers)',
           '  if n == 0: return',
           '  mean = float(sum(numbers)) / n',
           '  variance = sum((x - mean) ** 2 for x in numbers) / n',
           '  return math.sqrt(variance)']);
      code = functionName + '(' + list + ')';
      break;
    case 'RANDOM':
      addDefinition('import_random', 'import random');
      code = 'random.choice(' + list + ')';
      break;
    default:
      throw 'Unknown operator: ' + func;
  }
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['math_modulo'] = function(block) {
  // Remainder computation.
  var argument0 = valueToCode(block, 'DIVIDEND', ORDER.MULTIPLICATIVE) || '0';
  var argument1 = valueToCode(block, 'DIVISOR', ORDER.MULTIPLICATIVE) || '0';
  var code = argument0 + ' % ' + argument1;
  return [code, ORDER.MULTIPLICATIVE];
};

PythonOcto['math_constrain'] = function(block) {
  // Constrain a number between two limits.
  var argument0 = valueToCode(block, 'VALUE', ORDER.NONE) || '0';
  var argument1 = valueToCode(block, 'LOW', ORDER.NONE) || '0';
  var argument2 = valueToCode(block, 'HIGH', ORDER.NONE) || 'float(\'inf\')';
  var code = 'min(max(' + argument0 + ', ' + argument1 + '), ' +
      argument2 + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['math_random_int'] = function(block) {
  // Random integer between [X] and [Y].
  addDefinition('import_random', 'import random');
  var argument0 = valueToCode(block, 'FROM', ORDER.NONE) || '0';
  var argument1 = valueToCode(block, 'TO', ORDER.NONE) || '0';
  var code = 'random.randint(' + argument0 + ', ' + argument1 + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['math_random_float'] = function(block) {
  // Random fraction between 0 and 1.
  addDefinition('import_random', 'import random');
  return ['random.random()', ORDER.FUNCTION_CALL];
};

PythonOcto['math_framed'] = function(block) {
  // Framed arithmetic operations
  var OPERATORS = {
    'MAX': 'Max',
    'MIN': 'Min',
    'AVERAGE': 'Avg',
    'CHANGE': 'Change'
  };
  var fn = OPERATORS[block.getFieldValue('OP')];
  var expr = valueToCode(block, 'INPUT', ORDER.NONE) || '0';
  var time = parseFloat(block.getFieldValue('TIME')) || '0';
  var code = fn + '(' + expr + ', frame = ' + time + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['math_throttle'] = function(block) {
  // Framed arithmetic operations
  var OPERATORS = {
    'MAX': 'max',
    'MIN': 'min',
    'AVERAGE': 'avg',
    'LATEST': 'latest'
  };
  var fn = OPERATORS[block.getFieldValue('OP')];
  var expr = valueToCode(block, 'INPUT', ORDER.NONE) || '0';
  var time = parseFloat(block.getFieldValue('TIME')) || '0';
  var code = 'Throttle(' + expr + ', method = \'' + fn + '\', frame = ' + time + ')';
  return [code, ORDER.FUNCTION_CALL];
};
