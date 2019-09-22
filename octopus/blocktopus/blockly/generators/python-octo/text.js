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
 * @fileoverview Generating Python for text blocks.
 * @author q.neutron@gmail.com (Quynh Neutron)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER, FUNCTION_NAME_PLACEHOLDER_} from '../python-octo-constants';
import {getVariableName, addDefinition, provideFunction, statementToCode, valueToCode, prefixLines, scrub, quote} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['text'] = function(block) {
  // Text value.
  var code = quote(block.getFieldValue('TEXT'));
  return [code, ORDER.ATOMIC];
};

PythonOcto['text_join'] = function(block) {
  // Create a string made up of any number of elements of any type.
  if (block.mutation_.items === 0) {
    return ['\'\'', ORDER.ATOMIC];
  } else {
    var code = [];
    for (var n = 0; n < block.mutation_.items; n++) {
      code[n] = valueToCode(block, 'ADD' + n, ORDER.NONE) || '\'\'';
    }
    return [code.join(' + '), ORDER.FUNCTION_CALL];
  }
};

PythonOcto['text_append'] = function(block) {
  // Append to a variable in place.
  var varName = getVariableName(block.getVariable());
  var argument0 = valueToCode(block, 'TEXT', ORDER.NONE) || '\'\'';
  return varName + ' = str(' + varName + ') + str(' + argument0 + ')\n';
};

PythonOcto['text_length'] = function(block) {
  // String length.
  var argument0 = valueToCode(block, 'VALUE', ORDER.NONE) || '\'\'';
  return ['len(' + argument0 + ')', ORDER.FUNCTION_CALL];
};

PythonOcto['text_isEmpty'] = function(block) {
  // Is the string null?
  var argument0 = valueToCode(block, 'VALUE', ORDER.NONE) || '\'\'';
  var code = 'not len(' + argument0 + ')';
  return [code, ORDER.LOGICAL_NOT];
};

PythonOcto['text_indexOf'] = function(block) {
  // Search the text for a substring.
  // Should we allow for non-case sensitive???
  var operator = block.getFieldValue('END') == 'FIRST' ? 'find' : 'rfind';
  var argument0 = valueToCode(block, 'FIND', ORDER.NONE) || '\'\'';
  var argument1 = valueToCode(block, 'VALUE', ORDER.MEMBER) || '\'\'';
  var code = argument1 + '.' + operator + '(' + argument0 + ') + 1';
  return [code, ORDER.MEMBER];
};

PythonOcto['text_charAt'] = function(block) {
  // Get letter at index.
  // Note: Until January 2013 this block did not have the WHERE input.
  var where = block.getFieldValue('WHERE') || 'FROM_START';
  var at = valueToCode(block, 'AT', ORDER.UNARY_SIGN) || '1';
  var text = valueToCode(block, 'VALUE', ORDER.MEMBER) || '\'\'';
  switch (where) {
    case 'FIRST':
      var code = text + '[0]';
      return [code, ORDER.MEMBER];
    case 'LAST':
      var code = text + '[-1]';
      return [code, ORDER.MEMBER];
    case 'FROM_START':
      // Blockly uses one-based indicies.
      if (typeof at === 'number') {
        // If the index is a naked number, decrement it right now.
        at = parseInt(at, 10) - 1;
      } else {
        // If the index is dynamic, decrement it in code.
        at = 'int(' + at + ' - 1)';
      }
      var code = text + '[' + at + ']';
      return [code, ORDER.MEMBER];
    case 'FROM_END':
      var code = text + '[-' + at + ']';
      return [code, ORDER.MEMBER];
    case 'RANDOM':
      addDefinition('import_random', 'import random');
      var functionName = provideFunction(
          'text_random_letter',
          ['def ' + FUNCTION_NAME_PLACEHOLDER_ + '(text):',
           '  x = int(random.random() * len(text))',
           '  return text[x];']);
      code = functionName + '(' + text + ')';
      return [code, ORDER.FUNCTION_CALL];
  }
  throw 'Unhandled option (text_charAt).';
};

PythonOcto['text_getSubstring'] = function(block) {
  // Get substring.
  var text = valueToCode(block, 'STRING', ORDER.MEMBER) || '\'\'';
  var where1 = block.getFieldValue('WHERE1');
  var where2 = block.getFieldValue('WHERE2');
  var at1 = valueToCode(block, 'AT1', ORDER.ADDITIVE) || '1';
  var at2 = valueToCode(block, 'AT2', ORDER.ADDITIVE) || '1';
  if (where1 == 'FIRST' || (where1 == 'FROM_START' && at1 == '1')) {
    at1 = '';
  } else if (where1 == 'FROM_START') {
    // Blockly uses one-based indicies.
    if (typeof at1 === 'number') {
      // If the index is a naked number, decrement it right now.
      at1 = parseInt(at1, 10) - 1;
    } else {
      // If the index is dynamic, decrement it in code.
      at1 = 'int(' + at1 + ' - 1)';
    }
  } else if (where1 == 'FROM_END') {
    if (typeof at1 === 'number') {
      at1 = -parseInt(at1, 10);
    } else {
      at1 = '-int(' + at1 + ')';
    }
  }
  if (where2 == 'LAST' || (where2 == 'FROM_END' && at2 == '1')) {
    at2 = '';
  } else if (where1 == 'FROM_START') {
    if (typeof at2 === 'number') {
      at2 = parseInt(at2, 10);
    } else {
      at2 = 'int(' + at2 + ')';
    }
  } else if (where1 == 'FROM_END') {
    if (typeof at2 === 'number') {
      // If the index is a naked number, increment it right now.
      at2 = 1 - parseInt(at2, 10);
      if (at2 == 0) {
        at2 = '';
      }
    } else {
      // If the index is dynamic, increment it in code.
      // Add special case for -0.
      addDefinition('import_sys', 'import sys');
      at2 = 'int(1 - ' + at2 + ') or sys.maxsize';
    }
  }
  var code = text + '[' + at1 + ' : ' + at2 + ']';
  return [code, ORDER.MEMBER];
};

PythonOcto['text_changeCase'] = function(block) {
  // Change capitalization.
  var OPERATORS = {
    'UPPERCASE': '.upper()',
    'LOWERCASE': '.lower()',
    'TITLECASE': '.title()'
  };
  var operator = OPERATORS[block.getFieldValue('CASE')];
  var argument0 = valueToCode(block, 'TEXT', ORDER.MEMBER) || '\'\'';
  var code = argument0 + operator;
  return [code, ORDER.MEMBER];
};

PythonOcto['text_trim'] = function(block) {
  // Trim spaces.
  var OPERATORS = {
    'LEFT': '.lstrip()',
    'RIGHT': '.rstrip()',
    'BOTH': '.strip()'
  };
  var operator = OPERATORS[block.getFieldValue('MODE')];
  var argument0 = valueToCode(block, 'TEXT', ORDER.MEMBER) || '\'\'';
  var code = argument0 + operator;
  return [code, ORDER.MEMBER];
};

PythonOcto['controls_log'] = function(block) {
  var argument0 = valueToCode(block, 'TEXT', ORDER.NONE) || '\'\'';
  return 'log(' + argument0 + ')';
};
