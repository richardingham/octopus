/**
 * @license
 * Visual Blocks Editor
 *
 * Copyright 2011 Google Inc.
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
 * @fileoverview Toolbox from whence to create blocks.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Flyout from './flyout';

var Toolbox = {};
export default Toolbox;

/**
 * Width of the toolbox.
 * @type {number}
 */
Toolbox.width = 0;

/**
 * Creates the toolbox's DOM.  Only needs to be called once.
 * @param {!Element} svg The top-level SVG element.
 * @param {!Element} container The SVG's HTML parent element.
 */
Toolbox.createDom = function(svg, container) {
  /**
   * @type {!Flyout}
   * @private
   */
  Toolbox.flyout_ = new Flyout();
  svg.appendChild(Toolbox.flyout_.createDom());
};

/**
 * Initializes the toolbox.
 */
Toolbox.init = function() {
  Toolbox.flyout_.init(Blockly.mainWorkspace);
  Toolbox.populate_();
  Toolbox.width = -1;
};

Toolbox.populate_ = function () {};
