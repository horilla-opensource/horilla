staticUrl = $("#statiUrl").attr("data-url");
$(document).ready(function () {
    function available_asset_chart(dataSet) {
        var Asset_available_chart = document.getElementById("assetAvailableChart");
        if (Asset_available_chart) {
            var assetAvailableChartChart = new Chart(Asset_available_chart, {
                type: "pie",
                data: {
                    labels: dataSet.labels,
                    datasets: dataSet.dataset,
                    emptyImageSrc: dataSet.emptyImageSrc,
                    message: dataSet.message,
                },
                plugins: [
                    {
                        afterRender: (assetAvailableChartChart) => emptyAssetAvialabeChart(assetAvailableChartChart),
                    },
                ],
            });
        }
    }

    function asset_category_chart(dataSet) {
        var Asset_category_chart = document.getElementById("assetCategoryChart");
        if (Asset_category_chart) {
            var assetCategoryChart = new Chart(Asset_category_chart, {
                type: "bar",
                data: {
                    labels: dataSet.labels,
                    datasets: dataSet.dataset,
                    emptyImageSrc: dataSet.emptyImageSrc,
                    message: dataSet.message,
                },
                plugins: [
                    {
                        afterRender: (assetCategoryChart) => emptyAssetAvialabeChart(assetCategoryChart),
                    },
                ],
            });
        }
    }

    $.ajax({
        type: "GET",
        url: "/asset/asset-available-chart",
        dataType: "json",
        success: function (response) {
            available_asset_chart(response);
        },
        error: (error) => {
            console.log("Error", error);
        },
    });

    $.ajax({
        type: "GET",
        url: "/asset/asset-category-chart",
        dataType: "json",
        success: function (response) {
            asset_category_chart(response);
        },
        error: (error) => {
            console.log("Error", error);
        },
    });
});

function emptyAssetAvialabeChart(assetAvailableChartChart, args, options) {
    flag = false;
    for (let i = 0; i < assetAvailableChartChart.data.datasets.length; i++) {
        flag = flag + assetAvailableChartChart.data.datasets[i].data.some(Boolean);
    }
    if (!flag) {
        const { ctx, canvas } = assetAvailableChartChart;
        assetAvailableChartChart.clear();
        const parent = canvas.parentElement;

        // Set canvas width/height to match
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
        // Calculate center position
        const x = canvas.width / 2;
        const y = (canvas.height - 70) / 2;
        var noDataImage = new Image();
        noDataImage.src = assetAvailableChartChart.data.emptyImageSrc
            ? assetAvailableChartChart.data.emptyImageSrc
            : staticUrl + "images/ui/joiningchart.png";

        message = assetAvailableChartChart.data.message
            ? assetAvailableChartChart.data.message
            : emptyMessages[languageCode];

        noDataImage.onload = () => {
            // Draw image first at center
            ctx.drawImage(noDataImage, x - 35, y, 70, 70);

            // Draw text below image
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "hsl(0,0%,45%)";
            ctx.font = "16px Poppins";
            ctx.fillText(message, x, y + 70 + 30);
        };
    }
}
