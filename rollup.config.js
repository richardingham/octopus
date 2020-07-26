import builtins from 'rollup-plugin-node-builtins';
import multiEntry from '@rollup/plugin-multi-entry';

export default [{
  // core input options
  input: {
    include: [
      'octopus/blocktopus/blockly/core/blockly.js',
      'octopus/blocktopus/blockly/blocks/*.js',
    ],
    exclude: [
      'octopus/blocktopus/blockly/blocks/mixins.js',
      'octopus/blocktopus/blockly/blocks/lists.js'
    ]
  },
  output: {
    file: 'octopus/blocktopus/resources/blockly/pack/blockly.js',
    format: 'iife',
    name: 'Blockly',
    globals: {
      tinycolor: 'tinycolor'
    }
  },
  plugins: [
    builtins(), 
    multiEntry()
  ]
}, {
  input: {
    include: [
      'octopus/blocktopus/blockly/generators/python-octo.js',
      'octopus/blocktopus/blockly/generators/python-octo/*.js',
    ],
    exclude: [
      'octopus/blocktopus/blockly/generators/python-octo/lists.js',
    ]
  },
  plugins: [
    multiEntry()
  ],
  output: {
    file: 'octopus/blocktopus/resources/blockly/pack/octopus-generator.js',
    format: 'iife',
    name: 'PythonOctoGenerator',
    globals: {
      Blockly: 'Blockly'
    }
  }
}, {
  input: 'octopus/blocktopus/blockly/msg/messages.js',
  output: {
    file: 'octopus/blocktopus/resources/blockly/pack/blockly-messages.js',
    format: 'iife',
    name: 'Blockly.Msg',
    globals: {
      Blockly: 'Blockly'
    }
  }
}];
