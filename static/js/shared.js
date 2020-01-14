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

$(document).ready(function() {
    $('.navbar.plugin').html("<a href=\"/\">Home</a><a href=\"/logout\" style=\"float:right\">Logout</a>");
});
