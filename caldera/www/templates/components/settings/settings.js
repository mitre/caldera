function Settings() {
    var self = this;
    self.username = ko.observable();
    self.email = ko.observable();
    self.admin = ko.observable();
    self.password1 = ko.observable("");
    self.password2 = ko.observable("");
    self.password_message = ko.observable("");
    self.unlock = ko.observable("");
    self.new_recursion_depth = ko.observable("");

    self.users = ko.observableArray();

    self.passwordOK = ko.computed(function () {
        if (self.password1() === self.password2()) {
            if (self.password1().length >= 8) {
                return true;
            } else {
                self.password_message("Password must be 8 characters or larger")
            }
        } else {
            self.password_message("Passwords must match")
        }

        return false;
    });

    self.num_tactics = ko.computed( function () {
        return app.bindings.data.attack_tactic().length
    });

    self.num_techniques = ko.computed( function () {
        return app.bindings.data.attack_technique().length
    });

    self.num_groups = ko.computed( function() {
        return app.bindings.data.attack_group().length
    });

    self.recursion_limit = ko.computed( function() {
        if (app.bindings.data.setting()[0] != undefined) {
            return app.bindings.data.setting()[0].recursion_limit
        }
        return 0;
    });

    self.update_depth = function () {
        $.ajax({
            type: "POST",
            url: '/api/update_depth',
            data: ko.toJSON({new_value: self.new_recursion_depth()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done()
    };

    self.last_attack_update = ko.computed( function () {
        if (app.bindings.data.setting()[0] && app.bindings.data.setting()[0].last_attack_update) {
            return app.bindings.data.setting()[0].last_attack_update
        }
        return new Date(0)
    });

    self.last_ps_update = ko.computed( function () {
        if (app.bindings.data.setting()[0] && app.bindings.data.setting()[0].last_psexec_update) {
            return app.bindings.data.setting()[0].last_psexec_update
        }
        return new Date(0)
    });

    self.loadAttack = function () {
        $.get('/api/load_attack');
    };

    self.loadPsExec = function () {
        $.get('/api/load_psexec');
    };

    self.loadUsers = function () {
        $.getJSON('/api/site_user')
            .success(function (data) {
                data = _.map(data, function (x) {return _.extend({email: 'N/A', last_login: 0}, x)});
                for (var i = 0; i < data.length; i++) {
                    data[i].last_login = new Date(data[i].last_login)
                }
                self.users(data);
            })
    };

    self.focus = function () {
        self.loadUsers();
    };

    self.newUserSubmit = function () {
        $.ajax({
            type: 'POST',
            url: '/api/site_user',
            data: ko.toJSON({username: self.username(), email: self.email(), admin: self.admin(), password: self.password1()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function() {
            self.loadUsers();
        });
    };

    self.revokeAdmin = function (user) {
        $.ajax({
            type: 'DELETE',
            url: '/api/site_user/' + user._id + '/admin'
        }).done(function() {
            self.loadUsers();
        });
    };

    self.makeAdmin = function (user) {
        $.ajax({
            type: 'PUT',
            url: '/api/site_user/' + user._id + '/admin'
        }).done(function() {
            self.loadUsers();
        });
    };

    self.deleteUser = function (user) {
        $.ajax({
            type: 'DELETE',
            url: '/api/site_user/' + user._id
        }).done(function() {
            self.loadUsers();
        });
    };

    self.editUser = function (user) {
        app.bindings.settings_modal.user = user;
        app.bindings.settings_modal.username(user.username);
        app.bindings.settings_modal.email(user.email);
        $('#settingsEdit').modal('show');
    };
}

function SettingsModal () {
    var self = this;

    self.user = undefined;
    self.username = ko.observable();
    self.email = ko.observable();
    self.password1 = ko.observable("");
    self.password2 = ko.observable("");
    self.password_message = ko.observable("");

    self.passwordOK = ko.computed(function () {
        if (self.password1() === self.password2()) {
            if (self.password1().length >= 8) {
                return true;
            } else {
                self.password_message("Password must be 8 characters or larger")
            }
        } else {
            self.password_message("Passwords must match")
        }

        return false;
    });

    self.changeUsername = function () {
        $.ajax({
            type: 'PATCH',
            url: '/api/site_user/' + self.user._id,
            data: ko.toJSON({username: self.username()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function() {
            app.bindings.settings.loadUsers();
        });
    };
    self.changePassword = function () {
        $.ajax({
            type: 'POST',
            url: '/api/site_user/' + self.user._id + '/password',
            data: ko.toJSON({password: self.password1()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function() {
            app.bindings.settings.loadUsers();
        });
    };
    self.changeEmail = function () {
         $.ajax({
            type: 'POST',
            url: '/api/site_user/' + self.user._id + '/email',
            data: ko.toJSON({email: self.email()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function() {
            app.bindings.settings.loadUsers();
        });
    }

}

app.bindings.settings = new Settings();
app.bindings.settings_modal = new SettingsModal();
