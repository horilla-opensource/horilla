$(document).ready(function () {
  //Hired candididates recruitment wise chart
  $.ajax({
    type: "GET",
    url: "/onboarding/hired-candidate-chart",
    success: function (response) {
      const ctx = document.getElementById("hiredCandidate");
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: response.labels,
          datasets: [
            {
              label: "#Hired candidates",
              data: response.data,
              backgroundColor: response.background_color,
              borderColor: response.border_color,
              borderWidth: 1,
            },
          ],
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
            },
          },
          onClick: (e, activeEls) => {
            let datasetIndex = activeEls[0].datasetIndex;
            let dataIndex = activeEls[0].index;
            let datasetLabel = e.chart.data.datasets[datasetIndex].label;
            let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
            let label = e.chart.data.labels[dataIndex];
            localStorage.removeItem("savedFilters");
            window.location.href =
              "/recruitment/candidate-view" +
              "?recruitment=" +
              label +
              "&hired=true";
          },
        },
      });
    },
  });

  //onboarding started candidate chart
  $.ajax({
    type: "GET",
    url: "/onboarding/onboard-candidate-chart",
    success: function (response) {
      const ctx = document.getElementById("onboardCandidate");
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: response.labels,
          datasets: [
            {
              label: "#onboarding candidates",
              data: response.data,
              backgroundColor: response.background_color,
              borderColor: response.border_color,
              borderWidth: 1,
            },
          ],
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
            },
          },
          onClick: (e, activeEls) => {
            let datasetIndex = activeEls[0].datasetIndex;
            let dataIndex = activeEls[0].index;
            let datasetLabel = e.chart.data.datasets[datasetIndex].label;
            let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
            let label = e.chart.data.labels[dataIndex];
            localStorage.removeItem("savedFilters");
            window.location.href =
              "/recruitment/candidate-view" +
              "?recruitment=" +
              label +
              "&start_onboard=true";
          },
        },
      });
    },
  });
});
