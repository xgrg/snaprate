function detailsPolygon(polygonButton){
  label = polygonButton.attr("data-value");
  idx = polygonButton.attr("data-index");

  $("#polygonModal h5#itemtitle").text("Edit polygon (#" + idx + ")");
  $("#polygonModal input#textbox").val(idx)

  $('#polygonModal').modal('show');

}
