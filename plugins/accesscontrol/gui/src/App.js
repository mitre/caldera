import React, { useState } from 'react';

function App() {
  const [username, setUsername] = useState('');
  const [abilities, setAbilities] = useState([]);
  const [newAbility, setNewAbility] = useState('');
  const [message, setMessage] = useState('');

  const createUser = async () => {
    const res = await fetch('/plugin/accesscontrol/user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    if (res.ok) {
      setMessage('User created!');
      fetchAbilities();
    } else {
      setMessage('Error creating user');
    }
  };

  const assignAbility = async () => {
    const res = await fetch('/plugin/accesscontrol/user/ability', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, ability: newAbility })
    });
    if (res.ok) {
      setMessage('Ability assigned!');
      fetchAbilities();
    } else {
      setMessage('Error assigning ability');
    }
  };

  const fetchAbilities = async () => {
    const res = await fetch(`/plugin/accesscontrol/user/abilities?username=${username}`);
    if (res.ok) {
      const data = await res.json();
      setAbilities(data.allowed_abilities || []);
    } else {
      setAbilities([]);
    }
  };

  return (
    <div style={{padding: 20}}>
      <h2>AccessControl Dashboard</h2>
      <input
        placeholder="Username"
        value={username}
        onChange={e => setUsername(e.target.value)}
        style={{marginRight: 10}}
      />
      <button onClick={createUser}>Create User</button>
      <button onClick={fetchAbilities}>View Abilities</button>
      <div style={{marginTop: 20}}>
        <input
          placeholder="New Ability"
          value={newAbility}
          onChange={e => setNewAbility(e.target.value)}
          style={{marginRight: 10}}
        />
        <button onClick={assignAbility}>Assign Ability</button>
      </div>
      <div style={{marginTop: 20}}>
        <h3>Assigned Abilities:</h3>
        <ul>
          {abilities.map(ab => <li key={ab}>{ab}</li>)}
        </ul>
      </div>
      <div style={{color: 'green'}}>{message}</div>
    </div>
  );
}

export default App;