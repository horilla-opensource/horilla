$(document).ready(function() {
    function available_asset_chart(dataSet) {
        var Asset_available_chart = document.getElementById("assetAvailableChart");
        var availableLeaveChart = new Chart(Asset_available_chart, {
            type: "pie",
            data: {
                labels: dataSet.labels,
                datasets: dataSet.dataset,
            },
        });
    }
    
    function asset_category_chart(dataSet) {
        var Asset_category_chart = document.getElementById("assetCategoryChart");
        var categoryLeaveChart = new Chart(Asset_category_chart, {
            type: "bar",
            data: {
                labels: dataSet.labels,
                datasets: dataSet.dataset,
            },
        });
    }

    $.ajax({
		type: "GET",
		url: "/asset/asset-available-chart",
		dataType: "json",
		success: function (response) {
            console.log("success");
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
            console.log("success");
            asset_category_chart(response);
		},
		error: (error) => {
			console.log("Error", error);
		},
	});

});
