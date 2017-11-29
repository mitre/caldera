function CommandWindow() {
    var self = this;
    self.command_line = ko.observable();
    self.host = ko.observable();
    self.stdout = ko.observable("");
    self.commands = ko.observableArray();
    self.hosts = ko.computed(() => _.sortBy(app.bindings.data.host(), ["hostname"]));

    self.uri = ko.computed(function() {
        if (self.host() && self.host()._id) {
            return '/api/hosts/' + self.host()._id + '/commands'
        }
    });

    self.clear = function() {
        self.commands([])
    };

    self.submit = function() {
        var command = ko.observable();
        self.commands.push(command);
        command("[" + self.host().hostname + "] > " + self.command_line());
        $.ajax({
            type: 'POST',
            url: self.uri(),
            data: ko.toJSON({'command_line': self.command_line()}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function(id) {
            $.getJSON(self.uri() + '/' + id + '?wait=True', function(data) {
                if (!data.error) {
                    command(command() + "\n" + data.output)
                } else {
                    command(command() + "\n" + data.error)
                }
            });
        });
    }
}

app.bindings.commandWindow = new CommandWindow();
