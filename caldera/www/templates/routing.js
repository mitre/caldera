var pages = {};
$('.page').each(function() {
    pages[$(this).attr('id')] = this;
});

function switchPage(link) {
    $('.page').css('display', 'none');
    if (pages[link]) {
        $(pages[link]).css('display', 'block');
    }
}

function handleChanges(newHash, oldHash) {
    crossroads.parse(newHash);
}

var focus;

function handleRoute(route, id) {
    crossroads.addRoute(route , function(message) {
        if (focus !== undefined && focus.unfocus != undefined) {
            focus.unfocus();
        }

        var object = app.bindings[id];
        if (object && object.routed !== undefined) {
            object.routed.apply(this, arguments);
        }
        switchPage(id);
        focus = object;
        if (object && object.focus !== undefined) {
            object.focus();
        }
    })
}

handleRoute('main', 'main');
handleRoute('agent', 'agent');
handleRoute('client', 'client');
handleRoute('add_adversary', 'add_adversary');
handleRoute('add_adversary/{id}', 'add_adversary');
handleRoute('adversaries', 'adversaries');
handleRoute('active_adversary/{id}', 'active_adversary');
handleRoute('attack_matrix', 'attack_matrix');
handleRoute('command_window', 'commandWindow');
handleRoute('globalconsole', 'globalconsole');
handleRoute('activeop_console', 'activeop_console');
handleRoute('incomplete_jobs', 'incomplete_jobs');
handleRoute('add_network', 'add_network');
handleRoute('networks', 'networks');
handleRoute('active_network/{id}', 'active_network');
handleRoute('add_operation', 'operationForm');
handleRoute('operations', 'operations');
handleRoute('active_operation/{id}', 'active_operation');
handleRoute('settings', 'settings');
handleRoute('editor', 'editor');
handleRoute('step_config/{id}', 'step_config');
handleRoute('step_view/{id}', 'step_view');
handleRoute('steps{?query}', 'steps');
handleRoute('steps', 'steps');
handleRoute('rat_command_window', 'rat_command_window');
handleRoute('artifactlists', 'artifactlists');
handleRoute('add_artifactlist', 'add_artifactlist');
handleRoute('add_fancy_artifactlist/{id}', 'add_fancy_artifactlist');
handleRoute('add_fancy_artifactlist', 'add_fancy_artifactlist');

