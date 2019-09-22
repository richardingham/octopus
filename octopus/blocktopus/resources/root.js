
jQuery(function ($) {
  $('#stored table').DataTable({
    order: [[1, 'desc']],
    columns: [
      null,
      null,
      { orderable: false }
    ]
  });

  var past_filters = [];
  $('#past table').DataTable({
    order: [[ 1, 'desc']],
    dom: "<'row'<'col-sm-12'tr>><'row'<'col-sm-6'i><'col-sm-6'p>>",
    serverSide: true,
    "ajax": function (data, callback, settings) {
      $.ajax('/experiments.json', {
        data: {
          draw: data.draw,
          start: data.start,
          length: data.length,
          sort: JSON.stringify($.map(data.order, function (order) {
            order.column = data.columns[order.column].data;
            return order;
          })),
          filter: function () {
            var guid_filter = [];
            if (selected) {
                guid_filter.push({ column: 'sketch_guid', value: $(selected).data('guid') });
            }
            return JSON.stringify(past_filters.concat(guid_filter));
          }()
        },
        dataType: 'json',
        success: function (result) {
          for (i = 0, m = result.data.length; i < m; i++) {
              result.data[i].DT_RowData = { 'guid': result.data[i].guid };
          }
          callback(result);
        },
        error: function (error, status, e) { console.log(error, status, e); }
      });
    },

    columns: [{
      data: "title",
      name: "title",
      render: function (data, type, row, meta) {
        var expt_url = '/experiment/' + row.guid;
        return '<a href="' + expt_url + '">' + data + '</a>';
      }
    }, {
      data: "finished_date",
      name: "finished_date",
      render: function (data, type, row, meta) {
        return moment(new Date(data * 1000)).format('D MMM YYYY, HH:mm');
      }
    }, {
      data: "duration",
      name: "duration",
      render: function (data, type, row, meta) {
        var result = [];
        var days   = Math.floor(data / 86400);
        data -= days * 86400;

        var hours = Math.floor(data / 3600);
        if (hours > 0) result.push(hours);
        data -= hours * 3600;

        var minutes = Math.floor(data / 60);
        if (minutes > 0) {
          result.push((result.length !== 0 && minutes < 10 ? '0' : '') + minutes);
        }

        var seconds = data - (minutes * 60);
        if (result.length === 0) {
          result.push(seconds + 's');
        } else if (seconds > 0) {
          result.push((seconds < 10 ? '0' : '') + seconds);
        }

        result = result.join(':');
        if (days > 0) {
          return days + 'd ' + result;
        }

        return result;
      }
    }, {
      data: null,
      orderable: false,
      render: function (data, type, row, meta) {
        var download_url = '/experiment/' + row.guid + '/download';
        return '<a class="btn btn-sm btn-default" href="' +
          download_url + '">Download Data</a> ' +
          '<button class="btn btn-sm btn-danger">Delete</button>';
      }
    }]
  });

  // Delete / restore functions
  function deleteRestoreHandler (type) {
    return function () {
      var button = $(this);
      var row = button.parents('tr');
      var url = [type, row.data('guid')];
      var success, errorMsg, buttonText = button.html();

      if (row.is('.deleted')) {
        url.push('restore');
        errorMsg = 'Error restoring ' + type + '.';
        success = function () {
          row.removeClass('deleted');
          button.html('Delete');
        };
      } else {
        url.push('delete');
        errorMsg = 'Error deleting ' + type + '.';
        success = function () {
          row.addClass('deleted');
          button.html('Undo');
        };
      }

      $.ajax(url.join('/'), {
        method: 'POST',
        success: success,
        error: function () {
          alert(errorMsg);
          button.html(buttonText);
        },
        complete: function () {
          button.attr('disabled', false);
        }
      });

      button.empty().append('<i class="fa fa-spin fa-cog">');
      button.attr('disabled', true);
      return false;
    };
  }
  $('#stored table tbody').on('click', 'button.btn-danger', deleteRestoreHandler('sketch'));
  $('#past table tbody').on('click', 'button.btn-danger', deleteRestoreHandler('experiment'));


  var past_dt = $('#past table').DataTable();
  var selected;
  $('#stored tbody').on('click', 'tr', function () {
    $(selected).removeClass('active');
    if (selected === this) {
      selected = '';
    } else {
      selected = this;
      $(this).addClass('active');
    }
    past_dt.draw();
  });

  $('#filter-date-on, #filter-date-before, #filter-date-after').datepicker({
    endDate: '+0d',
    autoclose: true,
    format: 'd M yyyy'
  }).on('change', function () {
    var t = $(this);
    t.siblings("span").find("input[type='checkbox']").prop("checked", true);

    if (t.is('#filter-date-on')) {
      $('#filter-date-before-on, #filter-date-after-on').prop('checked', false);
    } else {
      $('#filter-date-on-on').prop('checked', false);
    }
  });

  $('#filter-text').on('keyup', function () {
    $(this).siblings("span").find("input[type='checkbox']").prop("checked", $(this).val() !== "");
  });

  $('#do-filter').click(function () {
    var filters = [];
    if ($('#filter-text-on').prop('checked')) {
      filters.push({ column: 'title', value: $('#filter-text').val(), operator: 'like' });
    }
    if ($('#filter-date-on-on').prop('checked') && $('#filter-date-on').val() !== '') {
      var date = moment(new Date($('#filter-date-on').val()));
      filters.push({ column: 'finished_date', value: date.startOf('day').unix(), operator: 'gt' });
      filters.push({ column: 'finished_date', value: date.endOf('day').unix(), operator: 'lt' });
    } else {
      if ($('#filter-date-before-on').prop('checked') && $('#filter-date-before').val() !== '') {
        filters.push({ column: 'finished_date', value: moment(new Date($('#filter-date-before').val())).unix(), operator: 'lt' });
      }
      if ($('#filter-date-after-on').prop('checked') && $('#filter-date-after').val() !== '') {
        filters.push({ column: 'finished_date', value: moment(new Date($('#filter-date-after').val())).unix(), operator: 'gt' });
      }
    }
    past_filters = filters;
    past_dt.draw();
    return false;
  });
});
