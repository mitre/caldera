var OperationForm = function(network_model, host_model, rat_model) {
    var self = this;
    self.name = ko.observable("");
    self.network = ko.observable("");
    self.start_host = ko.observable("");
    self.adversary = ko.observable("");
    self.start_user = ko.observable("");
    self.start_password = ko.observable("");
    self.start_rat = ko.observable("");
    self.start_path = ko.observable("");
    self.parent_process = ko.observable("");
    self.start_type = ko.observable("bootstrap");
    self.user_type = ko.observable("system");
    self.last_parent_process = 0;
    self.perform_cleanup = ko.observable("true");
    self.delay = ko.observable("0");
    self.jitter = ko.observable("0");

    self.usernameOK = ko.computed( function () {
        var parts = self.start_user().split('\\');
        if (parts.length !== 2)
            return false;

        return parts[0].length > 0 && parts[1].length > 0
    });

    self.formValidated = ko.computed( function () {
        if (self.user_type === "custom") {
            return self.usernameOK();
        }
        return true;
    });


    self.network_hosts = ko.computed( function () {
        if (network_model() && self.network() && host_model()) {
            var net = _.find(network_model(), {_id: self.network()});
            return _.filter(host_model(), function(host) { return _.includes(net.hosts, host._id) });
        }
    });

    self.rats = ko.computed( function () {
        rats = [];
        if (self.start_host() && rat_model) {
            var rats = _.filter(rat_model(), function(rat) { return self.start_host() === rat.host});
        }
        living_rats = [];
        for (var i = 0; i < rats.length; i++) {
            if (rats[i].active) {
                living_rats.push(rats[i]);
            }
        }
        if (living_rats.length === 0) {
            return [{'_id': undefined, name: 'No Rats available'}]
        }
        return living_rats;
    });

    self.networks = app.bindings.data.network;
    self.adversaries = app.bindings.data.adversary;

    self.clone = ko.observable("");
    self.active = ko.computed(() => _.find(app.bindings.data.operation(), {'_id': self.clone()}))

    self.operations = ko.computed(function () {
        var ops = _.sortBy(app.bindings.data.operation().map(x => _.extend({start_time: new Date(0)}, x)),
                           ['start_time', 'name']);

        var filtered_ops = [];
        for (operation of ops) {
            // find the adversary
            var adversary = _.find(app.bindings.data.adversary(), {'_id': operation.adversary});
            if (adversary !== undefined) {
                filtered_ops.push(_.extend(operation, {adversary: adversary.name}));
            }
        }
        return filtered_ops;
    });

    self.clone_op = function(){
        var op = self.active();
        self.name(op.name + "-clone");
        self.network(op.network);
        self.start_host(op.start_host);
        self.adversary(op.adversary);
        self.start_user(op.start_user);
        self.start_password(op.start_password);
        self.start_rat(op.start_rat);
        self.start_path(op.start_path);
        self.parent_process(op.parent_process);
        self.start_type(op.start_type);
        self.user_type(op.user_type);
        self.perform_cleanup(op.perform_cleanup);
        self.delay(op.delay);
        self.jitter(op.jitter);
    };

    self.submit = function() {
            var obj = {
                name: self.name, start_host: self.start_host, adversary: self.adversary, start_type: self.start_type,
                user_type: self.user_type, perform_cleanup: self.perform_cleanup, delay: Number(self.delay()),
                jitter: Number(self.jitter())
            };
            if (self.start_type() === "existing") {
                obj.start_rat = self.start_rat();
            } else if (self.start_type() === "bootstrap") {
                if (self.user_type() === "custom") {
                    obj.start_user = self.start_user;
                    obj.start_password = self.start_password;
                }
            }

            if (self.start_path() && self.start_path().length > 0) {
                obj.start_path = self.start_path;
            }

            if (self.parent_process() && self.parent_process().length > 0 && (self.user_type() === "custom" || self.user_type() === "active")) {
                obj.parent_process = self.parent_process;
            }

            var jsObj = ko.toJS(obj);
            $.ajax({
                type: 'POST',
                url: '/api/networks/' + self.network() + '/operations',
                data: ko.toJSON(jsObj),
                dataType: 'json',
                contentType: "application/json; charset=utf-8"
            }).done(function (id) {
                hasher.setHash('active_operation/' + id);
            });
    };
};

app.bindings.operationForm = new OperationForm(app.bindings.data.network, app.bindings.data.host, app.bindings.data.rat);
