function ArtifactLists() {
    var self = this;

    self.artifactlists = ko.computed(function () {
        return _.map(app.bindings.data.artifactlist(), x => _.extend({}, x, {url: '#/add_fancy_artifactlist/' +x._id}));
    });
}

app.bindings.artifactlists = new ArtifactLists();