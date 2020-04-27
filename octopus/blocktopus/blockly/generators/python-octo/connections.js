import {ORDER} from '../python-octo-constants';
import {getVariableName, addDefinition, quote} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

PythonOcto['connection_tcp'] = function (block) {
  var host = block.getFieldValue('HOST');
  var port = parseInt(block.getFieldValue('PORT'));
  var code = 'tcp(' + quote(host) + ', ' + port + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['connection_serial'] = function(block) {
  var port = block.getFieldValue('PORT');
  var baud = parseInt(block.getFieldValue('BAUD'));
  var code = 'serial(' + quote(port) + ', baudrate = ' + baud + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['connection_phidget'] = function(block) {
  addDefinition('import_transport_basic_phidget', 'from octopus.transport.basic import Phidget');
  var id = parseInt(block.getFieldValue('ID'));
  var code = 'Phidget(' + id + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['connection_cvcamera'] = function(block) {
  addDefinition('import_image_source', 'from octopus.image.source import cv_webcam');
  var id = parseInt(block.getFieldValue('ID'));
  var code = 'cv_webcam(' + id + ')';
  return [code, ORDER.FUNCTION_CALL];
};

PythonOcto['connection_gsioc'] = function(block) {
  var name = getVariableName(block.getVariable());
  var id = parseInt(block.getFieldValue('ID'));
  var code = name + '.gsioc(' + id + ')';
  return [code, ORDER.FUNCTION_CALL];
};
