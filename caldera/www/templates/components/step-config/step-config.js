function StepConfig() {
    var self = this;

    self.techniques =  ko.computed(function () {
        return _.sortBy(app.bindings.data.attack_technique(), function (x) {return x.name.toLowerCase()})
    });

    self.step_select_id = ko.observable();
    self.step_select = ko.computed( function () {
        if (self.step_select_id() !== undefined && app.bindings.data.step()){
            var found_step = _.find(app.bindings.data.step(), {_id: self.step_select_id()});
            if (found_step !== undefined) {
                return found_step
            }
        }
        return {summary: "", name: ""};
    });

    self.selected_technique = ko.observable();
    self.technique_tactics = ko.computed( function () {
        if (self.selected_technique() !== undefined) {
            return _.map(self.selected_technique().tactics, x => _.find(app.bindings.data.attack_tactic(), {'_id': x}))
        }
        return [];
    });

    self.routed = function (obj_id) {
        self.step_select_id(obj_id);
    };

    self.selected_tactics = ko.observableArray([]);
    self.new_mapping = ko.observable(false);

    self.step_bindings = ko.computed( function () {
        if (self.step_select()) {
            var newstuff = _.map(self.step_select().mapping, function (x) {
                return {technique: _.find(app.bindings.data.attack_technique(), {_id: x.technique}),
                        tactic: _.find(app.bindings.data.attack_tactic(), {_id: x.tactic})}
            })}
            return newstuff
        }
    );

    self.deleteBinding = function (item) {
        $.ajax({
                type: 'DELETE',
                url: '/api/steps/' + self.step_select()._id + '/mapping',
                data: ko.toJSON({technique: item.technique._id, tactic: item.tactic._id}),
                dataType: 'json',
                contentType:"application/json; charset=utf-8"
            })
    };

    self.close_mapping = function () {
        self.selected_tactics([]);
        self.new_mapping(false);
        self.selected_technique(undefined);
    };

    self.valid_mapping_selected = function () {
        return self.selected_tactics().length > 0 && self.selected_technique() !== undefined
    };

    self.submit_mapping = function () {
        if (self.valid_mapping_selected()) {
            $.ajax({
                type: 'POST',
                url: '/api/steps/' + self.step_select()._id + '/mapping',
                data: ko.toJSON({technique: self.selected_technique()._id, tactics: _.map(self.selected_tactics(), x => x._id)}),
                dataType: 'json',
                contentType:"application/json; charset=utf-8"
            }).success(function () {
                self.close_mapping();
            });
        }
    };

    self.routed = function (step_id) {
        self.step_select_id(step_id);
    };

    self.restoreDefaultMapping = function () {
        if (confirm('Are you sure you want to reload default ATT&CK Mappings?')) {
            $.ajax({
                type: 'GET',
                url: '/api/steps/' + self.step_select()._id + '/mapping/load_defaults'
            });
        }
    }
}

app.bindings.step_config = new StepConfig();