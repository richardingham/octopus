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
 * @fileoverview Variable blocks for Blockly.
 * @author mail@richardingham.net (Richard Ingham)
 */
'use strict';

import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import Mutator from '../core/mutator';
import {GlobalScope} from '../core/variables';
import FieldDropdown from '../core/field_dropdown';
import FieldTextInput from '../core/field_textinput';
import FieldFlydown from '../core/field_flydown';
import FieldMachineFlydown from '../core/field_machine_flydown';
import {withVariableDefinition} from './mixins.js';
import {MACHINES_CATEGORY_HUE} from '../colourscheme';
import {_extend as extend} from '../core/utils';
import {numberValidator} from '../core/validators';

var _K120_vars = [
  { name: "status", title: "Status", type: "String", readonly: true },
  { name: "power", title: "Power", type: "String", options: ['off', 'on'] },
  { name: "target", title: "Target", type: "Number", unit: { options: [['mL/min', 1000], ['uL/min', 1]], default: 1000 } },
  { name: "rate", title: "Flow Rate", type: "Number", readonly: true }
];
var _S100_vars = [
  { name: "status", title: "Status", type: "String", readonly: true },
  { name: "power", title: "Power", type: "String", options: ['off', 'on'] },
  { name: "target", title: "Target", type: "Number", unit: { options: [['mL/min', 1000], ['uL/min', 1]], default: 1000 } },
  { name: "pressure", title: "Pressure", type: "Number", readonly: true, unit: { options: [['mbar', 1], ['bar', 1000]], default: 1000 } },
  { name: "rate", title: "Flow Rate", type: "Number", readonly: true }
];

var _MultiValve_vars = [
  { name: "position", title: "Position", type: "Number" }
];

var _MultiValve_options = [
  { name: "num_positions", title: "Number of positions", type: "Number", min: 0 }
];

var _iCIR_vars = [];
var _iCIR_options = [
  { name: "stream_names", title: "Data Streams", type: "String", multi: true, createAttributes: { type: "Number", readonly: true } }
];

var _SingleTracker_vars = [
  { name: "height", title: "Height", type: "Number", readonly: true }
];

var _MultiTracker_vars = [];
var _MultiTracker_options = [
  { name: "count", title: "Number to track", type: "Number", createAttributes: { name: "height%", title: "Height #%", type: "Number", readonly: true } }
];

var _ARROW_CHAR = /*goog.userAgent.ANDROID ? ' \u25B6 ' :*/ ' \u25B8 ';

var machineBlock = {
  init: function() {
    var default_name = this.machineDefaultName || "reactor";

    var thisBlock = this;

    function createMachineVariable () {
      var machineVars = thisBlock.machineVars;
      var machineVar = GlobalScope.addVariable(default_name, "machine");
      machineVar.setType("component");
      machineVar.setReadonly("true");

      if (thisBlock.machineVarFlags) {
        machineVar.flags = thisBlock.machineVarFlags;
      }

      addParts(machineVar, machineVars, "");
      return machineVar;
    }

    function addParts (variable, parts, titlePart) {
      var part;
      for (var i = 0; i < parts.length; i++) {
        part = parts[i];
        var display = titlePart + _ARROW_CHAR + part.title;
        var partVar = variable.addAttribute(part.name);
        partVar.setMenu(part.title);
        partVar.setDisplay(display);
        partVar.setType(part.parts ? "component" : part.type);
        partVar.setReadonly(part.readonly || part.parts);

        if (part.flags) {
          partVar.flags = part.flags;
        }

        if (part.options) {
          partVar.flags.options = part.options;
        }

        if (part.unit) {
          partVar.flags.unit = part.unit;
        }

        if (part.parts) {
          addParts(partVar, part.parts, display);
        }
      }
    }

    this.fieldName_ = withVariableDefinition(
      this, FieldMachineFlydown,
      FieldFlydown.DISPLAY_BELOW,
      default_name,
      true,
      createMachineVariable
    );

    //this.setHelpUrl('http://www.example.com/');
    this.setColour(MACHINES_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(this.machineTitle + " ")
        .appendField(this.fieldName_, 'NAME');
    this.appendValueInput("CONNECTION")
        .setCheck(this.machineConnectionType || "MachineConnection")
        .setAlign(Blockly.ALIGN_RIGHT)
        .appendField("connection");
    this.setTooltip('');
    this.setInputsInline(false);

    if (!this.isInFlyout) {
      if (this.machineOptions) {
        // Decide whether or not there are options requiring draggable blocks
        var options = this.machineOptions, multi = false;
        for (var i = 0, max = options.length; i < max; i++) {
          multi |= !!options[i].multi;
        }
        this.mutation = {};
        this.setMutator(new Mutator(
          multi ? ['machine_quark_argument'] : []
        ));

        this.decompose = function decompose (workspace) {
          var containerBlock = Block.obtain(workspace, 'machine_quark');
          var mutation = thisBlock.mutation;
          containerBlock.initSvg();
          var opt;
          for (var i = 0, max = options.length; i < max; i++) {
            opt = options[i];
            if (opt.multi) {
              containerBlock.appendDummyInput().appendField(opt.title);
              containerBlock.appendStatementInput(opt.name);
              var connection = containerBlock.getInput(opt.name).connection;
              if (mutation[opt.name] && mutation[opt.name].length) {
                for (var x = 0; x < mutation[opt.name].length; x++) {
                  var subBlock = Block.obtain(workspace, 'machine_quark_argument');
                  subBlock.setFieldValue(mutation[opt.name][x], 'VALUE');
                  subBlock.initSvg();
                  connection.connect(subBlock.previousConnection);
                  connection = subBlock.nextConnection;
                }
              }
            } else {
              if (opt.options) {
                containerBlock.appendDummyInput()
                  .appendField(new FieldDropdown(
                    opt.options.map(function (o) { return [o, o]; })
                  ), opt.name);
                if (mutation[opt.name]) {
                  containerBlock.setFieldValue(mutation[opt.name], opt.name);
                }
              } else if (opt.type == "Number") {
                containerBlock.appendDummyInput()
                  .appendField(opt.title + ": ")
                  .appendField(new FieldTextInput(
                    (mutation[opt.name] && mutation[opt.name].toString && mutation[opt.name].toString()) || '0',
                    numberValidator
                  ), opt.name);
              } else if (opt.type == "String") {
                containerBlock.appendDummyInput()
                  .appendField(opt.title + ": ")
                  .appendField(new FieldTextInput(mutation[opt.name] || ''), opt.name);
              }
            }
          }
          return containerBlock;
        };
        this.compose = function compose (containerBlock) {
          var block, opt, mutation = {};
          for (var i = 0, max = options.length; i < max; i++) {
            opt = options[i];
            if (opt.multi) {
              var values = [];
              block = containerBlock.getInputTargetBlock(opt.name);
              while (block) {
                values.push(block.getFieldValue('VALUE'));
                block = block.nextConnection &&
                  block.nextConnection.targetBlock();
              }
              mutation[opt.name] = values;
            } else {
              var value = containerBlock.getFieldValue(opt.name);
              mutation[opt.name] = opt.type === "Number" ? parseFloat(value) : value;
            }
          }
          thisBlock.mutation = mutation;
          thisBlock.applyMutation();
        };
        this.mutationToJSON = function mutationToJSON () {
          return JSON.stringify(thisBlock.mutation);
        };
        this.JSONToMutation = function JSONToMutation (obj) {
          thisBlock.mutation = obj;
          thisBlock.applyMutation();
        };
        this.mutationToDom = function mutationToDom () {
          if (!thisBlock.mutation) {
            return null;
          }
          var container = document.createElement('mutation');
          var opt;
          for (var i = 0, max = options.length; i < max; i++) {
            opt = options[i];
            if (opt.multi) {
              container.setAttribute(opt.name, JSON.stringify(thisBlock.mutation[opt.name]));
            } else {
              container.setAttribute(opt.name, thisBlock.mutation[opt.name]);
            }
          }
          return container;
        };
        this.domToMutation = function domToMutation (xmlElement) {
          var opt, mutation = {};
          for (var i = 0, max = options.length; i < max; i++) {
            opt = options[i];
            if (opt.multi) {
              mutation[opt.name] = JSON.parse(xmlElement.getAttribute(opt.name) || []);
            } else if (opt.type === "Number") {
              mutation[opt.name] = parseFloat(xmlElement.getAttribute(opt.name) || 0);
            } else {
              mutation[opt.name] = xmlElement.getAttribute(opt.name) || "";
            }
          }
          thisBlock.mutation = mutation;
          thisBlock.applyMutation();
        };
        this.applyMutation = function applyMutation (xmlElement) {
          var opt, attributes = machineVars.slice();
          for (var i = 0, max = options.length; i < max; i++) {
            opt = options[i];
            if (opt.createAttributes) {
              if (opt.multi) {
                thisBlock.mutation[opt.name].forEach(function (value) {
                  attributes.push(extend(opt.createAttributes, {
                    name: value,
                    title: value
                  }));
                });
              } else {
                var count = thisBlock.mutation[opt.name];
                for (var j = 0; j < count; j++) {
                  attributes.push(extend(opt.createAttributes, {
                    name: opt.createAttributes.name.replace('%', j + 1),
                    title: opt.createAttributes.title.replace('%', j + 1)
                  }));
                };
              }
            }
          }
          thisBlock.variable_.clearAttributes();
          addParts(thisBlock.variable_, attributes, "");
        };
      }
    }
  },
};

Blocks['machine_quark'] = {
  init: function() {
    //this.setHelpUrl(Msg.CONTROLS_IF_HELPURL);
    this.setColour(MACHINES_CATEGORY_HUE);
  }
};

Blocks['machine_quark_argument'] = {
  init: function() {
    //this.setHelpUrl(Msg.CONTROLS_IF_HELPURL);
    this.setColour(MACHINES_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField(new FieldTextInput(''), 'VALUE');
    this.setPreviousStatement(true);
    this.setNextStatement(true);
  }
};

Blocks['machine_knauer_K120'] = extend({
  machineTitle: "Knauer K120",
  machineDefaultName: "pump",
  machineVars: _K120_vars,
}, machineBlock);

Blocks['machine_knauer_S100'] = extend({
  machineTitle: "Knauer S100",
  machineDefaultName: "pump",
  machineVars: _S100_vars,
}, machineBlock);

Blocks['machine_vici_multivalve'] = extend({
  machineTitle: "VICI multi-position valve",
  machineDefaultName: "valve",
  machineVars: _MultiValve_vars,
  machineOptions: _MultiValve_options,
}, machineBlock);

Blocks['machine_mt_icir'] = extend({
  machineTitle: "MT FlowIR",
  machineDefaultName: "ir",
  machineVars: _iCIR_vars,
  machineOptions: _iCIR_options,
}, machineBlock);

Blocks['machine_wpi_aladdin'] = extend({
  machineTitle: "WPI Aladdin syringe pump",
  machineDefaultName: "pump",
  machineVars: [
    { name: "status", title: "Status", type: "String", readonly: true },
    { name: "rate", title: "Flow rate", type: "Number", unit: { options: [['mL/min', 1000], ['uL/min', 1]], default: 1000 } },
    { name: "direction", title: "Direction", type: "String", options: ['infuse', 'withdraw'] },
    { name: "dispensed", title: "Dispensed volume", type: "Number", readonly: true },
    { name: "withdrawn", title: "Withdrawn volume", type: "Number", readonly: true }
  ],
  machineOptions: [
    { name: "syringe_diameter", title: "Syringe Diameter /mm", type: "Number", min: 0 }
  ]
}, machineBlock);

Blocks['machine_phidgets_phsensor'] = extend({
  machineTitle: "Phidgets pH Sensor",
  machineDefaultName: "phsensor",
  machineVars: [
    { name: "ph", title: "pH Reading", type: "Number", readonly: true },
    { name: "temperature", title: "Temperature", type: "Number", unit: 'C' }
  ],
  machineOptions: [
    { name: "min_change", title: "Minimum pH Change", type: "Number", min: 0 }
  ],
  machineConnectionType: "PhidgetConnection"
}, machineBlock);

Blocks['machine_imageprovider'] = extend({
  machineTitle: "Image Provider",
  machineDefaultName: "camera",
  machineVars: [
    { name: "image", title: "Image", type: "Image", readonly: true }
  ],
  machineConnectionType: "CameraConnection"
}, machineBlock);

Blocks['machine_singletracker'] = extend({
  machineTitle: "Single Tracker",
  machineDefaultName: "tracker",
  machineVars: _SingleTracker_vars,
  machineConnectionType: "CameraConnection"
}, machineBlock);

Blocks['machine_multitracker'] = extend({
  machineTitle: "Multi Tracker",
  machineDefaultName: "tracker",
  machineVars: _MultiTracker_vars,
  machineOptions: _MultiTracker_options,
  machineConnectionType: "CameraConnection"
}, machineBlock);

Blocks['machine_omega_hh306a'] = extend({
  machineTitle: "Omega HH306A",
  machineDefaultName: "thermocouple",
  machineVars: [
    { name: "temp1", title: "Temperature 1", type: "Number", readonly: true },
    { name: "temp2", title: "Temperature 2", type: "Number", readonly: true }
  ]
}, machineBlock);

Blocks['machine_harvard_phd2000'] = extend({
  machineTitle: "Harvard PHD2000 infuse-only syringe pump",
  machineDefaultName: "pump",
  machineVars: [
    { name: "status", title: "Status", type: "String", readonly: true },
    { name: "rate", title: "Flow rate", type: "Number", unit: { options: [['mL/min', 1000], ['uL/min', 1]], default: 1000 } },
    { name: "dispensed", title: "Dispensed volume", type: "Number", readonly: true },
    { name: "target_volume", title: "Target volume", type: "Number", unit: 'mL' }
  ],
  machineOptions: [
    { name: "syringe_diameter", title: "Syringe Diameter /mm", type: "Number", min: 0 }
  ]
}, machineBlock);

Blocks['machine_mt_sics_balance'] = extend({
  machineTitle: "MT Balance (SICS)",
  machineDefaultName: "balance",
  machineVars: [
    { name: "status", title: "Status", type: "String", readonly: true },
    { name: "weight", title: "Weight", type: "Number", readonly: true }
  ]
}, machineBlock);

Blocks['machine_startech_powerremotecontrol'] = extend({
  machineTitle: "StarTech Power Remote Control",
  machineDefaultName: "powerswitch",
  machineVars: [
    { name: "current", title: "Current", type: "Number", readonly: true },
    { name: "port1", title: "Port 1", type: "String", options: ['off', 'on'] },
    { name: "port2", title: "Port 2", type: "String", options: ['off', 'on'] },
    { name: "port3", title: "Port 3", type: "String", options: ['off', 'on'] },
    { name: "port4", title: "Port 4", type: "String", options: ['off', 'on'] },
    { name: "port5", title: "Port 5", type: "String", options: ['off', 'on'] },
    { name: "port6", title: "Port 6", type: "String", options: ['off', 'on'] },
    { name: "port7", title: "Port 7", type: "String", options: ['off', 'on'] },
    { name: "port8", title: "Port 8", type: "String", options: ['off', 'on'] }
  ]
}, machineBlock);

Blocks['machine_gilson_FractionCollector203B'] = extend({
  machineTitle: "Gilson Fraction Collector 203B",
  machineDefaultName: "fractioncollector",
  machineVars: [
    { name: "position", title: "Position", type: "Number" },
    { name: "valve", title: "Valve", type: "String", options: ['waste', 'collect'] }
  ],
  machineConnectionType: "GSIOCConnection"
}, machineBlock);

Blocks.addMachineBlock = function(name, definition) {
  Blocks[name] = extend(definition, machineBlock);
};
