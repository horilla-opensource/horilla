

const objectiveChart = document.getElementById('objectiveChart');
console.log('--------------------------------');
console.log(objectiveChart);
console.log('--------------------------------');
// data dictionary 
var objectiveStatusData = {
    labels: [],
    datasets: [{
        label: '',
        data: [],
        backgroundColor: [  '#8de5b3',  '#f0a8a6',  '#8ed1f7',  '#f8e08e',  '#c2c7cc'],
        hoverOffset: 3
    }]
};


// chart constructor
if (objectiveChart != null) {
    var objectiveStatusChart = new Chart(objectiveChart, {
        type: "doughnut",
        data: objectiveStatusData,
    });
}

function objectiveStatusDataUpdate(data){
    objectiveStatusData.labels = data.objective_label
    objectiveStatusData.datasets[0].data = data.objective_value
    objectiveStatusChart.update()
}

$.ajax({
    url: '/pms/dashboard-objective-status',
    type: "GET",
    dataType: "json",
    headers: {
        "X-Requested-With": "XMLHttpRequest",
    },
    success: (response) => {
        objectiveStatusDataUpdate(response)
        
    },
    error: (error) => {
        console.log('Error', error);
    }
});


// chart change
$('#objective-status-chart').click(function (e) { 
    var chartType = objectiveStatusChart.config.type
    if (chartType === 'line') {
        chartType = 'bar';
    } else if(chartType==='bar') {
        chartType = 'doughnut';
    } else if(chartType==='doughnut'){
        chartType = 'pie'
    }else if(chartType==='pie'){
        chartType = 'line'
    }
    objectiveStatusChart.config.type = chartType;
    objectiveStatusChart.update();
    
})

// objecitve chart section end

const keyResultStatusChartCtx = document.getElementById('keyResultChart');

// data dictionary 
var keyResultStatusData = {
    labels: [],
    datasets: [{
        label: '',
        data: [],
        backgroundColor: [  '#8de5b3',  '#f0a8a6',  '#8ed1f7',  '#f8e08e',  '#c2c7cc'],
        hoverOffset: 3
    }]
};

// chart constructor
if (keyResultStatusChartCtx != null) {
    var keyResultStatusChart = new Chart(keyResultStatusChartCtx, {
        type: "pie",
        data: keyResultStatusData,
    });
}

function keyResultStatusDataUpdate(data){
    keyResultStatusData.labels = data.key_result_label
    keyResultStatusData.datasets[0].data = data.key_result_value
    keyResultStatusChart.update()
}

$.ajax({
    url: '/pms/dashbord-key-result-status',
    type: "GET",
    dataType: "json",
    headers: {
        "X-Requested-With": "XMLHttpRequest",
    },
    success: (response) => {
        keyResultStatusDataUpdate(response)
    },
    error: (error) => {
        console.log('Error', error);
    }
});


// chart change
$('#key-result-status-chart').click(function (e) { 
    var chartType = keyResultStatusChart.config.type
    if (chartType === 'line') {
        chartType = 'bar';
    } else if(chartType==='bar') {
        chartType = 'doughnut';
    } else if(chartType==='doughnut'){
        chartType = 'pie'
    }else if(chartType==='pie'){
        chartType = 'line'
    }
    keyResultStatusChart.config.type = chartType;
    keyResultStatusChart.update();
    
})

// key result chart section 

const feedbackStatusChartCtx = document.getElementById('feedbackChart');


// data dictionary 
var feedbackStatusData = {
    labels: [],
    datasets: [{
        label: 'Feedback',
        data: [],
        backgroundColor: [  '#8de5b3',  '#f0a8a6',  '#8ed1f7',  '#f8e08e',  '#c2c7cc'],
        hoverOffset: 3
    }]
};

// chart constructor
if (feedbackStatusChartCtx != null) {
    var feedbackStatusChart = new Chart(feedbackStatusChartCtx, {
        type: "pie",
        data: feedbackStatusData,
    });
}
    
function feedbackStatusDataUpdate(data){
    feedbackStatusData.labels = data.feedback_label
    feedbackStatusData.datasets[0].data = data.feedback_value
    feedbackStatusChart.update()
}

$.ajax({
    url: '/pms/dashboard-feedback-status',
    type: "GET",
    dataType: "json",
    headers: {
        "X-Requested-With": "XMLHttpRequest",
    },
    success: (response) => {
        feedbackStatusDataUpdate(response)
    },
    error: (error) => {
        console.log('Error', error);
    }
});


// chart change
$('#feedback-status-chart').click(function (e) { 
    var chartType = feedbackStatusChart.config.type
    if (chartType === 'line') {
        chartType = 'bar';
    } else if(chartType==='bar') {
        chartType = 'doughnut';
    } else if(chartType==='doughnut'){
        chartType = 'pie'
    }else if(chartType==='pie'){
        chartType = 'line'
    }
    feedbackStatusChart.config.type = chartType;
    feedbackStatusChart.update();
    
})


