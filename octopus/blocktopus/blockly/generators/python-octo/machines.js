'use strict';

import {ORDER} from '../python-octo-constants';
import {addDefinition, getVariableName, valueToCode, quote} from '../python-octo-methods';
import PythonOcto from '../python-octo-blocks';

function machineBlockGenerator (smod, mod, cls) {
  return function (block) {
    var blockVariable = block.getVariable();
    var name = getVariableName(blockVariable);
    var alias = (blockVariable ? blockVariable.getVarName() : "_");
    var conn = valueToCode(block, 'CONNECTION', ORDER.NONE) || 'dummy()';
    addDefinition('import_' + smod + '_' + mod, 'from ' + smod + ' import ' + mod);

    var attributes = []
    if (block.mutation) {
      var opt, options = block.machineOptions || [];
      for (var i = 0, max = options.length; i < max; i++) {
        opt = options[i];
        if (opt.multi) {
          attributes.push(opt.name + ' = ' + JSON.stringify(block.mutation[opt.name] || []));
        } else {
          attributes.push(opt.name + ' = ' + (block.mutation[opt.name] || (opt.type === "Number" ? 0 : '""')));
        }
      }
    }

    return [
      name, ' = ', mod, '.', cls, '(', conn,
      attributes.length ? ', ' : '', attributes.join(', '),
      ', alias = ', quote(alias), ')'
    ].join('');
  };
};

PythonOcto['machine_vapourtec_R2R4'] = machineBlockGenerator('octopus.manufacturer', 'vapourtec', 'R2R4');
PythonOcto['machine_knauer_K120'] = machineBlockGenerator('octopus.manufacturer', 'knauer', 'K120');
PythonOcto['machine_knauer_S100'] = machineBlockGenerator('octopus.manufacturer', 'knauer', 'S100');
PythonOcto['machine_vici_multivalve'] = machineBlockGenerator('octopus.manufacturer', 'vici', 'MultiValve');
PythonOcto['machine_mt_icir'] = machineBlockGenerator('octopus.manufacturer', 'mt', 'iCIR');
PythonOcto['machine_wpi_aladdin'] = machineBlockGenerator('octopus.manufacturer', 'wpi', 'Aladdin');
PythonOcto['machine_phidgets_phsensor'] = machineBlockGenerator('octopus.manufacturer', 'phidgets', 'PHSensor');
PythonOcto['machine_singletracker'] = machineBlockGenerator('octopus.image', 'tracker', 'SingleBlobTracker');
PythonOcto['machine_multitracker'] = machineBlockGenerator('octopus.image', 'tracker', 'MultiBlobTracker');
PythonOcto['machine_imageprovider'] = machineBlockGenerator('octopus.image', 'provider', 'ImageProvider');
PythonOcto['machine_omega_hh306a'] = machineBlockGenerator('octopus.manufacturer', 'omega', 'HH306A');
PythonOcto['machine_harvard_phd2000'] = machineBlockGenerator('octopus.manufacturer', 'harvard', 'PHD2000');
PythonOcto['machine_mt_sics_balance'] = machineBlockGenerator('octopus.manufacturer', 'mt', 'SICSBalance');
PythonOcto['machine_startech_powerremotecontrol'] = machineBlockGenerator('octopus.manufacturer', 'startech', 'PowerRemoveControl');
PythonOcto['machine_gilson_FractionCollector203B'] = machineBlockGenerator('octopus.manufacturer', 'gilson', 'FractionCollector203B');
