function IncompleteJobs() {
    var self = this;
    self.jobs = ko.computed(() => _.filter(app.bindings.data.job(), x => x.status !== 'success' && x.status !== 'failed'))

    self.console_output = ko.computed( function () {
    	if (self.jobs() !== undefined) {
	    	return ko.toJSON(self.jobs(), null, 2)
	    }
    })	
}

app.bindings.incomplete_jobs = new IncompleteJobs();