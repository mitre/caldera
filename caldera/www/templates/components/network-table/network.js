function Host(obj) {
    var self = this;
    obj = obj || {};
    // static values don't need to be observables
    self.hostname = obj.hostname;
    self._id = obj._id;

    // dynamic values could be
    self.status = ko.observable(obj.status || 'visible');
}

function NetworkView() {
    var self = this;
    self.networks = app.bindings.data.network;

    self.remove = function(item) {
        if (confirm('Are you sure you want to delete the network "' + item.name +'"?')) {
            $.ajax({
                type: 'DELETE',
                url: '/api/networks/'+item._id
            });
        }
    }
}

app.bindings.networks = new NetworkView();