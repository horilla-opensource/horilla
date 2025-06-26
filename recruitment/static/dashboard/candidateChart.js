$(document).ready(function () {
    let myChart; // Declare myChart globally to access it outside the scope

    // Load image only once
    const centerImage = new Image();
    centerImage.src = "/static/horilla_theme/assets/img/icons/gender.svg"; // Adjust path as needed

    function candidateChart(dataSet, labels) {
        const data = {
            labels: labels,
            datasets: [{
                data: dataSet.map(item => item.data),
                backgroundColor: ['#C6BEC4', '#FFF255', '#55C4FF', '#FF4646', '#2AFF0C'],
                borderWidth: 0, // Match the original design
            }]
        };

        const ctx = document.getElementById('candidateChart').getContext('2d');
        myChart = new Chart(ctx, {
            type: 'doughnut', // Changed from pie to doughnut to match original
            data: data,
            options: {
                cutout: "70%", // Match the original cutout percentage
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 20,
                            font: {
                                size: 12,
                            },
                            color: "#000",
                        },
                    },
                },
                onClick: handleClick // Retain click handler
            },
            plugins: [{
                id: "centerIcon",
                afterDatasetDraw(chart) {
                    if (!centerImage.complete) return; // Wait till image is loaded
                    const ctx = chart.ctx;
                    const size = 70;
                    ctx.drawImage(
                        centerImage,
                        chart.width / 2 - size / 2,
                        chart.height / 2 - size / 2 - 20,
                        size,
                        size
                    );
                },
            }],
        });
    }

    function handleClick(event, chartElements) {
        if (chartElements.length > 0) {
            const index = chartElements[0].index;
            let url;
            if (index === 0) {
                url = '/recruitment/candidate-view?offer_letter_status=not_sent';
            } else if (index === 1) {
                url = '/recruitment/candidate-view?offer_letter_status=sent';
            } else if (index === 2) {
                url = '/recruitment/candidate-view?offer_letter_status=accepted';
            } else if (index === 3) {
                url = '/recruitment/candidate-view?offer_letter_status=rejected';
            } else {
                url = '/recruitment/candidate-view?offer_letter_status=joined';
            }
            window.location.href = url;
        }
    }

    $.ajax({
        url: "/recruitment/candidate-status",
        type: "GET",
        success: function (response) {
            dataSet = response.dataSet;
            labels = response.labels;
            candidateChart(dataSet, labels);
        },
    });
});

// $(document).ready(function(){
//     let myChart; // Declare myChart globally to access it outside the scope

//     function candidateChart(dataSet, labels){
//         const data = {
//             labels: labels,
//             datasets: [{
//                 data: dataSet.map(item => item.data),
//                 backgroundColor: ['#C6BEC4', '#FFF255', '#55C4FF', '#FF4646', '#2AFF0C']
//             }]
//         };

//         const ctx = document.getElementById('candidateChart').getContext('2d');
//         myChart = new Chart(ctx, {
//             type: 'pie',
//             data: data,
//             options: {
//                 onClick: handleClick // Attach onClick event handler
//             }
//         });
//     }

//     function handleClick(event, chartElements) {
//         if (chartElements.length > 0) {
//             // Get the index of the clicked element
//             const index = chartElements[0].index;

//             if(index === 0){
//                 // Assuming each data point corresponds to a URL
//                 url = '/recruitment/candidate-view?offer_letter_status=not_sent'
//             }else if(index === 1){

//                 url = '/recruitment/candidate-view?offer_letter_status=sent'
//             }else if(index === 2){

//                 url = '/recruitment/candidate-view?offer_letter_status=accepted'
//             }else if(index === 3){

//                 url = '/recruitment/candidate-view?offer_letter_status=rejected'
//             }else{

//                 url = '/recruitment/candidate-view?offer_letter_status=joined'
//             }
//             // Redirect to the corresponding URL
//             window.location.href = url;
//         }
//     }

//     $.ajax({
//         url: "/recruitment/candidate-status",
//         type: "GET",
//         success: function(response){
//             dataSet = response.dataSet;
//             labels = response.labels;
//             candidateChart(dataSet, labels);
//         },
//     });

// });
