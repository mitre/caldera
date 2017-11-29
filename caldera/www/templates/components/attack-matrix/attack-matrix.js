function AttackMatrix() {
    var self = this;

    self.matrixCols = ko.observableArray([]);
    self.techniques = ko.pureComputed(app.bindings.data.attack_technique).extend({ rateLimit: 200 });
    self.steps = ko.pureComputed(app.bindings.data.step).extend({ rateLimit: 200 });
    self.listing = ko.pureComputed(app.bindings.data.attack_list).extend ({ rateLimit:200});
    self.mode = ko.observable('all');

    function compare(a,b){
        if (a.name < b.name) {
            return -1;
        }
        if (a.name > b.name) {
            return 1;
        }
        return 0;
    }

    self.produceGrid = function (techniques) {
      var dedup = [];
      var defaultBackground = "white";
      var list = "";
      if (self.listing()[0] == null){
           // catch for case where table attempts to load prior
           // to database population
           return [null,null];
      }
      else {
          list = self.listing()[0].master_list;
      }
      var cannon_list = list.split(", ");

      build_tech = function(name, tactic, _id, defaultBackground) {
          return {name: name,
                    tactic: tactic,
                    _id: _id,
                    defaultBackground: defaultBackground,
                    background: defaultBackground};
        };
      _.forEach(techniques, function (technique) {
        var name = technique.name;
        var _id = technique._id;
        _.forEach(technique.tactics, function (tactic) {
            if (self.mode() === 'all') {
                dedup.push(build_tech(name, tactic, _id, defaultBackground));
            }
            else if (self.mode() === 'windows'){
                if (technique.isWindows){
                    dedup.push(build_tech(name, tactic, _id, defaultBackground));
                }
            }
            else if (self.mode() === 'mac') {
                if (technique.isMac) {
                    dedup.push(build_tech(name, tactic, _id, defaultBackground));
                }
            }
            else if (self.mode() === 'linux'){
                if (technique.isLinux) {
                    dedup.push(build_tech(name, tactic, _id, defaultBackground));
                }
            }
        });
      });
      var columns = [];
      var coltemp = [];
      dedup.sort();
      _.forEach(dedup, function (technique) {
        var col = _.find(coltemp, {_id: technique.tactic});
        if (col === undefined) {
          var tactic = _.find(app.bindings.data.attack_tactic(), {_id: technique.tactic});
          col = {_id: technique.tactic, name: tactic.name, techniques: []};
          coltemp.push(col);
        }
        col.techniques.push(technique);
      });
      coltemp.forEach(function(entry){
          entry.techniques.sort(compare);
        });
      for (var i=0; i < coltemp.length; i++) {
          for (var j=0; j < coltemp.length; j++) {
              if (coltemp[j].name === cannon_list[i]) {
                  columns.push(coltemp[j]);
                  break;
              }
          }
      }
      var longestLength = 0;
      _.forEach(columns, function (col) {
        longestLength = col.techniques.length > longestLength ? col.techniques.length : longestLength;
      });

      var transposed = [];
      for (var i=0; i < longestLength; i++) {
        transposed.push([]);
        for (var j=0; j < columns.length; j++) {
          if (i >= columns[j].techniques.length) {
            transposed[i].push({name: "", defaultBackground: "white", background: 'white', outline: ''});
          } else {
            transposed[i].push(columns[j].techniques[i]);
          }
        }
      }
      return [columns, transposed];
    };

    clear_buttons = function() {
        $('#btn_a').removeClass('active');
        $('#btn_w').removeClass('active');
        $('#btn_i').removeClass('active');
        $('#btn_m').removeClass('active');
    };

    set_all = function() {
        self.mode('all');
        clear_buttons();
        $('#btn_a').addClass('active');
    };
    set_mac = function(){
        self.mode('mac');
        clear_buttons();
        $('#btn_m').addClass('active');
    };
    set_windows = function() {
        self.mode('windows');
        clear_buttons();
        $('#btn_w').addClass('active');
    };
    set_linux = function() {
        self.mode('linux');
        clear_buttons();
        $('#btn_l').addClass('active');
    };

    self.matrix = ko.computed(function () {
        var gridRes = self.produceGrid(self.techniques(), true);
        var matrixColumns = gridRes[0];
        var grid = gridRes[1];
        // highlight items that are used by steps
        for (var x = 0; x < self.steps().length; x++) {
            for (var y = 0; y < self.steps()[x].mapping.length; y++) {
                var tactic = self.steps()[x].mapping[y].tactic;
                var technique = self.steps()[x].mapping[y].technique;
                // get index of tactic in matrix cols
                var columnNumber = _.findIndex(matrixColumns, {_id: tactic});
                if (columnNumber >= 0) {
                    for (var rowNumber = 0; rowNumber < grid.length; rowNumber++) {
                        if (grid[rowNumber][columnNumber]._id === technique) {
                            if (self.mode() === 'all' || self.mode() === 'windows') {
                                grid[rowNumber][columnNumber].class = 'highlight';
                            }
                        }
                    }
                }
            }
        }
        self.matrixCols(matrixColumns);
        return grid;
    });
}

app.bindings.attack_matrix = new AttackMatrix();