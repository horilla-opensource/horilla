$(document).ready(function () {
	$("#pipelineSearch").keyup(function (e) {
		e.preventDefault();
		var search = $(this).val().toLowerCase();
		$(".candidate-container div.change-cand").each(function () {
			var candidate = $(this).attr("data-candidate");
			if (candidate.toLowerCase().includes(search)) {
				$(this).show();
			} else {
				$(this).hide();
			}
			let stageId = $(this).parent().attr("data-stage-id");
			var count = $(this).parent().find(".candidate:visible").length;
			badge = $(`#stageCount${stageId}`).html(count);
			$(`#stageCount${stageId}`).attr("title",`${count} candidates`)
		});
	});
	function count_element () {
		let stage = $(".recruitment_items")
		let count = $(".stage_count")
		let nos = []
		for(i=0;i<stage.length;i++){
			nos.push($(stage[i]).find("[data-candidate]:visible").length)
		}

		$.each(nos, function(index, value1) {
			var value2 = count[index];
			console.log(value2);
			$(value2).text(value1);
			$(value2).attr('title',`${value1} candidates`)
		});
	}

	function job_Position (){
		let search = $("#job_pos_id").val().toLowerCase()
		if (search != "") {
			job = $("[data-job-position]:visible")
			job.each(function () {
				var candidate = $(this).attr("data-job-position");
				if (candidate.toLowerCase().includes(search)) {
					$(this).show();
				} else {
					$(this).hide();
				}
			});
		}

	}

	$("#filter_item").on("click",function(){
		var candidate = $("[data-job-position]");
		candidate.each(function () { 
				$(this).show();
		})
		$(".pipeline_items").each(function () {
			$(this).removeClass("d-none");
		});
		job_Position();
		count_element();

	})
	$(".oh-tabs__tab").on("click",function (){
		$(".pipeline_items").each(function () {
			$(this).removeClass("d-none");
		});
		job_Position();
		count_element();
	})
	
});
