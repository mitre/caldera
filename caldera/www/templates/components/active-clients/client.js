function Client() {
    var self = this;
    self.rats = ko.computed( function () {
        if (app.bindings.data.rat && app.bindings.data.host) {
            var temp = app.bindings.data.rat().map(intro => {
                var host_obj = _.find(app.bindings.data.host(), {_id: intro.host})
                if (host_obj !== undefined) {
                    // create a new intovirts object so that the dependencies are notified
                    return _.extend({}, intro, {host: host_obj})
                }
                return intro
            })
            // This block filters out "inactive" elements from the rat listing
            var amended = [];
            for (var i = 0; i < temp.length; i++) {
                if (temp[i].active){
                    amended.push(temp[i]);
                }
            }
            return _.sortBy(amended, x => x.host.hostname)
        }
        return []
    })

    self.kill = function (rat) {
        // issue the command to the agent
        var uri = '/api/hosts/' + rat.host._id + '/commands';
        var jsObj = {command_line: 'taskkill /f /pid ' + rat.name}
        
        $.ajax({
            type: 'POST',
            url: uri,
            data: ko.toJSON(jsObj),
            dataType: 'json',
            contentType:"application/json; charset=utf-8",
        })
    }
}

app.bindings.client = new Client();