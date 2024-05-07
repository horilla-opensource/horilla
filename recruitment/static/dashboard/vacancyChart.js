$(document).ready(function(){
    function vacancyChart(dataSet, labels){
        const data = {
            labels: labels,
            datasets: dataSet,
        };
        window['mychart2'] = {}
        const ctx = document.getElementById('vacancy')
        mychart2 = new Chart(ctx, {
            type: 'pie',
            data: data
        });
    }

    $.ajax({
        url: "/recruitment/dashboard-vacancy",
        type: "GET",
        success: function(response){
            dataSet = response.dataSet;
            labels = response.labels;
            vacancyChart(dataSet, labels);
        },
    });

})
