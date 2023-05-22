function mark_defect_device_ajax(device_id, kip_report_id) {
    const csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
    const url = "/arm/device/defect/" + device_id + "/";
    django.jQuery.ajax({
        type: "POST",
        url: url,
        data: {"csrfmiddlewaretoken": csrf_token,
               "kip_report_id": kip_report_id},
        success: function(data) {
            console.log("Device marked defect");
            location.reload();
        },
        error: function(err) {
            console.error("Error updating device defect:", err);
        }
    });
}