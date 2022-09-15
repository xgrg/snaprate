// Get params from a URL
$.urlParam = function(name) {
  var results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href);
  if (results == null) {
    return null;
  } else {
    return results[1] || 0;
  }
}

function validate() {
  ans = $('input').val();
  if (ans.indexOf('"') > -1) {
    alert('Please remove any " from your comments before validating.')
    return false;
  }
  c = get_score();
  if (ans != '' && c === '') {
    alert('Please also give a score or remove your comment otherwise.')
    return false;
  } else {
    return true;
  }
}

function cycle_button(e) {
  var btn = $('a#score');
  if (btn.hasClass("btn-secondary")) {
    btn.removeClass("btn-secondary");
    btn.addClass("btn-success");
  } else if (btn.hasClass("btn-success")) {
    btn.removeClass("btn-success");
    btn.addClass("btn-danger");
  } else if (btn.hasClass("btn-danger")) {
    btn.removeClass("btn-danger");
    btn.addClass("btn-warning");
  } else if (btn.hasClass("btn-warning")) {
    btn.removeClass("btn-warning");
    btn.addClass("btn-secondary");
  }
}

function color_button(value) {
  $("#score").removeClass("btn-success");
  $("#score").removeClass("btn-danger");
  $("#score").removeClass("btn-secondary");
  $("#score").removeClass("btn-warning");
  if ("" + value == "") {
    $("#score").addClass("btn-secondary");
  } else {
    value = parseInt(value);
    if (value == 1) {
      $("#score").addClass("btn-warning");
    } else if (value == 0) {
      $("#score").addClass("btn-success");
    } else if (value == -1) {
      $("#score").addClass("btn-danger");
    }
  }
}

function color_test(value) {
  $("#test").removeClass("btn-success");
  $("#test").removeClass("btn-danger");
  $("#test").removeClass("btn-secondary");
  if (value == "True") {
    $("#test").addClass("btn-success");
  } else if (value == "False") {
    $("#test").addClass("btn-danger");
  }
}

function get_score() {
  if ($("#score").hasClass('btn-secondary')) {
    return '';
  } else if ($("#score").hasClass('btn-danger')) {
    return -1;
  } else if ($("#score").hasClass('btn-warning')) {
    return 1;
  } else if ($("#score").hasClass('btn-success')) {
    return 0;
  }
}

function save_subject(then) {
  Pace.track(function(){

  $.ajax({
    type: "POST",
    url: "/post/",
    data: {
      "score": get_score(),
      "comments": $('input').val(),
      "polygons": JSON.stringify(polygons),
      "index": index,
      "then": then
    },
    dataType: 'json',
    success: function(data) {
      console.log('data', data)
      id = data[0];
      fp = data[1];
      points = [];
      d3.selectAll('g').remove();
      d3.select('image').attr("xlink:href", fp);
      polygons = data[2]

      $('input').val(data[3]);
      color_button(data[4]);

      howmany_polygons = 0;
      drawPoly(polygons);

      return data;

    }
  });
})
}
