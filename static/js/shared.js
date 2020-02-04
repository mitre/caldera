// check user prefs
const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;
if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
}

//check browser
window.onload = function checkBrowser(){
    let isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    if(!isChrome) {
        $('#notice').css('display', 'block');
    }
};

// AJAX caller
function restRequest(type, data, callback, endpoint='/plugin/chain/rest') {
    $.ajax({
       url: endpoint,
       type: type,
       contentType: 'application/json',
       data: JSON.stringify(data),
       success: function(data, status, options) { callback(data); },
       error: function (xhr, ajaxOptions, thrownError) { console.log(thrownError) }
    });
}

// form validation
function validateFormState(conditions, selector){
    (conditions) ?
        updateButtonState(selector, 'valid') :
        updateButtonState(selector, 'invalid');
}

// download report
function downloadReport(endpoint, filename, data={}) {
    function downloadObjectAsJson(data){
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

// flashy function
function flashy(elem, message) {
    let flash = $('#'+elem);
    flash.find('#message').text(message);
    flash.delay(100).fadeIn('normal', function() {
        $(this).delay(3000).fadeOut();
    });
    flash.find('#message').text(message);
}

function showHide(show, hide) {
    $(show).each(function(){$(this).prop('disabled', false).css('opacity', 1.0)});
    $(hide).each(function(){$(this).prop('disabled', true).css('opacity', 0.5)});
}

$(document).ready(function() {
    $('.navbar.plugin').html("<a href=\"/\">Home</a><a href=\"/logout\" style=\"float:right\">Logout</a><a href=\"/docs/index.html\" style=\"float:right\" target=\"_blank\">Docs</a>" +
        "<div  class=\"subnav-right\">" +
        "    <button class=\"subnavbtn\">Plugins <i class=\"fa fa-caret-down\"></i></button>" +
        "    <div id=\"subnav-plugins\" class=\"subnav-content subnav-content-right\"></div></div>");

    restRequest('POST', {"index": "plugins", "enabled": true}, function(data){
        $.each(data, function (index, value) {
            if (value['address']) {
                $('#subnav-plugins').append("<a href=" + value['address'] + ">" + value['name'] + "</a>")
            } else {
                $('#subnav-plugins').append("<a onclick=\"alert('No GUI component to this plugin')\">" + value['name'] + "</a>")
            }
        })
    });
});

function doNothing() {}
