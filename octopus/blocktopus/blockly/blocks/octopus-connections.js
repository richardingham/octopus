
import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import FieldTextInput from '../core/field_textinput';
import FieldLexicalVariable from '../core/field_lexical_variable';
import {withVariableDropdown} from './mixins.js';
import {CONNECTIONS_CATEGORY_HUE} from '../colourscheme';
import {_extend as extend} from '../core/utils';


var connectionBlock = {
  init: function () {
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    var di = this.appendDummyInput();

    for (var i = 0, max = this.connInputFields.length; i < max; i++) {
      var fieldSpec = this.connInputFields[i];
      
      if (typeof fieldSpec == 'string') {
        di.appendField(fieldSpec);
      } else if (typeof fieldSpec == 'object') {
        if (fieldSpec.type == 'string') {
          di.appendField(new FieldTextInput(fieldSpec.default), fieldSpec.name);
        } else if (fieldSpec.type == 'integer') {
          di.appendField(new FieldTextInput(
            fieldSpec.default, 
            FieldTextInput.nonnegativeIntegerValidator
          ), fieldSpec.name);
        }
      }
    }

    this.setOutput(true, this.connOutputType || "MachineConnection");
    this.setTooltip(true, this.connTooltip || "");
  }
}


Blocks.addConnectionBlock = function(name, definition) {
  Blocks[name] = extend(definition, connectionBlock);
};


Blocks['connection_tcp'] = extend({
  "connInputFields": [
    "TCP - ip",
    { "name": "HOST", "type": "string", "default": "192.168.15.100" },
    "port",
    { "name": "PORT", "type": "integer", "default": "9000" }
  ],
  "connOutputType": "MachineConnection",
  "connTooltip": "Represents a TCP/IP (Ethernet) connection to a machine."
}, connectionBlock);


Blocks['connection_serial'] = extend({
  "connInputFields": [
    "Serial - port",
    { "name": "PORT", "type": "string", "default": "/dev/ttyS0" },
    "baudrate",
    { "name": "BAUD", "type": "integer", "default": "19200" }
  ],
  "connOutputType": "MachineConnection",
  "connTooltip": "Represents a Direct serial (RS-232) connection to a machine."
}, connectionBlock);


Blocks['connection_phidget'] = extend({
  "connInputFields": [
    "Phidget - ID",
    { "name": "ID", "type": "integer", "default": "0" },
  ],
  "connOutputType": "PhidgetConnection",
  "connTooltip": "Represents a Phidget device. Specify the serial ID of the phidget board."
}, connectionBlock);


Blocks['connection_cvcamera'] = extend({
  "connInputFields": [
    "Camera - No",
    { "name": "ID", "type": "integer", "default": "0" },
  ],
  "connOutputType": "CameraConnection",
  "connTooltip": "Represents a USB webcamera. The first camera has id 0, the second 1, and so on."
}, connectionBlock);


Blocks['connection_camera_proxy'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("Camera - no:")
        .appendField(new FieldTextInput("0", iv), "ID")
        .appendField("host:")
        .appendField(new FieldTextInput("host.docker.internal"), "HOST")
        .appendField("port:")
        .appendField(new FieldTextInput("8081", iv), "PORT");
    this.setOutput(true, "CameraConnection");
    this.setTooltip('Represents an octopus webcam proxy running on the host machine.');
  }
};


Blocks['connection_gsioc'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');
    this.fieldVar_ = new FieldLexicalVariable(
      " ",
      { type: 'component', providesGSIOC: true },
      'No GSIOC providers available'
    );
    this.fieldVar_.setBlock(this);

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("GSIOC connection from ")
        .appendField(this.fieldVar_, 'VAR')
        .appendField(' ID ')
        .appendField(new FieldTextInput("0", iv), "ID");
    this.setOutput(true, "GSIOCConnection");
    this.setTooltip('Represents a USB GSIOC connection provided by a machine.');

    withVariableDropdown.call(this, this.fieldVar_, 'VAR');
  }
};
