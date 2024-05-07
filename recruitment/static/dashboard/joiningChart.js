$(document).ready(function () {
    function hiringChart(dataSet, labels) {
      const data = {
        labels: labels,
        datasets: dataSet,
      };
      // Create chart using the Chart.js library
      // $("#hiringChart").html("<canvas id='hiring'></canvas>")
      window['myChart1'] = {}
      var ctx = document.getElementById("hiringChart");

      if (ctx != null) {
        ctx = ctx.getContext("2d")
        myChart1 = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: {
          },
        });
      }
    }

    function joining(){
      var year = $("#year").val()

      $.ajax({
        url: "/recruitment/dashboard-hiring",
        type: "GET",
        data: {
          id : year
        },
        success: function (response) {
          dataSet = response.dataSet;
          labels = response.labels;
          hiringChart(dataSet, labels);
        },
      });
    }

    $("#year").on("change", function (e) {
      myChart1.destroy();
      joining()
    });

    joining()

    $('#chart2').click(function (e) {
      var chartType = myChart1.config.type
      if (chartType === 'line') {
        chartType = 'bar';
      } else if(chartType==='bar') {
          chartType = 'line';
      }
      myChart1.config.type = chartType;
      myChart1.update();
    });

  });
