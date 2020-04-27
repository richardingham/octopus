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
 * @fileoverview Utility functions for handling variables and procedure names.
 * Note that variables and procedures share the same name space, meaning that
 * one can't have a variable and a procedure of the same name.
 * @author fraser@google.com (Neil Fraser)
 */
'use strict';

import Blockly from './blockly';
import {inherits, _extend} from './utils';

var Variable = function (name, scope, subScope) {
  this.name_ = "";
  this.display_ = null;
  this.scope_ = scope;
  this.subScope_ = subScope;
  this.type_ = null;
  this.readonly = false;
  this.flags = {};

  // local.subscope::myvar
  // local.subscope::myvar::subobj.subsubobj
  this.setName(name);
};

// Updates the displayed value in each variable field
Variable.variableRenamed_ = function (oldName, newName, variable) {
  var block, blocks = Blockly.mainWorkspace.getAllBlocks();
  for (var i = 0, max = blocks.length; i < max; i++) {
    block = blocks[i];
    if (block.renameVar) {
      block.renameVar(oldName, newName, variable);
    }
  }
};

// Sends var rename event back to server for each block referencing a var
Variable.announceRenamed = function (name) {
  var block, blocks = Blockly.mainWorkspace.getAllBlocks();
  for (var i = 0, max = blocks.length; i < max; i++) {
    block = blocks[i];
    if (block.announceRename) {
      block.announceRename(name);
    }
  }
};

Variable.prototype.getScopeName_ = function () {
  return this.scope_.getName() + (this.subScope_ ? "." + this.subScope_ : "");
};

Variable.prototype.getName = function () {
  return this.name_;
};

Variable.prototype.setName = function (name) {
  var oldName = this.name_;
  var varName, attribute = this.attribute_, split;
  name = name.toLowerCase();     // TODO: Allow upper case in names, but do lower case comparisons.
  // TODO: make sure there are no "::" in name!!

  // Check that there is a namespace. This assumes that no-one will try
  // to set a name with attributes without also specifying the namespace.
  if (name.indexOf('::') < 0) {
    varName = name;
    split = [
      this.getScopeName_(),
      name
    ]
    if (attribute) {
      split.push(attribute);
    }
    name = split.join('::');
  } else {
    split = name.split('::');
    varName = split[1];
    if (split.length === 3) {
      attribute = split[2];
    }
  }

  if (varName === "") {
    varName = "_";
    split[1] = varName;
    name = split.join('::');
  }

  if (name === this.name_) {
    return;
  }

  if (!this.scope_.isAvailableName(varName, attribute)) {
    varName = this.scope_.validName(varName, this.varName_);
    name = this.getScopeName_() + '::' + varName;
    if (attribute) {
      name += "::" + attribute;
    }
    split[1] = varName;
  }

  this.name_ = name;
  this.varName_ = varName;
  this.attribute_ = attribute;

  if (this.attributeScope_) {
    this.attributeScope_.setTopName(varName);
  }

  split.length = 3;
  this.split_ = split;

  Variable.variableRenamed_(oldName, name, this);

  return name;
};

Variable.prototype.splitName_ = function () {
  return this.split_;
};

Variable.prototype.getNamespace = function () {
  return this.split_[0];
};

Variable.prototype.getVarName = function () {
  return this.varName_;
};

Variable.prototype.getVarAttribute = function () {
  return this.split_[2];
};

Variable.prototype.setMenu = function (name) {
  this.menu_ = name;
};

Variable.prototype.setDisplay = function (name) {
  this.display_ = name;
};

Variable.prototype.setReadonly = function (readonly) {
  this.readonly = readonly;
};

Variable.prototype.setType = function (type) {
  this.type_ = type;
};

Variable.prototype.getType = function () {
  return this.type_;
};

Variable.prototype.addAttribute = function (name) {
  if (!this.attributeScope_) {
    this.attributeScope_ = new VariableSubScope(this.scope_);
  }
  name = this.name_ + (this.split_[2] ? '.' : '::') + name;
  var variable = this.attributeScope_.addVariable(name, this.subScope_);
  return variable;
};

Variable.prototype.getAttribute = function (attributeName) {
  return this.attributeScope_ && this.attributeScope_.getVariable(attributeName);
};

Variable.prototype.getAttributes = function () {
  return this.attributeScope_ ? this.attributeScope_.getVariables() : [];
};

Variable.prototype.clearAttributes = function () {
  this.attributeScope_ && this.attributeScope_.removeAllVariables();
};

Variable.prototype.getNamespacedName = function () {
  return this.splitName_().slice(0, 2).join('::');
};

Variable.prototype.getDisplay = function () {
  var split_ns = this.split_[0].split(".");
  var name = (this.scope_.global_ ? split_ns[1] + " " : "") + this.varName_;
  return (this.display_ ? name + this.display_ : name);
};

Variable.prototype.getMenu = function () {
  var split_ns = this.split_[0].split(".");
  if (this.menu_) {
    return this.menu_;
  }
  return (this.scope_.global_ ? split_ns[1] + " " : "") + this.varName_;
};

Variable.prototype.getScope = function () {
  return this.scope_;
};


var VariableScope = function (block) {
  if (block === "global") {
    this.global_ = true;
    this.block_ = null;
    this.namespace_ = 'global';
  } else {
    this.global_ = false;
    this.block_ = block;
    this.namespace_ = 'local.' + block.id;
  }

  this.variables_ = [];
};

VariableScope.prototype.isGlobal = function () {
  return this.global_;
};

VariableScope.prototype.getName = function () {
  return this.namespace_;
};

/**
 * Create a variable within this scope.
 * @param {string} name  Name for variable (optional). If no name is provided, one is generated.
 * @return {Variable} New variable.
 */
VariableScope.prototype.addVariable = function (name, subScope) {
  if (typeof name === "undefined" || name === "") {
    name = this.generateUniqueName();
  }
  var variable = new Variable(name, this, subScope);
  this.variables_.push(variable);
  return variable;
};

/**
 * Delete a variable from this scope.
 * @param {string} name  Name of variable.
 */
VariableScope.prototype.removeVariable = function (name) {
  var v = this.variables_;
  for (var i = 0; i < v.length; i++) {
    if (v[i].varName_ === name) {
      v.splice(i, 1);
      i--;
    }
  }
};

/**
 * Delete all variables from this scope.
 */
VariableScope.prototype.removeAllVariables = function () {
  this.variables_ = [];
};

/**
 * Return variable defined in this scope with the desired name.
 * @return {Variable | null} The variable.
 */
VariableScope.prototype.getVariable = function (name, attribute) {
  var v = this.variables_;
  for (var i = 0; i < v.length; i++) {
    if (v[i].varName_ === name) {
      if (attribute) {
        return v[i].getAttribute(attribute);
      } else {
        return v[i];
      }
    }
  }
  return null;
};

/**
 * Return all variables defined in this scope.
 * @return {!Array.<Variable>} Array of variables.
 */
VariableScope.prototype.getVariables = function () {
  return this.variables_;
};

/**
 * Return all variables defined in this scope.
 * @return {!Array.<Variable>} Array of variables.
 */
VariableScope.prototype.getVariableNames = function () {
  return this.variables_.map(function (v) { return v.getVarName() });
};

/**
 * Return all variables defined in this scope.
 * @return {!Array.<Variable>} Array of variables.
 */
VariableScope.prototype.isAvailableName = function (name) {
  return (this.getNamesInScope().indexOf(name) === -1);
};

/**
 * Return all variables defined in this scope.
 * @return {!Array.<Variable>} Array of variables.
 */
VariableScope.prototype.getNamesInScope = function () {
  if (this.global_) {
    return GlobalScope.getVariableNames();
  }
  return this.getVariablesInScope().concat(
    this.getVariablesInChildScopes()
  ).map(function (v) { return v.getVarName() });
};

/**
 * Find a variable with the given name in the available scopes.
 * @return {Variable} The variable.
 */
VariableScope.prototype.getScopedVariable = function (name) {
  var split = name.split('::');
  if (this.global_ || (split.length > 1 && split[0].substr(0, 6) === "global")) {
    return GlobalScope.getVariable(split[1], split[2]);
  } else if (!this.block_) {
    return;
  } else {
    name = split[+(split.length > 1)];

    var attribute = split[2],
      variable = this.getVariable(name, attribute),
      scope,
      block = this.block_.getSurroundParent();

    if (variable) {
      return variable;
    }

    while (block) {
      scope = block.getVariableScope(true);
      if (scope) {
        variable = this.getVariable(name, attribute);
        if (variable) {
          return variable;
        }
      }
      block = block.getSurroundParent();
    }
  }
};

VariableScope.prototype.flattenScopedVariableArray_ = function (array) {
  var index = -1,
      length = array ? array.length : 0,
      result = [],
      seen = [],
      extra = 0;

  while (++index < length) {
    var value = array[index];

    var val, name, valIndex = -1,
        valLength = value.length,
        resIndex = result.length - extra;

    result.length += valLength;
    seen.length += valLength;
    while (++valIndex < valLength) {
      val = value[valIndex];
      name = val.getVarName();
      if (seen.indexOf(name) === -1) {
        result[resIndex] = val;
        seen[resIndex++] = name;
      } else {
        extra++;
      }
    }
  }

  result.length -= extra;
  return result;
}

/**
 * Return all variables that are in scope for blocks within this one.
 * @return {!Array.<Variable>} The variables.
 */
VariableScope.prototype.getVariablesInScope = function () {
  if (this.global_) {
    return [];
  }

  var scope, scopes = [],
      variables,
      block = this.block_;

  do {
    scope = block.getVariableScope(true);
    if (scope) {
      scopes.push(scope.getVariables());
    }
    block = block.getSurroundParent();
  } while (block);

  variables = this.flattenScopedVariableArray_(scopes);

  return variables;
};

/**
 * Return all variables that defined in blocks within this one.
 * @return {!Array.<Variable>} The variables.
 */
VariableScope.prototype.getVariablesInChildScopes = function () {
  var blocks = [], variables = [];
  if (typeof this.block_.blocksInScope === 'function') {
    blocks = this.block_.blocksInScope();
  }

  var scope, block, scopeVars;

  for (var i = 0; i < blocks.length; i++) {
    block = blocks[i];
  if (block.childBlocks_.length) {
    Array.prototype.push.apply(blocks, block.childBlocks_);
  }
  scope = block.getVariableScope(true);
    if (scope) {
    scopeVars = scope.getVariables();
    for (var j = 0; j < scopeVars.length; j++) {
    variables.push(scopeVars[i]);
    }
  }
  }

  return variables;
};

/**
* Return a new variable name that is not yet being used in this scope. This will try to
* generate single letter variable names in the range 'i' to 'z' to start with.
* If no unique name is located it will try 'i1' to 'z1', then 'i2' to 'z2' etc.
* @return {string} New variable name.
*/
VariableScope.prototype.generateUniqueName = function () {
  var variableList = this.getVariableNames();
  var newName = '';
  if (variableList.length) {
    variableList.sort(goog.string.caseInsensitiveCompare);
    var nameSuffix = 0, potName = 'i', i = 0, inUse = false;
    while (!newName) {
      i = 0;
      inUse = false;
      while (i < variableList.length && !inUse) {
        if (variableList[i].toLowerCase() == potName) {
          // This potential name is already used.
          inUse = true;
        }
        i++;
      }
      if (inUse) {
        // Try the next potential name.
        if (potName[0] === 'z') {
          // Reached the end of the character sequence so back to 'a' but with
          // a new suffix.
          nameSuffix++;
          potName = 'a';
        } else {
          potName = String.fromCharCode(potName.charCodeAt(0) + 1);
          if (potName[0] == 'l') {
            // Avoid using variable 'l' because of ambiguity with '1'.
            potName = String.fromCharCode(potName.charCodeAt(0) + 1);
          }
        }
        if (nameSuffix > 0) {
          potName += nameSuffix;
        }
      } else {
        // We can use the current potential name.
        newName = potName;
      }
    }
  } else {
    newName = 'i';
  }
  return newName;
};

var prefixSuffix = function(name) {
  var prefix = name;
  var suffix = "";
  var matchResult = name.match(/^(.*?)(\d+)$/);
  if (matchResult)
    return [matchResult[1], matchResult[2]]; // List of prefix and suffix
  else
    return [name, ""];
};

/**
 * Possibly add a digit to name to distinguish it from names in list.
 * Used to guarantee that two names aren't the same in situations that prohibit this.
 * @param {string} name Proposed name.
 * @param {string} currentName If the variable is being renamed, current name.
 * @return {string} Non-colliding name.
 */
VariableScope.prototype.validName = function (name, currentName) {
  // First find the nonempty digit suffixes of all names in nameList that have the same prefix as name
  // e.g. for name "foo3" and nameList = ["foo", "bar4", "foo17", "bar" "foo5"]
  // suffixes is ["17", "5"]
  var nameList = this.getVariableNames();
  var namePrefixSuffix = prefixSuffix(name);
  var namePrefix = namePrefixSuffix[0];
  var nameSuffix = namePrefixSuffix[1];
  var emptySuffixUsed = false; // Tracks whether "" is a suffix.
  var isConflict = false; // Tracks whether nameSuffix is used
  var suffixes = [];
  for (var i = 0; i < nameList.length; i++) {
    if (nameList[i] === currentName) {
      continue;
    }
    var prefixSuffixI = prefixSuffix(nameList[i]);
    var prefix = prefixSuffixI[0];
    var suffix = prefixSuffixI[1];
    if (prefix === namePrefix) {
      if (suffix === nameSuffix) {
        isConflict = true;
      }
      if (suffix === "") {
        emptySuffixUsed = true;
      } else {
        suffixes.push(suffix);
      }
    }
  }
  if (! isConflict) {
    // There is no conflict; just return name
    return name;
  } else if (! emptySuffixUsed) {
    // There is a conflict, but empty suffix not used, so use that
    return namePrefix;
  } else {
    // There is a possible conflict and empty suffix is not an option.
    // First sort the suffixes as numbers from low to high
    var suffixesAsNumbers = suffixes.map( function (elt, i, arr) { return parseInt(elt,10); } )
    suffixesAsNumbers.sort( function(a,b) { return a-b; } );
    // Now find smallest number >= 2 that is unused
    var smallest = 2; // Don't allow 0 or 1 an indices
    var index = 0;
    while (index < suffixesAsNumbers.length) {
      if (smallest < suffixesAsNumbers[index]) {
        return namePrefix + smallest;
      } else if (smallest == suffixesAsNumbers[index]) {
        smallest++;
        index++;
      } else { // smallest is greater; move on to next one
        index++;
      }
    }
    // Only get here if exit loop
    return namePrefix + smallest;
  }
};


var VariableSubScope = function (scope) {
  this.superScope_ = scope.superScope_ ? scope.superScope_ : scope;
  this.variables_ = [];
};
inherits(VariableSubScope, VariableScope);
_extend(VariableSubScope.prototype, {
  isGlobal: function () {
    return this.superScope_.global_;
  },
  getName: function () {
    return this.superScope_.getName();
  },
  getVariable: function (attributeName) {
    // Hopefully this can be cleaned up a bit...
    if (typeof attributeName === "string") {
      attributeName = attributeName.split('.');
    }
    var firstName = attributeName.shift();
    var variable, variables = this.variables_;
    if (attributeName.length) {
      attributeName[0] = firstName + "." + attributeName[0];
    }
    for (var i = 0; i < variables.length; i++) {
      variable = variables[i];
      if (variable.attribute_ === firstName) {
        if (attributeName.length) {
          if (variable.attributeScope_) {
            return variable.attributeScope_.getVariable(attributeName);
          } else {
            return null;
          }
        } else {
          return variable;
        }
      }
    }
    return null;
  },
  getNamesInScope: VariableScope.prototype.getVariableNames,
  getScopedVariable: VariableScope.prototype.getVariable,
  getVariablesInScope: VariableScope.prototype.getVariables,
  getVariablesInChildScopes: function () {
    return [];
  },
  isAvailableName: function (name, attribute) {
    return (this.getNamesInScope().indexOf(attribute) === -1);
  },
  setTopName: function (name) {
    var v = this.variables_;
    for (var i = 0; i < v.length; i++) {
      v[i].setName(name);
    }
  }
});


var GlobalScope = new VariableScope("global", "global");

GlobalScope.addVariable = function (name, type) {
  if (typeof type !== "string" || type === "") {
    type = "global";
  }
  return VariableScope.prototype.addVariable.call(this, name, type);
};

export {Variable, VariableScope, GlobalScope};
