function mark_defect_device_ajax(device_id) {
    const csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
    const url = "/arm/device/defect/" + device_id + "/";
    const title = document.getElementsByName("title")[0].value;
    const kip_report_id = parseInt(title.match(/\d+/));
    django.jQuery.ajax({
        type: "POST",
        url: url,
        data: {"csrfmiddlewaretoken": csrf_token,
                "kip_report_id": kip_report_id},
        success: function(data) {
            if (data){
               if (data.success) {
                    console.log("Marked device defect");
                    location.reload();
                    if (data.message){
                        alert(data.message);
                    }
                } else {
                    console.error("Error updating device defect:", data.message);
                    alert(data.message);
                    return
                }
            } else {
               console.log("Marked device defect");
               location.reload();
            }
        },
        error: function(xhr, status, err) {
            console.error("Error updating device defect:", err);
            alert("Произошла ошибка при попытке пометить " +
                "устройство как неисправное. Проверьте подключение " +
                "к сети или обратитесь к администратору сайта.");
        }
    });
}