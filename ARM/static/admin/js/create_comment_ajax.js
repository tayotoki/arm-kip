function create_comment_ajax(mech_report_id) {
    const csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
    const url = "/arm/comment/create/" + mech_report_id + "/";
    const textAreas = document.querySelectorAll(".vLargeTextField");
    const sampleText = textAreas[textAreas.length - 2].value
    django.jQuery.ajax({
        type: "POST",
        url: url,
        data: {"csrfmiddlewaretoken": csrf_token,
                text: sampleText},
        success: function(data) {
            console.log("Comment created");
            location.reload();
        },
        error: function(err) {
            console.error("Error creating comment:", err);
        }
    });
}