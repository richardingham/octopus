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
 * @fileoverview Generating Python-Octo for variable blocks.
 * @author q.neutron@gmail.com (Quynh Neutron)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER} from '../python-octo-constants';
import {getVariableName, valueToCode} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['lexical_variable_get'] = function(block) {
  // Variable getter.
  var name = getVariableName(block.getVariable());
  return [name, ORDER.ATOMIC];
};

PythonOcto['lexical_variable_set'] = function(block) {
  // Variable setter.
  var argument0 = valueToCode(block, 'VALUE', ORDER.NONE) || '0';
  var name = getVariableName(block.getVariable());
  return 'set(' + name + ', ' + argument0 + ')';
};

PythonOcto['lexical_variable_set_to'] = function(block) {
  // Variable setter.
  var variable = block.getVariable();
  var name = getVariableName(variable);
  var type = variable && variable.getType();
  var value = block.getFieldValue('VALUE');
  var defaultValue;

  if (type == 'Number') {
    if (!value) {
      value = 0;
    }
  } else if (type == 'Boolean') {
    value = value ? 'true' : 'false';
  } else if (!value) {
    value = '\'\'';
  } else {
    value = '\'' + value + '\'';
  }

  return 'set(' + name + ', ' + value + ')';
};

PythonOcto['global_declaration'] = function(block) {
  var argument0 = valueToCode(block, 'VALUE', ORDER.NONE) || '0';
  var name = getVariableName(block.variable_);
  var targetBlock = block.getInputTargetBlock('VALUE');
  var vars = targetBlock && targetBlock.getVars();
  var conn = targetBlock && targetBlock.outputConnection;

  if (vars && vars.length) {
    return name + ' = ' + argument0;
  } else if (conn) {
    var type = "str";
    if (conn && conn.check_) {
      if (conn.check_.indexOf("Number") !== -1) {
        type = argument0.indexOf('.') > -1 ? "float" : "int";
      }
      if (conn.check_.indexOf("Boolean") !== -1) {
        type = "bool";
      }
    }
    return name + ' = variable(' + type + ', ' + argument0 + ')';
  } else {
    return name + ' = variable()';
  }
};
