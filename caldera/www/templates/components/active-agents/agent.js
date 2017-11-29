function Agent() {
    var self = this;
    self.connections = ko.computed(function () {
        var age = app.bindings.data.agent();
        var t_age = [];
        for (var j = 0; j < age.length; j++) {
            if (age[j].alive) {
                t_age.push(age[j]);
            }
        }
        var connected = _.filter(app.bindings.data.active_connection(), x => x.connections > 0);
        var t_connected = [];
        for (var i = 0; i < t_age.length; i++) {
            for (var k = 0; k < connected.length; k++) {
                if (t_age[i].host === connected[k].host) {
                    t_connected.push(connected[k]);
                }
            }
        }
        t_connected = _.map(t_connected, x => _.extend({host_fqdn: ''}, x));
        t_connected = _.map(t_connected, self.replace_host);
        return _.sortBy(t_connected, "ip")
    });

    self.replace_host = function (x) {
        if (_.has(x, 'host') && x.host_fqdn.length === 0) {
            var h = _.find(app.bindings.data.host(), {_id: x.host});

            if (h !== undefined) {
                x.host_fqdn = h.fqdn
            }
        }

        return x
    }
}

app.bindings.agent = new Agent();