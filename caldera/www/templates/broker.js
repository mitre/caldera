app.bindings.data = {};

var ddp_client = function (data) {
    var self = this;
    self.connection = null;
    self.data = data;
    self.counter = 1;
    self.allsubs = [];
    self.subs = [];
    self.connected = ko.observable(false);

    self._removeObjectID = function (obj) {
        var ret = obj;

        if (obj === undefined || obj === null) {
            return ret
        }
        // iterate over dict
        Object.keys(obj).forEach(function (key) {
            var value = obj[key];
            if (value !== null && typeof value === 'object' && value.hasOwnProperty("_bsontype") && value._bsontype == "ObjectID") {
                ret[key] = value.toString()
            } else if (value !== null && typeof value === 'object') {
                ret[key] = self._removeObjectID(value)
            } else {
                ret[key] = value
            }
            
        });
        return ret
    };

    self.connect = function (uri) {
        for (var m in self.data) {
            self.data[m].removeAll()
        }
        self.connection = new WebSocket(uri);
        self.connection.binaryType = 'arraybuffer';
        self.connection.onclose = function () {
            self.connected(false);
            self.connect(uri);
        };
        self.connection.onopen = function () {
            self.subs = self.allsubs.slice();
            self.connected(true);
            self.connection.send(JSON.stringify({'msg': "connect"}));
            while (self.subs.length) {
                var sub = self.subs.pop();
                self.connection.send(sub);
            }
        };
        self.connection.onerror = function () {
            app.bindings.login_modal.test_logon()
        };
        self.connection.onmessage = function (e) {
            var d = bson().BSON.deserialize(new Uint8Array(e.data));
            d = self._removeObjectID(d)
            if ("bson" in d && 'collection' in d && 'msg' in d && d['msg'] === 'insert') {
                var fields = bson().BSON.deserialize(d["bson"].buffer);
                fields = self._removeObjectID(fields);
                var id = fields['_id'];
                var pend_updates = _.filter(self.data[d['collection']](), {_id: id});
                if (pend_updates.length > 0) {
                    _.map(pend_updates, x => {
                        $.extend(x, fields)
                    })
                    self.data[d['collection']].valueHasMutated()
                } else {
                    self.data[d['collection']].push(fields)
                }
            }
            if ("fields" in d && '_id' in d['fields'] && 'collection' in d && 'msg' in d && d['msg'] === 'changed') {
                var id = d['fields']['_id'];
                var pend_updates = _.filter(self.data[d['collection']](), {_id: id});
                if (pend_updates.length > 0) {
                    _.map(pend_updates, x => {
                        _.forIn(d['fields'], (val, key) => {
                            var spl = key.split(".")
                            // check that last element is not number
                            if (/^[0-9]+$/.test(spl[spl.length - 1])) {
                                spl.push(+spl.pop())
                            }
                            var lookup = x
                            for (var i = 0; i < spl.length; i++) {
                                if (i == spl.length -  1) {
                                    // we are at the end so set the last value
                                    lookup[spl[i]] = val
                                } else {
                                    lookup = lookup[spl[i]]
                                }
                            }
                        })
                    })
                    self.data[d['collection']].valueHasMutated();
                } else {
                    // Note: We get here because sometimes mongo likes to emit 'update' for objects that don't exist
                    // Who knows why?
                    self.data[d['collection']].push(d['fields'])
                }
            } else if ("msg" in d && d['msg'] === 'removed' && 'id' in d) {
                var id = d['id'];
                self.data[d['collection']].remove( function (item) { return item._id === id } )
            }
        }
    };
    self.subscribe = function (collection) {
        if (self.connection == null) {
            console.log("Cannot subscribe to an unconnected DDP Server");
            return
        }
        var msg = JSON.stringify({'msg': "sub", "name": collection, "id": self.counter.toString()});
        self.allsubs.push(msg);
        self.counter++;

        if (self.connection.readyState === 0) {
            // Connecting
            self.subs.push(msg)
        } else if (self.connection.readyState === 1) {
            // Open
            self.connection.send(msg)
        } else {
            console.log("Websocket error connecting")
        }

        self.data[collection] = ko.observableArray([])
    }
};

app.ddp_client = new ddp_client(app.bindings.data);
app.ddp_client.connect(window.location.protocol.replace('http', 'ws') + '//' + window.location.host + '/websocket');
app.ddp_client.subscribe('domain');
app.ddp_client.subscribe('host');
app.ddp_client.subscribe('network');
app.ddp_client.subscribe('operation');
app.ddp_client.subscribe('rat');
app.ddp_client.subscribe('observed_rat');
app.ddp_client.subscribe('observed_host');
app.ddp_client.subscribe('observed_file');
app.ddp_client.subscribe('observed_schtask');
app.ddp_client.subscribe('rat_command');
app.ddp_client.subscribe('job');
app.ddp_client.subscribe('log');
app.ddp_client.subscribe('step');
app.ddp_client.subscribe('adversary');
app.ddp_client.subscribe('active_connection');
app.ddp_client.subscribe('agent');
app.ddp_client.subscribe('attack_technique');
app.ddp_client.subscribe('attack_tactic');
app.ddp_client.subscribe('attack_list');
app.ddp_client.subscribe('attack_group');
app.ddp_client.subscribe('setting');
app.ddp_client.subscribe('artifactlist');
