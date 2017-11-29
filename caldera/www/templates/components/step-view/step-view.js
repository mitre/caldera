function StepView() {
    var self = this;

    self.step_select_id = ko.observable();
    self.step_select = ko.computed( function () {
        if (self.step_select_id() !== undefined && app.bindings.data.step()){
            var found_step = _.find(app.bindings.data.step(), {_id: self.step_select_id()});
            if (found_step !== undefined) {
                return found_step
            }
        }
        return {summary: "", name: "", requirement_terms: [], requirement_comparisons: [], add: [], remove: [], cddl: ""};
    });


    self.routed = function (obj_id) {
        self.step_select_id(obj_id);
    };

    self.step_bindings = ko.computed( function () {
        if (self.step_select()) {
            var newstuff = _.map(self.step_select().mapping, function (x) {
                return {technique: _.find(app.bindings.data.attack_technique(), {_id: x.technique}),
                        tactic: _.find(app.bindings.data.attack_tactic(), {_id: x.tactic})}
            })}
            return newstuff
        }
    );

    function build_term(term) {
        var term_array = [];
        term_array.push(term.predicate);
        term_array.push("(");
        for (var y = 0; y < term.literals.length; y+= 2) {
            if (y > 0) {
                term_array.push(", ");
            }
            term_array.push(term.literals[y]);
            term_array.push(" ");
            term_array.push(term.literals[y + 1]);
        }

        term_array.push(")");
        return term_array.join("");
    }

    function build_comparison(comp) {
        var arr = [];
        arr.push(comp.obj1[1]);
        arr.push(comp.comp);
        arr.push(comp.obj2[1]);
        return arr.join(" ");
    }

    self.preconditions = ko.computed( function () {
        var ret = [];
        if (self.step_select() ) {
            for (var x = 0; x < self.step_select().requirement_terms.length; x++) {
                ret.push(build_term(self.step_select().requirement_terms[x]));
            }
            for (var y = 0; y < self.step_select().requirement_comparisons.length; y++) {
                ret.push(build_comparison(self.step_select().requirement_comparisons[y]));
            }
        }
        return ret;
    });

    self.postconditions = ko.computed( function () {
        var ret = [];
        if (self.step_select() ) {
            for (var x = 0; x < self.step_select().add.length; x ++) {
                ret.push('+ ' + build_term(self.step_select().add[x]));
            }
            for (var x = 0; x < self.step_select().remove.length; x ++) {
                ret.push('- ' + build_term(self.step_select().remove[x]));
            }
        }
        return ret;
    });

    self.routed = function (step_id) {
        self.step_select_id(step_id);
    };
}

app.bindings.step_view = new StepView();