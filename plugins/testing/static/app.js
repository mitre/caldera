console.log('rbac app.js loaded');

(function () {
  function start() {
    const VueGlobal = window.Vue;
    if (!VueGlobal) { console.error('Vue not found'); return; }

    const { createApp, reactive, onMounted } = VueGlobal;

    const api = {
      async get(u){
        const r = await fetch(u, { credentials: 'include' });
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      },
      async post(u, b){
        const r = await fetch(u, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(b)
        });
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      }
    };

    createApp({
      setup(){
        const state = reactive({
          roles: {}, users: {}, groups: {}, msg: '',
          optionAbilities: [], optionRoles: [], optionUsers: [],
          formRole:  { name: '',  allowed_abilities: [] },
          formUser:  { username: '', group: 'red', roles: [] },
          formGroup: { name: '', members: [], roles: [] }
        });

        // ---- helpers exposed to template ----
        function sortObject(obj){
          if (!obj || typeof obj !== 'object') return obj;
          const sortedKeys = Object.keys(obj).sort();
          const out = {};
          for (const k of sortedKeys) out[k] = obj[k];
          return out;
        }
        function syntaxHighlight(json) {
          if (typeof json !== 'string') json = JSON.stringify(json, null, 2);
          json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          return json.replace(
            /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
            function (match) {
              let cls = 'val';
              if (/^"/.test(match)) {
                if (/:$/.test(match)) cls = 'key';
              } else if (/true|false/.test(match)) {
                cls = 'bool';
              } else if (/null/.test(match)) {
                cls = 'null';
              }
              return '<span class="' + cls + '">' + match + '</span>';
            }
          );
        }

        async function refresh(){
          // current RBAC data
          state.roles  = await api.get('/plugin/testing/rbac/roles');
          state.users  = await api.get('/plugin/testing/rbac/users');
          state.groups = await api.get('/plugin/testing/rbac/groups');

          // dropdown options
          const ab = await api.get('/plugin/testing/abilities'); // [{display...}]
          state.optionAbilities = (ab.abilities || [])
            .map(a => ({
              id: a.ability_id || a.id,
              label: `${a.name || 'Ability'} — ${(a.ability_id || a.id || '').slice(0,8)}`
            }))
            .filter(o => o.id);
          state.optionRoles = Object.keys(state.roles || {});
          state.optionUsers = Object.keys(state.users || {});
        }

        async function saveRole(){
          await api.post('/plugin/testing/rbac/roles', state.formRole);
          state.msg = `Saved role ${state.formRole.name}`;
          state.formRole = { name:'', allowed_abilities:[] };
          await refresh();
        }

        async function saveUser(){
          await api.post('/plugin/testing/rbac/users', state.formUser);
          state.msg = `Saved user ${state.formUser.username}`;
          state.formUser = { username:'', group:'red', roles:[] };
          await refresh();
        }

        async function saveGroup(){
          await api.post('/plugin/testing/rbac/groups', state.formGroup);
          state.msg = `Saved group ${state.formGroup.name}`;
          state.formGroup = { name:'', members:[], roles:[] };
          await refresh();
        }

        onMounted(refresh);
        return { state, saveRole, saveUser, saveGroup, refresh, syntaxHighlight, sortObject };
      }
    }).mount('#rbac-app');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
