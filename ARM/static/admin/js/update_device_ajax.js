function update_device_ajax(device_id) {
    const csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
    const url = "/arm/device/update/" + device_id + "/";
    django.jQuery.ajax({
        type: "POST",
        url: url,
        data: {"csrfmiddlewaretoken": csrf_token},
        success: function(data) {
            console.log("Device status updated");
            location.reload();
        },
        error: function(err) {
            console.error("Error updating device status:", err);
        }
    });
}