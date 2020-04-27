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
 * @fileoverview Generating Python for image blocks.
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import {ORDER} from '../python-octo-constants';
import {valueToCode} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['image_findcolour'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.select(' + input + ', "' + block.getFieldValue('OP').toLowerCase() + '")';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_threshold'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.threshold(' + input + ', ' + parseInt(block.getFieldValue('THRESHOLD')) + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_erode'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.erode(' + input + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_invert'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.invert(' + input + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_colourdistance'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var colour = valueToCode(block, 'COLOUR', ORDER.NONE) || '\'#000000\'';
  var code = 'image.colorDistance(' + [input, colour].join(', ') + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_huedistance'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var colour = valueToCode(block, 'COLOUR', ORDER.NONE) || '\'#000000\'';
  var code = 'image.hueDistance(' + [input, colour].join(', ') + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_intensityfn'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.intensity(' + input + ', \'' + block.getFieldValue('OP') + '\')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_crop'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var x = parseInt(block.getFieldValue('X'));
  var y = parseInt(block.getFieldValue('Y'));
  var w = parseInt(block.getFieldValue('W'));
  var h = parseInt(block.getFieldValue('H'));
  var code = 'image.crop(' + [input, x, y, w, h].join(', ') + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['image_tonumber'] = function(block) {
  var input = valueToCode(block, 'INPUT', ORDER.NONE) || 'None';
  var code = 'image.calculate(' + input + ', "' + block.getFieldValue('OP') + '")';
  return [code, ORDER.FUNCTION_CALL];
};
