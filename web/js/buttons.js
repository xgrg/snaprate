function onclick_xnat(){

  imgObj = images[visible_subject - 1];
  src = imgObj.small;
  $.ajax({
        type: "POST",
        url: "/xnat/",
        data: {"src": src},
        dataType:'json',
        success: function(data) {
          url = 'https://barcelonabrainimaging.org/data/'
             + 'experiments/' + data + '?format=html'
          var win = window.open(url, '_blank');
          if (win) {
              win.focus();
          } else {
              alert('Please allow popups for this website');
          }
          return true;
        },
        error: function(xhr, status, error){
          console.log(error)
          console.log(xhr)
          console.log(status)
        }
      });
}

function onclick_prev(){
  if (validate() == true){
    save_subject("prev");

    visible_class = 'subject' + visible_subject;
    if (visible_subject == 1) {
      visible_subject = n_subjects;
    }
    else {
      visible_subject = visible_subject - 1;
    }

    showImage() //visible_class, visible_subject, visible_image)
  }
}

function onclick_next(){
  if (validate() == true){
    save_subject("next");

    visible_class = 'subject' + visible_subject;
    if (visible_subject == n_subjects) {
      visible_subject = 1;
    }
    else {
      visible_subject = visible_subject + 1;
    }

    showImage() ; //visible_class, visible_subject, visible_image)
  }
}
