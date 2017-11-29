function RatCommandWindow() {
  var self = this;
  self.commands = ko.observableArray([]);
  self._opcodes = ko.observable();
  self.opcode = ko.observable();
  self.opcodes = ko.observableArray([]);
  self.params = ko.observable({});

  $.ajax({
      type: 'GET',
      url: "/api/opcodes",
      contentType:"application/json; charset=utf-8"
  }).done(function(opcodes) {
      self.opcodes(Object.keys(opcodes));
      self._opcodes = opcodes;
  });

  self.opcodeParams = ko.computed(function() {
    var opcode = self.opcode();
    if (!opcode) {
      return [];
    } else {
      var fields = self._opcodes[opcode] || [];
      // reset params
      var params = {};
      fields.forEach(function(f) {
        params[f] = ko.observable();
      });
      self.params(params);
      return fields;
    }
  });
  self.rat = ko.observable();
  self.rats = ko.computed( function () {
      var rats = [{'_id': undefined, name: 'No Rats available'}];
      if (app.bindings.data.rat() && app.bindings.data.host()) {
          rats = _.map(app.bindings.data.rat(), function(rat) {
              var host_obj = _.find(app.bindings.data.host(), {_id: rat.host});
              var hostname = "";
              if (host_obj !== undefined) {
                  hostname = " (on " + host_obj.hostname + ")";
              }
              return _.extend({}, rat, {display_name: "PID: " + rat.name + hostname})
          });
      }
      rats_active = [];
      for (var i = 0; i < rats.length; i++) {
          if (rats[i].active){
              rats_active.push(rats[i]);
          }
      }
      if (rats_active.length === 0) {
          rats_active = [{'_id': undefined, name: 'No Rats available'}];
      }
      return rats_active;
  });

  self.uri = ko.computed(function() {
    if (self.rat()) {
      return '/api/rats/' + self.rat()._id + '/commands'
    }
  });

  self.clear = function() {
    self.commands([])
  };

  self.submit = function() {
    var opcode = self.opcode();
    function tabulate(obj) {
        var output = "";
        Object.keys(obj).forEach(function(key) {
            if (obj[key]) {
                output += key + ":";
                output += obj[key];
                output += "\n";
            }
        });
        return output;
    }

    var command = ko.observable();
    self.commands.push(command);
    var params = self.params();
    command(" > " + opcode + "\n" + tabulate(ko.toJS(params)));
    var uri = self.uri();
    $.ajax({
      type: 'POST',
      url: uri,
      data: ko.toJSON({function: opcode, parameters: params}),
      dataType: 'json',
      contentType:"application/json; charset=utf-8"
    }).done(function(id) {
      $.getJSON(uri + '/' + id + '?wait=True', function(result) {
        if (result.status == 'success') {
          command(command() + tabulate(result.outputs));
        } else {
          command(command() + "\nerror!\n\n" + tabulate(result));
        }
      });
    });
  }
}

app.bindings.rat_command_window = new RatCommandWindow();
