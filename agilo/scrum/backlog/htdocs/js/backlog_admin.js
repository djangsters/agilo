$(function() {
  $('#ticket_types').change(update_fields);
  update_scope();
  $('#scope').change(update_scope);
  $('.preview').hide();
});

function update_fields() {
  $.get('', {'ticket_types':$('#ticket_types').val()}, function(data) {
    var fields = new Object();
    $(data).find('item').each(function() {
      fields[$(this).text()] = 1;
    });
    
    $('#column_table tbody tr').each(function() {
      var $this = $(this);
      if (this.id in fields) {
        /* allowed field, show it and enable all inputs */
        $this.show();
        $this.find('input, select').each(function() {
          $(this).removeAttr('disabled');
        });
      } else {
        /* disallowed field, hide it and disable all inputs */
        $this.hide();
        $this.find('input, select').each(function() {
          $(this).attr('disabled', 'disabled');
        });
      }
    });
  });
}

function update_scope() {
  $('#strict_field .help').hide()
    .filter('.scope_' + $('#scope').val()).show();
}