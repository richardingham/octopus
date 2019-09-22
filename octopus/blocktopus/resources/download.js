
jQuery(function ($) {
  var checkboxes = $('<div>').hide().appendTo($('form'));
  $('#variables-list tbody input[type=checkbox]').appendTo(checkboxes);

  $('[data-toggle="tooltip"]').each(function () {
    this._tooltip = new Tooltip(this, { placement: 'top' });
  });

  $('#variables-list').DataTable({
    order: [[1, 'asc']],
    paging: false,
    autoWidth: false,
    columns: [
      { visible: false, orderable: false },
      null,
      null,
      null
    ]
  });

  var dt = $('#variables-list').DataTable();
  $('<button class="btn btn-default">Clear</button>')
    .appendTo('#variables-list_filter')
    .on('click', function () {
      dt.search('');
      dt.draw();
      return false;
    });
  $('<button class="btn btn-default">Select filtered</button>')
    .appendTo('#variables-list_filter')
    .on('click', generateToggleAllStatesFunction(true));
  $('<button class="btn btn-default">Deselect filtered</button>')
    .appendTo('#variables-list_filter')
    .on('click', generateToggleAllStatesFunction(false));

  $('#variables-list tbody').on('click', 'tr', function () {
    toggleSelectedState(this);
    setSubmitButtonState();
  });

  function generateToggleAllStatesFunction (state) {
    return function () {
      $('#variables-list tbody tr').each(function () {
        toggleSelectedState(this, state);
      });
      setSubmitButtonState();
      return false;
    };
  }

  function toggleSelectedState (tr, state) {
    $(tr).toggleClass('active', state);
    $('input[value="' + $(tr).data('key') + '"]', checkboxes)
      .attr('checked', $(tr).is('.active'));
  }

  // Disable submit button initially.
  function setSubmitButtonState () {
    var selectedVars = $('input[checked]', checkboxes).length;
    var button = $('form .buttons button[type="submit"]');
    var tooltipElement = button.parent('.tooltip-wrapper');

    button.attr('disabled', selectedVars === 0);

    if (selectedVars === 0) {
      tooltipElement.data('tooltip', new Tooltip(tooltipElement, {
        title: 'Select some data variables to continue',
        placement: 'right'
      }));
    } else {
      tooltipElement.data('tooltip').dispose();
    }
  }

  setSubmitButtonState();
});
