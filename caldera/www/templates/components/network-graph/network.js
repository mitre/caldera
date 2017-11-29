function createNetworkGraph(parentNode, dims, source) {
    var temp = document.getElementById(source).offsetWidth;
    if (source === 'graphWindow') {
        if (temp === 0) {
            temp = dims.win;
        }
        else {
            dims.win = temp;
        }
    }
    else if (source === 'networkView') {
        if (temp === 0) {
            temp = dims.op;
        }
        else {
            dims.op = temp;
        }
    }

    var width = 0;
    var height = 0;
    if (temp > 60) {
        width = temp - 60;
        height = 500;
    }

    var force = d3.layout.force()
        .charge(-300)
        .linkDistance(300)
        .gravity(0.05)
        .size([width, height]);

    d3.select("svg").remove();

    var svg = parentNode
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .attr('id', 'networkGraph');

    var link = svg.append('g').attr('id', 'links').selectAll(".link").data([])
    var node = svg.append('g').attr('id', 'nodes').selectAll(".node").data([])

    // graph is a knockout observable
    var init = function(graph) {
        force
            .nodes(graph.nodes)
            .links(graph.links)
            .start();

        refresh();
    }

    var refresh = function() {
        link = link.data(force.links());
        link.exit().remove();
        link.enter().append("line")
            .attr("class", "link")
            .style("stroke-width", function(d) { return Math.sqrt(d.value); });

        node = node.data(force.nodes());
        node.exit().remove();
        nodes = node.enter().append("g")
        nodes.append("circle")
            .attr("r", 45)

        nodes.append("title")
            .text(function(d) { return d.hostname; });
        nodes.append("text")    
            .text(function(d) { return d.hostname; })
            .attr("y", "0.3em")
            .attr("text-anchor", "middle");

        nodes.call(force.drag());

        force.on("tick", function() {
            link.attr("x1", function(d) { return d.source.x; })
                .attr("y1", function(d) { return d.source.y; })
                .attr("x2", function(d) { return d.target.x; })
                .attr("y2", function(d) { return d.target.y; });

            node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")" })
                .attr('class', d => 'node ' + d.status());
        });
    };

    return {
        svg: svg,
        force: force,
        init: init,
        refresh: refresh
    };

}

// Bindings
function NetworkGraph(parentNode) {
    var self = this;
    self.target = ko.observable();
    self.current = ko.observable();
    self.dims = {win: 0, op: 0};

    self.boot = function(source) {
        self.network_graph = createNetworkGraph(parentNode, self.dims, source);
    };

    self.pivot = function (source, target) {
        if (source && target && (source != target)) {
            self.network_graph.force.links().push({source: source, target: target});
            self.network_graph.refresh();
        }
    };

}
