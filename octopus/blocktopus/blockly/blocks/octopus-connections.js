
import Blockly from '../core/blockly';
import Blocks from '../core/blocks';
import Block from '../core/block';
import Msg from '../core/msg';
import FieldTextInput from '../core/field_textinput';
import FieldLexicalVariable from '../core/field_lexical_variable';
import {withVariableDropdown} from './mixins.js';
import {CONNECTIONS_CATEGORY_HUE} from '../colourscheme';

Blocks['connection_tcp'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("TCP - ip")
        .appendField(new FieldTextInput("192.168.15.100"), "HOST")
        .appendField("port")
        .appendField(new FieldTextInput("9000", iv), "PORT");
    this.setOutput(true, "MachineConnection");
    this.setTooltip('Represents a TCP/IP (Ethernet) connection to a machine. Fill in the IP and Port fields.');
  }
};

Blocks['connection_serial'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("Serial - port")
        .appendField(new FieldTextInput("/dev/ttyS0"), "PORT")
        .appendField("baudrate")
        .appendField(new FieldTextInput("19200", iv), "BAUD");
    this.setOutput(true, "MachineConnection");
    this.setTooltip('Represents a Direct serial (RS-232) connection to a machine. Fill in the Port and Baudrate fields.');
  }
};

Blocks['connection_phidget'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("Phidget ID")
        .appendField(new FieldTextInput("0", iv), "ID");
    this.setOutput(true, "PhidgetConnection");
    this.setTooltip('Represents a Phidget device. Specify the serial ID of the phidget board.');
  }
};

Blocks['connection_cvcamera'] = {
  init: function() {
    //this.setHelpUrl('http://www.example.com/');

    var iv = FieldTextInput.nonnegativeIntegerValidator;
    this.setColour(CONNECTIONS_CATEGORY_HUE);
    this.appendDummyInput()
        .appendField("Camera - no. ")
        .appendField(new FieldTextInput("0", iv), "ID");
    this.setOutput(true, "CameraConnection");
    this.setTooltip('Represents a USB webcamera. The first camera has id 0, the second 1, and so on.');
  }
};

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
