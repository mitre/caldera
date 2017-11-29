var ArtifactlistFancyForm = function() {
    var self = this;
    self.name = ko.observable("");
    self.description = ko.observable("");
    self.configuration = ko.observable();
    self.delayed_configuration =  ko.pureComputed(self.configuration).extend({ rateLimit: { timeout: 500, method: "notifyWhenChangesStop" } });
    self.parsed = ko.observableArray([]);
    self.errorText = ko.observable("");
    self.active_id = ko.observable("");

    self.parseConfiguration = function () {
        $.ajax({
            type: 'POST',
            url: '/api/parse_artifactlist',
            data: self.configuration(),
            dataType: 'text',
            contentType:"application/text; charset=utf-8"
        }).done(function(result) {
            self.parsed([]);
            var decode =  $.parseJSON(result);
            for (var k in decode) {
                if (decode.hasOwnProperty(k)) {
                    self.parsed.push({ key: k, value: decode[k] });
                }
            }
            self.errorText("");
        }).fail(function(jqXHR) {
            if (jqXHR.status === 400) {
                self.parsed([]);
                self.errorText(jqXHR.responseText);
            } else {
                console.error(jqXHR)
            }
        });
    };

    self.delayed_configuration.subscribe(self.parseConfiguration);

    self.submit = function() {
        var method = 'POST';
        var url = '/api/artifactlists';
        if (self.active_id() !== "") {
            method = 'PUT';
            url += '/' + self.active_id();
        }
        $.ajax({
            type: method,
            url: url,
            data: "name: " + self.name() + "\ndescription: " + self.description() + "\n" + self.configuration(),
            contentType:"text/x-yaml; charset=utf-8"
        }).done(function() {
            self.active_id("");
            self.set_default_values();
            hasher.setHash('artifactlists')
        });
    };

    self.set_default_values = function () {
        if (self.active_id() !== "") {
            $.get('/api/artifactlists/' + self.active_id()).done(function(cur_obj) {
                self.name(cur_obj.name);
                self.description(cur_obj.description);
                var conf = "";
                for (var k in cur_obj) {
                    if (cur_obj.hasOwnProperty(k) && k !== 'name' && k !== 'description' && k !== '_id') {
                        conf += k + ':';
                        for (var i = 0; i < cur_obj[k].length; i++) {
                            conf += '\n - ' + cur_obj[k][i];
                        }
                        conf += '\n';
                    }
                }
                self.configuration(conf)
            });
        }
        else {
            self.name("");
            self.description("");
            self.configuration("dlls:\n- \nexecutables:\n- \nfile_paths:\n- \nschtasks:\n- \nservices:\n- ");
        }
    };

    self.routed = function (id) {
        if (id) {
            self.active_id(id);
        } else {
            self.active_id('');
        }
        self.set_default_values();
    };

    self.set_default_values();

    self.deleteArtifactlist = function () {
      $.ajax({
            type: 'DELETE',
            url: '/api/artifactlists/' + self.active_id()
      }).done(function() {
            self.active_id("");
            self.set_default_values();
            hasher.setHash('artifactlists')
        });
    }
};

app.bindings.add_fancy_artifactlist = new ArtifactlistFancyForm();

// Applied globally on all textareas with the "auto-expand" class
$(document)
    .one('focus.auto-expand', 'textarea.auto-expand', function(){
        var savedValue = this.value;
        this.value = '';
        this.baseScrollHeight = this.scrollHeight;
        this.value = savedValue;
    })
    .on('input.auto-expand', 'textarea.auto-expand', function(){
        var minRows = this.getAttribute('data-min-rows')|0, rows;
        this.rows = minRows;
        rows = Math.ceil((this.scrollHeight - this.baseScrollHeight) / 17);
        this.rows = minRows + rows;
    });