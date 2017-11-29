function Console(csl) {
    var self = this;
    self.name = csl || 'default';
    self.last = ko.observable();
    self.stdout = ko.observableArray();
    self.write = function(obj) {
        if (obj != undefined) {
            obj.error = obj.error || '';
            obj.hostname = obj.hostname ? '[' + obj.hostname + ']' : '';
            obj.text = obj.text || '';
            obj.command = obj.command || '';
            self.stdout.push(obj);
            self.last(obj);
            $('#' + self.name)[0].scrollTop = $('#' + self.name)[0].scrollHeight;
        }
    }
}

app.bindings.globalconsole = new Console('globalconsole');
app.bindings.activeop_console = new Console('activeop_console');