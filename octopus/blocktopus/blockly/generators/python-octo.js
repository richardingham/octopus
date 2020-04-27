/**
 * @license
 * MIT
 */

'use strict';

import Names from '../core/names';
import {addReservedWords, initDefinitions, getDefinitions, blockToCode, makeSequence, scrubNakedValue} from './python-octo-methods';

// import keyword
// print ','.join(keyword.kwlist)
addReservedWords(
  // http://docs.python.org/reference/lexical_analysis.html#keywords
  'and,as,assert,break,class,continue,def,del,elif,else,except,exec,finally,for,from,global,if,import,in,is,lambda,not,or,pass,print,raise,return,try,while,with,yield,' +
  //http://docs.python.org/library/constants.html
  'True,False,None,NotImplemented,Ellipsis,__debug__,quit,exit,copyright,license,credits,' +
  // http://docs.python.org/library/functions.html
  'abs,divmod,input,open,staticmethod,all,enumerate,int,ord,str,any,eval,isinstance,pow,sum,basestring,execfile,issubclass,print,super,bin,file,iter,property,tuple,bool,filter,len,range,type,bytearray,float,list,raw_input,unichr,callable,format,locals,reduce,unicode,chr,frozenset,long,reload,vars,classmethod,getattr,map,repr,xrange,cmp,globals,max,reversed,zip,compile,hasattr,memoryview,round,__import__,complex,hash,min,set,apply,delattr,help,next,setattr,buffer,dict,hex,object,slice,coerce,dir,id,oct,sorted,intern'
);

/**
 * Prepend the generated code with the variable definitions.
 * @param {string} code Generated code.
 * @return {string} Completed code.
 */
function finish (code) {
  // Convert the definitions dictionary into a list.
  var imports = [];
  var contextDefinitions = getDefinitions();
  var definitions = [];
  //var machines = [];
  for (var name in contextDefinitions) {
    var def = contextDefinitions[name];
    if (def.match && def.match(/^(from\s+\S+\s+)?import\s+\S+/)) {
      imports.push(def);
    } else {
      if (def.join) {
        def = def.join("\n");
      }
      definitions.push(def);
    }
  }
  var allDefs = imports.join('\n') + '\n\n' + definitions.join('\n\n');
  return allDefs.replace(/\n\n+/g, '\n\n').replace(/\n*$/, '\n\n\n') + code;
};

/**
 * Generate code for all blocks in the workspace to the specified language.
 * @return {string} Generated code.
 */
export function workspaceToCode (blocks) {
  var code = [];
  initDefinitions();
  for (var x = 0, block; block = blocks[x]; x++) {
    var line = blockToCode(block);
    if (Array.isArray(line) && line.length === 2 && typeof line[1] === "number") {
      // Value blocks return tuples of code and operator order.
      // Top-level blocks don't care about operator order.
      line = line[0];
    }
    if (line) {
      line = makeSequence(line);
      if (block.outputConnection && scrubNakedValue) {
        // This block is a naked value.  Ask the language's code generator if
        // it wants to append a semicolon, or something.
        line = scrubNakedValue(line);
      }
      code.push(line);
    }
  }
  code = code.join('\n\n');  // Blank line between each section.
  code = finish(code);
  // Final scrubbing of whitespace.
  code = code.replace(/^\s+\n/, '');
  code = code.replace(/\n\s+$/, '\n');
  code = code.replace(/[ \t]+\n/g, '\n');
  return code;
};
