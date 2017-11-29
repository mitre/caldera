var AdversaryTable = function() {
    var self = this;
    self.adversaries = ko.computed(function () {
        if (app.bindings.data.adversary() && app.bindings.data.step()) {
            return _.map(app.bindings.data.adversary(),
                         x => _.extend({}, x, {steps : _.map(x.steps,
                              y =>
                                  {
                                      var res = _.find(app.bindings.data.step(), {_id: y});
                                      if (res)
                                      {
                                          return res.display_name
                                      } else {
                                          return ""
                                      }
                                  }
                              )
            }));
        }
        return [{name: "", steps: []}]
    });

    self.remove = function(item) {
        if (confirm('Are you sure you want to delete the adversary "' + item.name +'"?')) {
            $.ajax({
                type: 'DELETE',
                url: '/api/adversaries/'+item._id
            })
        }
    }
};

app.bindings.adversaries = new AdversaryTable();
