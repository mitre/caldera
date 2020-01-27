/** SECTIONS **/

function viewSection(identifier){
    let parent = $('#'+identifier);
    $(parent).insertBefore($('#atomic-blocks-end'));
    $(parent).css('display', 'block');
    window.location.hash='#'+identifier;
}

function removeSection(identifier){
    $('#'+identifier).hide();
}

function toggleSidebar(identifier) {
    let sidebar = $('#'+identifier);
    if (sidebar.is(":visible")) {
        sidebar.hide();
    } else {
        sidebar.show();
    }
}

/** ALL DROPDOWNS **/

function alphabetize_dropdown(obj) {
    let selected_val = $(obj).children("option:selected").val();
    let disabled = $(obj).find('option:disabled');
    let opts_list = $(obj).find('option:enabled').clone(true);
    opts_list.sort(function (a, b) {
        return a.text.toLowerCase() == b.text.toLowerCase() ? 0 : a.text.toLowerCase() < b.text.toLowerCase() ? -1 : 1;
    });
    $(obj).empty().append(opts_list).prepend(disabled);
    obj.val(selected_val);
}

$(document).ready(function () {
    $(document).find("select").each(function () {
        if(!$(this).hasClass('avoid-alphabetizing')) {
            alphabetize_dropdown($(this));
            let observer = new MutationObserver(function (mutations, obs) {
                obs.disconnect();
                alphabetize_dropdown($(mutations[0].target));
                obs.observe(mutations[0].target, {childList: true});
            });
            observer.observe(this, {childList: true});
        }
    });
});

/** GROUPS **/

$(document).ready(function () {
    $('#netTbl').DataTable({
        ajax: {
            url: '/plugin/chain/rest',
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            data: function ( d ) {
                return JSON.stringify({'index':'agent'});
            },
            dataSrc: ''
        },
        deferRender: true,
        rowId: 'paw',
        stateSave: true,
        columnDefs: [
            {
                targets: 0,
                data: null,
                render: function ( data, type, row, meta ) {
                    return data['paw'];
                }
            },
            {
                targets: 1,
                data: null,
                render: function ( data, type, row, meta ) {
                    return data['host'];
                }
            },
            {
                targets: 2,
                data: null,
                render: function ( data, type, row, meta ){
                    let str = "<select id=\""+data['paw']+"-status\">";
                    if ( data['trusted'] == 1 ){
                        str += "<option value=\"1\" selected=\"selected\">trusted</option>\n" +
                               "<option value=\"0\">untrusted</option>\n";
                    } else {
                        str += "<option value=\"1\">trusted</option>\n" +
                               "<option value=\"0\" selected=\"selected\">untrusted</option>";
                    }
                    str += "</select>";
                    return str;
                }
            },
            {
                targets: 3,
                data: null,
                render: {
                    _:'platform'
                }
            },
            {
                targets: 4,
                data: null,
                render: function ( data, type, row, meta ) {
                    let str = "";
                    data['executors'].forEach(function(e) {
                        str += e + "<br/>"
                    });
                    return str;
                }
            },

            {
                targets: 5,
                data: null,
                render: {
                    _:'contact'
                }
            },
            {
                targets: 6,
                data: null,
                render: {
                    _:'last_seen'
                }
            },
            {
                targets: 7,
                data: null,
                render: function ( data, type, row, meta ){
                    return "<input id=\""+data['paw']+"-sleep\" type=\"text\" value=\""+data['sleep_min']+"/"+data['sleep_max']+"\">";
                }
            },
            {
                targets: 8,
                data: null,
                render: function ( data, type, row, meta ) {
                    return "<input id=\""+data['paw']+"-watchdog\" type=\"text\" value=\""+data['watchdog']+"\">";
                }
            },
            {
                targets: 9,
                data: null,
                render: {
                    _:'pid'
                }
            },
            {
                targets: 10,
                data: null,
                render: {
                    _:'privilege'
                }
            },
            {
                targets: 11,
                data: null,
                orderDataType: 'dom-text',
                type: 'string',
                render: function ( data, type, row, meta ) {

                    return "<input value=\""+data['group']+"\" type=\"text\" id=\""+data['paw']+"-group\" name=\""+data['paw']+"-group\"><br>";
                }
            },
            {
                targets: 12,
                data: null,
                fnCreatedCell: function (td, cellData, rowData, row , col) {
                    $(td).addClass('delete-agent');
                    $(td).attr('paw', rowData['paw']);
                },
                defaultContent: "&#x274C;"
            }
        ],
        errMode: 'throw',
        buttons: [ // Add the column selection button using ColVis.
            {
                extend: 'colvis',
                text: 'Filter Columns', // Button text.
                columns: ':not(:last-child)' // Keep last column (the remove agent column) as is.
            }
        ],
        // Button, length-changer, pRocessing display element, filtering, table,
        // table Info summary, pagination control
        dom: 'Blrftip'
    });


    $('#netTbl tbody').on('click', 'td.delete-agent', function (e) {
        restRequest('DELETE', {"index": "agent", "paw": $(this).attr('paw')}, saveGroupsCallback);
    } );
});

function agent_table_refresh(){
    $('#netTbl').DataTable().ajax.reload();
}

function saveGroups(){
    let data = $('#netTbl').DataTable().rows().data();
    data.each(function (value, index) {
        let group = document.getElementById(value['paw']+'-group').value;
        let status = document.getElementById(value['paw']+'-status').value;
        let sleep = document.getElementById(value['paw']+'-sleep').value;
        let watchdog = document.getElementById(value['paw']+'-watchdog').value;
        let update = {"index":"agent", "paw": value['paw'], "group": group, "trusted": status, "watchdog": watchdog};
        let sleepArr = parseSleep(sleep);
        if (sleepArr.length !== 0) {
            update["sleep_min"] = sleepArr[0];
            update["sleep_max"] = sleepArr[1];
        }
        restRequest('PUT', update, doNothing);
    });
    let globalMinsleep = $('#globalSleepMin').val();
    let globalMaxsleep = $('#globalSleepMax').val();
    let globalWatchdog = $('#watchdog').val();
    let d = {"index": "agent","sleep_min":parseInt(globalMinsleep),"sleep_max":parseInt(globalMaxsleep),"watchdog":parseInt(globalWatchdog)};
    restRequest('PUT', d, doNothing);
}

function saveGroupsCallback(data) {
    restRequest('POST', {"index":"agent"}, reloadGroupElements);
    agent_table_refresh();
}

function reloadGroupElements(data) {
    let gp_elem = $("#queueGroup");
    gp_elem.empty();
    gp_elem.append("<option value=\"\" disabled selected>Group</option>");
    $.each(data, function(index, agent) {
        if(!gp_elem.find('option[value="'+ agent['group'] +'"]').length > 0) {
            gp_elem.append("<option id='qgroup-" + agent['group'] + "' value='" + agent['group'] + "'>" + agent['group'] + "</option>");
        }
    });
}

function parseSleep(sleep){
    let patt = new RegExp("\\d+\\/\\d+");
    if (patt.test(sleep)){
        let result = sleep.split("/");
        if (parseInt(result[0]) <= parseInt(result[1])){
            return result;
        }
        return result.reverse();
    }
    return [];
}

function doNothing() {}

/** FACTS **/

const createdCell = function(cell) {
  cell.setAttribute('contenteditable', true);
  cell.setAttribute('spellcheck', false);
  cell.addEventListener('blur', function(e) {});
};
$(document).ready(function () {
    $('#factTbl').DataTable({
            columnDefs: [{
            targets: '_all',
            createdCell: createdCell
        }]
    });
});

function toggleSourceView() {
    $('#viewSource').toggle();
    $('#addSource').toggle();
    clearFactCanvas();
}

function clearFactCanvas(){
    $('#factTbl').DataTable().clear().draw();
    let source = $('#source-name');
    source.data('id', '');
    source.val('');
    $("#profile-source-name").val($("#profile-source-name option:first").val());
    $('#source-rules').empty();
}

function loadSource() {
    restRequest('POST', {'index':'source', 'id': $('#profile-source-name').val()}, loadSourceCallback);
}

function loadSourceCallback(data) {
    clearFactCanvas();
    let source = $('#source-name');
    data[0].facts.forEach(f => {
        addFactRow([f.trait, f.value,
            '<p onclick="removeFactRow($(this))">&#x274C;</p>']);
    });
    source.data('id', data[0].id);
    applyRules(data[0].rules);
    source.val(data[0].name);
}

function addFactRow(r){
    $('#factTbl').DataTable().row.add(r).draw();
}

function removeFactRow(r){
    $('#factTbl').DataTable().row($(r).parents('tr')).remove().draw();
}

function saveSource(){
    let source = $('#source-name');
    let name = source.val();
    let id = source.data('id');
    if(!name){ alert('Please enter a name!'); return; }
    if(!id) {
        id = uuidv4();
        source.data('id', id);
    }
    let data = {};
    data['index'] = 'source';
    data['id'] = id;
    data['name'] = name;
    data['facts'] = [];
    data['rules'] = [];

    let table = $('#factTbl').DataTable();
    table.rows().invalidate('dom').draw();
    let rows = table.rows().data();
    rows.each(function (value, index) {
        data['facts'].push({'trait': value[0], 'value': value[1]});
    });
    if(data['facts'].length === 0) { alert('Please enter some facts!'); return; }

    let invalidRules = 0;
    $('#source-rules li').each(function() {
        let trait = $(this).find('#trait').val();
        let match = $(this).find('#match').val();
        let action = $(this).find('#action').val();
        if(trait === undefined || match === undefined || action === undefined){
            return;
        }
        if(action !== 'ALLOW' && action !== 'DENY') {
            invalidRules += 1;
        }
        data['rules'].push({'trait': trait, 'match': match, 'action': action});
    });
    if(invalidRules > 0) {
        alert(invalidRules + ' invalid rules!');
        return;
    }
    restRequest('PUT', data, saveSourceCallback);
}

function saveSourceCallback(data) {
    clearFactCanvas();
    appendToSelect('profile-source-name', data[0].id, data[0].name, 'view-'+data[0].id);
}

function viewRules(){
    document.getElementById("source-modal").style.display = "block";
    let sourceName = $('#source-name').val();
    $('#rules-name').text(sourceName);
}

function applyRules(rules){
    rules.forEach(r => {
        let template = $("#rule-template").clone();
        template.find('#trait').val(r.trait);
        template.find('#match').val(r.match);
        if(r.action === 0) {
            template.find('#action').val('DENY');
        } else if (r.action === 1) {
            template.find('#action').val('ALLOW');
        }
        template.show();
        $('#source-rules').append(template);
    });
}

function addRuleBlock(){
    let template = $("#rule-template").clone();
    template.show();
    $('#source-rules').append(template);
}

/** OPERATIONS **/

let atomic_interval = null;

function toggleOperationView() {
    $('#viewOperation').toggle();
    $('#addOperation').toggle();

    if ($('#togBtnOp').is(':checked')) {
        showHide('.queueOption,#opBtn,#scheduleBtn', '#operation-list');
    } else {
        showHide('#operation-list', '.queueOption,#opBtn,#scheduleBtn');
    }
}

function handleStartAction(){
    let op = buildOperationObject();
    op['index'] = 'operation';
    restRequest('PUT', op, handleStartActionCallback);
}

function checkOpBtns(){
    validateFormState(($('#operation-list').val()), '#opDelete');
    validateFormState(($('#operation-list').val()), '#reportBtn');
}

function deleteOperation(){
    let data = {'index': 'operation', 'id': parseInt($('#operation-list option:selected').attr('value'))};
    restRequest('DELETE', data, window.location.reload());
}

function handleScheduleAction(){
    let op = buildOperationObject();
    let hour = parseInt(document.getElementById("schedule-hour").value);
    let minute = parseInt(document.getElementById("schedule-minute").value);
    restRequest('PUT', {'index': 'schedule', 'operation': op, 'schedule': {'hour': hour, 'minute': minute}}, doNothing);
    flashy('operation-flash', 'Operation scheduled!');
}

function buildOperationObject() {
    let name = document.getElementById("queueName").value;
    if(!name){ alert('Please enter an operation name'); return; }

    let jitter = document.getElementById("queueJitter").value || "4/8";
    try {
        let [jitterMin, jitterMax] = jitter.split("/");
        jitterMin = parseInt(jitterMin);
        jitterMax = parseInt(jitterMax);
        if(!jitterMin || !jitterMax){
            throw true;
        }
        if(jitterMin >= jitterMax){
            alert('Jitter MIN must be less than the jitter MAX.');
            return;
        }
    } catch (e) {
        alert('Jitter must be of the form "min/max" (e.x. 4/8)');
        return;
    }
    return {
        "index": "operation",
        "name":name,
        "group":document.getElementById("queueGroup").value,
        "adversary_id":document.getElementById("queueFlow").value,
        "state":document.getElementById("queueState").value,
        "planner":document.getElementById("queuePlanner").value,
        "autonomous":document.getElementById("queueAuto").value,
        "phases_enabled":document.getElementById("queuePhasesEnabled").value,
        "obfuscator":document.getElementById("queueObfuscated").value,
        "auto_close": document.getElementById("queueAutoClose").value,
        "jitter":jitter,
        "source":document.getElementById("queueSource").value,
        "visibility": document.getElementById("queueVisibility").value
    };
}

function changeCurrentOperationState(newState){
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    if(OPERATION.finish !== ''){
        alert('This operation has finished.');
        return;
    }
    let data = {'name': parseInt(selectedOperationId), 'state': newState};
    restRequest('PUT', data, function(d){refresh()}, '/plugin/chain/operation/state');
}

function handleStartActionCallback(data){
    $("#togBtnOp").prop("checked", false).change();
    restRequest('POST', {'index':'operation'}, reloadOperationsElements);
}

function reloadOperationsElements(data){
    let op_elem = $("#operation-list");
    $.each(data, function(index, op) {
        if(!op_elem.find('option[value="'+op.id+'"]').length > 0){
            op_elem.append('<option id="' + op.id + '" class="operationOption" ' +
                'value="' + op.id +'" >' + op.name + ' - ' + op.start + '</option>');
        }
    });
    op_elem.prop('selectedIndex', op_elem.find('option').length-1).change();
}

function refresh() {
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    let postData = selectedOperationId ? {'index':'operation','id': parseInt(selectedOperationId)} : null;
    if (selectedOperationId != null){
        $('.op-selected').css('visibility', 'visible');
    }
    restRequest('POST', postData, operationCallback, '/plugin/chain/full');
}

function clearTimeline() {
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    $('.event').each(function() {
        let opId = $(this).attr('operation');
        if(opId && opId !== selectedOperationId) {
            $(this).remove();
        }
    });
}

let OPERATION = {};
function operationCallback(data){
    function spacing() { return "&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;" }
    OPERATION = data[0];
    $("#op-control-state").html(OPERATION.state + spacing() + findOpDuration(OPERATION) + spacing() + OPERATION.chain.length + ' decisions');
    if (OPERATION.autonomous) {
        $("#togBtnHil").prop("checked", true);
    } else {
        $("#togBtnHil").prop("checked", false);
    }
    applyOperationAgents(OPERATION);
    changeProgress(parseInt((OPERATION.phase / Object.keys(OPERATION.adversary.phases).length) * 100));
    clearTimeline();
    for(let i=0; i<OPERATION.chain.length; i++){
        if(OPERATION.chain[i].status === -1) {
            $('#hil-linkId').html(OPERATION.chain[i].unique);
            $('#hil-paw').html(OPERATION.chain[i].paw);
            $('#hil-command').html(atob(OPERATION.chain[i].command));
            document.getElementById("loop-modal").style.display = "block";
            return;
        } else if($("#op_id_" + OPERATION.chain[i].id).length === 0) {
            let template = $("#link-template").clone();
            let title = OPERATION.chain[i].ability.name;
            if(OPERATION.chain[i].cleanup) {
                title = title + " (CLEANUP)"
            }
            let agentPaw = OPERATION.chain[i].paw;
            template.attr("id", "op_id_" + OPERATION.chain[i].id);
            template.attr("operation", OPERATION.id);
            template.attr("data-date", OPERATION.chain[i].decide.split('.')[0]);
            template.find('#time-tactic').html('<div style="font-size: 13px;font-weight:100" ' +
                'ondblclick="rollup('+OPERATION.chain[i].id+')">agent#'+ agentPaw + '... ' +
                title + '<span id="'+OPERATION.chain[i].id+'-rs" class="tactic-find-result" ' +
                'onclick="findResults(this, OPERATION.chain['+i+'].unique)"' +
                'data-encoded-cmd="'+OPERATION.chain[i].command+'"'+'>&#9733;</span>' +
                '<span id="'+OPERATION.chain[i].id+'-rm" style="font-size:11px;float:right;" onclick="updateLinkStatus(OPERATION.chain['+i+'].unique, -2)">&#x274C;</span>' +
                '<span id="'+OPERATION.chain[i].id+'-add" style="font-size:22px;float:right;" onclick="updateLinkStatus(OPERATION.chain['+i+'].unique, -3)">&#x002B;</span></div>');
            refreshUpdatableFields(OPERATION.chain[i], template);

            template.insertAfter("#time-start");
            $(template.find("#inner-contents")).slideUp();
            template.show();
        } else {
            let existing = $("#op_id_"+OPERATION.chain[i].id);
            refreshUpdatableFields(OPERATION.chain[i], existing);
        }
    }
    if(OPERATION.finish !== '') {
        clearInterval(atomic_interval);
        atomic_interval = null;
    } else {
        if(!atomic_interval) {
            atomic_interval = setInterval(refresh, 5000);
        }
    }
}

function findOpDuration(operation){
    function convertSeconds(operationInSeconds){
        let operationInMinutes = Math.floor(operationInSeconds / 60) % 60;
        operationInSeconds -= operationInMinutes * 60;
        let secondsRemainder = operationInSeconds % 60;
        return operationInMinutes + ' min ' + Math.round(secondsRemainder) + ' sec';
    }
    if(operation.finish) {
        return convertSeconds(Math.abs(new Date(operation.finish) - new Date(operation.start)) / 1000);
    } else {
        return convertSeconds(Math.abs(new Date() - new Date(operation.start)) / 1000);
    }
}

function applyOperationAgents(operation) {
    for(let i=0; i<operation.host_group.length; i++){
        let paw = operation.host_group[i].paw;
        if($("#potential-agent-filter option[value='agent-"+paw+"'").length === 0){
             $('#potential-agent-filter').append($("<option></option>")
                    .attr("value", 'agent-'+paw)
                    .text(operation.host_group[i].display_name + '-'+operation.host_group[i].paw));
        }
    }
}

function fetchPotentialLinks() {
    $('#potential-links').empty();
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    let selectedAgent = $('#potential-agent-filter option:selected').attr('value');
    let paw = selectedAgent.split('-')[1];
    let postData = {"op_id": parseInt(selectedOperationId), "paw": paw};
    restRequest('POST', postData, potentialLinksCallback, '/plugin/chain/potential-links');
}

function potentialLinksCallback(data){
    tacticFilter = $('#potential-link-tactic-filter option:selected').attr('value')
    techniqueFilter = $('#potential-link-technique-filter option:selected').attr('value')
    for(let i=0; i<data.links.length; i++){
        let link = data.links[i];
        let template = $("#potential-link-template").clone();
        let uniqueLinkId = 'potential-link-template-'+link.executor+'-'+link.ability.id;
        if(!(tacticFilter === '-- any --' || typeof tacticFilter === 'undefined') && !(tacticFilter === ("tactic-" + link.ability.tactic)))
            continue;
        if(!(techniqueFilter === '-- any --' || typeof techniqueFilter === 'undefined') && !(techniqueFilter === ("technique-"+link.ability.technique_id)))
            continue;/**/
        template.attr('id', uniqueLinkId);
        template.find('#potential-name').html(link.ability.name);
        template.find('#potential-technique').html(link.ability.technique_id+' - '+link.ability.technique_name+' ('+link.ability.tactic+')')
        template.find('#potential-description').html(link.ability.description);
        template.find('#potential-command').html(atob(link.command));
        template.find('#potential-score').html(link.score);
        template.find('#potential-visibility').html(link.visibility.score);
        template.data('link', link);
        template.show();
        if($("#potential-link-tactic-filter option[value='tactic-"+link.ability.tactic+"'").length === 0){
            $('#potential-link-tactic-filter').append($("<option></option>")
                .attr("value", 'tactic-'+link.ability.tactic)
                .text(link.ability.tactic)
            );
        }
        if($("#potential-link-technique-filter option[value='technique-"+link.ability.technique_id+"'").length === 0){
            $('#potential-link-technique-filter').append($("<option></option>")
                .attr("value", 'technique-'+link.ability.technique_id)
                .text(link.ability.technique_id + ' - ' + link.ability.technique_name)
            );
        }
        $('#potential-links').append(template);
    }
    updatePotentialLinkCount();
}

function updateTacticFilter() {
    $('#potential-link-technique-filter').children('option:not(:first)').remove();
    $('#potential-link-technique-filter').append($("<option></option>").text("-- any --"));/**/
    fetchPotentialLinks();
}

function updateTechniqueFilter() {
    fetchPotentialLinks();
}

function closePotentialLinksModal() {
    document.getElementById('potential-modal').style.display='none';
    $('#potential-links-count').html('');
    $('#potential-links').empty();
    $('#potential-agent-filter').prop("selectedIndex", 0);
}

function addLink(l) {
    let linkDiv = l.parent().parent().parent().parent().parent().parent().parent();
    let link = linkDiv.data('link');
    let uniqueLinkId = 'potential-link-template-'+link.executor+'-'+link.ability.id;
    link.command = btoa(linkDiv.find('#potential-command').html());
    $('#'+uniqueLinkId).remove();
    updatePotentialLinkCount();
    restRequest('PUT', link, doNothing, '/plugin/chain/potential-links');
}

function updatePotentialLinkCount(){
    $('#potential-links-count').html($('#potential-links li').length + ' potential links');
}

function refreshUpdatableFields(chain, div){
    if(chain.status !== -5) {
        div.find('#'+chain.id+'-add').remove();
    }
    if(chain.collect || chain.status <= -4) {
        div.find('#'+chain.id+'-rm').remove();
    }
    if(chain.finish) {
        div.find('#'+chain.id+'-rs').css('display', 'block');
        div.find('#'+chain.id+'-rm').remove();
    }
    if(chain.status === 0) {
        applyTimelineColor(div, 'success');
    } else if (chain.status === -2) {
        div.find('#'+chain.id+'-rm').remove();
        applyTimelineColor(div, 'discarded');
    } else if (chain.status === 1) {
        applyTimelineColor(div, 'failure');
    } else if (chain.status === 124) {
        applyTimelineColor(div, 'timeout');
    } else if (chain.status === -3 && chain.collect) {
        applyTimelineColor(div, 'collected');
    } else if (chain.status === -4) {
        applyTimelineColor(div, 'untrusted');
    } else if (chain.status === -5) {
        applyTimelineColor(div, 'visibility');
    } else {
        applyTimelineColor(div, 'queued');
    }
}

function applyTimelineColor(div, color) {
    div.removeClass('collected');
    div.removeClass('queued');
    div.removeClass('visibility');
    div.addClass(color);
}

function rollup(id) {
    let inner = $("#op_id_"+id).find("#inner-contents");
    if ($("#op_id_"+id).find("#inner-contents").is(":visible")) {
        $(inner).slideUp();
    } else {
        $(inner).slideDown();
    }
}

function findResults(elem, link_id){
    document.getElementById('more-modal').style.display='block';
    $('#resultCmd').html(atob($(elem).attr('data-encoded-cmd')));
    restRequest('POST', {'index':'result','link_id':link_id}, loadResults);
}

function loadResults(data){
    if (data) {
        let res = atob(data.output);
        $.each(data.link.facts, function (k, v) {
            let regex = new RegExp(v.value, "g");
            res = res.replace(regex, "<span class='highlight'>" + v.value + "</span>");
        });
        $('#resultView').html(res);
    }
}

function downloadOperationReport() {
    function downloadObjectAsJson(data){
        let operationName = data['name'];
        let exportName = 'operation_report_' + operationName;
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
        let downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", exportName + ".json");
        document.body.appendChild(downloadAnchorNode); // required for firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    let agentOutput = $('#agent-output').prop("checked");
    let postData = selectedOperationId ? {'index':'operation_report', 'op_id': selectedOperationId, 'agent_output': Number(agentOutput)} : null;
    restRequest('POST', postData, downloadObjectAsJson, '/plugin/chain/rest');
}

function changeProgress(percent) {
    if(percent >= 100) {
        percent = 100;
        if(!OPERATION.finish) {
            percent = 99;
        }
    }
    let elem = document.getElementById("myBar");
    elem.style.width = percent + "%";
    elem.innerHTML = percent + "%";
}

$(document).ready(function(){
  $("#optional").click(function(){
    $("#optional-options").slideToggle("slow");
  });
  $("#schedules").click(function(){
    $("#schedules-options").slideToggle("slow");
  });
  $("#stealth").click(function(){
    $("#stealth-options").slideToggle("slow");
  });
  $("#autonomous").click(function(){
    $("#autonomous-options").slideToggle("slow");
  });
});

/** ADVERSARIES **/

function toggleAdversaryView() {
    //clear out canvas
    $('#profile-existing-name option:eq(0)').prop('selected', true);
    $('#profile-goal').val('');
    $('#profile-description').val('');
    $('.tempPhase').remove();
    $('.phase-headers').remove();
}

function addPhase(number) {
    let template = $("#phase-template").clone();
    if(number == null) {
        let existingPhases = $('.tempPhase').length;
        number = existingPhases + 1;
    }
    template.attr("id", "tempPhase" + number);
    template.addClass("tempPhase");
    if(number == 1) {
        template.insertBefore('#dummy');
    } else {
        template.insertAfter('#tempPhase' + (number-1));
    }
    template.show();
    let phaseHeader = $('<h4 class="phase-headers"><span class="phase-title">Phase ' + number +'</span><span class="ability-add" onclick="showPhaseModal('+number+')">&#10010; add ability</span><span class="pack-add" onclick="showPackModal('+number+')">&#10010; add pack</span><hr></h4>');
    $('#tempPhase' + number).prepend(phaseHeader);
    phaseHeader.show();
    return template;
}

function saveAdversary() {
    let identifier = $('#profile-existing-name').val();
    if(!identifier){
        identifier = uuidv4();
    }
    let name = $('#profile-goal').val();
    if(!name){ alert('Please enter an adversary name!'); return; }
    let description = $('#profile-description').val();
    if(!description){ alert('Please enter a description!'); return; }

    let abilities = [];
    $('#profile-tests li').each(function() {
        abilities.push({"id": $(this).attr('id'),"phase":$(this).data('phase')})
    });
    restRequest('PUT', {"name":name,"description":description,"phases":abilities,"index":"adversary", 'i': identifier}, saveAdversaryCallback);
}

function saveAdversaryCallback(data) {
    flashy('adv-flashy-holder', 'Adversary saved!');
    appendToSelect('profile-existing-name', data[0].adversary_id, data[0].name, 'view-'+data[0].adversary_id);
    appendToSelect('queueFlow', data[0].adversary_id, data[0].name, 'qflow-'+data[0].adversary_id);
}

function saveAbility() {
    let name = $('#ability-name').val();
    if(!name){ alert('Please enter an ability name!'); return; }
    let description = $('#ability-description').val();
    if(!description){ alert('Please enter a description!'); return; }

    let data = {};
    let platforms = {};
    $('#ttp-tests li').each(function() {
        let platform = $(this).find('#ability-platform').val();

        if(platforms[platform] === undefined) {
            platforms[platform] = {};
        }

        let executor = $(this).find('#ability-executor').val();
        let command = $(this).find('#ability-command').val();
        let payload = $(this).find('#ability-payload').val();
        let cleanup = $(this).find('#ability-cleanup').val();

        if(!name || !description || !command) {
            return;
        }
        let ex = {'command': command};
        if(payload) {
            ex['payload'] = payload;
        }
        if(cleanup) {
            ex['cleanup'] = cleanup;
        }
        platforms[platform][executor] = ex;
    });
    data['index'] = 'ability';
    data['id'] = $('#ability-identifier').val();
    data['name'] = name;
    data['description'] = description;
    data['tactic'] = $('#ability-tactic-name').val();
    data['technique'] = {'attack_id': $('#ability-tech-id').val(), 'name': $('#ability-tech-name').val()};
    data['platforms'] = platforms;
    restRequest('PUT', data, saveAbilityCallback);
}

function saveAbilityCallback(data) {
    flashy('ability-flashy-holder', 'Ability saved!');
    let options = $('#phase-modal').find('#ability-ability-filter');
    let ability = options.find(":selected").data('ability');
    if((!ability) || (ability && ability.ability_id != data[0].ability_id)) {
        let a = addPlatforms([data[0]]);
        appendAbilityToList('phase-modal', a[0]);
        options.val(a[0].name);
    }
}

function removeBlock(element){
    element.parent().parent().parent().remove();
}

function appendToSelect(field, identifier, value, optionId) {
    let exists = false;
    $('#'+field+' option').each(function(){
        if (this.value === identifier) {
            exists = true;
            return false;
        }
    });
    if(!exists) {
        $("#"+field).append($("<option></option>")
            .attr("id", optionId)
            .attr("value", identifier)
            .text(value));
    }
}

function loadAdversary() {
    restRequest('POST', {'index':'adversary', 'adversary_id': $('#profile-existing-name').val()}, loadAdversaryCallback);
}

function loadAdversaryCallback(data) {
    $('#profile-goal').val(data[0].name);
    $('#profile-description').val(data[0].description);

    $('.tempPhase').remove();
    $('.phase-headers').remove();
    $.each(data[0].phases, loadAdversaryPhase);
}

function loadAdversaryPhase(phase, abilities) {
    let template = $("#tempPhase" + phase);
    if (!template.length) {
        template = addPhase(phase);
    }

    abilities = addPlatforms(abilities);
    abilities.forEach(function(a) {
        let abilityBox = buildAbility(a, phase);
        template.find('#profile-tests').append(abilityBox);
    });
}

function loadPackCallback(data) {
    let packPhases = data[0]['phases'];
    let phaseKeys = Object.keys(packPhases);
    let curPhase = $('#pack-modal').data('phase');
    let mergePhase = $('#adv-pack-merge').is(':checked');
    let phaseMod = 0;

    if (!mergePhase) {
        shiftPhasesDown(curPhase, phaseKeys.length);
        phaseMod = curPhase;
    }
    phaseKeys.forEach(function(key) {
        loadAdversaryPhase(parseInt(key) + phaseMod, packPhases[key]);
    });
}

function shiftPhasesDown(after, number) {
    $('.tempPhase').each(function(idx, phaseDiv) {
        let i = idx + 1;
        if (i <= after) {
            return;
        }
        let newi = i + number;
        $(phaseDiv).attr('id', $(phaseDiv).attr('id').slice(0, -1) + newi);
        $(phaseDiv).find('.phase-title').text('Phase ' + newi);
        $(phaseDiv).find('.ability-box').data('phase', newi);
        $(phaseDiv).find('.ability-add').attr('onclick', 'showPhaseModal('+newi+')');
        $(phaseDiv).find('.pack-add').attr('onclick', 'showPackModal('+newi+')');
    });
}


$('#StopConditionTbl').DataTable({columnDefs: [{
            targets: '_all',
            createdCell: createdCell
        }],
        searching: false, paging: false, info: false})
 $('#StopConditionTbl').hide();


function loadPlanner() {
    restRequest('POST', {'index':'planners', 'name': $('#planner-select').val()}, loadPlannerCallback);
}

function loadPlannerCallback(data) {
    // remove old text before displaying new text
    $('#planner-title').empty();
    $('#planner-description').empty();
    $('#planner-stop-conditions').empty();
    $('#StopConditionTbl').DataTable().clear().draw();

    // fill text from API callback
    $('#add_sc_button').show();
    $('#StopConditionTbl').show();
    $('#planner-title').text(data[0]['name']);
    $('#planner-description').html(data[0]['description'].replace(/\n\n/g, '<br/>')).show();
    sc_traits = Array.from(data[0]['stopping_conditions'], x => x['trait'])
    sc_values = Array.from(data[0]['stopping_conditions'], x => x['value'])
    $('#stop-conditions').text("Stopping Conditions");
    sc =  data[0]['stopping_conditions']
    sc.forEach(element => addStopConditionRow([element['trait'], element['value'],
        '<p onclick="removeStopConditionRow($(this))">&#x274C;</p>']))
}

function addStopConditionRow(r){
    $('#StopConditionTbl').DataTable().row.add(r).draw();
}

function removeStopConditionRow(r){
    $('#StopConditionTbl').DataTable().row($(r).parents('tr')).remove().draw();
}

function savePlanner(){
    let planner = $('#planner-title');
    if(!planner){ alert('Please select a planner!'); return; }
    let data = {};
    data['index'] = 'planner';
    data['name'] = $('#planner-select').val()
    data['stopping_conditions'] = [];
    let table = $('#StopConditionTbl').DataTable();
    table.rows().invalidate('dom').draw();
    let rows = table.rows().data();
    rows.each(function (value, index) {
        data['stopping_conditions'].push({'trait': value[0], 'value': value[1]});
    });
    restRequest('PUT', data, savePlannerCallback);
}

function savePlannerCallback(data) {
    location.reload();
}

function addPlatforms(abilities) {
    let ab = [];
    abilities.forEach(function(a) {
        let exists = false;
        for(let i in ab){
            if(ab[i].ability_id === a.ability_id) {
                ab[i]['platform'].push(a.platform);
                ab[i]['executor'].push(a.executor);
                exists = true;
                break;
            }
        }
        if(!exists) {
            a['platform'] = [a.platform];
            a['executor'] = [a.executor];
            ab.push(a);
        }
    });
    return ab;
}

function buildAbility(ability, phase){
    let requirements = buildRequirements(ability.test);
    let template = $("#ability-template").clone();
    template.attr('id', ability.ability_id)
        .data('parsers', ability.parsers)
        .data('testId', ability.ability_id)
        .data('phase', phase)
        .data('requirements', requirements);

    template.find('#name').html(ability.name);
    template.find('#ability-attack').html(ability.tactic + ' | '+ ability.technique_name);

    if(requirements.length > 0) {
        template.find('#ability-metadata').append('<td><div id="ability-padlock"><div class="tooltip"><span class="tooltiptext">This ability has requirements</span>&#128274;</div></div></td>');
    }
    if(ability.cleanup) {
        template.find('#ability-metadata').append('<td><div id="ability-broom"><div class="tooltip"><span class="tooltiptext">This ability can clean itself up</span>&#128465;</div></div></td>');
    }
    if(ability.parsers.length > 0) {
       template.find('#ability-metadata').append('<td><div id="ability-parser"><div class="tooltip"><span class="tooltiptext">This ability unlocks other abilities</span>&#128273;</div></div></td>');
    }
    if(ability.payload.length > 0) {
       template.find('#ability-metadata').append('<td><div id="ability-payload"><div class="tooltip"><span class="tooltiptext">This ability uses a payload</span>&#128176;</div></div></td>');
    }
    template.find('#ability-rm').html('<div class="ability-remove"><div style="font-size:8px;">&#x274C;</div></div>');
    template.find('.ability-remove').click(function() {
        removeAbility(ability.ability_id);
    });

    ability.platform.forEach(function(p, index) {
        let icon = null;
        let exec = ability.executor[index];
        if (exec === 'psh'){exec = 'powershell';}
        else if(exec === 'pwsh') {exec = 'powershell core';}
        else if(exec === 'sh') {exec = 'shell';}
        else if(exec === 'cmd') {exec = 'commandline';}
        if(p === 'windows') {
            icon = $('<div class="tooltip"><span class="tooltiptext">Works on Windows ('+ exec +')</span><img src="/gui/img/windows.png"/></div>');
        } else if (p === 'linux') {
            icon = $('<div class="tooltip"><span class="tooltiptext">Works on Linux ('+ exec +')</span><img src="/gui/img/linux.png"/></div>');
        } else {
            icon = $('<div class="tooltip"><span class="tooltiptext">Works on MacOS ('+ exec +')</span><img src="/gui/img/macos.png"/></div>');
        }
        icon.appendTo(template.find('#icon-row'));
    });
    template.show();
    return template;
}

function buildRequirements(encodedTest){
    let matchedRequirements = atob(encodedTest).match(/#{([^}]+)}/g);
    if(matchedRequirements) {
        matchedRequirements = matchedRequirements.filter(function(e) { return e !== '#{server}' });
        matchedRequirements = matchedRequirements.filter(function(e) { return e !== '#{group}' });
        matchedRequirements = matchedRequirements.filter(function(e) { return e !== '#{location}' });
        matchedRequirements = matchedRequirements.filter(function(e) { return e !== '#{paw}' });
        matchedRequirements = [...new Set(matchedRequirements)];
        return matchedRequirements.map(function(val){
           return val.replace(/[#{}]/g, "");
        });
    }
    return [];
}

function removeAbility(ability_id){
    $('#'+ability_id).remove();
}

function populateTechniques(parentId, exploits){
    exploits = addPlatforms(exploits);
    let parent = $('#'+parentId);
    $(parent).find('#ability-technique-filter').empty().append("<option disabled='disabled' selected>Choose a technique</option>");

    let tactic = $(parent).find('#ability-tactic-filter').find(":selected").data('tactic');
    let found = [];
    let showing = [];
    exploits.forEach(function(ability) {
        if(ability.tactic.includes(tactic) && !found.includes(ability.technique_id)) {
            found.push(ability.technique_id);
            appendTechniqueToList(parentId, tactic, ability);
            showing += 1;
        }
    });
}

function populateAbilities(parentId, exploits){
    exploits = addPlatforms(exploits);
    let parent = $('#'+parentId);
    $(parent).find('#ability-ability-filter').empty();

    let showing = [];
    let attack_id = $(parent).find('#ability-technique-filter').find(":selected").data('technique');
    exploits.forEach(function(ability) {
        if(attack_id === ability.technique_id) {
            appendAbilityToList(parentId, ability);
            showing += 1;
        }
    });
    $(parent).find('#ability-ability-filter').prepend("<option disabled='disabled' selected>"+showing.length+" abilities</option>");
}

function appendTechniqueToList(parentId, tactic, value) {
    $('#'+parentId).find('#ability-technique-filter').append($("<option></option>")
        .attr("value", value['technique_id'])
        .data("technique", value['technique_id'])
        .text(value['technique_id'] + ' | '+ value['technique_name']));
}

function appendAbilityToList(parentId, value) {
    $('#'+parentId).find('#ability-ability-filter').append($("<option></option>")
        .attr("value", value['name'])
        .data("ability", value)
        .text(value['name']));
}

function showAbility(parentId, exploits) {
    $('#ability-name').val('');
    $('#ability-description').val('');
    $('#ttp-tests').empty();

    let aid = $('#'+parentId).find('#ability-ability-filter').find(":selected").data('ability');
    $('#ability-identifier').val(aid.ability_id);
    $('#ability-name').val(aid.name);
    $('#ability-description').val(aid.description);
    $('#ability-tactic-name').val(aid.tactic);
    $('#ability-tech-id').val(aid.technique_id);
    $('#ability-tech-name').val(aid.technique_name);

    exploits.forEach(function(ability) {
        if(aid.ability_id === ability.ability_id) {
            let template = $("#ttp-template").clone();
            template.find('#ability-platform').val(ability.platform);
            template.find('#ability-executor').val(ability.executor);
            template.find('#ability-command').val(atob(ability.test));
            template.find('#ability-cleanup').val(atob(ability.cleanup));
            template.find('#ability-payload').val(ability.payload);
            template.show();
            $('#ttp-tests').append(template);
        }
    });
}

function showPack() {
    $('#pack-phases').empty();

    restRequest('POST', {'index':'adversary', 'adversary_id': $('#adv-pack-filter').val()}, showPackCallback);
}

function showPackCallback(data) {
    Object.keys(data[0].phases).forEach(function(phaseID) {
        let phaseTemplate = $("#pack-phase-template").clone();
        phaseTemplate.attr('id', 'pack-phase' + phaseID);

        let abilities = addPlatforms(data[0].phases[phaseID]);
        abilities.forEach(function(ability) {
            let template = $("#pack-ability-template").clone();
            template.find('.ability-identifier').text(ability.ability_id);
            template.find('.ability-name').text(ability.name);
            template.find('.ability-description').text(ability.description);
            template.find('.ability-tactic').text(ability.tactic);
            template.find('.ability-tech-id').text(ability.technique_id);
            template.find('.ability-tech-name').text(ability.technique_name);
            template.find('.ability-platforms').text(ability.platform.join(', '));
            template.show();
            phaseTemplate.append(template);
        });

        phaseTemplate.show();
        $('#pack-phases').append("<h4>Phase " + phaseID + "</h4>");
        $('#pack-phases').append(phaseTemplate);
    });
}

function addExecutorBlock(){
    let template = $("#ttp-template").clone();
    template.show();
    $('#ttp-tests').prepend(template);
}

function showPhaseModal(phase) {
    $('#phase-modal').data("phase", phase);
    $('#ability-identifier').text(uuidv4());
    document.getElementById("phase-modal").style.display="block";
}

function showPackModal(phase) {
    $('#pack-modal').data("phase", phase);
    document.getElementById("pack-modal").style.display="block";
}

function freshId(){
    $('#ability-identifier').val(uuidv4());
}

function uploadPayload() {
    let file = document.getElementById('uploadPayloadFile').files[0];
    let fd = new FormData();
    fd.append('file', file);
    $.ajax({
         type: 'POST',
         url: '/plugin/chain/payload',
         data: fd,
         processData: false,
         contentType: false
    }).done(function (){
        let exists = $("#ability-payload option").filter(function (i, o) { return o.value === file.name; }).length > 0;
        if(!exists) {
            $('.ability-payload').each(function(i, obj) {
                $(this).append(new Option(file.name, file.name));
            });
        }
    })
}
$('#uploadPayloadFile').on('change', function (event){
    if(event.currentTarget) {
        let filename = event.currentTarget.files[0].name;
        if(filename){
            uploadPayload();
        }
    }
});

function addAbilityToPhase() {
    let parent = $('#phase-modal');
    let phase = $(parent).data('phase');
    let ability = $('#phase-modal').find('#ability-ability-filter').find(":selected").data('ability');
    let abilityBox = buildAbility(ability, phase);
    $('#tempPhase' + phase).find('#profile-tests').append(abilityBox);
    document.getElementById('phase-modal').style.display='none';
}

function addPackToPhase() {
    restRequest('POST', {'index':'adversary', 'adversary_id': $('#adv-pack-filter').val()}, loadPackCallback);
    document.getElementById('pack-modal').style.display='none';
}

function checkOpformValid(){
    validateFormState(($('#queueName').val()), '#opBtn');
    validateFormState(($('#queueName').val()) && ($('#schedule-hour').prop('selectedIndex') !== 0) && ($('#schedule-minute').prop('selectedIndex') !== 0),
        '#scheduleBtn');
}

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    let r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function resetMoreModal() {
    let modal = $('#more-modal');
    modal.hide();
    modal.find('#resultCmd').text('');
    modal.find('#resultView').text('');
}

/** DUK MODALS */

function openDuk2(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... you can link abilities together by matching the output property from an ability\'s ' +
        'parser to variables inside another ability\'s command. Variables can be identified by looking for ' +
        '#{variable_name_goes_here} syntax.');
}

function openDuk3(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... You can click the ' +
        'star icon to view the standard output or error from the command that was executed. Highlighted text indicates ' +
        'facts which were learned from executing the step.');
}

function openDuk4(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... The default agent is ' +
        'called 54ndc47 (sandcat) and can be found in the plugins section. 54ndc47 is a multi-platform agent which ' +
        'can be deployed by just pasting a 1-line command into a terminal.');
}

function openDuk5(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... A fact trait can be placed inside any ability command as a variable, allowing '+
        'you to create extensible abilities. '+
        'Additionally, sources can include rules which can restrict agents from using specific traits.');
}

function openDuk6(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... an operation chain contains all the decisions - or links - which were made by ' +
        'the planner, utilizing the abilities contained inside the chosen adversary profile. This list shows, per agent, ' +
        'the potential links that will not run as part of the operation but otherwise could. Add them as you wish.');
}

function openDuk7(){
    document.getElementById("duk-modal").style.display="block";
    $('#duk-text').text('Did you know... Stopping conditions are trait and value pairs that can signal to '+
        'the adversary emulation system that it should stop an operation immediately. You can add them to '+
        'your planners here. For example, let\'s say that I want an operation to stop once I laterally move '+
        'to machine named "domaincontroller.acme". I could add a stopping condition below with a trait of '+
        'local.host.name and a value of domaincontroller.acme. If during the course of an operation an ability '+
        'parsers out a fact that matches the stopping condition, the planner will stop generating links and exit '+
        'the operation. ');
}

/** HUMAN-IN-LOOP */

function submitHilChanges(status){
    document.getElementById("loop-modal").style.display = "none";
    let command = $('#hil-command').val();
    updateLinkStatus($('#hil-linkId').html(), status, btoa(command));
    refresh();
    return false;
}

function updateLinkStatus(linkId, status, command='') {
    let data = {'index':'chain', 'link_id': linkId, 'status': status};
    if(command) {
        data['command'] = command;
    }
    restRequest('PUT', data, doNothing);
}

function toggleHil(){
    let op_id = $('#operation-list option:selected').attr('value');
    let data = {};
    if(OPERATION.autonomous){
        data['autonomous'] = 0;
    } else{
        data['autonomous'] = 1;
    }
    restRequest('PUT', data, function(d){refresh()}, `/plugin/chain/operation/${op_id}`);
}

function hilApproveAll(){
    document.getElementById("loop-modal").style.display = "none";
    let currentLinkUnique = $('#hil-linkId').html();
    let currentLinkId = currentLinkUnique.split('-')[1];
    for(let i=0; i<OPERATION.chain.length; i++){
        let nextLink = OPERATION.chain[i];
        if (nextLink.id >= currentLinkId){
            let data = {'index':'chain','link_id': nextLink.unique, 'status': -3};
            restRequest('PUT', data, doNothing);
        }
    }
    if (!OPERATION.autonomous){
        toggleHil();
    }
    refresh();
    return false;
}
