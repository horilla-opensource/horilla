var originalConfirm = window.confirm;

window.confirm = function(message) {
    // This method is used to launch Horilla confirmation modal
    var event = window.event || {};
    event.preventDefault();

    $('#confirmModal').toggleClass('oh-modal--show');
    // Add event listener to "Confirm" button
    $("#confirmModalBody").html(message)
    var submit = false;
    $('#ok').on('click', function() {
      $('#confirmModal').removeClass('oh-modal--show');
      submit = true;
      // Submit form or follow link, depending on the type of element
      if (event.target.tagName.toLowerCase() === 'form') {
        event.target.submit();
      }
      else if (event.target.tagName.toLowerCase() === 'a') {
        window.location.href = event.target.href;
      }
    });
    // Add event listener to "Cancel" button
    $('#cancel').on('click', function() {
      $('#confirmModal').removeClass('oh-modal--show');
    });
    
  }