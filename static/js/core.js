/* Alpine.js data & functions called from core navigation template */

function alpineCore() {
    return {
        openTabs: [],
        activeTabIndex: 0,
        errors: startupErrors,
        showErrors: false,

        setTabContent(tab, html) {
            const newTabDiv = document.createElement('div');
            newTabDiv.setAttribute('id', tab.contentID);
            newTabDiv.setAttribute('x-show', 'openTabs[activeTabIndex] && openTabs[activeTabIndex].contentID === $el.id');
            setInnerHTML(newTabDiv, html);

            document.getElementById('active-tab-display').appendChild(newTabDiv);
        },

        addTab(tabName, address) {
            if (tabName === 'fieldmanual') {
                restRequest('GET', null, (data) => { this.setTabContent({ name: tabName, contentID: `tab-${tabName}`, address: address }, data); }, address);
                return;
            }
            const existingTabIndex = this.openTabs.findIndex((tab) => tab.name === tabName);
            if (existingTabIndex === -1) {
                const tab = { name: tabName, contentID: `tab-${tabName}`, address: address };

                restRequest('GET', null, (data) => { this.setTabContent(tab, data); }, tab.address);

                this.openTabs.push(tab);
                this.activeTabIndex = this.openTabs.length - 1;
            } else {
                this.activeTabIndex = existingTabIndex;
            }
        },

        deleteTab(index, contentID) {
            document.getElementById(contentID).remove();
            this.activeTabIndex -= 1;
            this.openTabs.splice(index, 1);
        },

    };
}
