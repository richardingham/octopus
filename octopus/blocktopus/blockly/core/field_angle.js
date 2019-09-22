/**
 * @license
 * Visual Blocks Editor
 *
 * Copyright 2013 Google Inc.
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
 * @fileoverview Angle input field.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import FieldTextInput from './field_textinput';
import {inherits} from './utils';
import {bindEvent_, unbindEvent_, createSvgElement} from './utils';
import {numberValidator} from '../core/validators';
import WidgetDiv from './widgetdiv';

/**
 * Class for an editable angle field.
 * @param {string} text The initial content of the field.
 * @param {Function} opt_changeHandler An optional function that is called
 *     to validate any constraints on what the user entered.  Takes the new
 *     text as an argument and returns the accepted text or null to abort
 *     the change.
 * @extends {FieldTextInput}
 * @constructor
 */
var FieldAngle = function(text, opt_changeHandler) {
  var changeHandler;
  if (opt_changeHandler) {
    // Wrap the user's change handler together with the angle validator.
    var thisObj = this;
    changeHandler = function(value) {
      value = FieldAngle.angleValidator.call(thisObj, value);
      if (value !== null) {
        opt_changeHandler.call(thisObj, value);
      }
      return value;
    };
  } else {
    changeHandler = FieldAngle.angleValidator;
  }

  // Add degree symbol: "360°" (LTR) or "°360" (RTL)
  this.symbol_ = createSvgElement('tspan', {}, null);
  this.symbol_.appendChild(document.createTextNode('\u00B0'));

  FieldAngle.super_.call(this, text, changeHandler);
};
inherits(FieldAngle, FieldTextInput);
export default FieldAngle;

/**
 * Clone this FieldAngle.
 * @return {!FieldAngle} The result of calling the constructor again
 *   with the current values of the arguments used during construction.
 */
FieldAngle.prototype.clone = function() {
  return new FieldAngle(this.getText(), this.changeHandler_);
};

/**
 * Round angles to the nearest 15 degrees when using mouse.
 * Set to 0 to disable rounding.
 */
FieldAngle.ROUND = 15;

/**
 * Half the width of protractor image.
 */
FieldAngle.HALF = 100 / 2;

/**
 * Radius of protractor circle.  Slightly smaller than protractor size since
 * otherwise SVG crops off half the border at the edges.
 */
FieldAngle.RADIUS = FieldAngle.HALF - 1;

/**
 * Clean up this FieldAngle, as well as the inherited FieldTextInput.
 * @return {!Function} Closure to call on destruction of the WidgetDiv.
 * @private
 */
FieldAngle.prototype.dispose_ = function() {
  var thisField = this;
  return function() {
    FieldAngle.superClass_.dispose_.call(thisField)();
    thisField.gauge_ = null;
    if (thisField.clickWrapper_) {
      unbindEvent_(thisField.clickWrapper_);
    }
    if (thisField.moveWrapper1_) {
      unbindEvent_(thisField.moveWrapper1_);
    }
    if (thisField.moveWrapper2_) {
      unbindEvent_(thisField.moveWrapper2_);
    }
  };
};

/**
 * Show the inline free-text editor on top of the text.
 * @private
 */
FieldAngle.prototype.showEditor_ = function() {
  var noFocus = false;
  // TODO
  //    goog.userAgent.MOBILE || goog.userAgent.ANDROID || goog.userAgent.IPAD;
  // Mobile browsers have issues with in-line textareas (focus & keyboards).
  FieldAngle.super_.prototype.showEditor_.call(this, noFocus);
  var div = WidgetDiv.DIV;
  if (!div.firstChild) {
    // Mobile interface uses window.prompt.
    return;
  }
  // Build the SVG DOM.
  var svg = createSvgElement('svg', {
    'xmlns': 'http://www.w3.org/2000/svg',
    'xmlns:html': 'http://www.w3.org/1999/xhtml',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
    'version': '1.1',
    'height': (FieldAngle.HALF * 2) + 'px',
    'width': (FieldAngle.HALF * 2) + 'px'
  }, div);
  var circle = createSvgElement('circle', {
    'cx': FieldAngle.HALF, 'cy': FieldAngle.HALF,
    'r': FieldAngle.RADIUS,
    'class': 'blocklyAngleCircle'
  }, svg);
  this.gauge_ = createSvgElement('path',
      {'class': 'blocklyAngleGauge'}, svg);
  this.line_ = createSvgElement('line',
      {'x1': FieldAngle.HALF,
      'y1': FieldAngle.HALF,
      'class': 'blocklyAngleLine'}, svg);
  // Draw markers around the edge.
  for (var a = 0; a < 360; a += 15) {
    createSvgElement('line', {
      'x1': FieldAngle.HALF + FieldAngle.RADIUS,
      'y1': FieldAngle.HALF,
      'x2': FieldAngle.HALF + FieldAngle.RADIUS -
          (a % 45 == 0 ? 10 : 5),
      'y2': FieldAngle.HALF,
      'class': 'blocklyAngleMarks',
      'transform': 'rotate(' + a + ', ' +
          FieldAngle.HALF + ', ' + FieldAngle.HALF + ')'
    }, svg);
  }
  svg.style.marginLeft = '-35px';
  this.clickWrapper_ =
      bindEvent_(svg, 'click', this, this.onClick);
  this.moveWrapper1_ =
      bindEvent_(circle, 'mousemove', this, this.onMouseMove);
  this.moveWrapper2_ =
      bindEvent_(this.gauge_, 'mousemove', this, this.onMouseMove);
  this.updateGraph_();
};

/**
 * Close the widget and emit event.
 * @param {!Event} e Mouse click event.
 */
FieldAngle.prototype.onClick = function(e) {
  WidgetDiv.hide();
  this.emit("changed", Blockly.FieldTextInput.htmlInput_.value);
};

/**
 * Set the angle to match the mouse's position.
 * @param {!Event} e Mouse move event.
 */
FieldAngle.prototype.onMouseMove = function(e) {
  var bBox = this.gauge_.ownerSVGElement.getBoundingClientRect();
  var dx = e.clientX - bBox.left - FieldAngle.HALF;
  var dy = e.clientY - bBox.top - FieldAngle.HALF;
  var angle = Math.atan(-dy / dx);
  if (isNaN(angle)) {
    // This shouldn't happen, but let's not let this error propogate further.
    return;
  }
  angle = angle / Math.PI * 180;
  // 0: East, 90: North, 180: West, 270: South.
  if (dx < 0) {
    angle += 180;
  } else if (dy > 0) {
    angle += 360;
  }
  if (FieldAngle.ROUND) {
    angle = Math.round(angle / FieldAngle.ROUND) *
        FieldAngle.ROUND;
  }
  if (angle >= 360) {
    // Rounding may have rounded up to 360.
    angle -= 360;
  }
  angle = String(angle);
  FieldTextInput.htmlInput_.value = angle;
  this.setText(angle);
};

/**
 * Insert a degree symbol.
 * @param {?string} text New text.
 */
FieldAngle.prototype.setText = function(text) {
  FieldAngle.super_.prototype.setText.call(this, text);
  this.updateGraph_();
  // Insert degree symbol.
  if (Blockly.RTL) {
    this.textElement_.insertBefore(this.symbol_, this.textElement_.firstChild);
  } else {
    this.textElement_.appendChild(this.symbol_);
  }
  // Cached width is obsolete.  Clear it.
  this.size_.width = 0;
};

/**
 * Redraw the graph with the current angle.
 * @private
 */
FieldAngle.prototype.updateGraph_ = function() {
  if (!this.gauge_) {
    return;
  }
  var angleRadians = Number(this.getText()) / 180 * Math.PI;
  if (isNaN(angleRadians)) {
    this.gauge_.setAttribute('d',
        'M ' + FieldAngle.HALF + ', ' + FieldAngle.HALF);
    this.line_.setAttribute('x2', FieldAngle.HALF);
    this.line_.setAttribute('y2', FieldAngle.HALF);
  } else {
    var x = FieldAngle.HALF + Math.cos(angleRadians) *
        FieldAngle.RADIUS;
    var y = FieldAngle.HALF + Math.sin(angleRadians) *
        -FieldAngle.RADIUS;
    var largeFlag = (angleRadians > Math.PI) ? 1 : 0;
    this.gauge_.setAttribute('d',
        'M ' + FieldAngle.HALF + ', ' + FieldAngle.HALF +
        ' h ' + FieldAngle.RADIUS +
        ' A ' + FieldAngle.RADIUS + ',' + FieldAngle.RADIUS +
        ' 0 ' + largeFlag + ' 0 ' + x + ',' + y + ' z');
    this.line_.setAttribute('x2', x);
    this.line_.setAttribute('y2', y);
  }
};

/**
 * Ensure that only an angle may be entered.
 * @param {string} text The user's text.
 * @return {?string} A string representing a valid angle, or null if invalid.
 */
FieldAngle.angleValidator = function(text) {
  var n = numberValidator(text);
  if (n !== null) {
    n = n % 360;
    if (n < 0) {
      n += 360;
    }
    n = String(n);
   }
  return n;
};
