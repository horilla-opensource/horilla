$(document).ready(function () {

	function count_element () {
		let stage = $(".onboarding_items")
		let count = $(".stage_count")
		let nos = []
		for(i=0;i<stage.length;i++){
			nos.push($(stage[i]).find("[data-candidate]:visible").length)
		}

		$.each(nos, function(index, value1) {
			var value2 = count[index];
			$(value2).text(value1);
		});
	}

	$("#search").keyup(function (e) {
		e.preventDefault();
		let search = $(this).val().toLowerCase();
		$(".onboarding_items").each(function () {
			$(this).removeClass("d-none");
		});
		cands = $("[data-candidate]")
		cands.each(function () {
			var candidate = $(this).attr("data-candidate");
			if (candidate.toLowerCase().includes(search)) {
				$(this).show();
			} else {
				$(this).hide();
			}
		});
		count_element()
	});


	function job_Position (){
		let search = $("#job_position_id").val().toLowerCase()
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
			count_element()
		}

	}

	function join_date (){
		let date = $("#join_date").val()
		if (date != "") {

			var dateObject = new Date(date);
				
			var monthNames = [
				"Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
				"July", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."
			];

			var month = monthNames[dateObject.getMonth()];
			var day = dateObject.getDate();
			var year = dateObject.getFullYear();

			var search = month + " " + day + ", " + year;

				let dates = $("[data-join-date]:visible")
				dates.each(function () {
					var candidate = $(this).attr("data-join-date");
					if (candidate.includes(search)) {
						$(this).show();
					} else {
						$(this).hide();
					}
				});
				count_element()
		}
	}

	function portal(){
		let search = $("#portal_stage").val()
		
		if (search != "") {
			let portal_items = $("[data-portal-count]:visible")
			portal_items.each(function () {
			var candidate = $(this).attr("data-portal-count");
			if (candidate.includes(search)) {
				$(this).show();
			} else {
				$(this).hide();
			}
			});
			count_element()
		}
	}
	function join_date_range() {
		let start_date = $("#join_date_start").val();
		let end_date = $("#join_date_end").val();

		
		
		if (start_date || end_date) {
			let visibleDates = $("[data-join-date]:visible");
	
			visibleDates.each(function () {
				let candidateDateString = $(this).data("join-date");
				let candidateDate = new Date(candidateDateString);
	
				if (!isNaN(candidateDate)) {
					let showElement = true;

					if (start_date && !end_date) {
						showElement = candidateDate >= new Date(start_date);
					} else if (!start_date && end_date) {
						showElement = candidateDate <= new Date(end_date);
					} else if (start_date && end_date) {
						showElement = candidateDate >= new Date(start_date) && candidateDate <= new Date(end_date);
					}


					if (showElement) {
						$(this).show();
					} else {
						$(this).hide();
					}
				}
				else {
					$(this).hide();
				}
			});
	
			count_element();
		
		}
		else{
		}
	}

	$("#filter_item").on("click",function(){
		var candidate = $("[data-job-position]");
		candidate.each(function () { 
				$(this).show();
		})
		$(".onboarding_items").each(function () {
			$(this).removeClass("d-none");
		});
		job_Position();
		join_date();
		portal();
		join_date_range()

	})

	$(".oh-tabs__tab").on("click",function (){
		$(".onboarding_items").each(function () {
			$(this).removeClass("d-none");
		});
		job_Position();
		join_date();
		portal();
		join_date_range()
	})
	
	$("#job_position_id").select2()	
	$("#portal_stage").select2()

});