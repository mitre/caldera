$(document).ready(function () {
  $(function () {
    //setup ajax error handling
    $.ajaxSetup({
      error: function (event, jqxhr, settings, thrownError) {
        if (event.status == 403) {
          document.cookie = 'AUTH=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
          $('#login').modal('show');
        } else if (event.status == 404) {
            console.error('Got HTTP 404')
        }
      }
    });
  });
});

ko.options.deferUpdates = true;

// https://coderwall.com/p/weiq1q/auto-scrolling-extender-for-knockout-js
ko.extenders.scrollFollow = function (target, selector) {
    target.subscribe(function (newval) {
        var el = document.querySelector(selector);

        // the scroll bar is all the way down, so we know they want to follow the text
        if (el.scrollTop == el.scrollHeight - el.clientHeight) {
            // have to push our code outside of this thread since the text hasn't updated yet
            setTimeout(function () { el.scrollTop = el.scrollHeight - el.clientHeight; }, 0);
        }
    });

    return target;
};