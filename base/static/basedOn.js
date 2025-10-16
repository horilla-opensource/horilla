$(document).on('htmx:load', function () {
	function hidBasedOn(basedOn) {
		if (basedOn == "after") {
			$("#id_rotate_after_day_parent_div").show();

			$("#id_rotate_every_weekend_parent_div").hide();
			$("#id_rotate_every_parent_div").hide();

		} else if (basedOn == "weekly") {
			$("#id_rotate_every_weekend_parent_div").show();

			$("#id_rotate_after_day_parent_div").hide();
			$("#id_rotate_every_parent_div").hide();

		} else if (basedOn == "monthly") {
			$("#id_rotate_every_parent_div").show();

			$("#id_rotate_after_day_parent_div").hide();
			$("#id_rotate_every_weekend_parent_div").hide();

		}
	}

	var basedOn = $("#id_based_on");
	hidBasedOn(basedOn.val());

	basedOn.on('change', function (e) {
		hidBasedOn(basedOn.val());
	});
});
