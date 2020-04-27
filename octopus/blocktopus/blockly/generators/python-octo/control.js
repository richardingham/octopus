/**
 * @fileoverview Generating Python-Octo for control blocks.
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER, INDENT} from '../python-octo-constants';
import {getVariableName, addDefinition, valueToCode, statementToCode, prefixLines} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';
import {numberValidator} from '../../core/validators';

function stringFill (x, n) {
  var s = '';
  for (;;) {
    if (n & 1) s += x;
    n >>= 1;
    if (n) x += x;
    else break;
  }
  return s;
}

function indent (code, times) {
  var i = INDENT;
  if (times !== undefined) {
    if (times < 1) return code;
    i = stringFill(i, times);
  }
  return prefixLines(code, i)
}

PythonOcto['controls_if'] = function(block) {
  // If/elseif/else condition.
  var n = 0;
  var argument = valueToCode(block, 'IF' + n, ORDER.NONE) || 'False';
  var branch = statementToCode(block, 'DO' + n) || '[]';
  var code = 'do_if(' + argument + ', \n';
  code += indent(branch);

  for (n = 1; n <= block.mutation_.elseif; n++) {
    argument = valueToCode(block, 'IF' + n, ORDER.NONE) || 'False';
    branch = statementToCode(block, 'DO' + n) || '[]';
    code += ',\n';
    code += indent('do_if(' + argument + ', \n' + indent(branch), n);
  }
  if (block.mutation_.else) {
    branch = statementToCode(block, 'ELSE') || '[]';
    code += ',\n' + indent(indent(branch) + '\n)', n - 1);
  } else {
    code += '\n' + indent(')', n - 1);
  }
  for (; n > 1; n--) {
    code += '\n' + indent(')', n - 2);
  }
  return code;
};

PythonOcto['controls_wait'] = function(block) {
  var argument = valueToCode(block, 'TIME', ORDER.NONE) || '0';
  var code = 'wait(' + argument + ')';
  return code;
};

PythonOcto['controls_wait_until'] = function(block) {
  var argument = valueToCode(block, 'CONDITION', ORDER.NONE) || 'True';
  var code = 'wait_until(' + argument + ')';
  return code;
};

PythonOcto['controls_maketime'] = function(block) {
  var h = parseFloat(numberValidator(block.getFieldValue('HOUR'))) || 0;
  var m = parseFloat(numberValidator(block.getFieldValue('MINUTE'))) || 0;
  var s = parseFloat(numberValidator(block.getFieldValue('SECOND'))) || 0;
  var code = 3600 * h + 60 * m + s;

  return [code, ORDER.ATOMIC];
};

PythonOcto['controls_run'] = function(block) {
  var later = block.getFieldValue('MODE') === 'PAUSED';
  var branch = statementToCode(block, 'STACK') || 'sequence()';
  var code = 'run' + (later ? '_later' : '') + '(' + branch + ')';
  return code;
};

PythonOcto['controls_parallel'] = function(block) {
  var code = [];
  var stackCode;

  for (var n = 0; n < block.mutation_.stacks; n++) {
    stackCode = statementToCode(block, 'STACK' + n);
    if (stackCode) {
      code.push(stackCode);
    }
  }

  return 'parallel(' + (code.length ? '\n' : '') +
      indent(code.join(',\n')) + (code.length ? '\n' : '') + ')';
};

PythonOcto['controls_dependents'] = function(block) {
  var code = [];
  var branch = statementToCode(block, 'STACK') || 'sequence()';

  var depCode;
  for (var n = 0; n < block.mutation_.dependents; n++) {
    depCode = valueToCode(block, 'DEP' + n, ORDER.NONE);
    if (depCode) {
      code.push(depCode);
    }
  }

  var n = code.length ? '\n' : '';
  code = 'with_dependents(' + branch + ', [' + n +
      indent(code.join(',\n')) + n + '])';
  return code;
};

PythonOcto['controls_bind'] = function(block) {
  addDefinition('import_sequence_control', 'from octopus.sequence import control');

  var value = valueToCode(block, 'VALUE', ORDER.NONE) || 'False';
  var name = getVariableName(block.getVariable());
  var code = 'control.Bind(' + name + ', ' + value + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['controls_statemonitor'] = function(block) {
  addDefinition('import_sequence_control', 'from octopus.sequence import control');

  var code = [];
  var triggerBranch = statementToCode(block, 'TRIGGER') || 'sequence()';
  var resetBranch = statementToCode(block, 'RESET') || 'sequence()';

  var testCode;
  for (var n = 0; n < block.mutation_.tests; n++) {
    testCode = valueToCode(block, 'TEST' + n, ORDER.NONE);
    if (testCode) {
      code.push(testCode);
    }
  }

  var n = code.length ? '\n' : '';
  code = 'control.StateMonitor(\n' +
    indent('tests = [' + n + indent(code.join(',\n')) + n + '],\n' +
    'trigger_step = ' + triggerBranch + ',\n' +
    'reset_step = ' + resetBranch) +
    '\n)';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['controls_dependent_stack'] = function(block) {
  var code = statementToCode(block, 'STACK') || 'sequence()';
  return [code, ORDER.FUNCTION_CALL];
};
