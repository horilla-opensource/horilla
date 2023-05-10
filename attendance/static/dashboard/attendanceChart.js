$(document).ready(function () {
    function attendanceChart(dataSet, labels) {
      const data = {
        labels: labels,
        datasets: dataSet,
      };
      // Create chart using the Chart.js library
      window['myChart'] = {}
      const ctx = document.getElementById("dailyAnalytic").getContext("2d");
      myChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
        },
      });
    }
      $.ajax({
        url: "/attendance/dashboard-attendance",
        type: "GET",
        success: function (response) {
          // Code to handle the response
          dataSet = response.dataSet;
          labels = response.labels;
    
          attendanceChart(dataSet, labels);
        },
      });
    
      $('.oh-card-dashboard__title').click(function (e) { 
        var chartType = myChart.config.type
        if (chartType === 'line') {
          chartType = 'bar';
        } else if(chartType==='bar') {
            chartType = 'doughnut';
        } else if(chartType==='doughnut'){
          chartType = 'pie'
        }else if(chartType==='pie'){
          chartType = 'line'
        }
        myChart.config.type = chartType;
        myChart.update();    
      });
        
    });
    