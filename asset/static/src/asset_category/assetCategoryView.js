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


// function getCurrentLanguageCode(callback) {
//     $.ajax({
//       type: "GET",
//       url: "/get-language-code",
//       success: function (response) {
//         var languageCode = response.language_code;
//         callback(languageCode); // Pass the language code to the callback
//       },
//     });
//   }




$("#asset-info-import").click(function (e) {
    e.preventDefault();
    // getCurrentLanguageCode(function (code) {
        // Use SweetAlert for the confirmation dialog
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
    // });
  });
