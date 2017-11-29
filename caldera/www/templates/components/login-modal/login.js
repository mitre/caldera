LoginModal = function () {
    var self = this;
    self.username = ko.observable();
    self.password = ko.observable();
    self.loggedin = ko.observable();
    self.failure = ko.observable();
    self.loggedInUser = ko.observable();
    self.loggedInUserID = ko.observable();
    self.loggedInUserType = ko.observable();
    self.loggedInUserText = ko.observable();

    self.getcookie = function (name) {
        var cookies = document.cookie.split(';');
        for(var i=0; i < cookies.length; i++) {
            var c = cookies[i].trim().split('=');
            if (c[0].indexOf(name) == 0) {return c[1]}
        }
        return false;
    };

    self.test_logon = function () {
        if (self.loggedin()) {
            $.get('/api/networks')
                .fail(function (jqXHR) {
                    if (jqXHR.status === 403) {
                        console.log('failed login');
                        window.location = '/login';
                    }
                })
        }
    };

    self.loggedin(!!self.getcookie("AUTH"));
    if (!self.loggedin()) {
        window.location = '/login';
    }

    self.logout = function () {
        $.ajax({
            type: 'POST',
            url: '/logout',
            success: function() {
                self.loggedin(false);
                window.location = '/login';
            }
        });
    };

    self.test_logon();

    var login_subscription = ko.computed(function () {
        if (self.loggedin()) {
            self.failure("");
            self.username("");
            self.password("");
            $.get('/deflate_token')
                .success(function (login_token) {
                    self.loggedInUser(login_token.username);
                    self.loggedInUserID(login_token._id);
                    if (_.indexOf(login_token.groups, "admin") !== -1) {
                        self.loggedInUserType("Admin");
                    } else {
                        self.loggedInUserType("User");
                    }
                    self.loggedInUserText(login_token.username + ' (' + self.loggedInUserType() + ')')
                })
        }
    });
};

app.bindings.login_modal = new LoginModal();
