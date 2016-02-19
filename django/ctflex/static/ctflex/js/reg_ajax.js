function attempt_register() {
  $.ajax({
    url : "/register_user/",
    type : "POST",
    data : $('#register-submit').serialize(),

    success : function(response) {
      if ('errors' in response) {
        var err_html = "<p>There were one or more errors:</p>";
        for (var i = 0 ; i < response.errors.length ; i += 1) {
          var err = response.errors[i];
          err_html += "<p>\t" + err[0] + ": " + err[1] + "</p>";
        }
        document.getElementById("errors").innerHTML = err_html;
      }
      else {

      }
      //console.log(response);
    },

    error : function(xhr, msg, err) {
      alert(err);
    }
  });
}