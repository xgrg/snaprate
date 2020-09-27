
// Get params from a URL
$.urlParam = function(name){
    var results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href);
    if (results==null){
       return null;
    }
    else{
       return results[1] || 0;
    }
}

function showImage() {
          visible_class = 'subject' + visible_subject;
          imgObj = images[visible_subject - 1];
          viewer.load(imgObj.small, imgObj.big);
          $("span#subject_number").text(visible_subject);
          $("span#image_number").text(visible_image);
        }

function validate(){
  ans = $('input').val();
  if (ans.indexOf('"') > -1){
    alert('Please remove any " from your comments before validating.')
    return false;
  }
  c = get_score();
  console.log(c)
  if (ans != '' && c === ''){
     alert('Please also give a score or remove your comment otherwise.')
     return false;
  }
  else{
    return true;
  }
}

function cycle_button(e){
  var btn = $('a#score');
  if (btn.hasClass("btn-secondary")) {
      btn.removeClass("btn-secondary");
      btn.addClass("btn-success");
  }
  else if (btn.hasClass("btn-success")) {
      btn.removeClass("btn-success");
      btn.addClass("btn-danger");
  }
  else if (btn.hasClass("btn-danger")) {
      btn.removeClass("btn-danger");
      btn.addClass("btn-warning");
  }
  else if (btn.hasClass("btn-warning")) {
      btn.removeClass("btn-warning");
      btn.addClass("btn-secondary");
  }
}

function color_button(value){
  $("#score").removeClass("btn-success");
  $("#score").removeClass("btn-danger");
  $("#score").removeClass("btn-secondary");
  $("#score").removeClass("btn-warning");
  if ("" + value == ""){
    $("#score").addClass("btn-secondary");
  }
  else{
    value = parseInt(value);
    if (value == 1){
      $("#score").addClass("btn-warning");
    }
    else if (value == 0){
      $("#score").addClass("btn-success");
    }
    else if (value == -1){
      $("#score").addClass("btn-danger");
    }
  }
}
function color_test(value){
  $("#test").removeClass("btn-success");
  $("#test").removeClass("btn-danger");
  $("#test").removeClass("btn-secondary");
  if (value == "True"){
    $("#test").addClass("btn-success");
  }
  else if (value == "False"){
    $("#test").addClass("btn-danger");
  }
}

function get_score(){
  if ($("#score").hasClass('btn-secondary')) {
      return '';
  }
  else if ($("#score").hasClass('btn-danger')) {
      return -1;
  }
  else if ($("#score").hasClass('btn-warning')) {
      return 1;
  }
  else if ($("#score").hasClass('btn-success')) {
      return 0;
  }
}

function save_subject(then){
  pipeline = $.urlParam('s')
  //if (s==null){
  //  s = ''
  //}

  $.ajax({
        type: "POST",
        url: "/post/",
        data: {"score": get_score(),
               "comments": $('input').val(),
               "subject":visible_subject,
               "pipeline":pipeline,
               "then":then},
        dataType:'json',
        success: function(data) {
            if (data == 'UPDATE'){
              alert('Missing data (probably after server reboot). Please logout and login again.');
              window.location.replace("/auth/logout/");
              return;
            }
            if ($('#score').hasClass('btn-secondary')){
                $( "span.skipped" ).fadeIn( 150 ).delay( 100 ).fadeOut( 300 );
            }
            else {
              $( "span.success" ).fadeIn( 150 ).delay( 100 ).fadeOut( 300 );
            }
            color_button(data[0]);
            $('input').val(data[1]);
            //$('#username').text(data[2]);
            if (then == 'nextbad'){
              visible_class = 'subject' + visible_subject;
              visible_subject = parseInt(data[2]);
              showImage()
            }
            if (data.length > 3){
              color_test(data[3]);
              for (i = 0 ; i < data[4].length ; i++){
                $('#test'+i).removeClass("badge-light")
                $('#test'+i).removeClass("badge-success")
                $('#test'+i).removeClass("badge-danger")
                if (data[4][i][1] == 'True'){
                  $('#test'+i).text(data[4][i][0]) //+': ' + data[5][i][1])
                  $('#test'+i).addClass("badge-success")
                }
                else if (data[4][i][1] == 'False'){
                  $('#test'+i).text(data[4][i][0]) //+': ' + data[5][i][1])
                  $('#test'+i).addClass("badge-danger")
                }
                else {
                  s = data[4][i][1];
                  if (s.length > 20) {
                    s = s.substring(0, 20) + "…";
                  }

                  $('#test'+i).text(s)
                  $('#test'+i).addClass("badge-light")
                  title =  data[4][i][0] + ': '+  data[4][i][1]
                  $('#test'+i).attr('title', title)
                  $('#test'+i).attr('data-original-title', title)
                }
                $('#test'+i).tooltip();
                $('[data-toggle="tooltip"]').tooltip();

              }
            }

            $.ajax({
                  type: "POST",
                  url: "/pipelines/",
                  data: {"id": visible_subject,
                         "pipeline": pipeline},
                  dataType:'text',
                  success: function(data) {
                    $("#otherp").html(data);
                    return;
                  }

            });
            return data;

        }
    });
}
