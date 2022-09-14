function onclick_xnat(){

  imgObj = images[index - 1];
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

    //visible_class = 'subject' + index;
    if (index == 0) {
      index = n_subjects -1 ;
    }
    else {
      index = index - 1;
    }

    showImage() //visible_class, index, visible_image)
  }
}

function onclick_next(){
  if (validate() == true){
    save_subject("next");

    //visible_class = 'subject' + index;
    if (index == n_subjects-1) {
      index = 0;
    }
    else {
      index = index + 1;
    }

    showImage() ; //visible_class, index, visible_image)
  }
}
