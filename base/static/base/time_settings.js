function saveTimeFormat() {
    var timeFormatSelector = document.getElementById('timeFormat');
    const selectedTimeFormat = timeFormatSelector.value;

    // Set the selected time format in the utility
    timeFormatter.setTimeFormat(selectedTimeFormat);

    // Save the time format to the backend
    saveTimeFormatToBackend(selectedTimeFormat);
  }

  function saveTimeFormatToBackend(selectedTimeFormat) {
    $.ajax({
      url: '/settings/save-time/',
      method: 'POST',
      data: { 'selected_format': selectedTimeFormat, csrfmiddlewaretoken: getCookie('csrftoken') },
      success: function(response) {
        window.location.reload();
      },
      error: function(xhr, textStatus, errorThrown) {
        // Handle the error here
        console.error('Error:', errorThrown);
        window.location.reload();
      },
    });
  }
