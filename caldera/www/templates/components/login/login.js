Login = function () {
    var self = this;
    self.username = ko.observable();
    self.password = ko.observable();
    self.loggedin = ko.observable();
    self.failure = ko.observable();

    self.getcookie = function (name) {
        var cookies = document.cookie.split(';');
        for (var i=0; i < cookies.length; i++) {
            var c = cookies[i].trim().split('=');
            if (c[0].indexOf(name) == 0) {return c[1]}
        }
        return false;
    };

    self.test_logon = function () {
        if (self.loggedin()) {
            $.ajax({
                type: 'GET',
                url: '/api/networks'
            })
        }
    };

    self.loggedin(!!self.getcookie("AUTH"));

    self.login = function () {
        // get login token
        $.ajax({
            type: 'POST',
            url: '/login',
            data: JSON.stringify({username: self.username(), password:self.password()}),
            contentType:"application/json; charset=utf-8",
            success: function(id) {
                window.location = "/";
            },
            error: function() {
                self.failure("Incorrect login. try again")
            }
        });
    };


    self.test_logon();

    var login_subscription = ko.computed(function () {
        if (self.loggedin()) {
            self.failure("");
            self.username("");
            self.password("");
        }
    });
};

app.bindings.login = new Login();
