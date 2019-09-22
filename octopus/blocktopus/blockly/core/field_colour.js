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
 * @fileoverview Colour input field.
 * @author fraser@google.com (Neil Fraser)
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import Blockly from './blockly';
import Field from './field';
import WidgetDiv from './widgetdiv';
import {inherits} from './utils';
import {getAbsoluteXY_} from './utils';

// Insert JS and CSS into body.
$('head').append('<link rel="stylesheet" href="/resources/colpick/colpick.css" type="text/css" />');
$('head').append('<script src="/resources/colpick/colpick.js" type="text/javascript" />');

/**
 * Class for a colour input field.
 * @param {string} colour The initial colour in '#rrggbb' format.
 * @param {Function} opt_changeHandler A function that is executed when a new
 *     colour is selected.  Its sole argument is the new colour value.  Its
 *     return value becomes the selected colour, unless it is undefined, in
 *     which case the new colour stands, or it is null, in which case the change
 *     is aborted.
 * @extends {Field}
 * @constructor
 */
var FieldColour = function(colour, opt_changeHandler) {
  FieldColour.super_.call(this, '\u00A0\u00A0\u00A0');

  this.changeHandler_ = opt_changeHandler;
  this.borderRect_.style['fillOpacity'] = 1;

  // Set the initial state.
  this.setValue(colour);
};
inherits(FieldColour, Field);
export default FieldColour;

/**
 * Clone this FieldColour.
 * @return {!FieldColour} The result of calling the constructor again
 *   with the current values of the arguments used during construction.
 */
FieldColour.prototype.clone = function() {
  return new FieldColour(this.getValue(), this.changeHandler_);
};

/**
 * Mouse cursor style when over the hotspot that initiates the editor.
 */
FieldColour.prototype.CURSOR = 'default';

/**
 * Close the colour picker if this input is being deleted.
 */
FieldColour.prototype.dispose = function() {
  WidgetDiv.hideIfOwner(this);
  FieldColour.super_.prototype.dispose.call(this);
};

/**
 * Return the current colour.
 * @return {string} Current colour in '#rrggbb' format.
 */
FieldColour.prototype.getValue = function() {
  return this.colour_;
};

/**
 * Set the colour.
 * @param {string} colour The new colour in '#rrggbb' format.
 */
FieldColour.prototype.setValue = function(colour) {
  this.colour_ = colour;
  this.borderRect_.style.fill = colour;
  if (this.sourceBlock_ && this.sourceBlock_.rendered) {
    this.sourceBlock_.workspace.fireChangeEvent();
  }
};

/**
 * Create a palette under the colour field.
 * @private
 */
FieldColour.prototype.showEditor_ = function() {
  var thisObj = this;
  var oldValue = this.getValue();

  WidgetDiv.show(this, function() {
    if (oldValue !== thisObj.getValue()) {
      thisObj.emit("changed", thisObj.getValue());
    }
  });
  var $window = $(window);


  // Create the colour picker widget
  var options = {
    flat: true,
    submit: false,
    color: this.getValue().substring(1),
    onChange: function (hsb, hex) {
      var colour = '#' + (hex || '000000');
      if (thisObj.changeHandler_) {
        // Call any change handler, and allow it to override.
        var override = thisObj.changeHandler_(colour);
        if (override !== undefined) {
          colour = override;
        }
      }
      if (colour !== null) {
        thisObj.setValue(colour);
      }
    }
  };

  var $widget = $('<div>').colpick(options).appendTo($(WidgetDiv.DIV));

  // Position the palette to line up with the field.
  // Record windowSize and scrollOffset before adding the palette.
  var boundsX = $window.width();
  var boundsY = $window.height();
  //var scrollOffset = goog.style.getViewportPageOffset(document);
  var offsetX = $window.scrollLeft();
  var offsetY = $window.scrollTop();
  var pickerWidth = $widget.outerWidth()
  var pickerHeight = $widget.outerHeight()

  var xy = getAbsoluteXY_(this.borderRect_);

  // getBBox gives an error in polyfilled browser.
  var borderBBox;
  if (window.ShadowDOMPolyfill) {
    borderBBox = window.ShadowDOMPolyfill.unwrapIfNeeded(this.borderRect_).getBBox();
  } else {
    borderBBox = (this.borderRect_).getBBox();
  }

  // Flip the palette vertically if off the bottom.
  if (xy.y + pickerHeight + borderBBox.height >=
      boundsY + offsetY) {
    xy.y -= pickerHeight - 1;
  } else {
    xy.y += borderBBox.height - 1;
  }
  if (Blockly.RTL) {
    xy.x += borderBBox.width;
    xy.x -= pickerWidth;
    // Don't go offscreen left.
    if (xy.x < offsetX) {
      xy.x = offsetX;
    }
  } else {
    // Don't go offscreen right.
    if (xy.x > boundsX + offsetX - pickerWidth) {
      xy.x = boundsX + offsetX - pickerWidth;
    }
  }
  WidgetDiv.position(xy.x, xy.y, { height: boundsY, width: boundsX }, { height: offsetY, width: offsetX });

};
