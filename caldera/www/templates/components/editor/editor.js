function ScriptEditor() {
    var self = this;

    self.editor = ace.edit("editor_window");
    self.editor.setTheme("ace/theme/monokai");
    self.editor.getSession().setMode("ace/mode/powershell");
    self.editor.gotoLine(0);
    self.file = '';

    self.filename = ko.observable("");

    loadTree = function () {
        $.ajax({
            type: 'GET',
            url: '/api/list_file',
            data: ko.toJSON(),
            dataType: 'json',
            contentType: "application/json; charset=utf-8"
        }).success(
            function (data) {
                self.swin = $('#selection_window').on('changed.jstree', function (e, data) {
                    var r = [];
                    r.push(data.instance.get_node(data.selected[0]).id);
                    self.file = r.join();
                    loadFile();
                }).jstree({
                    'core': {
                        'data': data
                    }
                });
            }
        );
    };

    loadTree();
    saveFile = function() {
        core = self.editor.getValue();
        $.ajax({
            type: 'POST',
            url: '/api/save_file',
            data: ko.toJSON({edited: core, file: self.file}),
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        });
        $('#selection_window').jstree(true).refresh();
    };

    loadFile = function() {
        $.ajax({
            type: 'POST',
            url: '/api/load_file',
            data: ko.toJSON({file: self.file}),
            dataType: 'json',
            contentType: "application/json; charset=utf-8"
        }).success(
            function (data) {
                self.filename(self.file);
                self.editor.setValue(data);
                self.editor.gotoLine(0);
            }
        );
    };

    self.editing_file = ko.computed( function () {
        if (self.filename() !== '') {
                return self.filename();
        }
        return 'No file selected';
    });

    self.fileOK = ko.computed(function () {
        if (self.filename() === "") {
            return true;
        }
        return self.filename().endsWith('-ps1');
    });

    self.file_extend = ko.computed(function () {
        if (self.filename().includes("[-d-]")) {
            return '[Directory]';
        }
        var seg = self.filename().split('\\');
        seg = seg[seg.length-1].split("-");
        seg = seg[seg.length-1];
        seg = "[-" + seg + "]";
        return seg;
    });
}

app.bindings.scriptEditor = new ScriptEditor();