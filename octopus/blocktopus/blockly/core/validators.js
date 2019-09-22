
'use strict';

export function numberValidator(text, integer, nonnegative) {
  // TODO: Handle cases like 'ten', '1.203,14', etc.
  // 'O' is sometimes mistaken for '0' by inexperienced users.
  text = text.replace(/O/ig, '0');
  // Strip out thousands separators.
  text = text.replace(/,/g, '');

  var n = parseFloat(text);
  if (isNaN(n)) return null;

  if (nonnegative) {
    n = Math.max(0, n);
  }

  if (integer) {
    return String(Math.floor(n));
  } else {
    var s = String(n);
    if (s.indexOf('.') === -1 && text.indexOf('.') !== -1 && parseInt(text || 0) === n) {
      return s + '.0';
    }
    return s;
  }
}
