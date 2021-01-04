/* HELPFUL functions to call */

function restRequest(type, data, callback, endpoint='/api/rest') {
    $.ajax({
       url: endpoint,
       type: type,
       contentType: 'application/json',
       data: JSON.stringify(data),
       success: function(data, status, options) {
           callback(data);
       },
       error: function (xhr, ajaxOptions, thrownError) {
           stream(thrownError);
       }
    });
}

function validateFormState(conditions, selector){
    (conditions) ?
        updateButtonState(selector, 'valid') :
        updateButtonState(selector, 'invalid');
}

function downloadReport(endpoint, filename, data={}) {
    function downloadObjectAsJson(data){
        stream('Downloading report: '+filename);
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
        let downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", filename + ".json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }
    restRequest('POST', data, downloadObjectAsJson, endpoint);
}

function updateButtonState(selector, state) {
    (state === 'valid') ?
        $(selector).attr('class','button-success atomic-button') :
        $(selector).attr('class','button-notready atomic-button');
}

function showHide(show, hide) {
    $(show).each(function(){$(this).prop('disabled', false).css('opacity', 1.0)});
    $(hide).each(function(){$(this).prop('disabled', true).css('opacity', 0.5)});
}

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    let r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function stream(msg, speak=false){
    let streamer = $('#streamer');
    if(streamer.text() != msg){
        streamer.fadeOut(function() {
            if(speak) { window.speechSynthesis.speak(new SpeechSynthesisUtterance(msg)); }
            $(this).text(msg).fadeIn(1000);
        });
    }
}

function doNothing() {}

/* SECTIONS */

function viewSection(name, address){
    function display(data) {
        let plugin = $($.parseHTML(data, keepScripts=true));
        $('#section-container').append('<div id="section-'+name+'"></div>');
        let newSection = $('#section-'+name);
        newSection.html(plugin);
        $('html, body').animate({scrollTop: newSection.offset().top}, 1000);
    }
    closeNav();
    restRequest('GET', null, display, address);
}

function removeSection(identifier){
    $('#'+identifier).remove();
}

function toggleSidebar(identifier) {
    let sidebar = $('#'+identifier);
    if (sidebar.is(":visible")) {
        sidebar.hide();
    } else {
        sidebar.show();
    }
}
/* AUTOMATIC functions for all pages */

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
    $(document).keyup(function(e){
        if(e.key == "Escape"){
            $('.modal').hide();
            $('#mySidenav').width('0');
        }
    });
    $('body').click(function(event) {
        if(!$(event.target).closest('.modal-content').length && $(event.target).is('.modal')) {
            $('.modal').hide();
        }
        if(!$(event.target).closest('#mySidenav').length && !$(event.target).is('.navbar span')) {
            $('#mySidenav').width('0');
        }
    });
});

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

(function($){
  $.event.special.destroyed = {
    remove: function(o) {
      if (o.handler) {
        o.handler()
      }
    }
  }
})(jQuery);

$(document).ready(function () {
   stream('Welcome home. Go into the Agents tab to review your deployed agents.');
});

window.onerror = function(error, url, line) {
    let msg = 'Check your JavaScript console. '+error;
    if(msg.includes('TypeError')) {
        stream('Refresh your GUI');
    } else {
        stream(msg);
    }
};

function warn(msg){
    document.getElementById("alert-modal").style.display="block";
    $("#alert-text").html(msg);
}

function display_errors(errors){
    function add_element(txt, level){
        let newitem = $("#infolist-template").clone();
        newitem.show();
        newitem.find(".infolist-contents p").html(txt)
        if(!level){
            newitem.find(".infolist-icon img").attr('src', '/gui/img/success.png')
        }
        $("#info-list").append(newitem);
    }
    document.getElementById("list-modal").style.display="block";
    $("#info-list").empty();
    if(errors.length === 0) {
        add_element("no errors to view", 0);
    }
    for(let id in errors){
        add_element(errors[id].name + ": " + errors[id].msg, 1);
    }
}

function openNav() {
  $('#mySidenav').width('250px');
}
function closeNav() {
  $('#mySidenav').width('0');
}
