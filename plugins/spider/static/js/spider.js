function generateLayer() {
    function downloadObjectAsJson(data){
        let exportName = 'layer';
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
        let downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", exportName + ".json");
        document.body.appendChild(downloadAnchorNode); // required for firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    let selectionAdversaryID = $('#layer-selection-adversary option:selected').attr('value');
    let postData = selectionAdversaryID ? {'index':'adversary', 'adversary_id': selectionAdversaryID} : {'index': 'all'};
    restRequest('POST', postData, downloadObjectAsJson, '/plugin/compass/layer');
}

function uploadAdversaryLayerButtonFileUpload() {
    document.getElementById('adversaryLayerInput').click();
}
$('#adversaryLayerInput').on('change', function (event){
    if(event.currentTarget) {
        let filename = event.currentTarget.files[0].name;
        if(filename){
            uploadAdversaryLayer();
        }
    }
});

function uploadAdversaryLayer() {
    let file = document.getElementById('adversaryLayerInput').files[0];
    let fd = new FormData();
    fd.append('file', file);
    $.ajax({
         type: 'POST',
         url: '/plugin/compass/adversary',
         data: fd,
         processData: false,
         contentType: false
    }).done(function (data){
        $('#advesary-create-name').html(data['name']);
        $('#adversary-create-response').html(data['description']);

        let unmatched_techniques = data['unmatched_techniques'];
        if (unmatched_techniques.length){
            document.getElementById('missing-abilities').style.display='block';
        } else {
            document.getElementById('missing-abilities').style.display='none';
        }
        $('#missing-abilities-body').children().remove();
        unmatched_techniques.forEach(element => {
           let row = document.getElementById('missing-abilities-body').insertRow();
           ['tactic', 'technique_id'].forEach( cell_name => {
               let cell = row.insertCell();
               cell.innerHTML = element[cell_name];
           });
        });
        $('#missing-abilities-table').DataTable({
            retrieve:  true,
            paging:    false,
            info:      false,
            searching: false,
        });


        document.getElementById('create-adversary-modal-compass').style.display='block';
    })
}

function openHelp() {
    document.getElementById("duk-modal-compass").style.display="block";
}