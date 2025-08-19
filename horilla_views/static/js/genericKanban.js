var modelName = $("#helperContainer").attr("data-model");
var appLabel = $("#helperContainer").attr("data-app-label");
var groupKey = $("#helperContainer").attr("data-group-key");
var groupOrderBy = $("#helperContainer").attr("data-group-order-by");
var instanceOrderBy = $("#helperContainer").attr("data-instance-order-by");
var model = `${appLabel}.${modelName}`;
var groupOrder = []
var stageOrderJson = []

function isNextStage(currentStageId, targetStageId, parsedStageOrder) {
	var currentStageIndex = parsedStageOrder.findIndex(
		(stage) => stage.id == currentStageId
	);
	var targetStageIndex = parsedStageOrder.findIndex(
		(stage) => stage.id == targetStageId
	);
	return (
		targetStageIndex === currentStageIndex + 1 ||
		currentStageIndex === targetStageIndex
	);
}

function groupSequenceGet(groupHead) {
	var sequence = [];
	var groupContainers = groupHead.closest('.groupContainer').find(".pipeline_item")

	$.each(groupContainers, function (index, element) {
		sequence.push($(element).attr("data-group-id"));
	});

	$.ajax({
		type: "GET",
		url: "/update-kanban-group-sequence/",
		data: {
			"sequence": JSON.stringify(sequence),
			"tab_id": groupHead.attr("data-tab-id"),
			"model": model,
			"group_key": groupKey,
			"orderBy": groupOrderBy,
		},
		success: function (response) {
			message = response.message || "Group sequence updated successfully.";
			Toast.fire({
				icon: "success",
				title: message,
				position: "top-end",
			});
		},
	});
}

function handleValidDrop(groupId, objectId, row) {
	if (groupId != window.candidateCurrentStage) {
		var container = row.closest(".pipeline_item");
		var array = container.find(".task-card");

		var values = [];
		for (let i = 0; i < array.length; i++) {
			values.push($(array[i]).attr("data-instance-id"));
		}

		$.ajax({
			type: "GET",
			url: "/update-kanban-item-group/",
			traditional: true,
			data: {
				model: model,
				groupId: groupId,
				groupKey: groupKey,
				objectId: objectId,
				orderBy: instanceOrderBy,
				order: JSON.stringify(values),
			},
			success: function (response) {
				row.find(`[name="group_id"]`).val(groupId);

				Toast.fire({
					icon: "success",
					title: "Stage updated",
					position: "top-end",
				});

				if (response.message) {
					Swal.fire({
						title: response.message,
						text: `Total vacancy is ${response.vacancy}.`,
						icon: "info",
						confirmButtonText: "Ok",
					});
				}
			},
			error: function (xhr) {
				Toast.fire({
					icon: "error",
					title: "Failed to update sequence: " + xhr.responseJSON?.error || "Unknown error",
					position: "top-end",
				});
			},
		});
	}
}

function handleSortableUpdate(event, ui, container) {
	var array = container.find(".task-card");
	var groupId = $(ui.item).data("group");

	var values = [];
	for (let i = 0; i < array.length; i++) {
		values.push($(array[i]).attr("data-instance-id"));
	};

	$.ajax({
		type: "get",
		url: "/update-kanban-sequence/",
		traditional: true,
		data: {
			model: model,
			groupId: groupId,
			groupKey: groupKey,
			orderBy: instanceOrderBy,
			order: JSON.stringify(values),
		},
		success: function (response) {
			$(".reload-badge").click();

			if (response.info) {
				console.warn(response.info)
			}
			else if (!response.error) {
				Toast.fire({
					icon: "success",
					title: "Sequence updated",
					position: "top-end",
				});
			}
			else {
				Toast.fire({
					icon: "success",
					title: response.error,
					position: "top-end",
				});
			}
		},
		error: function (xhr) {
			Toast.fire({
				icon: "error",
				title: "Failed to update sequence: " + xhr.responseJSON?.error || "Unknown error",
				position: "top-end",
			});
		}
	});
}

function initializeSortable() {
	$(".groupContainer")
		.sortable({
			handle: ".oh-kanban__section-head",
			connectWith: ".pipeline_item",
			placeholder: "group-placeholder",

			start: function (event, ui) {
				const $stage = $(ui.item).find(".kanban-head");
				if ($stage.length === 0) return;

				window["tabId"] = $stage.attr("data-tab-id");
				window["groupSequence"] = $(this).attr("data-group-sequence");
				window["oldSequences"] = [];
				window["groups"] = [];
				window["elements"] = [];

				$(".kanban-head").each(function (i, obj) {
					if (tabId == $(obj).attr("data-tab-id")) {
						window["groups"].push($(obj).attr("data-group-id"));
						window["oldSequences"].push($(obj).attr("data-group-sequence"));
					}
				});
			},

			stop: function (event, ui) {
				const $stage = $(ui.item).find(".kanban-head");
				if ($stage.length === 0) return;

				var newSequences = [];

				setTimeout(() => {
					groupSequenceGet($stage);
				}, 0);

				$(".kanban-head").each(function (i, obj) {
					if (
						tabId == $(obj).attr("data-tab-id") ||
						$(obj).attr("data-tab-id") == undefined
					) {
						newSequences.push($(obj).attr("data-group-sequence"));
						if ($(obj).attr("data-tab-id") != undefined) {
							window["elements"].push(obj);
						}
					}
				});

				if (newSequences.includes(undefined)) {
					newSequences = newSequences.filter((e) => e !== groupSequence);
					newSequences = newSequences.map((elem) =>
						elem === undefined ? stageSequence : elem
					);
				}

				oldSequences = JSON.stringify(oldSequences);
				groups = JSON.stringify(groups);

				elements.forEach(function (element) {
					for (let index = 0; index < newSequences.length; index++) {
						const sequence = newSequences[index];
						if (sequence == $(element).attr("data-group-sequence")) {
							$(element).attr("data-group-sequence", `${index + 1}`);
							return;
						}
					}
				});

				// Reset
				window["groupSequence"] = null;
				window["tabId"] = null;
				window["oldSequences"] = [];
				window["elements"] = [];
				window["groups"] = [];
			},
		})
		.disableSelection();
}

function initializeKanbanSortable(sectionSelector, stageSelector) {

	$(sectionSelector).sortable({
		connectWith: sectionSelector,
		items: "> :not(.htmx-indicator)",
		ghostClass: "blue-background-class",
		placeholder: "sortable-placeholder",
		forcePlaceholderSize: true,
		appendTo: "body",
		zIndex: 9999,
		helper: function (event, ui) {
			var helper = ui.clone();
			helper.css({
				width: "360px",
				"max-width": "360px",
				"min-width": "360px",
				"box-sizing": "border-box"
			});
			return helper;
		},

		start: function (event, ui) {
			var row = $(ui.item);
			var nodeId = row.closest(stageSelector).attr("data-group-id");
			var currentStage = parseInt(nodeId);

			if (isNaN(currentStage)) {
				currentStage = nodeId
			}

			window.candidateCurrentStage = currentStage;
			ui.item.data("origin-parent", ui.item.parent());
			ui.item.data("origin-index", ui.item.index());
		},

		stop: function (event, ui) {
			var row = $(ui.item);
			var candidateId = row.data("instanceId");
			var nodeId = row.closest(stageSelector).attr("data-group-id");
			var targetStageId = parseInt(nodeId);

			if (isNaN(currentStage)) {
				targetStageId = nodeId
			}

			var originalStageId = window.candidateCurrentStage;

			var parsedStageOrder = stageOrderJson;
			var preStage = parsedStageOrder.find(stage => stage.id == originalStageId);
			var currentStage = parsedStageOrder.find(stage => stage.id == targetStageId);

			if (!isNextStage(originalStageId, targetStageId, parsedStageOrder)) {
				if (sessionStorage.getItem(`showKanban${modelName}Confirmation`) !== "false") {
					Swal.fire({
						title: "Confirm Stage Change",
						html: `
                            <p class="mb-2">The candidate is being moved from ${preStage.stage}
                            to the ${currentStage.stage} stage. Do you want to proceed?</p>
                            <label><input type="checkbox" id="doNotShowAgain"> Don't show this again in this session</label>
                        `,
						icon: "warning",
						showCancelButton: true,
						cancelButtonColor: "#d33",
						confirmButtonColor: "#008000",
						confirmButtonText: i18nMessages.confirm,
						preConfirm: () => {
							const doNotShowAgain = Swal.getPopup().querySelector("#doNotShowAgain").checked;
							if (doNotShowAgain) {
								sessionStorage.setItem(`showKanban${modelName}Confirmation`, "false");
							}
						},
					}).then((result) => {
						if (result.isConfirmed) {
							handleValidDrop(targetStageId, candidateId, row);
							handleSortableUpdate(event, ui, $(this));
						} else {
							revertItemPosition(ui);
						}
					});
					return;
				}
			}

			handleValidDrop(targetStageId, candidateId, row);
			handleSortableUpdate(event, ui, $(this));
		}
	});
}

function revertItemPosition(ui) {
	const originParent = ui.item.data("origin-parent");
	const originIndex = ui.item.data("origin-index");

	if (originParent && originIndex !== undefined) {
		const currentItem = ui.item.detach();
		const children = originParent.children();

		if (originIndex >= children.length) {
			originParent.append(currentItem);
		} else {
			currentItem.insertBefore(children.eq(originIndex));
		}

		originParent.sortable("refresh");
	}
}

$(document).ready(function () {

	$(".pipeline_item").each(function () {
		var stageId = parseInt($(this).attr("data-group-id"), 10);
		var stageName = $(this).attr("data-group-instance"); // group.label from your HTML

		stageOrderJson.push({
			id: stageId,
			stage: stageName
		});
	});

	initializeKanbanSortable(".oh-kanban__section-body", ".pipeline_item");

});
