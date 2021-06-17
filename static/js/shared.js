/* HELPFUL functions to call */

function restRequest(requestType, data, callback = () => {
    console.log('do nothing')
}, endpoint = '/api/rest') {
    const requestData = requestType === 'GET' ?
        {method: requestType, headers: {'Content-Type': 'application/json'}} :
        {method: requestType, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}

    fetch(endpoint, requestData)
        .then(data => callback(data))
        .catch((error) => console.error(error));
}

function downloadReport(endpoint, filename, data = {}) {
    function downloadObjectAsJson(data) {
        stream('Downloading report: ' + filename);
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

function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        let r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// TODO: JQuery functions

function showHide(show, hide) {
    $(show).each(function () {
        $(this).prop('disabled', false).css('opacity', 1.0)
    });
    $(hide).each(function () {
        $(this).prop('disabled', true).css('opacity', 0.5)
    });
}

function validateFormState(conditions, selector) {
    (conditions) ?
        updateButtonState(selector, 'valid') :
        updateButtonState(selector, 'invalid');
}

function updateButtonState(selector, state) {
    (state === 'valid') ?
        $(selector).attr('class', 'button-success atomic-button') :
        $(selector).attr('class', 'button-notready atomic-button');
}

function stream(msg, speak = false) {
    let streamer = $('#streamer');
    if (streamer.text() != msg) {
        streamer.fadeOut(function () {
            if (speak) {
                window.speechSynthesis.speak(new SpeechSynthesisUtterance(msg));
            }
            $(this).text(msg).fadeIn(1000);
        });
    }
}

/* SECTIONS */

// Alternative to JQuery parseHTML(keepScripts=true)
function setInnerHTML(elm, html) {
    elm.innerHTML = html;
    Array.from(elm.querySelectorAll("script")).forEach( oldScript => {
        const newScript = document.createElement("script");
        Array.from(oldScript.attributes)
            .forEach( attr => newScript.setAttribute(attr.name, attr.value) );
        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
        oldScript.parentNode.replaceChild(newScript, oldScript);
    });
}


// TODO: remove this from all individual plugins in future, as close (x) will be in the tab rather than inside the plugins itself
function removeSection(identifier) {
    $('#' + identifier).remove();
}


//
// function viewSection(name, address) {
//     function display(data) {
//         let plugin = $($.parseHTML(data, keepScripts = true));
//         $('#section-container').append('<div id="section-' + name + '"></div>');
//         let newSection = $('#section-' + name);
//         newSection.html(plugin);
//         $('html, body').animate({scrollTop: newSection.offset().top}, 1000);
//     }
//
//     restRequest('GET', null, display, address);
// }

function toggleSidebar(identifier) {
    let sidebar = $('#' + identifier);
    if (sidebar.is(":visible")) {
        sidebar.hide();
    } else {
        sidebar.show();
    }
}

/* AUTOMATIC functions for all pages */

$(document).ready(function () {
    $(document).find("select").each(function () {
        if (!$(this).hasClass('avoid-alphabetizing')) {
            alphabetize_dropdown($(this));
            let observer = new MutationObserver(function (mutations, obs) {
                obs.disconnect();
                alphabetize_dropdown($(mutations[0].target));
                obs.observe(mutations[0].target, {childList: true});
            });
            observer.observe(this, {childList: true});
        }
    });
    $(document).keyup(function (e) {
        if (e.key == "Escape") {
            $('.modal').hide();
            $('#mySidenav').width('0');
        }
    });
    $('body').click(function (event) {
        if (!$(event.target).closest('.modal-content').length && $(event.target).is('.modal')) {
            $('.modal').hide();
        }
        if (!$(event.target).closest('#mySidenav').length && !$(event.target).is('.navbar span')) {
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

(function ($) {
    $.event.special.destroyed = {
        remove: function (o) {
            if (o.handler) {
                o.handler()
            }
        }
    }
})(jQuery);

$(document).ready(function () {
    stream('Welcome home. Go into the Agents tab to review your deployed agents.');
});

window.onerror = function (error, url, line) {
    let msg = 'Check your JavaScript console. ' + error;
    if (msg.includes('TypeError')) {
        stream('Refresh your GUI');
    } else {
        stream(msg);
    }
};

function warn(msg) {
    document.getElementById("alert-modal").style.display = "block";
    $("#alert-text").html(msg);
}

function display_errors(errors) {
    function add_element(txt, level) {
        let newitem = $("#infolist-template").clone();
        newitem.show();
        newitem.find(".infolist-contents p").html(txt)
        if (!level) {
            newitem.find(".infolist-icon img").attr('src', '/gui/img/success.png')
        }
        $("#info-list").append(newitem);
    }

    document.getElementById("list-modal").style.display = "block";
    $("#info-list").empty();
    if (errors.length === 0) {
        add_element("no errors to view", 0);
    }
    for (let id in errors) {
        add_element(errors[id].name + ": " + errors[id].msg, 1);
    }
}

function b64EncodeUnicode(str) { //https://stackoverflow.com/a/30106551
    if (str != null) {
        return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g,
            function toSolidBytes(match, p1) {
                return String.fromCharCode('0x' + p1);
            }));
    } else return null;
}

function b64DecodeUnicode(str) { //https://stackoverflow.com/a/30106551
    if (str != null) {
        // An error check is needed in case the wrong codec (i.e. not UTF-8) was used at source
        try {
            return decodeURIComponent(atob(str).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
        } catch {
            return atob(str);
        }
    } else return "";
}

