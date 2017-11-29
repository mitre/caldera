var ArtifactlistForm = function() {
    var self = this;
    self.name = ko.observable();
    self.description = ko.observable();
    self.services = ko.observable();
    self.file_paths = ko.observable();
    self.executables = ko.observable();
    self.dlls = ko.observable();
    self.schtasks = ko.observable();

    self.submit = function() {
        var jsObj = ko.toJS(this);
        jsObj.services = jsObj.services.split("\n");
        jsObj.file_paths = jsObj.file_paths.split("\n");
        jsObj.executables = jsObj.executables.split("\n");
        jsObj.dlls = jsObj.dlls.split("\n");
        jsObj.schtasks = jsObj.schtasks.split("\n");
        $.ajax({
            type: 'POST',
            url: '/api/artifactlists',
            data: ko.toJSON(jsObj),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }).done(function(id) {
            hasher.setHash('artifactlists/' + id)
        });
    };
};

app.bindings.add_artifactlist = new ArtifactlistForm();
