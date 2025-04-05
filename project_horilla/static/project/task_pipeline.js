function toggleDropdown(id) {
    var element = document.getElementById('taskCreateForm' + id);
    element.classList.toggle('d-none');
}

function updateStageClass(element) {
    const parent = $(element).parent();
    const isCollapsed = parent.hasClass('oh-kanban__section');
    const stageId = parent.data('stage-id');  // Get the data-stage-id attribute value
    const collapsedProjectStages = JSON.parse(localStorage.getItem('collapsedProjectStages')) || [];  // Get the collapsed stages from localStorage or initialize an empty array


    // Toggle between class states
    parent.toggleClass('oh-kanban__section oh-kanban-group stage');
    parent.toggleClass('ml-2 stage ui-sortable-handle');

    if (isCollapsed) {
        setTimeout(() => {
            parent.addClass('oh-kanban-card--collapsed stage');
        }, 100);
        if (!collapsedProjectStages.includes(stageId)) {
            collapsedProjectStages.push(stageId);
            localStorage.setItem('collapsedProjectStages', JSON.stringify(collapsedProjectStages));
        }
    } else {
        parent.removeClass('oh-kanban-card--collapsed');
        const index = collapsedProjectStages.indexOf(stageId);
        if (index > -1) {
            collapsedProjectStages.splice(index, 1);  // Remove the stageId from the array
            localStorage.setItem('collapsedProjectStages', JSON.stringify(collapsedProjectStages));  // Update localStorage
        }
    }

    // Toggle task container visibility
    parent.find('.task-container').toggleClass('d-none');
    parent.find('.oh-kanban__head-actions').first().toggleClass('d-none');

}

function loadCollapsedProjectStages() {
    // Retrieve collapsed project stages from local storage
    let collapsedProjectStages = [];
    const collapsedProjectStagesData = localStorage.getItem('collapsedProjectStages');
    if (collapsedProjectStagesData) {
        try {
            // Parse the JSON only if it's a valid string
            collapsedProjectStages = JSON.parse(collapsedProjectStagesData);
        } catch (error) {
            console.error('Error parsing JSON from local storage:', error);
        }
    }

    // Iterate over collapsed project stages
    $.each(collapsedProjectStages, function (index, stageId) {
        const stageElement = $(`[data-stage-id='${stageId}']`);
        if (stageElement.length) {
            const groupHead = stageElement.find('.oh-kanban-group__head');
            if (groupHead.length) {
                updateStageClass(groupHead[0]);
            }
        }
    });
}

$(document).ready(function () {
    let old_stage_seq = {}; // Define the old sequence of stages globally

    loadCollapsedProjectStages();

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    $('.task-container').sortable({
        // Enables sortable functionality for task containers,
        // tracking drag-and-drop events and updating task sequences via AJAX.
        connectWith: ".task-container",
        start: function (event, ui) {
            var $draggedCard = ui.item;
            var $taskOldStage = $draggedCard.closest('.oh-kanban__section');
            taskOldStageId = $taskOldStage.data('stage-id');  // Store the task old stage ID
            window.$oldStageTaskCount = $taskOldStage.find('.task-count')
        },
        stop: function (event, ui) {
            var $draggedCard = ui.item;
            var $taskNewStage = $draggedCard.closest('.oh-kanban__section');
            var $newStageTaskCount = $taskNewStage.find('.task-count');
            var taskNewStageId = $taskNewStage.data('stage-id');  // Get the task new stage ID
            var taskId = $draggedCard.data('task-id');

            // Check if the task has moved to a new stage
            if (taskNewStageId !== taskOldStageId) {
                var new_stage_seq = {};
                var task_container = $(this).children(".task");
                task_container.each(function (i, obj) {
                    new_stage_seq[$(obj).data('task-id')] = i;
                });

                // Update the task counts in old stage by -1
                var oldCount = parseInt(window.$oldStageTaskCount.html());
                window.$oldStageTaskCount.html(oldCount - 1);

                // Increment the new stage task count by 1
                var newCount = parseInt($newStageTaskCount.html());
                $newStageTaskCount.html(newCount + 1);

                // Trigger AJAX if the task has changed stages
                $.ajax({
                    type: "post",
                    url: '/project/drag-and-drop-task',
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        updated_task_id: taskId,
                        updated_stage_id: taskNewStageId,
                        previous_task_id: taskId,
                        previous_stage_id: taskOldStageId,
                        sequence: JSON.stringify(new_stage_seq),
                    },
                    success: function (response) {
                        if (response.change === true) {
                            $("#reloadMessagesButton").click();
                        }
                    },
                });
            }
        }
    });

    $('.stage').mousedown(function (e) {
        // Capture old sequence of stages on mousedown
        old_stage_seq = {};
        $('.stage').each(function (i, obj) {
            old_stage_seq[$(obj).attr('data-stage-id')] = i;
        });
    });

    $('.stage').mouseup(function (e) {
        //For stage position rearrange event
        setTimeout(function () {
            var new_stage_seq = {};
            $('.stage').each(function (i, obj) {
                new_stage_seq[$(obj).attr('data-stage-id')] = i;
            });

            // Compare old_stage_seq with new_stage_seq to trigger the ajax request
            if (JSON.stringify(old_stage_seq) !== JSON.stringify(new_stage_seq)) {
                $.ajax({
                    type: 'post',
                    url: '/project/drag-and-drop-stage',
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        sequence: JSON.stringify(new_stage_seq),
                    },
                    success: function (response) {
                        if (response.change) {
                            if (response.change === true) {
                                $("#reloadMessagesButton").click();
                            }
                        }
                    },
                });
            }
        }, 100);
    });
});
