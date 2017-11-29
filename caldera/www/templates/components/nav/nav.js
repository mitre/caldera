var Navigation = function() {
    var self = this;
    self.color = ko.computed(function () {
    	return app.ddp_client.connected() ? "green" : "red"
    });
    self.active_op = ko.computed(function () {
        var index;
        for (index = 0; index < app.bindings.data.operation().length; index++) {
            if (app.bindings.data.operation()[index].status === "started" || app.bindings.data.operation()[index].status === "cleanup" || app.bindings.data.operation()[index].status === "bootstrapping") {
                return "#active_operation/" + app.bindings.data.operation()[index]._id
            }
        }
        return "/#"
    });
};

app.bindings.nav = new Navigation();
