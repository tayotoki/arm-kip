function create_comment_ajax(mech_report_id) {
    const csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
    const url = "/arm/comment/create/" + mech_report_id + "/";
    const text = document.querySelector('.vLargeTextField[name|=comment_set]').value;
    const button = document.querySelector('#comment-button');
    console.log(button)
    button.disabled = true;
    if (text.length === 0){
        return;
    }
    if (button.disabled) {
       django.jQuery.ajax({
        type: "POST",
        url: url,
        data: {"csrfmiddlewaretoken": csrf_token,
                text: text},
        success: function(data) {
            console.log("Comment created");
            location.reload();

        },
        error: function(err) {
            console.error("Error creating comment:", err);
            button.disabled = false;
        }
    }); 
    }
    
}