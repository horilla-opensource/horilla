import $ from "jquery";

class ImageUpload {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Change image on upload.
    $(".oh-upload-input").on("change", this.uploadImage.bind(this));
    // Remove uploaded image preview.
    $(".oh-remove-image").on("click", this.removeImage.bind(this));
  }

  /**
   *  Upload Image
   */

  uploadImage(e) {
    let inputEl = e.target.closest('.oh-upload-input');
    let targetSelector = inputEl.dataset.target;
    this.readUploadPath(inputEl, targetSelector);
  }
  readUploadPath(input, renderTarget) {
    if (input.files && input.files[0]) {
      var reader = new FileReader();

      reader.onload = function (e) {
        $(renderTarget).attr("src", e.target.result);
      };

      reader.readAsDataURL(input.files[0]);
    }
  }
 /**
   *  Remove Uploaded Image Preview
   */
  removeImage(e){
    let clickedEl = $(e.target).closest('.oh-remove-image');
    let targetSelector = clickedEl.data('target');
    $(targetSelector).attr('src', '/static/images/ui/user.jpg');
    $('.oh-upload-input').val('');
  }
}

export default ImageUpload;
