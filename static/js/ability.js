
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

function populateTechniques(parentId, exploits){
    exploits = addPlatforms(exploits);
    let parent = $('#'+parentId);
    $(parent).find('#ability-technique-filter').empty().append("<option disabled='disabled' selected>Choose a technique</option>");

    let tactic = $(parent).find('#ability-tactic-filter').find(":selected").data('tactic');
    let found = [];
    exploits.forEach(function(ability) {
        if(ability.tactic.includes(tactic) && !found.includes(ability.technique_id)) {
            found.push(ability.technique_id);
            appendTechniqueToList(parentId, tactic, ability);
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

function searchAbilities(parent, abilities){
    let pElem = $('#'+parent);
    pElem.find('#ability-technique-filter').empty().append("<option disabled='disabled' selected>All Techniques</option>");;
    let abList = pElem.find('#ability-ability-filter');
    abList.empty();
    let val = pElem.find('#ability-search-filter').val().toLowerCase();
    let added = [];
    if(val){
        abilities.forEach(function(ab){
            let cmd = atob(ab['test']);
            if (
                (
                    ab['name'].toLowerCase().includes(val) ||
                    ab['description'].toLowerCase().includes(val) ||
                    cmd.toLowerCase().includes(val)
                ) && !added.includes(ab['ability_id'])
            ){
                let composite = addPlatforms([ab]);
                added.push(ab['ability_id']);
                appendAbilityToList(parent, composite[0]);
            }
        });
    }
    abList.prepend("<option disabled='disabled' selected>"+added.length+" abilities</option>");
}
