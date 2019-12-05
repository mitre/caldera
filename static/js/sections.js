
$(document).ready(function () {
    if(localStorage.getItem('intro') !== '0') {
        $('#intro').show();
    }
});

/** SECTIONS **/

function viewSection(identifier){
    let parent = $('#'+identifier);
    $(parent).insertBefore($('#atomic-blocks-end'));
    $(parent).css('display', 'block');
    window.location.hash='#'+identifier;
}

function showHide(show, hide) {
    $(show).each(function(){$(this).prop('disabled', false).css('opacity', 1.0)});
    $(hide).each(function(){$(this).prop('disabled', true).css('opacity', 0.5)});
}

function removeSection(identifier){
    $('#'+identifier).hide();
}

function removeIntro(){
    $('#intro').remove();
    localStorage.setItem('intro', '0');
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
                targets: 2,
                data: null,
                render: {
                    _:'platform'
                }
            },
            {
                targets: 3,
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
                targets: 4,
                data: null,
                render: {
                    _:'last_seen'
                }
            },
            {
                targets: 5,
                data: null,
                render: function ( data, type, row, meta ){
                    return "<input id=\""+data['paw']+"-sleep\" type=\"text\" value=\""+data['sleep_min']+"/"+data['sleep_max']+"\">";
                }
            },
            {
                targets: 6,
                data: null,
                render: {
                    _:'pid'
                }
            },
            {
                targets: 7,
                data: null,
                render: {
                    _:'privilege'
                }
            },
            {
                targets: 8,
                data: null,
                orderDataType: 'dom-text',
                type: 'string',
                render: function ( data, type, row, meta ) {

                    return "<input value=\""+data['group']+"\" type=\"text\" id=\""+data['paw']+"-group\" name=\""+data['paw']+"-group\"><br>";
                }
            },
            {
                targets: 9,
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
                text: 'Columns', // Button text.
                columns: ':lt(9)' // Keep last column (the remove agent column) as is.
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
        let update = {"index":"agent", "paw": value['paw'], "group": group, "trusted": status};
        let sleepArr = parseSleep(sleep);
        if (sleepArr.length !== 0) {
            update["sleep_min"] = sleepArr[0];
            update["sleep_max"] = sleepArr[1];
        }
        restRequest('PUT', update, doNothing);
    });
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

$(document).ready(function () {
    $('#factTbl').DataTable({});
});

function loadSource(sources) {
    let sourceName = $('#profile-source-name').val();
    sources.forEach(s => {
        if(s.name === sourceName) {
            let table = $('#factTbl').DataTable();
            s.facts.forEach(f => {
                table.row.add([f.trait, f.value]).draw();
            });
        }
    });
    validateFormState('#profile-source-name', '#sourceBtn');
}

function viewRules(sources){
    $('#source-rules').empty();
    document.getElementById("source-modal").style.display = "block";
    let sourceName = $('#profile-source-name').val();
    sources.forEach(s => {
        if(s.name === sourceName) {
            s.rules.forEach(r => {
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
    });
    $('#rules-name').text(sourceName);
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
        "jitter":jitter,
        "source":document.getElementById("queueSource").value,
        "allow_untrusted":document.getElementById("queueUntrusted").value
    };
}

function changeCurrentOperationState(newState){
    let selectedOperationId = $('#operation-list option:selected').attr('value');
    if(OPERATION.state === 'finished'){
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
    OPERATION = data[0];
    $("#op-control-state").html(OPERATION.state);
    if (OPERATION.autonomous) {
        $("#togBtnHil").prop("checked", true);
    } else {
        $("#togBtnHil").prop("checked", false);
    }
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
            let ability = OPERATION.abilities.filter(item => item.unique === OPERATION.chain[i].ability.unique)[0];
            template.find('#link-description').html(OPERATION.chain[i].ability.description);
            let title = OPERATION.chain[i].ability.name;
            if(OPERATION.chain[i].cleanup) {
                title = title + " (CLEANUP)"
            }
            let agentPaw = OPERATION.chain[i].paw;
            template.find('#link-technique').html(ability.technique_id + '<span class="tooltiptext">' + ability.technique_name + '</span>');
            template.attr("id", "op_id_" + OPERATION.chain[i].id);
            template.attr("operation", OPERATION.id);
            template.attr("data-date", OPERATION.chain[i].decide.split('.')[0]);
            template.find('#time-tactic').html('<div style="font-size: 13px;font-weight:100" ' +
                'ondblclick="rollup('+OPERATION.chain[i].id+')">agent#'+ agentPaw + '... ' +
                title + '<span id="'+OPERATION.chain[i].id+'-rs" style="font-size:14px;float:right;display:none" ' +
                'onclick="findResults(this, OPERATION.chain['+i+'].unique)"' +
                'data-encoded-cmd="'+OPERATION.chain[i].command+'"'+'>&#9733;</span>' +
                '<span id="'+OPERATION.chain[i].id+'-rm" style="font-size:11px;float:right" onclick="discard(OPERATION.chain['+i+'].unique)">&#x274C;</span></div>');
            template.find('#time-action').html(atob(OPERATION.chain[i].command));
            template.find('#time-executor').html(OPERATION.chain[i].executor);
            template.find('#paw-id').html(OPERATION.chain[i].paw);
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

function discard(linkId) {
    let operation = $('#operation-list option:selected').attr('value');
    let data = {'index':'chain', 'operation': operation, 'link_id': linkId, 'status': -2};
    restRequest('PUT', data, doNothing);
}

function refreshUpdatableFields(chain, div){
    if(chain.collect) {
        div.find('#'+chain.id+'-rm').remove();
        div.find('#link-collect').html(chain.collect.split('.')[0]);
    }
    if(chain.finish) {
        div.find('#'+chain.id+'-rs').css('display', 'block');
        div.find('#'+chain.id+'-rm').remove();
        div.find('#link-finish').html(chain.finish.split('.')[0]);
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
    } else {
        applyTimelineColor(div, 'queued');
    }
}

function applyTimelineColor(div, color) {
    div.removeClass('collected');
    div.removeClass('queued');
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

    let selectedOperationId = $('#report-list option:selected').attr('value');
    let selectedOpOutput = parseInt($('#report-output option:selected').attr('value'), 10);
    let postData = selectedOperationId ? {'index':'operation_report', 'op_id': selectedOperationId, 'agent_output': selectedOpOutput} : null;
    restRequest('POST', postData, downloadObjectAsJson, '/plugin/chain/rest');
}

function changeProgress(percent) {
    let elem = document.getElementById("myBar");
    elem.style.width = percent + "%";
    elem.innerHTML = percent + "%";
}

$(document).ready(function(){
  $("#optional").click(function(){
    $("#optional-options").slideToggle("slow");
  });
});
$(document).ready(function(){
  $("#schedules").click(function(){
    $("#schedules-options").slideToggle("slow");
  });
});

/** ADVERSARIES **/

function toggleAdversaryView() {
    $('#viewAdversary').toggle();
    $('#addAdversary').toggle();

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
    template.insertBefore('#dummy');
    template.show();
    let phaseHeader = $('<h4 class="phase-headers">Phase ' + number +'&nbsp&nbsp&nbsp;<span style="float:right;font-size:13px;" onclick="showPhaseModal('+number+')">&#10010; add ability</span><hr></h4>');
    phaseHeader.insertBefore("#tempPhase" + number);
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
    restRequest('POST', {"index":"adversary"}, reloadAdversaryElements);
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
        let executor = $(this).find('#ability-executor').val();
        let command = $(this).find('#ability-command').val();
        let payload = $(this).find('#ability-payload').val();
        if(!name || !description || !command) {
            return;
        }
        let executors = {};
        executors[executor] = {'command': command};
        if(payload) {
            executors[executor]['payload'] = payload;
        }
        platforms[platform] = executors;
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
    if((!ability) || (ability && ability.ability_id != data.ability_id)) {
        let a = addPlatforms([data]);
        appendAbilityToList('phase-modal', a[0]);
        options.val(a[0].name);
    }
}

function removeBlock(element){
    element.parent().parent().parent().remove();
}

function reloadAdversaryElements(data) {
    let adv_view_elem = $("#profile-existing-name");
    let adv_op_elem = $("#queueFlow");
    adv_view_elem.empty();
    adv_view_elem.append("<option value=\"\" disabled selected>Select an existing adversary</option>");
    adv_op_elem.empty();
    adv_op_elem.append("<option value=\"\" disabled selected>Adversary</option>");
    $.each(data, function(index, adv) {
        if(!adv_view_elem.find('option[value="'+ adv['adversary_id'] +'"]').length > 0) {
            adv_view_elem.append("<option value='" + adv['adversary_id'] + "'>" + adv['name'] + "</option>");
        }
        if(!adv_op_elem.find('option[value="'+ adv['adversary_id'] +'"]').length > 0) {
            adv_op_elem.append("<option id=\"qflow-" + adv['adversary_id'] + "\" value=\""+adv['id']+"\">"+ adv['name']+"</option>");
        }
    });
}

function loadAdversary() {
    restRequest('POST', {'index':'adversary', 'adversary_id': $('#profile-existing-name').val()}, loadAdversaryCallback);
    validateFormState(($('#profile-existing-name').val()), '#advNewBtn');
}

function loadAdversaryCallback(data) {
    $('#profile-goal').val(data[0]['name']);
    $('#profile-description').val(data[0]['description']);

    $('.tempPhase').remove();
    $('.phase-headers').remove();
    $.each(data[0]['phases'], function(phase, abilities) {
        let template = addPhase(phase);

        abilities = addPlatforms(abilities);
        abilities.forEach(function(a) {
            let abilityBox = buildAbility(a, phase);
            template.find('#profile-tests').append(abilityBox);
        });
    });
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
    template.find('#ability-rm').html('<div id="ability-remove"><div style="font-size:8px;">&#x274C;</div></div>');
    template.find('#ability-remove').click(function() {
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
            template.find('#ability-payload').val(ability.payload);
            template.show();
            $('#ttp-tests').append(template);
        }
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

function addToPhase() {
    let parent = $('#phase-modal');
    let phase = $(parent).data('phase');
    let ability = $('#phase-modal').find('#ability-ability-filter').find(":selected").data('ability');
    let abilityBox = buildAbility(ability, phase);
    $('#tempPhase' + phase).find('#profile-tests').append(abilityBox);
    document.getElementById('phase-modal').style.display='none';
}

function checkOpformValid(){
    validateFormState(($('#queueName').val()) && ($('#queueFlow').prop('selectedIndex') !== 0) && ($('#queueGroup').prop('selectedIndex') !== 0),
        '#opBtn');
    validateFormState(($('#queueName').val()) && ($('#queueFlow').prop('selectedIndex') !== 0) && ($('#queueGroup').prop('selectedIndex') !== 0) && ($('#schedule-hour').prop('selectedIndex') !== 0) && ($('#schedule-minute').prop('selectedIndex') !== 0),
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

/** REPORTS **/

function showReports(){
    validateFormState(($('#report-list').prop('selectedIndex') !== 0), '#reportBtn');
    let selectedOperationId = $('#report-list option:selected').attr('value');
    let postData = selectedOperationId ? {'index':'operation_report', 'op_id': selectedOperationId} : null;
    restRequest('POST', postData, displayReport, '/plugin/chain/rest');
}

function displayReport(data) {
    $('#report-name').html(data.name);
    $('#report-name-duration').html("The operation lasted " + reportDuration(data) + " with a random "+data.jitter + " second pause between steps");
    $('#report-adversary').html(data.adversary.name);
    $('#report-adversary-desc').html(data.adversary.description);
    $('#report-group').html(data.host_group[0]['group']);
    $('#report-group-cnt').html(data.host_group.length + ' agents were included');
    $('#report-steps').html(reportStepLength(data.steps));
    $('#report-steps-attack').html(data.adversary.name + " was " + reportScore(data.steps) + " successful in the attack");
    $('#report-planner').html(data.planner.name);
    $('#report-planner-desc').html(data.adversary.name + " collected " + data.facts.length + " facts and used them to make decisions");
    addAttackBreakdown(data.adversary.phases, data.steps);
    addFacts(data.facts);
    addSkippedAbilities(data.skipped_abilities);
}

function reportDuration(data) {
    if(data.finish) {
        let operationInSeconds = Math.abs(new Date(data.finish) - new Date(data.start)) / 1000;
        let operationInMinutes = Math.floor(operationInSeconds / 60) % 60;
        operationInSeconds -= operationInMinutes * 60;
        let secondsRemainder = operationInSeconds % 60;
        return operationInMinutes + 'min ' + secondsRemainder + 'sec';
    }
    return "(not finished yet))"
}

function reportStepLength(steps) {
    let step_len = 0;
    for ( let agent in steps ){
        step_len += steps[agent].steps.length;
    }
    return step_len;
}

function reportScore(steps) {
    let failed = 0;
    for ( let agent in steps ) {
        steps[agent].steps.forEach(s => {
        if(s.status > 0) {
            failed += 1;
        }
    });
    }
    return parseInt(100 - (failed/reportStepLength(steps) * 100)) + '%';
}

function addAttackBreakdown(phases, steps) {
    $("#reports-dash-attack").find("tr:gt(0)").remove();
    let plans = [];
    $.each(phases, function (k, v) {
        v.forEach(plannedStep => {
            if(!plans.some(e => e.tactic == plannedStep.tactic) || !plans.some(e => e.technique_id == plannedStep.technique_id) || !plans.some(e => e.technique_name == plannedStep.technique_name)) {
                plans.push({'tactic': plannedStep.tactic, 'technique_id': plannedStep.technique_id, 'technique_name': plannedStep.technique_name, "success": 0, "failure": 0});
            }
        });
    });
    plans.forEach(p => {
        for ( let agent in steps ) {
            steps[agent].steps.forEach(s => {
                if (p.tactic == s.attack.tactic && p.technique_id == s.attack.technique_id && p.technique_name == s.attack.technique_name) {
                    if (s.status > 0) {
                        p['failure'] += 1;
                    } else {
                        p['success'] += 1;
                    }
                }
            });
        }
    });
    plans.forEach(p => {
        $("#reports-dash-attack").append("<tr><td><span style='color:green'>"+p.success+"</span> / <span style='color:red'>"+p.failure+"</span></td><td>"+p.tactic+"</td><td>"+p.technique_id+"</td><td>"+p.technique_name+"</td></tr>");
    });
}

function addFacts(facts){
    $("#reports-dash-facts").find("tr:gt(0)").remove();
    let unique = [];
    facts.forEach(f => {
        let found = false;
        for(let i in unique){
            if(unique[i].trait == f.trait) {
                unique[i].count += 1;
                found = true;
                break;
            }
        }
        if(!found) {
            unique.push({'trait':f.trait, 'count':1});
        }
    });
    unique.forEach(u => {
        $("#reports-dash-facts").append("<tr><td>"+u.trait+"</td><td>"+u.count+"</td></tr>");
    });
}

function addSkippedAbilities(skipped_abilities) {
    clearSkippedAbilities();
    skipped_abilities.forEach(s => {
        for ( let agent in s ) {
            let template = $("#reports-dash-skipped-template").clone();
            template.attr('id', 'agent_'+agent);
            template.find('#skipped-host-name').text(agent);
            template.find('#skipped-host-total').text(s[agent].length);
            let skip_table = template.find("#skipped-host-abilities");
            s[agent].forEach(skipped => {
                skip_table.append("<tr id='skipped-"+skipped.ability_id+"'><td>"+skipped.ability_name+"</td><td>"+skipped.reason+"</td></tr>");
            });
            template.insertBefore("#skipped-start");
            template.show();
        }
    });
}

function clearSkippedAbilities() {
    let skipped = $('#reports-skipped-abilities');
    skipped.find('.agent-skipped').each(function() {
        $(this).remove();
    });
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
    $('#duk-text').text('Did you know... You can double-click on any row to show the details of the executed step. Click the ' +
        'star icon to view the standard output and error from the command that was executed. Highlighted text indicates ' +
        'facts which were learned from executing the step. Click the X to stop the ability from running.');
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
        'you to create extensible abilities. You can create new fact sources by adding YML files in the data/facts directory. '+
        'Additionally, sources can include rules which can restrict agents from using specific traits.');
}

/** HUMAN-IN-LOOP */

function submitHilChanges(status){
    document.getElementById("loop-modal").style.display = "none";
    let linkId = $('#hil-linkId').html();
    let command = $('#hil-command').val();
    let operation = $('#operation-list option:selected').attr('value');

    let data = {'index':'chain', 'operation': operation, 'link_id': linkId, 'status': status, 'command': btoa(command)};
    restRequest('PUT', data, doNothing);
    refresh();
    return false;
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
