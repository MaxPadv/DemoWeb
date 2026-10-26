import React, { useState, FormEvent } from 'react';
import './styles.css';

// Демо-аккаунты для пилота (пароли простые, хеши на бэкенде).
const DEMO_ACCOUNTS = [
  { name: 'Иван', login: 'ivan', password: 'ivan123' },
  { name: 'Алексей', login: 'alexey', password: 'kim123' },
  { name: 'Сергей', login: 'volkov', password: 'volkov123' },
];

export function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.text();
        // Бэкенд возвращает detail: 'Неверное имя пользователя или пароль'
        setError(body || 'Неверное имя пользователя или пароль');
        return;
      }
      // Успех — редирект на портал
      window.location.href = '/';
    } catch {
      setError('Неверное имя пользователя или пароль');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-card__title">
          HR Портал <span className="login-card__brand">SOGAZ</span>
        </h1>
        <form className="login-form" onSubmit={handleLogin}>
          <label className="login-form__label">
            <span className="login-form__label-text">Имя пользователя</span>
            <input
              className="login-form__input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
              autoComplete="username"
            />
          </label>
          <label className="login-form__label">
            <span className="login-form__label-text">Пароль</span>
            <input
              className="login-form__input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && <p className="login-form__error">{error}</p>}
          <button
            className="login-form__btn btn"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Вход…' : 'Войти'}
          </button>
        </form>
        <div className="login-card__demo">
          <p>Демо-аккаунты:</p>
          <ul className="login-card__demo-list">
            {DEMO_ACCOUNTS.map((a) => (
              <li key={a.login}>
                {a.name}: <code>{a.login} / {a.password}</code>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
