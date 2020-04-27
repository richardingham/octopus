/**
 * @license
 * Visual Blocks Language
 *
 * Copyright 2012 Google Inc.
 * https://github.com/google/PythonOcto
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
 * @fileoverview Generating Python for loop blocks.
 * @author q.neutron@gmail.com (Quynh Neutron)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER, FUNCTION_NAME_PLACEHOLDER_, INDENT} from '../python-octo-constants';
import {getVariableName, getDistinctName, provideFunction, statementToCode, valueToCode, prefixLines, addLoopTrap, scrub, quote} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';


const LOOP_PASS = '[]';

PythonOcto['controls_repeat'] = function(block) {
  // Repeat n times (internal number).
  var repeats = parseInt(block.getFieldValue('TIMES'), 10);
  var branch = statementToCode(block, 'DO');
  branch = addLoopTrap(branch, block.id) || LOOP_PASS;
  var code = 'loop_while(False,\n' + prefixLines(branch + ',\nmin_calls = ' + repeats, INDENT) + '\n)';
  return code;
};

PythonOcto['controls_repeat_ext'] = function(block) {
  // Repeat n times (external number).
  var repeats = valueToCode(block, 'TIMES', ORDER.NONE) || '0';
  //if (typeof repeats === 'number') {
  //  repeats = parseInt(repeats, 10);
  //} else {
  //  repeats = 'int(' + repeats + ')';
  //}
  var branch = statementToCode(block, 'DO');
  branch = addLoopTrap(branch, block.id) || LOOP_PASS;
  var code = 'loop_while(False,\n' + prefixLines(branch + ',\nmin_calls = ' + repeats, INDENT) + '\n)';
  return code;
};

PythonOcto['controls_whileUntil'] = function(block) {
  // Do while/until loop.
  var until = block.getFieldValue('MODE') === 'UNTIL';
  var argument0 = valueToCode(block, 'BOOL', ORDER.NONE) || (until ? 'True' : 'False');
  var branch = statementToCode(block, 'DO');
  branch = addLoopTrap(branch, block.id) || LOOP_PASS;
  var code = (until ? 'loop_until(' : 'loop_while(') + argument0 + ',\n' + prefixLines(branch, INDENT) + '\n)';
  return code;
};

PythonOcto['controls_for'] = function(block) {
  // For loop.
  var variable0 = getVariableName(block.getVariable());
  var argument0 = valueToCode(block, 'FROM', ORDER.NONE) || '0';
  var argument1 = valueToCode(block, 'TO', ORDER.NONE) || '0';
  var increment = valueToCode(block, 'BY', ORDER.NONE) || '1';
  var branch = statementToCode(block, 'DO');
  branch = addLoopTrap(branch, block.id) || LOOP_PASS;

  var code = '';
  var range;

  // Helper functions.
  var defineUpRange = function() {
    return provideFunction(
        'upRange',
        ['def ' + FUNCTION_NAME_PLACEHOLDER_ +
            '(start, stop, step):',
         '  while start <= stop:',
         '    yield start',
         '    start += abs(step)']);
  };
  var defineDownRange = function() {
    return provideFunction(
        'downRange',
        ['def ' + FUNCTION_NAME_PLACEHOLDER_ +
            '(start, stop, step):',
         '  while start >= stop:',
         '    yield start',
         '    start -= abs(step)']);
  };
  // Arguments are legal Python code (numbers or strings returned by scrub()).
  var generateUpDownRange = function(start, end, inc) {
    return '(' + start + ' <= ' + end + ') and ' +
        defineUpRange() + '(' + start + ', ' + end + ', ' + inc + ') or ' +
        defineDownRange() + '(' + start + ', ' + end + ', ' + inc + ')';
  };

  if (typeof argument0 === 'number' && typeof argument1 === 'number' &&
      typeof increment === 'number') {
    // All parameters are simple numbers.
    argument0 = parseFloat(argument0);
    argument1 = parseFloat(argument1);
    increment = Math.abs(parseFloat(increment));
    if (argument0 % 1 === 0 && argument1 % 1 === 0 && increment % 1 === 0) {
      // All parameters are integers.
      if (argument0 <= argument1) {
        // Count up.
        argument1++;
        if (argument0 == 0 && increment == 1) {
          // If starting index is 0, omit it.
          range = argument1;
        } else {
          range = argument0 + ', ' + argument1;
        }
        // If increment isn't 1, it must be explicit.
        if (increment != 1) {
          range += ', ' + increment;
        }
      } else {
        // Count down.
        argument1--;
        range = argument0 + ', ' + argument1 + ', -' + increment;
      }
      range = 'range(' + range + ')';
    } else {
      // At least one of the parameters is not an integer.
      if (argument0 < argument1) {
        range = defineUpRange();
      } else {
        range = defineDownRange();
      }
      range += '(' + argument0 + ', ' + argument1 + ', ' + increment + ')';
    }
  } else {
    // Cache non-trivial values to variables to prevent repeated look-ups.
    var scrub = function(arg, suffix) {
      if (typeof arg === 'number') {
        // Simple number.
        arg = parseFloat(arg);
      } else if (arg.match(/^\w+$/)) {
        // Variable.
        arg = 'float(' + arg + ')';
      } else {
        // It's complicated.
        var varName = getDistinctName(variable0 + suffix);
        code += varName + ' = float(' + arg + ')\n';
        arg = varName;
      }
      return arg;
    };
    var startVar = scrub(argument0, '_start');
    var endVar = scrub(argument1, '_end');
    var incVar = scrub(increment, '_inc');

    if (typeof startVar == 'number' && typeof endVar == 'number') {
      if (startVar < endVar) {
        range = defineUpRange(startVar, endVar, increment);
      } else {
        range = defineDownRange(startVar, endVar, increment);
      }
    } else {
      // We cannot determine direction statically.
      range = generateUpDownRange(startVar, endVar, increment);
    }
  }
  code += 'for ' + variable0 + ' in ' + range + ':\n' + branch;
  return code;
};

PythonOcto['controls_forEach'] = function(block) {
  // For each loop.
  var variable0 = getVariableName(block.getVariable());
  var argument0 = valueToCode(block, 'LIST', ORDER.RELATIONAL) || '[]';
  var branch = statementToCode(block, 'DO');
  branch = addLoopTrap(branch, block.id) || LOOP_PASS;
  var code = 'for ' + variable0 + ' in ' + argument0 + ':\n' + branch;
  return code;
};

PythonOcto['controls_flow_statements'] = function(block) {
  // Flow statements: continue, break.
  switch (block.getFieldValue('FLOW')) {
    case 'BREAK':
      return 'break\n';
    case 'CONTINUE':
      return 'continue\n';
  }
  throw 'Unknown flow statement.';
};
