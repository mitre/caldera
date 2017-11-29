function ActiveSteps() {
    var self = this;

    self.steps = ko.observableArray();

    self._steps = ko.computed(function () {
        self.steps(_.sortBy(_.map(app.bindings.data.step(), function (x) {
            return _.extend({}, x, {step_bindings: step_bindings_for_technique(x), url: '#/step_config/' + x._id});
        }), function (x) {return x.name.toLowerCase()}));
    });

    function step_bindings_for_technique (technique) {
        return _.map(technique.mapping, function (x) {
            return {technique: _.find(app.bindings.data.attack_technique(), {_id: x.technique}),
                    tactic: _.find(app.bindings.data.attack_tactic(), {_id: x.tactic})}
        });
    }

    self.selectedTactics = ko.observableArray();
    self.selectedTechniques = ko.observableArray();
    self.tacticFilter = ko.computed(function () {
        var retVals = [];
        if (app.bindings.data.step()) {
            retVals = _.flatten(_.map(app.bindings.data.step(), function (x) {
                return _.map(x.mapping, function (y) {
                    return _.find(app.bindings.data.attack_tactic(), {_id: y.tactic})
                });
            }))
        }
        core = Array.from(new Set(retVals));
        return core;
    });

    self.routed = function () {
        if (arguments.length > 0) {
            var keywords = arguments[0];
            var techniques = keywords.techniques;
            if (techniques) {
                console.log(techniques);
                self.selectedTechniques(techniques.split(','))
            }
        }
    };

    self.techniqueFilter = ko.computed(function () {
        var retVals = [];
        if (app.bindings.data.step()) {
            retVals = _.flatten(_.map(app.bindings.data.step(), function (x) {
                return _.map(x.mapping, function (y) {
                    return _.find(app.bindings.data.attack_technique(), {_id: y.technique})
                });
            }))
        }
        core = Array.from(new Set(retVals));
        return core;
    });

    self.filtered = ko.computed(function () {
        if (self.selectedTactics().length === 0 && self.selectedTechniques().length === 0) {
            core = self.steps();
            return core;
        }
        return _.filter(self.steps(), function (step) {
            var techniques = _.map(step.mapping, function (x) {return x.technique});
            var tactics = _.map(step.mapping, function (x) {return x.tactic});
            return _.intersection(techniques, self.selectedTechniques()).length === self.selectedTechniques().length &&
            _.intersection(tactics, self.selectedTactics()).length === self.selectedTactics().length
        })
    });

    self.view_step = function (step) {
        console.log(step);
    }
}

app.bindings.steps = new ActiveSteps();