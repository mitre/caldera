(function() {
    'use strict';

    var COOKIE_NAME = 'r2purple_consent';
    var COOKIE_DAYS = 365;

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }

    function setCookie(name, value, days) {
        var d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = name + '=' + value + ';expires=' + d.toUTCString() + ';path=/;SameSite=Lax';
    }

    function showBanner() {
        if (getCookie(COOKIE_NAME)) return;

        var banner = document.createElement('div');
        banner.id = 'cookie-consent';
        banner.innerHTML =
            '<div class="cc-inner">' +
                '<p class="cc-text">We use cookies to improve your experience and analyze site traffic. ' +
                'By continuing to use this site, you consent to our use of cookies.</p>' +
                '<div class="cc-actions">' +
                    '<button class="cc-btn cc-accept" id="cc-accept">Accept All</button>' +
                    '<button class="cc-btn cc-essential" id="cc-essential">Essential Only</button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(banner);

        document.getElementById('cc-accept').addEventListener('click', function() {
            setCookie(COOKIE_NAME, 'all', COOKIE_DAYS);
            banner.classList.add('cc-hidden');
            loadAnalytics();
        });

        document.getElementById('cc-essential').addEventListener('click', function() {
            setCookie(COOKIE_NAME, 'essential', COOKIE_DAYS);
            banner.classList.add('cc-hidden');
        });

        requestAnimationFrame(function() {
            banner.classList.add('cc-visible');
        });
    }

    function loadAnalytics() {
        // Placeholder: add your analytics script loading here
        // Example for Google Analytics:
        // var s = document.createElement('script');
        // s.src = 'https://www.googletagmanager.com/gtag/js?id=YOUR_GA_ID';
        // s.async = true;
        // document.head.appendChild(s);
        if (window.R2Purple && window.R2Purple.onAnalyticsConsent) {
            window.R2Purple.onAnalyticsConsent();
        }
    }

    // Auto-load analytics if already consented
    if (getCookie(COOKIE_NAME) === 'all') {
        loadAnalytics();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showBanner);
    } else {
        showBanner();
    }
})();
