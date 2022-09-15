function onclick_prev() {
  if (validate() == true) {
    save_subject("prev");
    if (index == 0) {
      index = n_cases - 1;
    } else {
      index = index - 1;
    }

    $("span#index").text(index);
  }
}

function onclick_next() {
  if (validate() == true) {
    save_subject("next");
    if (index == n_cases - 1) {
      index = 0;
    } else {
      index = index + 1;
    }
    $("span#index").text(index);
  }
}
