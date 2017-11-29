function ActiveAdversaryModel() {
    var self = this;

    self.active_id = ko.observable();
    self.active = ko.computed(() => _.find(app.bindings.data.adversary(), {'_id': self.active_id()}));
    self.active_name = ko.computed(() => self.active() ? self.active().name : "");
    self.edit_url = ko.computed(() => self.active_id() ? "#add_adversary/" + self.active_id() : "");
    self.exfil_method_name = ko.computed( () => self.active() ? self.active().exfil_method : "");
    self.exfil_method_address = ko.computed( () => self.active() ? self.active().exfil_address : "");
    self.exfil_method_port = ko.computed( () => self.active() ? self.active().exfil_port : "");

    self.routed = function (active) {
        self.active_id(active);
    };

    self.steps = ko.computed( function () {
        if (self.active() !== undefined && app.bindings.data.step() !== undefined) {
            return  _.map(self.active().steps, function (x) {
                var step = _.find(app.bindings.data.step(), {_id: x});
                if (step !== undefined) {
                    _.extend(step, {step_url: '#step_view/' + step._id});
                }
                return step === undefined ? {display_name: "", summary: "", step_url: "#"} : step
            });
        }
    });

    self.artifactlists = ko.computed( function () {
        if (self.active() !== undefined && app.bindings.data.artifactlist() !== undefined) {
            return _.map(self.active().artifactlists, function (x) {
                var artifactlist = _.find(app.bindings.data.artifactlist(), {_id: x});
                return artifactlist === undefined ? {name: "", description: ""} : artifactlist
            });
        }
    });
}

app.bindings.active_adversary = new ActiveAdversaryModel();