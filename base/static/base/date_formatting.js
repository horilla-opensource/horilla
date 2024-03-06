class DateFormattingUtility {
    constructor() {
        // Default date format
        this.dateFormat = 'MMM. D, YYYY';
    }

    setDateFormat(format) {
        // Save the selected format to localStorage
        localStorage.setItem('selectedDateFormat', format);
        this.dateFormat = format;
    }

    getFormattedDate(date) {

        // getCurrentLanguageCode(function (code) {
        //     languageCode = code;
        // });

        // // console.log("CODE>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        // // console.log(languageCode)

        // if (languageCode == 'en'){
        //     // Set locale to English
        //     moment.locale('en');
        // }
        // else if(languageCode == 'de'){
        //     // Set locale to German
        //     moment.locale('de');
        // }
        // else if(languageCode == 'es'){
        //     // Set locale to Spanish
        //     moment.locale('es');
        // }
        // else if(languageCode == 'fr'){
        //     // Set locale to French
        //     moment.locale('fr');
        // }
        // else if(languageCode == 'ar'){
        //     // Set locale to Arabic
        //     moment.locale('ar');
        // }



        // var specificDate = date; // Your specific date in YYYY-MM-DD format
        // var now = moment(specificDate);
        // // console.log('LANGUAGAE DATE')
        // // console.log(now.format('LL')); // Output will be the formatted date for the specific date you provided

        if (localStorage.getItem('selectedDateFormat')){

        }
        else{
            function fetchData(callback) {

                $.ajax({
                    url: '/settings/get-date-format/',
                    method: 'GET',
                    data: { csrfmiddlewaretoken: getCookie('csrftoken') },
                    success: function(response) {
                        var date_format = response.selected_format;

                        // Call the callback function and pass the value of 'date_format'
                        callback(date_format);
                    },
                });
            }

            // Use the fetchData function with a callback
            fetchData(function(date_format) {

                // If any date format is found setting it to the local storage.
                if(date_format){
                    localStorage.setItem('selectedDateFormat', date_format);

                }
                // Setting a default date format MMM. D, YYYY
                else{
                    localStorage.setItem('selectedDateFormat', 'MMM. D, YYYY');
                }
            });

        }
        // Use the stored date format
        const storedDateFormat = localStorage.getItem('selectedDateFormat') || 'MMM. D, YYYY';


        // Preprocess the date string based on the selected format
        let processedDate = date;
        if (storedDateFormat === 'DD-MM-YYYY') {
            processedDate = date.replace(/(\d{2})-(\d{2})-(\d{4})/, '$3-$2-$1');
        } else if (storedDateFormat === 'DD.MM.YYYY') {
            processedDate = date.replace(/(\d{2})\.(\d{2})\.(\d{4})/, '$3-$2-$1');
        } else if (storedDateFormat === 'DD/MM/YYYY') {
            processedDate = date.replace(/(\d{2})\/(\d{2})\/(\d{4})/, '$3-$2-$1');
        }

        // Format the processed date using moment.js
        const formattedDate = moment(processedDate).format(storedDateFormat);

        return formattedDate;
    }


}

// Create an instance of the utility
const dateFormatter = new DateFormattingUtility();

// Retrieve the selected date format from localStorage
const storedDateFormat = localStorage.getItem('selectedDateFormat');

if (storedDateFormat) {
    // If a date format is stored, set it in the utility
    dateFormatter.setDateFormat(storedDateFormat);
}
