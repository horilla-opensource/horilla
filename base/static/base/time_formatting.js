class TimeFormattingUtility {
    constructor() {
        // Default time format
        this.timeFormat = 'hh:mm A'; // Default to 12-hour format
    }

    setTimeFormat(format) {
        // Save the selected format to localStorage
        localStorage.setItem('selectedTimeFormat', format);
        this.timeFormat = format;
    }

    getFormattedTime(time) {
        if (localStorage.getItem('selectedTimeFormat')){

        }
        else{
            function fetchData(callback) {

                $.ajax({
                    url: '/settings/get-time-format/',
                    method: 'GET',
                    data: { csrfmiddlewaretoken: getCookie('csrftoken') },
                    success: function(response) {
                        var time_format = response.selected_format;

                        // Call the callback function and pass the value of 'time_format'
                        callback(time_format);
                    },
                });
            }

            // Use the fetchData function with a callback
            fetchData(function(time_format) {

                // If any time format is found setting it to the local storage.
                if(time_format){
                    localStorage.setItem('selectedTimeFormat', time_format);

                }
                // Setting a default time format hh:mm A
                else{
                    localStorage.setItem('selectedTimeFormat', 'hh:mm A');
                }
            });

        }
        // Use the stored time format
        const storedTimeFormat = localStorage.getItem('selectedTimeFormat') || 'hh:mm A';

        // Format the time using moment.js
        const formattedTime = moment(time, 'hh:mm A').format(storedTimeFormat);

        return formattedTime;
    }

    // Additional method for getting formatted time in 12-hour format
    getFormattedTime12Hour(time) {
        return this.getFormattedTime(time).replace(/^(\d{1,2}:\d{2}):\d{2}$/, '$1');
    }
}

// Create an instance of the TimeFormattingUtility
const timeFormatter = new TimeFormattingUtility();

// Retrieve the selected time format from localStorage
const storedTimeFormat = localStorage.getItem('selectedTimeFormat');

if (storedTimeFormat) {
    // If a time format is stored, set it in the utility
    timeFormatter.setTimeFormat(storedTimeFormat);
}
