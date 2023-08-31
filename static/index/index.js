var originalConfirm = window.confirm;
// Override the default confirm function with SweetAlert
window.confirm = function(message) {
  var event = window.event || {};
  event.preventDefault();
  // Add event listener to "Confirm" button
  $("#confirmModalBody").html(message)
  var submit = false;
  Swal.fire({
    text: message,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#008000',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Confirm',
    cancelButtonText: 'Cancel',
  }).then((result) => {
    if (result.isConfirmed) {
      if (event.target.tagName.toLowerCase() === 'form') {
        event.target.submit();
      }
      else if (event.target.tagName.toLowerCase() === 'a') {
        window.location.href = event.target.href;
      }
    } 
    else {
    }
  });
};
