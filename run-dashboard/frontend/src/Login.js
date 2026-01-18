import React, { useState } from 'react';
import axios from 'axios';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const API_TOKEN = process.env.API_TOKEN || "http://localhost:8002/token";

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // OAuth2推奨の形式(form-data)で送る
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const res = await axios.post("http://172.16.80.225:8002/token", params);

      // トークンを保存 (Local Storage)
      const token = res.data.access_token;
      localStorage.setItem('token', token);

      // 親コンポーネントに通知
      onLogin(token);
    } catch (err) {
      console.error(err);
      setError('Login failed. Check your credentials.');
    }
  };

  return (
    <div className="login-container">
      <h2>Ramos Running Coach Login</h2>
      <form onSubmit={handleSubmit}>
        <input type="text" placeholder="Username" onChange={e=>setUsername(e.target.value)} />
        <input type="password" placeholder="Password" onChange={e=>setPassword(e.target.value)} />
        <button type="submit">Login</button>
      </form>
      {error && <p style={{color:'red'}}>{error}</p>}
    </div>
  );
}
export default Login;