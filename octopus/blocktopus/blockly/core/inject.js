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
 * @fileoverview Functions for injecting Blockly into a web page.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import Workspace from './workspace';
import {ScrollbarPair} from './scrollbar';
import Xml from './xml';
import Toolbox from './toolbox';
import Tooltip from './tooltip';
import WidgetDiv from './widgetdiv';
import {bindEvent_, unbindEvent_, fireUiEvent, createSvgElement} from './utils';

/**
 * Initialize the SVG document with various handlers.
 * @param {!Element} container Containing element.
 * @param {Object} opt_options Optional dictionary of options.
 */
export function inject (container, opt_options) {
  if (opt_options) {
    parseOptions_(opt_options);
  }

  createDom_(container);
  init_();

  // Allow time for the polymer element to attach
  setTimeout(Blockly.svgResize, 10);
};

/**
 * Parse the provided toolbox tree into a consistent DOM format.
 * @param {Node|string} tree DOM tree of blocks, or text representation of same.
 * @return {Node} DOM tree of blocks or null.
 * @private
 */
function parseToolboxTree_ (tree) {
  if (tree) {
    if (typeof tree != 'string' && typeof XSLTProcessor == 'undefined') {
      // In this case the tree will not have been properly built by the
      // browser. The HTML will be contained in the element, but it will
      // not have the proper DOM structure since the browser doesn't support
      // XSLTProcessor (XML -> HTML). This is the case in IE 9+.
      tree = tree.outerHTML;
    }
    if (typeof tree == 'string') {
      tree = Xml.textToDom(tree);
    }
  } else {
    tree = null;
  }
  return tree;
};

/**
 * Configure Blockly to behave according to a set of options.
 * @param {!Object} options Dictionary of options.
 * @private
 */
function parseOptions_ (options) {
  var readOnly = !!options['readOnly'];
  if (readOnly) {
    var hasCategories = false;
    var hasTrashcan = false;
    var hasCollapse = false;
    var hasComments = false;
    var hasDisable = false;
    var tree = null;
  } else {
    var hasCategories = true;
    var hasTrashcan = options['trashcan'];
    if (hasTrashcan === undefined) {
      hasTrashcan = hasCategories;
    }
    var hasCollapse = options['collapse'];
    if (hasCollapse === undefined) {
      hasCollapse = hasCategories;
    }
    var hasComments = options['comments'];
    if (hasComments === undefined) {
      hasComments = hasCategories;
    }
    var hasDisable = options['disable'];
    if (hasDisable === undefined) {
      hasDisable = hasCategories;
    }
  }
  var hasScrollbars = options['scrollbars'];
  if (hasScrollbars === undefined) {
    hasScrollbars = true;
  }
  var hasSounds = options['sounds'];
  if (hasSounds === undefined) {
    hasSounds = true;
  }
  var enableRealtime = !!options['realtime'];
  var realtimeOptions = enableRealtime ? options['realtimeOptions'] : undefined;

  Blockly.RTL = !!options['rtl'];
  Blockly.collapse = hasCollapse;
  Blockly.comments = hasComments;
  Blockly.disable = hasDisable;
  Blockly.readOnly = readOnly;
  Blockly.maxBlocks = options['maxBlocks'] || Infinity;
  Blockly.pathToBlockly = options['path'] || './';
  Blockly.hasCategories = hasCategories;
  Blockly.hasScrollbars = hasScrollbars;
  Blockly.hasTrashcan = hasTrashcan;
  Blockly.hasSounds = hasSounds;
  Blockly.languageTree = tree;
  Blockly.enableRealtime = enableRealtime;
  Blockly.realtimeOptions = realtimeOptions;
};

/**
 * Create the SVG image.
 * @param {!Element} container Containing element.
 * @private
 */
function createDom_ (container) {
  // Sadly browsers (Chrome vs Firefox) are currently inconsistent in laying
  // out content in RTL mode.  Therefore Blockly forces the use of LTR,
  // then manually positions content in RTL as needed.
  container.setAttribute('dir', 'LTR');
  // Closure can be trusted to create HTML widgets with the proper direction.
  // TODO?
  //goog.ui.Component.setDefaultRightToLeft(Blockly.RTL);

  // Build the SVG DOM.
  /*
  <svg
    xmlns="http://www.w3.org/2000/svg"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    version="1.1"
    class="blocklySvg">
    ...
  </svg>
  */
  var svg = createSvgElement('svg', {
    'xmlns': 'http://www.w3.org/2000/svg',
    'xmlns:html': 'http://www.w3.org/1999/xhtml',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
    'version': '1.1',
    'class': 'blocklySvg'
  }, null);
  /*
  <defs>
    ... filters go here ...
  </defs>
  */
  var defs = createSvgElement('defs', {}, svg);
  var filter, feSpecularLighting, feMerge, pattern;
  /*
    <filter id="blocklyEmboss">
      <feGaussianBlur in="SourceAlpha" stdDeviation="1" result="blur"/>
      <feSpecularLighting in="blur" surfaceScale="1" specularConstant="0.5"
                          specularExponent="10" lighting-color="white"
                          result="specOut">
        <fePointLight x="-5000" y="-10000" z="20000"/>
      </feSpecularLighting>
      <feComposite in="specOut" in2="SourceAlpha" operator="in"
                   result="specOut"/>
      <feComposite in="SourceGraphic" in2="specOut" operator="arithmetic"
                   k1="0" k2="1" k3="1" k4="0"/>
    </filter>
  */
  filter = createSvgElement('filter', {'id': 'blocklyEmboss'}, defs);
  createSvgElement('feGaussianBlur',
      {'in': 'SourceAlpha', 'stdDeviation': 1, 'result': 'blur'}, filter);
  feSpecularLighting = createSvgElement('feSpecularLighting',
      {'in': 'blur', 'surfaceScale': 1, 'specularConstant': 0.5,
      'specularExponent': 10, 'lighting-color': 'white', 'result': 'specOut'},
      filter);
  createSvgElement('fePointLight',
      {'x': -5000, 'y': -10000, 'z': 20000}, feSpecularLighting);
  createSvgElement('feComposite',
      {'in': 'specOut', 'in2': 'SourceAlpha', 'operator': 'in',
      'result': 'specOut'}, filter);
  createSvgElement('feComposite',
      {'in': 'SourceGraphic', 'in2': 'specOut', 'operator': 'arithmetic',
      'k1': 0, 'k2': 1, 'k3': 1, 'k4': 0}, filter);
  /*
    <filter id="blocklyTrashcanShadowFilter">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur"/>
      <feOffset in="blur" dx="1" dy="1" result="offsetBlur"/>
      <feMerge>
        <feMergeNode in="offsetBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  */
  filter = createSvgElement('filter',
      {'id': 'blocklyTrashcanShadowFilter'}, defs);
  createSvgElement('feGaussianBlur',
      {'in': 'SourceAlpha', 'stdDeviation': 2, 'result': 'blur'}, filter);
  createSvgElement('feOffset',
      {'in': 'blur', 'dx': 1, 'dy': 1, 'result': 'offsetBlur'}, filter);
  feMerge = createSvgElement('feMerge', {}, filter);
  createSvgElement('feMergeNode', {'in': 'offsetBlur'}, feMerge);
  createSvgElement('feMergeNode', {'in': 'SourceGraphic'}, feMerge);
  /*
    <filter id="blocklyShadowFilter">
      <feGaussianBlur stdDeviation="2"/>
    </filter>
  */
  filter = createSvgElement('filter',
      {'id': 'blocklyShadowFilter'}, defs);
  createSvgElement('feGaussianBlur', {'stdDeviation': 2}, filter);
  /*
    <pattern id="blocklyDisabledPattern" patternUnits="userSpaceOnUse"
             width="10" height="10">
      <rect width="10" height="10" fill="#aaa" />
      <path d="M 0 0 L 10 10 M 10 0 L 0 10" stroke="#cc0" />
    </pattern>
  */
  pattern = createSvgElement('pattern',
      {'id': 'blocklyDisabledPattern', 'patternUnits': 'userSpaceOnUse',
       'width': 10, 'height': 10}, defs);
  createSvgElement('rect',
      {'width': 10, 'height': 10, 'fill': '#aaa'}, pattern);
  createSvgElement('path',
      {'d': 'M 0 0 L 10 10 M 10 0 L 0 10', 'stroke': '#cc0'}, pattern);
  Blockly.mainWorkspace = new Workspace(
      Blockly.getMainWorkspaceMetrics_,
      Blockly.setMainWorkspaceMetrics_);
  svg.appendChild(Blockly.mainWorkspace.createDom());
  Blockly.mainWorkspace.maxBlocks = Blockly.maxBlocks;

  // Pass through block events
  [
    "created", "disposed", "connected", "disconnected", "set-position",
    "set-disabled", "set-deletable", "set-editable", "set-movable",
    "set-help-url", "set-colour", "set-comment", "set-collapsed",
    "set-field-value", "set-inputs-inline", "add-input", "remove-input",
    "set-mutation", "transaction", "cancel"
  ].forEach(function (e) {
    Blockly.mainWorkspace.on("block-" + e, function (data) {
      Blockly.emit("block-" + e, data);
    });
  });

  if (!Blockly.readOnly) {
    Toolbox.createDom(svg, container);
  }

  svg.appendChild(Tooltip.createDom());

  // The SVG is now fully assembled.  Add it to the container.
  container.appendChild(svg);
  Blockly.svg = svg;
  Blockly.svgResize();

  // Create an HTML container for popup overlays (e.g. editor widgets).
  WidgetDiv.DIV = document.createElement('div');
  WidgetDiv.DIV.setAttribute('class', 'blocklyWidgetDiv');
  WidgetDiv.DIV.style.direction = Blockly.RTL ? 'rtl' : 'ltr';
  document.body.appendChild(WidgetDiv.DIV);
};


/**
 * Initialize Blockly with various handlers.
 * @private
 */
function init_ () {
  // Bind events for scrolling the workspace.
  // Most of these events should be bound to the SVG's surface.
  // However, 'mouseup' has to be on the whole document so that a block dragged
  // out of bounds and released will know that it has been released.
  // Also, 'keydown' has to be on the whole document since the browser doesn't
  // understand a concept of focus on the SVG image.
  bindEvent_(Blockly.svg, 'mousedown', null, Blockly.onMouseDown_);
  bindEvent_(Blockly.svg, 'contextmenu', null, Blockly.onContextMenu_);
  bindEvent_(WidgetDiv.DIV, 'contextmenu', null,
                     Blockly.onContextMenu_);

  if (!Blockly.documentEventsBound_) {
    // Only bind the window/document events once.
    // Destroying and reinjecting Blockly should not bind again.
    bindEvent_(window, 'resize', document, Blockly.svgResize);
    bindEvent_(document, 'keydown', null, Blockly.onKeyDown_);
    // Don't use bindEvent_ for document's mouseup since that would create a
    // corresponding touch handler that would squeltch the ability to interact
    // with non-Blockly elements.
    document.addEventListener('mouseup', Blockly.onMouseUp_, false);
    // Some iPad versions don't fire resize after portrait to landscape change.
    //if (goog.userAgent.IPAD) {
      bindEvent_(window, 'orientationchange', document, function() {
        fireUiEvent(window, 'resize');
      });
    //}
    Blockly.documentEventsBound_ = true;
  }

  Toolbox.init();

  if (Blockly.hasScrollbars) {
    Blockly.mainWorkspace.scrollbar =
        new ScrollbarPair(Blockly.mainWorkspace);
    Blockly.mainWorkspace.scrollbar.resize();
  }

  Blockly.mainWorkspace.addTrashcan();

  // Load the sounds.
  if (Blockly.hasSounds) {
    Blockly.loadAudio_(
        ['media/click.mp3', 'media/click.wav', 'media/click.ogg'], 'click');
    Blockly.loadAudio_(
        ['media/delete.mp3', 'media/delete.ogg', 'media/delete.wav'], 'delete');

    // Bind temporary hooks that preload the sounds.
    var soundBinds = [];
    var unbindSounds = function() {
      while (soundBinds.length) {
        unbindEvent_(soundBinds.pop());
      }
      Blockly.preloadAudio_();
    };
    // Android ignores any sound not loaded as a result of a user action.
    soundBinds.push(
        bindEvent_(document, 'mousemove', null, unbindSounds));
    soundBinds.push(
        bindEvent_(document, 'touchstart', null, unbindSounds));
  }
};
