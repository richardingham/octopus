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
 * @fileoverview Math blocks for Blockly.
 * @author q.neutron@gmail.com (Quynh Neutron)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Msg from '../core/msg';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import {MATH_CATEGORY_HUE} from '../colourscheme';
import {numberValidator} from '../core/validators';

Blocks['image_findcolour'] = {
  /**
   * Block for filtering a colour of an image
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [['red', 'RED'],
         ['green', 'GREEN'],
         ['blue', 'BLUE']];
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('select')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
  }
};

Blocks['image_threshold'] = {
  /**
   * Block for filtering an image
   * @this Blockly.Block
   */
  init: function() {
    this.fieldNumber_ = new FieldTextInput(
      '0',
      numberValidator
    );
    //this.setHelpUrl(Blockly.Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('threshold')
        .appendField(this.fieldNumber_, 'THRESHOLD');
  }
};

Blocks['image_erode'] = {
  /**
   * Block for eroding an image
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('erode');
  }
};

Blocks['image_invert'] = {
  /**
   * Block for eroding an image
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('invert');
  }
};

Blocks['image_colourdistance'] = {
  /**
   * Block for colourDistance function
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('Colour distance of');
    this.appendValueInput('COLOUR')
        .setCheck('Colour')
        .appendField('from colour:');
  }
};

Blocks['image_huedistance'] = {
  /**
   * Block for colourDistance function
   * @this Block
   */
  init: function() {
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('Hue distance of');
    this.appendValueInput('COLOUR')
        .setCheck('Colour')
        .appendField('from colour:');
  }
};

Blocks['image_intensityfn'] = {
  /**
   * Block for finding max pixel value of a grayscale image
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [['maximum', 'MAX'],
         ['minimum', 'MIN'],
         ['mean', 'MEAN'],
         ['median', 'MEDIAN']];
    //this.setHelpUrl(Blockly.Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('Calculate')
        .appendField(new FieldDropdown(OPERATORS), 'OP')
        .appendField('intensity');
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
  }
};

Blocks['image_crop'] = {
  /**
   * Block for cropping an image
   * @this Block
   */
  init: function() {
    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.fieldX_ = new FieldTextInput('0', iv);
    this.fieldY_ = new FieldTextInput('0', iv);
    this.fieldH_ = new FieldTextInput('0', iv);
    this.fieldW_ = new FieldTextInput('0', iv);

    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setTooltip('Crop an image, from top-left coordinate (x, y) to create an image size (w, h)')
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Image');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('Crop');
    this.appendDummyInput()
        .appendField('x:')
        .appendField(this.fieldX_, 'X')
        .appendField('y:')
        .appendField(this.fieldY_, 'Y');
    this.appendDummyInput()
        .appendField('w:')
        .appendField(this.fieldH_, 'W')
        .appendField('h:')
        .appendField(this.fieldW_, 'H');
  }
};

Blocks['image_tonumber'] = {
  /**
   * Block for getting a number from an image
   * @this Block
   */
  init: function() {
    var OPERATORS =
        [['centroid x', 'CENTROIDX'],
         ['centroid y', 'CENTROIDY'],
         ['size x', 'SIZEX'],
         ['size y', 'SIZEY']];
    //this.setHelpUrl(Msg.MATH_SINGLE_HELPURL);
    this.setColour(MATH_CATEGORY_HUE);
    this.setOutput(true, 'Number');
    this.appendValueInput('INPUT')
        .setCheck('Image')
        .appendField('calculate')
        .appendField(new FieldDropdown(OPERATORS), 'OP');
  }
};
