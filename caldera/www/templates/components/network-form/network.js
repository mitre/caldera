var NetworkForm = function() {
    var self = this;
    self.name = ko.observable("");
    self.hosts = ko.observableArray("");
    self.all_hosts = app.bindings.data.host
    self.domain = ko.observable();

    self.domain_hosts = ko.computed(function () {
        return _.filter(self.all_hosts(), {domain: self.domain()});
    });

    self.domains = app.bindings.data.domain 

    self.submit = function() {
        var jsObj = ko.toJS(this);
        delete jsObj.agents;
        delete jsObj.domain_hosts;
        delete jsObj.domains;
        delete jsObj.all_hosts;
        $.ajax({
            type: 'POST',
            url: '/api/networks',
            data: ko.toJSON(jsObj),
            dataType: 'json',
            contentType:"application/json; charset=utf-8",
        }).done(function(id) {
            hasher.setHash('active_network/' + id)
        });
    };
};

app.bindings.add_network = new NetworkForm();
