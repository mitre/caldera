function OperationsModel() {
    var self = this;

    self.operations = ko.computed(function () {
        // trick UI to update by creating new objects
        var ops = _.sortBy(app.bindings.data.operation().map(x => _.extend({start_time: new Date(0)}, x)),
                           ['start_time', 'name']);
        for (operation of ops) {
            // find the adversary
            var adversary = _.find(app.bindings.data.adversary(), {'_id': operation.adversary});
            if (adversary === undefined) {
                _.extend(operation, {adversary: 'Adversary no Longer exists'})
            } else {
                _.extend(operation, {adversary: adversary.name})
            }
        }
        return ops;
    });

    self.remove = function(item) {
        if (confirm('Are you sure you want to delete the operation "' + item.name +'"?')) {
            $.ajax({
                    type: 'DELETE',
                    url: '/api/networks/' + item.network + '/operations/' + item._id
            })
        }
    }
}

app.bindings.operations = new OperationsModel();