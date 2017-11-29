function Host(obj) {
    var self = this;
    obj = obj || {};
    // static values don't need to be observables
    self.hostname = obj.hostname;
    self._id = obj._id;

    // dynamic values could be
    self.status = ko.observable(obj.status || 'visible');
}

function NetworksModel(networkGraph) {
    var self = this;
    self.active_id = ko.observable(undefined);
    self.hostToAdd = ko.observable();
    self.opGraph = networkGraph;

    self.active = ko.computed(function () {
        if (self.active_id()) {
            return _.find(app.bindings.data.network(), {"_id": self.active_id()})
        }
        return undefined
    });

    self.hosts = ko.computed(function () {
        if (app.bindings.data.host() && self.active()) {
            return _.filter(app.bindings.data.host(), function (host) {return self.active().hosts.indexOf(host._id) !== -1; })
        }
    });

    self._hosts = ko.computed(function() {
        var listing = app.bindings.data.host();
        if (listing !== undefined && self.active())
        {
            listing = listing.filter(x => _.includes(self.active().hosts, x._id)).map(h => new Host(h))
            self.opGraph.boot('networkView');
            self.opGraph.network_graph.init({nodes: listing, links: []});
            self.store = listing;
            return listing
        }
    });

    self.unhosts = ko.computed(function () {
        if (app.bindings.data.host() && self.active()) {
            return _.filter(app.bindings.data.host(), function (host) {return self.active().hosts.indexOf(host._id) === -1; })
        }
    });

    self.routed = function(id) {
        self.active_id(id);
        self.opGraph.boot('networkView');
        if (self.store !== undefined) {
            self.opGraph.network_graph.init({nodes: self.store, links: []});
        }
    };

    self.remove = function(item) {
        if (confirm('Are you sure you want to delete the network "' + item.name +'"?')) {
            $.ajax({
                type: 'DELETE',
                url: '/api/networks/'+item._id
            }).done(function() {
                if (item == self.active()) {
                    self.active_id(undefined);
                    hasher.setHash('main')
                }
            })
        }
    };

    self.hostRemove = function(item) {
        if (self.active() && self.active()._id) {
            if (confirm('Are you sure you want to delete the host "' + item.hostname +'"?')) {
                $.ajax({
                    type: 'DELETE',
                    url: '/api/networks/' + self.active()._id + '/hosts/' + item._id
                })
            }
        }
    };

    self.hostAdd = function () {
        if (self.active() && self.active()._id) {
            $.ajax({
                type: 'PUT',
                url: '/api/networks/' + self.active()._id + '/hosts/' + self.hostToAdd()._id
            })
        }
    }
}

app.bindings.network_graph = new NetworkGraph(d3.select("#opGraph"));
app.bindings.active_network = new NetworksModel(app.bindings.network_graph);
