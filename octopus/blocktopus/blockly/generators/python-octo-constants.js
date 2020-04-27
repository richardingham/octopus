
export const GENERATOR_NAME = 'Octopus Python';

/**
 * Order of operation ENUMs.
 * http://docs.python.org/reference/expressions.html#summary
 */
export const ORDER = {
  ATOMIC: 0,            // 0 "" ...
  COLLECTION: 1,        // tuples, lists, dictionaries
  STRING_CONVERSION: 1, // `expression...`
  MEMBER: 2,            // . []
  FUNCTION_CALL: 2,     // ()
  EXPONENTIATION: 3,    // **
  UNARY_SIGN: 4,        // + -
  BITWISE_NOT: 4,       // ~
  MULTIPLICATIVE: 5,    // * / // %
  ADDITIVE: 6,          // + -
  BITWISE_SHIFT: 7,     // << >>
  BITWISE_AND: 8,       // &
  BITWISE_XOR: 9,       // ^
  BITWISE_OR: 10,       // |
  RELATIONAL: 11,       // in, not in, is, is not,
                                                  //     <, <=, >, >=, <>, !=, ==
  LOGICAL_NOT: 12,      // not
  LOGICAL_AND: 13,      // and
  LOGICAL_OR: 14,       // or
  CONDITIONAL: 15,      // if else
  LAMBDA: 16,           // lambda
  NONE: 99,             // (...)
};

/**
 * The method of indenting.  Defaults to two spaces, but language generators
 * may override this to increase indent or change to tabs.
 */
export const INDENT = '  ';

/**
 * This is used as a placeholder in functions defined using
 * Generator.provideFunction_.  It must not be legal code that could
 * legitimately appear in a function definition (or comment), and it must
 * not confuse the regular expression parser.
 * @private
 */
export const FUNCTION_NAME_PLACEHOLDER_ = '{leCUI8hutHZI4480Dc}';
export const FUNCTION_NAME_PLACEHOLDER_REGEXP_ = new RegExp(FUNCTION_NAME_PLACEHOLDER_, 'g');

/**
* Category to separate generated function names from variables and procedures.
*/
export const NAME_TYPE = 'generated_function';

/**
* Arbitrary code to inject into locations that risk causing infinite loops.
* Any instances of '%1' will be replaced by the block ID that failed.
* E.g. '  checkTimeout(%1);\n'
* @type ?string
*/
export const INFINITE_LOOP_TRAP = null;

/**
* Arbitrary code to inject before every statement.
* Any instances of '%1' will be replaced by the block ID of the statement.
* E.g. 'highlight(%1);\n'
* @type ?string
*/
export const STATEMENT_PREFIX = null;
