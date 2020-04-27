
'use strict';

import Names from '../core/names';
import Blocks from './python-octo-blocks';
import {NAME_TYPE, FUNCTION_NAME_PLACEHOLDER_REGEXP_, GENERATOR_NAME, STATEMENT_PREFIX, INDENT, INFINITE_LOOP_TRAP} from './python-octo-constants';
import {VARIABLES_NAME_TYPE, PROCEDURES_NAME_TYPE} from '../constants';

/**
 * List of illegal variable names.
 * This is not intended to be a security feature.  Blockly is 100% client-side,
 * so bypassing this list is trivial.  This is intended to prevent users from
 * accidentally clobbering a built-in object or function.
 * @private
 */
var RESERVED_WORDS = "";
export function addReservedWords (words) {
  RESERVED_WORDS += words + ',';
};
export function getReservedWords () {
  return RESERVED_WORDS
}

/**
 * Initialise the database of variable names.
 */
var CONTEXT_ = {};
export function initDefinitions () {
  // Create a dictionary of definitions to be printed before the code.

  CONTEXT_.definitions_ = Object.create(null);
  // Create a dictionary mapping desired function names in definitions_
  // to actual function names (to avoid collisions with user functions).
  CONTEXT_.functionNames_ = Object.create(null);

  if (!CONTEXT_.variableDB_) {
    CONTEXT_.variableDB_ =
        new Names(RESERVED_WORDS);
  } else {
    CONTEXT_.variableDB_.reset();
  }

  CONTEXT_.definitions_['import_runtime'] = 'from octopus.runtime import *';
}

export function addDefinition (name, def) {
  CONTEXT_.definitions_[name] = def;
}
export function getDefinitions () {
  return CONTEXT_.definitions_;
}

/**
 * Define a function to be included in the generated code.
 * The first time this is called with a given desiredName, the code is
 * saved and an actual name is generated.  Subsequent calls with the
 * same desiredName have no effect but have the same return value.
 *
 * It is up to the caller to make sure the same desiredName is not
 * used for different code values.
 *
 * The code gets output when Generator.finish() is called.
 *
 * @param {string} desiredName The desired name of the function (e.g., isPrime).
 * @param {!Array.<string>} code A list of Python statements.
 * @return {string} The actual name of the new function.  This may differ
 *     from desiredName if the former has already been taken by the user.
 * @private
 */
export function provideFunction (desiredName, code) {
  if (!CONTEXT_.definitions_[desiredName]) {
    var functionName =
        CONTEXT_.variableDB_.getDistinctName(desiredName, NAME_TYPE);
    CONTEXT_.functionNames_[desiredName] = functionName;
    CONTEXT_.definitions_[desiredName] = code.join('\n').replace(
      FUNCTION_NAME_PLACEHOLDER_REGEXP_, functionName
    );
  }
  return CONTEXT_.functionNames_[desiredName];
}

export function getVariableName (variable) {
  if (!variable) {
    return "_";
  }

  var split_ns = variable.getNamespace().split(".");
  var attr = variable.getVarAttribute();
  var prefix = variable.getScope().isGlobal() ? split_ns[1] + "_" : "";
  var name = CONTEXT_.variableDB_.getName(
    variable.getVarName(),
    VARIABLES_NAME_TYPE
  );

  return prefix + name + (attr ? "." + attr : "");
}

export function getProcedureName (name) {
  return CONTEXT_.variableDB_.getName(
    name,
    PROCEDURES_NAME_TYPE
  );
}

export function getDistinctName (name) {
  return CONTEXT_.variableDB_.getDistinctName(
    name,
    VARIABLES_NAME_TYPE
  );
}

/**
 * Naked values are top-level blocks with outputs that aren't plugged into
 * anything.
 * @param {string} line Line of generated code.
 * @return {string} Legal line of code.
 */
export function scrubNakedValue (line) {
  return line + '\n';
};

/**
 * Encode a string as a properly escaped Python string, complete with quotes.
 * @param {string} string Text to encode.
 * @return {string} Python string.
 * @private
 */
export function quote (string) {
  string = string.replace(/\\/g, '\\\\')
                 .replace(/\n/g, '\\\n')
                 .replace(/\%/g, '\\%')
                 .replace(/'/g, '\\\'');
  return '\'' + string + '\'';
};


export function makeSequence (code) {
  if (typeof code === "string") {
    return code;
  }
  if (code[code.length - 1] === "") {
    code.pop();
  }
  if (code.length > 1) {
    return "sequence(\n" + prefixLines(code.join(",\n"), INDENT) + "\n)";
  } else {
    return code[0];
  }
};

/**
 * Generate code for the specified block (and attached blocks).
 * @param {Block} block The block to generate code for.
 * @return {string|!Array} For statement blocks, the generated code.
 *     For value blocks, an array containing the generated code and an
 *     operator order value.  Returns '' if block is null.
 */
export function blockToCode (block) {
  if (!block) {
    return '';
  }
  if (block.disabled) {
    // Skip past this block if it is disabled.
    return blockToCode(block.getNextBlock());
  }

  var func = Blocks[block.type];
  if (!func) {
    throw 'Language "' + GENERATOR_NAME + '" does not know how to generate code ' +
        'for block type "' + block.type + '".';
  }
  // First argument to func.call is the value of 'this' in the generator.
  // Prior to 24 September 2013 'this' was the only way to access the block.
  // The current prefered method of accessing the block is through the second
  // argument to func.call, which becomes the first parameter to the generator.
  var code = func.call(block, block);
  if (Array.isArray(code)) {
    // Value blocks return tuples of code and operator order.
    return [scrub(block, code[0]), code[1]];
  } else if (typeof code === "string") {
    if (STATEMENT_PREFIX) {
      code = STATEMENT_PREFIX.replace(/%1/g, '\'' + block.id + '\'') +
          code;
    }
    return scrub(block, code);
  } else if (code === null) {
    // Block has handled code generation itself.
    return '';
  } else {
    throw 'Invalid code generated: ' + code;
  }
};

/**
 * Generate code representing the specified value input.
 * @param {!Block} block The block containing the input.
 * @param {string} name The name of the input.
 * @param {number} order The maximum binding strength (minimum order value)
 *     of any operators adjacent to "block".
 * @return {string} Generated code or '' if no blocks are connected or the
 *     specified input does not exist.
 */
export function valueToCode (block, name, order) {
  if (isNaN(order)) {
    throw 'Expecting valid order from block "' + block.type + '".';
  }
  var targetBlock = block.getInputTargetBlock(name);
  if (!targetBlock) {
    return '';
  }
  var tuple = blockToCode(targetBlock);
  if (tuple === '') {
    // Disabled block.
    return '';
  }
  if (!Array.isArray(tuple)) {
    // Value blocks must return code and order of operations info.
    // Statement blocks must only return code.
    throw 'Expecting tuple from value block "' + targetBlock.type + '".';
  }
  var code = tuple[0];
  var innerOrder = tuple[1];
  if (isNaN(innerOrder)) {
    throw 'Expecting valid order from value block "' + targetBlock.type + '".';
  }
  if (code && order <= innerOrder) {
    if (order == innerOrder || (order == 0 || order == 99)) {
      // 0 is the atomic order, 99 is the none order.  No parentheses needed.
      // In all known languages multiple such code blocks are not order
      // sensitive.  In fact in Python ('a' 'b') 'c' would fail.
    } else {
      // The operators outside this code are stonger than the operators
      // inside this code.  To prevent the code from being pulled apart,
      // wrap the code in parentheses.
      // Technically, this should be handled on a language-by-language basis.
      // However all known (sane) languages use parentheses for grouping.
      code = '(' + code + ')';
    }
  }
  return code;
};

/**
 * Generate code representing the statement.  Indent the code.
 * @param {!Block} block The block containing the input.
 * @param {string} name The name of the input.
 * @return {string} Generated code or '' if no blocks are connected.
 */
export function statementToCode (block, name) {
  var targetBlock = block.getInputTargetBlock(name);
  var code = blockToCode(targetBlock);
  if (code === "") {
	return code;
  }
  if (!Array.isArray(code) || (code.length === 2 && typeof code[1] === "number")) {
    // Value blocks must return code and order of operations info.
    // Statement blocks must only return code.
    throw 'Expecting code from statement block "' + targetBlock.type + '".';
  }
  if (code) {
    code = makeSequence(code);
  }
  return code;
};

/**
 * Common tasks for generating Python from blocks.
 * Handles comments for the specified block and any connected value blocks.
 * Calls any statements following this block.
 * @param {!Block} block The current block.
 * @param {string} code The Python code created for this block.
 * @return {string} Python code with comments and subsequent blocks added.
 * @private
 */
export function scrub (block, code) {
  var commentCode = '';
  // Only collect comments for blocks that aren't inline.
  if (!block.outputConnection || !block.outputConnection.targetConnection) {
    // Collect comment for this block.
    var comment = block.getCommentText();
    if (comment) {
      commentCode += prefixLines(comment, '# ') + '\n';
    }
    // Collect comments for all value arguments.
    // Don't collect comments for nested statements.
    for (var x = 0; x < block.inputList.length; x++) {
      if (block.inputList[x].type == Blockly.INPUT_VALUE) {
        var childBlock = block.inputList[x].connection.targetBlock();
        if (childBlock) {
          var comment = allNestedComments(childBlock);
          if (comment) {
            commentCode += prefixLines(comment, '# ');
          }
        }
      }
    }
  }
  var nextBlock = block.nextConnection && block.nextConnection.targetBlock();
  var nextCode = blockToCode(nextBlock);

  if (block.outputConnection) {
    // Is a value
    return commentCode + code + nextCode;
  } else {
    // Is a statement
    return [commentCode + code].concat(nextCode);
  }
};

/**
 * Prepend a common prefix onto each line of code.
 * @param {string} text The lines of code.
 * @param {string} prefix The common prefix.
 * @return {string} The prefixed lines of code.
 */
export function prefixLines (text, prefix) {
  return prefix + text.replace(/\n(.)/g, '\n' + prefix + '$1');
};

/**
 * Recursively spider a tree of blocks, returning all their comments.
 * @param {!Block} block The block from which to start spidering.
 * @return {string} Concatenated list of comments.
 */
export function allNestedComments (block) {
  var comments = [];
  var blocks = block.getDescendants();
  for (var x = 0; x < blocks.length; x++) {
    var comment = blocks[x].getCommentText();
    if (comment) {
      comments.push(comment);
    }
  }
  // Append an empty string to create a trailing line break when joined.
  if (comments.length) {
    comments.push('');
  }
  return comments.join('\n');
};

/**
 * Add an infinite loop trap to the contents of a loop.
 * If loop is empty, add a statment prefix for the loop block.
 * @param {string} branch Code for loop contents.
 * @param {string} id ID of enclosing block.
 * @return {string} Loop contents, with infinite loop trap added.
 */
export function addLoopTrap (branch, id) {
  if (INFINITE_LOOP_TRAP) {
    branch = INFINITE_LOOP_TRAP.replace(/%1/g, '\'' + id + '\'') + branch;
  }
  if (STATEMENT_PREFIX) {
    branch += prefixLines(STATEMENT_PREFIX.replace(/%1/g,
        '\'' + id + '\''), INDENT);
  }
  return branch;
};
