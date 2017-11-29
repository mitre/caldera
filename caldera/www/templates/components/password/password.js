function PasswordModal () {
    var self = this;

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

    self.show = function () {
        $('#passwordEdit').modal('show');
    };

    self.changePassword = function () {
        $.ajax({
            type: 'POST',
            url: '/api/site_user/' + app.bindings.login_modal.loggedInUserID() + '/password',
            data: ko.toJSON({password: self.password1()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function() {
            $('#passwordEdit').modal('hide');
        });
    };
}

app.bindings.password_modal = new PasswordModal();