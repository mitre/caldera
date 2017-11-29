function OpHost(obj, status) {
    var self = this;
    obj = obj || {};
    // static values don't need to be observables
    self.hostname = obj.hostname;
    self.fqdn = obj.fqdn;
    self._id = obj._id;
    self._status = status;
    // dynamic values could be
    self.status = function (x) {
        return self._status;
    }
}

function ActiveOperationModel(cnsl, operationGraph) {
    var self = this;

    self.console = cnsl;
    self.op_hosts = [];
    self.active_id = ko.observable();
    self.output = ko.observableArray([]);
    self.active = ko.computed(() => _.find(app.bindings.data.operation(), {'_id': self.active_id()}))
    self.active_name = ko.computed(() => self.active() ? self.active().name : "")
    self.adversary = ko.computed(() => self.active() ? self.active().adversary : "")
    self.start_time = ko.computed(() => (self.active() && self.active().start_time) ? self.active().start_time.toLocaleString() : "")
    self.initial_host = ko.computed(() => self.active() ? self.active().start_host : "")
    self.network = ko.computed(() => self.active() ? _.find(app.bindings.data.network(), {'_id': self.active().network}) : undefined);
    self.network_hosts = ko.computed(function () {
        if (self.network() && self.network().hosts && app.bindings.data.host()) {
            return self.network().hosts.map(x => _.find(app.bindings.data.host(), {_id: x})).filter(x => x)
        }
    });
    self.opGraph = operationGraph;

    self.active_adversary = ko.computed(function () {
        if (self.active() && self.adversary) {
            var i;
            for (i = 0; i < app.bindings.data.adversary().length; i++){
                if (app.bindings.data.adversary()[i]._id === self.adversary()){
                    return app.bindings.data.adversary()[i].name;
                }
            }
        }
    });

    self.start_host = ko.computed(function () {
        if (self.active() && app.bindings.data.host()) {
            var i;
            for (i = 0; i < app.bindings.data.host().length; i++){
                if (app.bindings.data.host()[i]._id === self.initial_host()){
                    return app.bindings.data.host()[i].hostname;
                }
            }
        }
    });


    self.known_files = ko.computed(function () {
        if (self.active() && app.bindings.data.observed_file()) {
            file_list = self.active().known_files.map(x => _.find(app.bindings.data.observed_file(), {_id: x}))
                .map(x => _.extend({}, x, {host: _.find(app.bindings.data.observed_host(), {_id: x.host})}));
            core = [];
            for (var i = 0; i < file_list.length; i++){
                if (file_list[i].use_case === 'rat' || file_list[i].use_case === 'modified' || file_list[i].use_case === 'dropped'){
                    core.push(file_list[i]);
                }
            }
            return core;
        }
    });

    self.known_processes = ko.computed(function () {
        if (self.active()) {
            ops_list = self.active().jobs.map(x => _.find(app.bindings.data.job(), {_id: x}))
            core = [];
            for (var i = 0; i < ops_list.length; i++) {
                if (ops_list[i].action.result !== undefined && ops_list[i].action.result.pid !== undefined){
                    core.push(ops_list[i]);
                }
            }
            return core;
        }
    });

    self.known_rat_processes = ko.computed(function (){
       if (self.active() && app.bindings.data.rat()){
           rat_list = self.active().rat_iv_map;
           core = [];
           for (var k = 0; k < rat_list.length; k++){
               core.push(rat_list[k].observed_rat);
           }
           absolute_list = app.bindings.data.observed_rat();
           filtered = [];
           for (var j = 0; j < absolute_list.length; j++){
               for (var i = 0; i < rat_list.length; i++){
                   if (core[i] === absolute_list[j]._id){
                       filtered.push(absolute_list[j]);
                   }
               }
           }
           self.reference = filtered.map(x => _.extend({}, x, {host: _.find(app.bindings.data.observed_host(), {_id: x.host})}));
           return self.reference
       }
    });

    self.known_schtasks = ko.computed(function () {
        if (self.active() && app.bindings.data.observed_schtask()) {
            return self.active().known_schtasks.map(x => _.find(app.bindings.data.observed_schtask(), {_id: x}))
                .map(x => _.extend({}, x, {host: _.find(app.bindings.data.observed_host(), {_id: x.host})}));
        }
    });

    self.clean_log = ko.computed(function () {
        if (self.active() && self.active().clean_log[0]) {
            return self.active().clean_log;
        }
    });

    self.routed = function (active) {
        self.active_id(active);
        $(document).ready(function() {
            self.opGraph.boot('graphWindow');
        });
        if (self.op_hosts !== undefined && self.opGraph.network_graph !== undefined){
            self.opGraph.network_graph.init({nodes: self.op_hosts, links: []});
        }
    };

    self.jobs = ko.computed(function () {
        if (self.active()) {
            return _.map(self.active().jobs, x => _.find(app.bindings.data.job(), {_id: x}));
        }
    });

    // list of observed rats
    self.ob_rats = ko.computed(function () {
        if (self.active() && self.active().rat_iv_map && app.bindings.data.observed_rat()) {
            return self.active().known_rats.map(x => _.find(app.bindings.data.observed_rat(), {_id: x}))
        }
    });

    // list of the observed hosts associated with the observed rats
    self.ob_rat_hosts = ko.computed(function () {
        if (self.ob_rats() && app.bindings.data.observed_host()) {
            return self.ob_rats().map(x => _.find(app.bindings.data.observed_host(), {_id: x.host})).filter(x => x)
        }
    });

    // list of the observed hosts for only the elevated rats
    self.ob_elevated_rat_hosts = ko.computed(function () {
        if (self.ob_rats() && app.bindings.data.observed_host()) {
            return _.filter(self.ob_rats(), x => x.elevated).map(x => _.find(app.bindings.data.observed_host(), {_id: x.host})).filter(x => x)
        }
    });

    // list of all known hosts
    self.known_hosts = ko.computed(function () {
        if (self.active() && app.bindings.data.observed_host()) {
            return _.filter(app.bindings.data.observed_host(), x => _.includes(self.active().known_hosts, x._id))
        }
    });

    self._hosts = ko.computed(function() {
        var get_status = h => {
            if (_.find(self.ob_elevated_rat_hosts(), {fqdn: h.fqdn})) {
                return "active"
            } else if (_.find(self.ob_rat_hosts(), {fqdn: h.fqdn})) {
                return "involved"
            } else if (_.find(self.known_hosts(), {fqdn: h.fqdn})) {
                return "visible"
            }
            return "down"
        }

        if (self.active() && self.network_hosts() && self.ob_elevated_rat_hosts() && self.ob_rat_hosts())
        {
            var new_op_hosts = [];
            // are there any hosts that have changed state?
            for (network_host of self.network_hosts()) {
                var status = get_status(network_host);
                // does this host exist?
                var op_host = _.find(self.op_hosts, {fqdn: network_host.fqdn});
                if (op_host !== undefined) {
                    // if so update it 
                    op_host._status = status
                } else {
                    // make a new one
                    op_host = new OpHost(network_host, status)
                }
                new_op_hosts.push(op_host)
            }
            self.op_hosts = new_op_hosts;
            // is this elevated?
            self.opGraph.boot('graphWindow');
            self.opGraph.network_graph.init({nodes: self.op_hosts, links: []});
        }
    });

    var create_output = function (x) {
        if (x === undefined || x.action === undefined || x.action.rats === undefined || x.action.rats.function === undefined)
        {
            return ""
        }
        var pre = "Hostname: " + x.action.rats.hostname + "\n"
        var post = "StdOut: \n";

        if (x.action.rats.function === "execute") {
            pre = pre + "Command Line: ";
            pre = pre + x.action.rats.parameters.command_line + "\n"
            if (x.action.rats.parameters.stdin !== undefined){
                pre = pre + "StdIn: "
                pre = pre +  x.action.rats.parameters.stdin + "\n"
                }
            if (x.action.result !== undefined && x.action.result.stdout !== undefined) {
                post = post + x.action.result.stdout
            }
        } else if (x.action.rats.function === "exfil_connection") {
            post = post + x.action.result.stdout
        }
        else {
            console.log("default else: we shouldn't be here")
        }
        return pre + post
    };

    self.active_tab = ko.observable("steps");

    // changed the selected tab when the active_tab changes
    ko.computed(function () {
        $('#active_operation .active').removeClass('active');
        $('#active_operation_tab_' + self.active_tab()).addClass('active')
    });

    // changed the view when tab changes
    ko.computed(function () {
        $('#active_operation .active-tab').removeClass('active-tab').hide();
        $('.active-operation-reveal-' + self.active_tab()).addClass('active-tab').show();
    });

    self.compromised_creds = ko.computed(function () {
        if (self.active() !== undefined) {
            return self.active().known_credentials.length;
        } else {
            return 0;
        }
    });

    self.compromised_hosts = ko.computed(function () {
        if (self.active() !== undefined) {
            return _.uniq(self.ob_rat_hosts()).length;
        } else {
            return 0;
        }
    });

    self.status = ko.computed(function () {
        if (self.active()) {
            if (self.active().status === 'start') {
                return 'pending';
            }
            else if (self.active().status === 'complete'){
                return self.active().status
            }
            else {
                return 'running'
            }
        }
    });

    self.phase = ko.computed(function () {
       if (self.active()) {
           if (self.active().status === 'bootstrapping'){
               return 'bootstrap';
           }
           if (self.active().status === 'started'){
               return 'operation';
           }
           if (self.active().status === 'cleanup') {
               return self.active().status;
           }
           return 'N/A';
       }
    });

    self.action = ko.computed(function () {
        if (self.active()) {
            if (self.active().status_state === 'planning' || self.active().status_state === 'execution'){
                return self.active().status_state;
            }
            else {
                return 'N/A';
            }
        }
    });

    self.console_output = ko.computed(function () {
        switch (self.active_tab()) {
            case "jobs":
                return ko.toJSON(self.jobs(), null, 2)
        }   
    }).extend({scrollFollow: '#operation-console'});

    self.steps = ko.computed(function () {
        if (self.active()) {
            var perf_steps = self.active().performed_steps;
            var steps = [];
            for (step of perf_steps) {
                var these_jobs = _.map(step.jobs, x => _.find(app.bindings.data.job(), {_id: x}));
                var step_obj = _.find(app.bindings.data.step(), {_id: step.step});
                _.extend(step_obj, {step_bindings: step_bindings(step_obj)});
                var new_obj = _.extend({}, step, {jobs: these_jobs.map(create_output), 'step': step_obj});
                steps.push(new_obj)
            }
            return steps;
        }
    });

    self.step_click = function (item, event) {
        console.log("click: " + item + event);
        // the description element
        var $target = $(event.target.nextElementSibling);
        $target.slideToggle();
    };

    self.cancel = function () {
        if (self.active()) {
            if (confirm("You cannot restart a canceled operation. Would you like to cancel this operation anyway?")) {
                $.ajax({
                    type: 'PATCH',
                    url: '/api/networks/' + self.active().network + '/operations/' + self.active_id(),
                    data: ko.toJSON({'stop_requested': true}),
                    dataType: 'json',
                    contentType: "application/json; charset=utf-8"
                });
            }
        }
    };


    self.decide_cleanup = function (choice) {
        if (choice){
            $.ajax({
                type: 'PATCH',
                url: '/api/networks/' + self.active().network + '/operations/' + self.active_id(),
                data: ko.toJSON({'perform_cleanup': true}),
                dataType: 'json',
                contentType: "application/json; charset=utf-8"
            });
        }
        else {
            if (confirm("Not cleaning-up may interfere with future operations. Are you sure?")) {
                $.ajax({
                    type: 'PATCH',
                    url: '/api/networks/' + self.active().network + '/operations/' + self.active_id(),
                    data: ko.toJSON({'skip_cleanup': true}),
                    dataType: 'json',
                    contentType: "application/json; charset=utf-8"
                });
            }
        }
    };

    self.showCancelButton = ko.computed(function () {
        if (self.active()) {
            return self.active().status !== 'complete' && !self.active().stop_requested && self.active().status !== 'cleanup'
        }
        return false;
    });

    self.showCleanupPanel = ko.computed(function () {
        if (self.active()) {
            return self.active().status == 'cleanup' && !self.active().perform_cleanup && !self.active().skip_cleanup
        }
        return false;
    });

    self.showPhasePanel = ko.computed(function (){
       return (self.status() === 'running');
    });

    self.showActionPanel = ko.computed(function() {
       return (self.phase() === 'operation');
    });

    self.bsfDownloadLink = ko.computed(function () {
        if (self.active())
        {
            var log = _.find(app.bindings.data.log(), {_id: self.active().log});
            if (log) {
                return '/api/bsf/' + log._id
            }
        }
    });

    function step_bindings(step) {
        return _.map(step.mapping, function (x) {
            return {technique: _.find(app.bindings.data.attack_technique(), {_id: x.technique}),
                    tactic: _.find(app.bindings.data.attack_tactic(), {_id: x.tactic})}
        });
    }
}

app.bindings.operation_graph = new NetworkGraph(d3.select("#operationGraph"));
app.bindings.active_operation = new ActiveOperationModel(app.bindings.activeop_console, app.bindings.operation_graph);
