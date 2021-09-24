/* eslint-disable */
/* HELPFUL functions to call */

function restRequest(requestType, data, callback = (r) => {
    console.log('Fetch Success', r);
}, endpoint = '/api/rest') {
    const requestData = requestType === 'GET' ?
        {method: requestType, headers: {'Content-Type': 'application/json'}} :
        {method: requestType, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}

    fetch(endpoint, requestData)
        .then((response) => {
            if (!response.ok) {
                throw (response.statusText);
            }
            return response.text();
        })
        .then((text) => {
            try {
                callback(JSON.parse(text));
            } catch {
                callback(text);
            }
        })
        .catch((error) => console.error(error));
}

function apiV2(requestType, endpoint, body = null) {
    let requestBody = { method: requestType, headers: { 'Content-Type': 'application/json' } };
    if (requestType !== 'GET') requestBody.body = JSON.stringify(body);

    return new Promise((resolve, reject) => {
        fetch(endpoint, requestBody)
            .then((response) => {
                if (!response.ok) {
                    reject(response.statusText);
                }
                return response.text();
            })
            .then((text) => {
                try {
                    resolve(JSON.parse(text));
                } catch {
                    resolve(text);
                }
            });
    });
}

const disabledPlugins = ['atomic', 'stockpile', 'emu'];
function isPluginDisabled(pluginName) {
    return disabledPlugins.includes(pluginName);
}

//
// Parse timestamp into human-friendly date format
// Modified from original code: https://stackoverflow.com/questions/7641791/javascript-library-for-human-friendly-relative-date-formatting
//
// Expected input: (i.e.) 2021-08-25 10:03:23
// Output: (i.e.) 5 hrs ago; (i.e. if older than 1 day): yesterday 10:03:23; (i.e. if older than 2 days): Aug 25 10:03:23
//
function getHumanFriendlyTime(date) {
    // i.e. format 2021-08-03 19:37:08
    if (!date) return '';
    let split = date.split('-');

    let hMonth = Number(split[1]) - 1;
    let hDate = Number(split[2].split(' ')[0]);
    let hTime = split[2].split(' ')[1].split(':');

    const givenDate = new Date(split[0], hMonth, hDate, hTime[0], hTime[1], hTime[2]);
    // Make a fuzzy time
    let delta = Math.round((new Date - givenDate) / 1000);

    let minute = 60,
        hour = minute * 60,
        day = hour * 24;

    let fuzzy;

    if (delta < 30) {
        fuzzy = 'just now';
    } else if (delta < minute) {
        fuzzy = delta + ' seconds ago';
    } else if (delta < 2 * minute) {
        fuzzy = 'a minute ago'
    } else if (delta < hour) {
        fuzzy = Math.floor(delta / minute) + ' min ago';
    } else if (Math.floor(delta / hour) === 1) {
        fuzzy = '1 hr ago'
    } else if (delta < day) {
        fuzzy = Math.floor(delta / hour) + ' hrs ago';
    } else if (delta < day * 2) {
        fuzzy = 'yesterday ' + (hTime.join(':'));
    } else {
        switch (hMonth) {
            case 0:
                hMonth = 'Jan';
                break;
            case 1:
                hMonth = 'Feb';
                break;
            case 2:
                hMonth = 'Mar';
                break;
            case 3:
                hMonth = 'Apr';
                break;
            case 4:
                hMonth = 'May';
                break;
            case 5:
                hMonth = 'Jun';
                break;
            case 6:
                hMonth = 'Jul';
                break;
            case 7:
                hMonth = 'Aug';
                break;
            case 8:
                hMonth = 'Sep';
                break;
            case 9:
                hMonth = 'Oct';
                break;
            case 10:
                hMonth = 'Nov';
                break;
            case 11:
                hMonth = 'Dec';
                break;
            default:
                hMonth = '';
                break;
        }
        fuzzy = hMonth + ' ' + hDate + ' ' + hTime.join(':');
    }
    return fuzzy;
}

function sortAlphabetically(list) {
    return list.sort((a, b) => {
        let x = a.toLowerCase(), y = b.toLowerCase();
        if (x < y) return -1;
        else if (x > y) return 1;
        else return 0;
    })
}

function toast(message, success) {
    bulmaToast.toast({
        message: `<span class="icon"><i class="fas fa-${success ? 'check' : 'exclamation'}"></i></span> ${message}`,
        type: `toast ${success ? 'is-success' : 'is-danger'}`,
        position: 'bottom-right',
        duration: '3000',
        pauseOnHover: true
    });
}

function validateInputs(obj, requiredFields) {
    let fieldErrors = [];
    requiredFields.forEach((field) => {
        if (obj[field].length === 0) {
            fieldErrors.push(field);
        }
    });

    return fieldErrors;
}

function downloadJson(filename, data) {
    let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
    let downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", filename + ".json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

function downloadReport(endpoint, filename, data = {}, jsonifyData = false) {
    function downloadObjectAsJson(data) {
        stream('Downloading report: ' + filename);
        const parsedData = jsonifyData ? JSON.stringify(data, null, 2) : data;
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(parsedData);
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
function setInnerHTML(elem, html) {
    elem.innerHTML = html;
    const scripts = Array.from(elem.querySelectorAll("script"));
    if (scripts) {
        scripts.forEach(oldScript => {
            const newScript = document.createElement("script");
            Array.from(oldScript.attributes)
                .forEach( attr => newScript.setAttribute(attr.name, attr.value) );
            newScript.appendChild(document.createTextNode(oldScript.innerHTML));
            oldScript.parentNode.replaceChild(newScript, oldScript);
        });
    }
}


// TODO: remove this from all individual plugins in future, as close (x) will be in the tab rather than inside the plugins itself
function removeSection(identifier) {
    $('#' + identifier).remove();
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

