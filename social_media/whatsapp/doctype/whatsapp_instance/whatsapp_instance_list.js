frappe.listview_settings['Whatsapp Instance'] = {
    get_indicator: function (doc) {
        if (doc.status === "Connected") {
            return [__("Connected"), "green", "status,=,Connected"];
        } else if (doc.status === "Connecting") {
            return [__("Connecting"), "orange", "status,=,Connecting"];
        } else {
            return [__("Disconnected"), "red", "status,=,Disconnected"];
        }
    }
};
