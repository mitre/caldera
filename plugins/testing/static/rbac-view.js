(function () {
  function start() {
    const { createApp, reactive, onMounted } = window.Vue;

    const api = {
      async get(u){ const r=await fetch(u,{credentials:'include'}); if(!r.ok) throw new Error(await r.text()); return r.json(); }
    };

    createApp({
      setup(){
        const state = reactive({
          users: [],                 // [{username, group, roles, allowed[], show}]
          abilityIndex: {}           // { ability_id: name }
        });

        function abilityName(id){
          return state.abilityIndex[id] || 'Ability';
        }

        async function load(){
          // 1) get current users from your RBAC store
          const usersObj = await api.get('/plugin/testing/rbac/users'); // {username:{group,roles,...}}
          const users = Object.entries(usersObj || {}).map(([username, u]) => ({
            username, group: u.group, roles: u.roles || []
          }));

          // 2) build ability id -> name index
          const ab = await api.get('/plugin/testing/abilities'); // {abilities:[{name, ability_id}]}
          state.abilityIndex = Object.fromEntries(
            (ab.abilities || [])
              .filter(a => a.ability_id)
              .map(a => [a.ability_id, a.name || 'Ability'])
          );

          // 3) resolve allowed for each user
          for (const u of users) {
            const res = await api.get('/plugin/testing/rbac/allowed?username=' + encodeURIComponent(u.username));
            u.allowed = (res && res.allowed_abilities) || [];
            u.show = false;
          }
          state.users = users;
        }

        onMounted(load);
        return { users: state.users, abilityName };
      }
    }).mount('#rbac-view');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
