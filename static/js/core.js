/* Alpine.js data & functions called from core navigation template */

function alpineCore() {
    return {
        openTabs: [],
        activeTabIndex: 0,
        errors: startupErrors,
        showErrors: false,
        version: '0.0.0',
        isFirstVisit: false,
        scrollTop: window.scrollY,
        newestVersion: '0.0.0',
        newVersionAvailable: false,

        initPage() {
            window.onscroll = () => {
                this.scrollTop = window.scrollY;
            };

            fetch("https://api.github.com/repos/mitre/caldera/releases")
                .then(response => response.json())
                .then(data => {
                    this.newestVersion = data[0].name;
                })
                .catch(error => console.error(error));

            apiV2('GET', '/api/v2/health').then((response) => {
                this.version = response.version;
                this.checkIfFirstVisit();
                if (response.version < this.newestVersion) {
                    this.newVersionAvailable = true;
                }
            }).catch((error) => {
                console.error(error);
                toast('Error loading page', false);
            });
        },

        checkIfFirstVisit() {
            let localStorage = window.localStorage;
            this.isFirstVisit = !localStorage.getItem('firstVisit');
            if (this.isFirstVisit) {
                localStorage.setItem('firstVisit', new Date().toISOString());
            }
        },

        setTabContent(tab, html) {
            const newTabDiv = document.createElement('div');
            newTabDiv.setAttribute('id', tab.contentID);
            newTabDiv.setAttribute('x-show', 'openTabs[activeTabIndex] && openTabs[activeTabIndex].contentID === $el.id');
            setInnerHTML(newTabDiv, html);

            document.getElementById('active-tab-display').appendChild(newTabDiv);
        },

        async addTab(tabName, address, queryString = '') {
            // Field manual does not create a tab
            if (tabName === 'fieldmanual') {
                restRequest('GET', null, (data) => { this.setTabContent({ name: tabName, contentID: `tab-${tabName}`, address: address }, data); }, address);
                return;
            }

            // If tab is already open, jump to it
            const existingTabIndex = this.openTabs.findIndex((tab) => tab.name === tabName);
            if (existingTabIndex !== -1) {
                this.activeTabIndex = existingTabIndex;
                this.checkQueryString(queryString);
                return;
            }

            // Tab does not exist, create it
            const tab = { name: tabName, contentID: `tab-${tabName}`, address: address };

            this.openTabs.push(tab);
            this.activeTabIndex = this.openTabs.length - 1;
            try {
                this.setTabContent(tab, await apiV2('GET', tab.address));
                this.checkQueryString(queryString);
            } catch (error) {
                toast('Unable to load page', false);
                console.error(error);
            }
        },

        checkQueryString(queryString) {
            if (history.pushState) {
                const newurl = `${window.location.protocol}//${window.location.host}${window.location.pathname}?${queryString}${window.location.hash}`;
                window.history.replaceState({ path: newurl }, "", newurl);
            } else {
                window.location.search = queryString;
            }
        },

        deleteTab(index, contentID) {
            try {
                document.getElementById(contentID).remove();
            } catch (error) {
                // Do nothing
            }

            if (this.activeTabIndex >= index) {
                this.activeTabIndex = Math.max(0, this.activeTabIndex - 1);
            }

            this.openTabs.splice(index, 1);
        },

    };
}
