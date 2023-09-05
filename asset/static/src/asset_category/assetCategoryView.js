$(document).ready(function () {
  $("#import-dropdown").hide();
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
        $("#import-button").on("click",function(){
          $("#import-dropdown").show();
        })
        $(".close-import").on("click" , function(){
          $("#import-dropdown").hide();
        })
    
});


$("#asset-info-import").click(function (e) {
    e.preventDefault();
        Swal.fire({
            text: "Do you want to download template ?",
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#008000',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Confirm'
        }).then(function(result) {
        if (result.isConfirmed) {
          $.ajax({
            type: "GET",
            url: "/asset/asset-excel",
            dataType: "binary",
            xhrFields: {
              responseType: "blob",
            },
            success: function (response) {
              const file = new Blob([response], {
                type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              });
              const url = URL.createObjectURL(file);
              const link = document.createElement("a");
              link.href = url;
              link.download = "my_excel_file.xlsx";
              document.body.appendChild(link);
              link.click();
            },
            error: function (xhr, textStatus, errorThrown) {
              console.error("Error downloading file:", errorThrown);
            },
          });
        }
      });
  });