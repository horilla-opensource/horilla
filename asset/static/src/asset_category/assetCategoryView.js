$(document).ready(function () {
    // asset category accordion
    $('.oh-accordion-meta__header--custom').on("click", function () {
        $(this).toggleClass('oh-accordion-meta__header--show');
        $(this).next().toggleClass('d-none');
    })

    function updateAssetCount(assetCategoryId) {
        // used to update the count of asset in asset category 
        var csrf_token = $('input[name="csrfmiddlewaretoken"]').attr('value');
        $.ajax({
            type: "POST",
            url: "asset-count-update",
            data: { 'asset_category_id': assetCategoryId, 'csrfmiddlewaretoken': csrf_token },
            dataType: "json",
            success: function (response) {
                $(`#asset-count${assetCategoryId}`).text(response);
            }
        });
    }
    
    // when created the count of the asset category
    $('.asset-create').on('click', function () {
        var assetCategoryId = $(this).attr('data-category-id').trim();
        setTimeout(function () {
            updateAssetCount(assetCategoryId);
        }, 1000);
    });

    //  search dropdown hiding 

        // Hide the select element initially
        $("select[name='type']").hide();
        
        // Listen for changes to the search input field
        $("input[name='search']").on("input", function() {
            // If the input value is not empty, show the select element
            if ($(this).val().trim() !== "") {
            $("select[name='type']").show();
            } else {
            $("select[name='type']").hide();
            }
        });
    
});