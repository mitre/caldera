var AdversaryForm = function() {
    var self = this;
    self.active_id = ko.observable("");
    self.name = ko.observable();
    self.all_artifactlists = app.bindings.data.artifactlist;
    self.all_steps = app.bindings.data.step;
    self.steps = ko.observableArray();
    self.artifactlists = ko.observableArray();
    self.exfil_method = ko.observable();
    // TODO: Continue filling this is as we get more supported exfil methods in crater
    self.all_exfil_methods = ko.observableArray(['rawtcp','http','https']);
    self.exfil_address = ko.observable();
    self.exfil_port = ko.observable();

    self.all_steps_drop = ko.computed( function() {
        return self.all_steps();
    });

    self.set_defaults = function () {
        if (self.active_id() !== "") {
            $.get('/api/adversaries/' + self.active_id()).done(function(cur_obj) {
                self.name(cur_obj.name);
                self.steps(cur_obj.steps);
                self.artifactlists(cur_obj.artifactlists);
                self.exfil_method(cur_obj.exfil_method);
                self.exfil_address(cur_obj.exfil_address);
                self.exfil_port(cur_obj.exfil_port);
            });
        } else {
            self.name("");
            self.steps([]);
            self.artifactlists([]);
            self.exfil_method([]);
            self.exfil_address("x.x.x.x");
            self.exfil_port("8889");
        }
    };

    self.submit = function() {
        var method = 'POST';
        var url =  '/api/adversaries';

        if (self.active_id() !== '') {
            method = 'PUT';
            url += '/' + self.active_id();
        }
        var jsObj = ko.toJS(_.pick(this, ['name', 'steps', 'artifactlists', 'exfil_method', 'exfil_address', 'exfil_port']));
        $.ajax({
            type: method,
            url: url,
            data: ko.toJSON(jsObj),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function(id) {
            self.active_id("");
            self.set_defaults();
            hasher.setHash('active_adversary/' + id)
        });
    };

    self.routed = function (id) {
        if (id !== undefined) {
            self.active_id(id);
        } else {
            self.active_id("");
        }
        self.set_defaults();
    };

    self.set_defaults();
};

app.bindings.add_adversary = new AdversaryForm();
