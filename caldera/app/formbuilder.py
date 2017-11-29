# The general idea here is to build an html form/associated js for a set of javascript functions

# functions + argument types
# generate html form for each function
# must be an api stub that accepts API calls
# also must inject this into html page
#
import inspect
from typing import List
from .util import CaseException
from .engine.objects import Host


def generate_whole_html(this_id, page_name, function_list, glyphicon=None):
    if glyphicon is None:
        glyphicon = ""

    # build a selector for all the functions
    nav_html = """<li> <a href="#{0}">
                            <span class="glyphicon {2}" aria-hidden="true"></span> {1}
                            </a>
                        </li>""".format(this_id, page_name, glyphicon)

    html = """<div id="{0}" data-bind="with: {0}" class="page">
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h1 class="panel-title">{1}</h1>
                </div>
                <div class="panel-body">
                    <form class="form-horizontal">
                        <div class="form-group">
                            <label class="control-label required col-sm-3"><abbr title="required">*</abbr>Select a Function</label>
                            <div class="col-sm-9">
                                <select class="form-control"
                                        data-bind="options: selections,
                                                   optionsCaption: 'Choose One...',
                                                   value: selected">
                                </select>
                            </div>
                        </div>
                        <div class="command-console" data-bind="foreach: commands">
                            <pre data-bind="text: $data"></pre>
                        </div>
                        <button class="btn btn-default btn-lg" data-bind="click:clear" type="button">Clear</button>
                    </form>""".format(this_id, page_name)

    js = ""

    for function in function_list:
        new_html, new_js = generateHtml(function)
        html += '\n' + new_html
        js += '\n' + new_js
        # js name is generated<fname>
        # html id is generated<fname>

    html += """</div>
           </div>
       </div>
    </div>
    </div>"""

    js += """\nvar {1} = function() {{
    var self = this;
    self.selections = ko.observableArray([{2}]);
    self.selected = ko.observable('{4}');
    self.commands = ko.observableArray([]);
    self.clear = function() {{
        self.commands([])
    }};
    {3}
}};

app.bindings.{0} = new {1}();
handleRoute('{0}', '{0}');""".format(this_id,
                                     this_id[0].capitalize() + this_id[1:],
                                     ','.join(['"' + x.__name__ + '"' for x in function_list]),
                                     '\n'.join(['self.{0} = new generated{0}(self);'.format(x.__name__) for x in function_list]),
                                     function_list[0].__name__)
    return html, js, nav_html


def generateHtml(function):
    name = function.__name__
    sig = inspect.signature(function)
    html = """<div id="generated{0}" data-bind="with: {0}">
       <form class="form-horizontal" data-bind="submit: submit, visible: $parent.selected() === '{0}'">
    """.format(name)
    js = """var generated{0} = function(parent) {{
    var self = this;""".format(name)

    on_submit = {}
    for param in sig.parameters.keys():
        if str == sig.parameters[param].annotation:
            new_html, new_js, new_var = buildControlForStrParam(name, param)
        elif List[str] == sig.parameters[param].annotation:
            new_html, new_js, new_var = buildControlForListParam(name, param)
        elif Host == sig.parameters[param].annotation:
            new_html, new_js, new_var = buildControlForDbParam(name, param)
        # this is so hacky but we need it to support 3.5.2 and 3.5.3
        elif str(sig.parameters[param].annotation).startswith('typing.Union'):
            new_html, new_js, new_var = buildControlForStrParam(name, param)
        elif bool == sig.parameters[param].annotation:
            new_html, new_js, new_var = buildControlForBoolParam(name, param)
        else:
            raise CaseException
        html += '\n' + new_html
        js += '\n' + new_js
        on_submit[param] = new_var

    html += """\n<button class="btn btn-primary" type="submit">Submit</button>
            </form>
        </div>"""

    var_string = ', '.join(['{}: self.{}'.format(k, v) for k, v in on_submit.items()])

    js += """\nself.submit = function() {{
        var obj = {{{1}}};

        var jsObj = ko.toJS(obj);
        var json = ko.toJSON(jsObj);
        var command = ko.observable();
        parent.commands.push(command);
        command("[{0}] > " + json);
        $.ajax({{
            type: 'POST',
            url: '/api/generated/{0}',
            data: json,
            dataType: 'json',
            contentType:"application/json; charset=utf-8"
        }}).done(function(data) {{
            if (data) {{
                var printable = _.isString(data) ? data : JSON.stringify(data, null, 2);
                command(command() + "\\n" + printable)
            }};
        }});
    }};}}""".format(name, var_string)
    return html, js


def buildControlForDbParam(funcname, paramname):
    html = """<div class="form-group">
            <label for="{0}{1}" class="control-label required col-sm-3"><abbr title="required">*</abbr>{1}</label>
            <div class="col-sm-9">
                <select id="{0}{1}" class="form-control"
                        data-bind="options: optionsFor{0}{1},
                                   optionsCaption: 'Choose One...',
                                   optionsText: function(item) {{
                                       return item.hostname;
                                   }},
                                   optionsValue: '_id',
                                   value: {0}{1}">
               </select>
           </div>
       </div>""".format(funcname, paramname)

    # create a knockout var for every parameter
    js = """
    self.optionsFor{0}{1} = app.bindings.data.host;
    self.{0}{1} = ko.observable();
    """.format(funcname, paramname)

    return html, js, "{}{}".format(funcname, paramname)


def buildControlForStrParam(funcname, paramname):
    html = """<div class="form-group">
                  <label for="{0}{1}" class="control-label required col-sm-3"><abbr title="required">*</abbr>{1}</label>
                  <div class="col-sm-9">
                      <input id="{0}{1}" type="text" class="form-control" data-bind="value: {0}{1}">
                  </div>
              </div>""".format(funcname, paramname)

    # create a knockout var for every parameter
    js = """
    self.{0}{1} = ko.observable("");
        """.format(funcname, paramname)

    return html, js, "{}{}".format(funcname, paramname)


def buildControlForBoolParam(funcname, paramname):
    html = """<div class="checkbox col-sm-offset-3">
        <label>
            <input type="checkbox" data-bind="checked: {0}{1}"> {1}
        </label>
      </div>""".format(funcname, paramname)

    # create a knockout var for every parameter
    js = """
    self.{0}{1} = ko.observable(false);
        """.format(funcname, paramname)

    return html, js, "{}{}".format(funcname, paramname)


def buildControlForListParam(funcname, paramname):
    html = """<div class="form-group">
                  <label for="{0}{1}" class="control-label required col-sm-3"><abbr title="required">*</abbr>{1} [List]</label>
                  <div class="col-sm-9">
                      <input id="{0}{1}" type="text" class="form-control" data-bind="value: raw_{0}{1}">
                  </div>
              </div>""".format(funcname, paramname)

    # create a knockout var for every parameter
    js = """
    self.raw_{0}{1} = ko.observable("");
    self.{0}{1} = ko.computed(function () {{
        return self.raw_{0}{1}().split(',');
    }});
        """.format(funcname, paramname)

    return html, js, "{}{}".format(funcname, paramname)