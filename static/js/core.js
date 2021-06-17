/* Alpine.js data & functions called from core navigation template */

function _alpNavigation() {
    return {
        isNavMinimized: false,
        openTabs: [],
        activeTabIndex: 0,

        setTabContent(tab, data) {
            setInnerHTML(document.getElementById(this.openTabs[this.activeTabIndex].contentID), data.toString());
        },

        getTabContent(tab) {
            restRequest('GET', null, (data) => { this.setTabContent(tab, data) }, tab.address);
        },

        addTab(tabName, address) {
            const existingTabIndex = this.openTabs.findIndex(tab => tab.name === tabName);
            if (existingTabIndex === -1) {
                const tab = {name: tabName, contentID: 'tab-' + tabName, address: address};
                this.openTabs.push(tab);
                this.activeTabIndex = this.openTabs.length - 1;
            } else {
                this.activeTabIndex = existingTabIndex;
            }
        },

        deleteTab(index) {
            if (this.openTabs.length > 0) this.openTabs.splice(index, 1);
            this.activeTabIndex = this.openTabs.length > 0 ? this.openTabs.length - 1 : 0;
        }
    }
}
