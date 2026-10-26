import React, { ComponentType, Suspense, lazy, useEffect, useState } from 'react';
import { loadRemote, registerRemotes } from '@module-federation/enhanced/runtime';
import { ErrorBoundary } from './ErrorBoundary';
import { fetchMe, fetchServices, logout, CurrentUser, HrService } from './api';

type Remote = NonNullable<HrService['remote']>;

// Remote подключается в рантайме по записи реестра — shell пересобирать не нужно.
const remotes = new Map<string, ComponentType>();
function remoteComponent(r: Remote): ComponentType {
  let c = remotes.get(r.name);
  if (!c) {
    registerRemotes([{ name: r.name, entry: r.entry }], { force: true });
    c = lazy(async () => {
      try {
        const m = await loadRemote<{ default: ComponentType }>(r.name + r.module.slice(1));
        if (!m) throw new Error(`remote ${r.name} не отдал модуль`);
        return m;
      } catch (e) {
        remotes.delete(r.name); // следующая попытка («Повторить») загрузит заново
        throw e;
      }
    });
    remotes.set(r.name, c);
  }
  return c;
}

function RemoteView({ remote }: { remote: Remote }) {
  const Component = remoteComponent(remote);
  return <Component />;
}

function ServicePlaceholder({ service }: { service: HrService }) {
  return (
    <div className="placeholder">
      <div className="placeholder__badge">
        <span className="status-dot status-dot--planned" />
        Сервис ещё не подключён
      </div>
      <h2 className="placeholder__title">{service.title}</h2>
      <p className="placeholder__desc">{service.description}</p>
      <div className="placeholder__guide">
        <div className="placeholder__guide-title">Как подключить этот сервис</div>
        <ol className="placeholder__steps">
          <li>Скопировать starter-репозиторий <code>hr-service-template</code></li>
          <li>
            Настроить <code>exposes</code> в ModuleFederationPlugin и написать FastAPI-бэкенд
          </li>
          <li>
            Зарегистрировать маршрут <code>/api/{service.key}/*</code> в API Gateway и строку в
            манифесте remotes — shell пересобирать не нужно
          </li>
        </ol>
      </div>
    </div>
  );
}

export function App() {
  const [services, setServices] = useState<HrService[]>([]);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [active, setActive] = useState<string>('home');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sessionChecking, setSessionChecking] = useState(true);

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      // сразу на страницу входа (не на '/', чтобы не триггерить /api/me 401 на сессии)
      window.location.href = '/mf/auth/';
    }
  };

  useEffect(() => {
    // Сначала проверяем сессию — если нет, редирект на auth; при успехе загружаем сервисы
    fetchMe()
      .then((me) => {
        setUser(me);
        setSessionChecking(false);
        return fetchServices();
      })
      .then((svcs) => {
        setServices(svcs);
      })
      .catch(() => {
        // Нет сессии — редирект на страницу входа
        window.location.href = '/mf/auth/';
      });
  }, []);

  const activeService = services.find((s) => s.key === active);
  const isHome = active === 'home';

  // Пока проверяем сессию — показываем заглушку, не рендерим портал
  if (sessionChecking) {
    return (
      <div className="layout">
        <main className="content">
          <div className="loading">
            <span className="loading__bar" />
            Проверка сессии…
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <button
          className="sidebar__brand sidebar__brand--btn"
          onClick={() => setActive('home')}
          title="На главную"
          type="button"
        >
          <span className="sidebar__logo" aria-hidden="true">
            HR
          </span>
          <span className="sidebar__name">Портал</span>
          <span className="sidebar__sogaz">SOGAZ</span>
        </button>
        <nav className="sidebar__nav" aria-label="Сервисы">
          <div className="sidebar__section">Сервисы</div>
          {services.map((s) => (
            <button
              key={s.key}
              className={
                'nav-item' + (active === s.key ? ' nav-item--active' : '')
              }
              onClick={() => setActive(s.key)}
            >
              <span
                className={
                  'status-dot ' +
                  (s.status === 'active' ? 'status-dot--active' : 'status-dot--planned')
                }
                aria-hidden="true"
              />
              <span className="nav-item__label">{s.title}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar__footer">
          <span className="status-dot status-dot--active" aria-hidden="true" />
          API Gateway: OK
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar__crumb">
            HR Портал <span className="topbar__sogaz">SOGAZ</span>{' '}
            <span className="topbar__sep">/</span>{' '}
            {isHome ? 'Главная' : activeService ? activeService.title : '…'}
          </div>
          <div className="topbar__right">
            <span className="badge badge--env">demo</span>
            <span className="badge" title="В проде — Keycloak OIDC">
              SSO: stub
            </span>
            {user && (
              <>
                <div className="user-chip">
                  <span className="user-chip__avatar" aria-hidden="true">
                    {user.name
                      .split(' ')
                      .map((w) => w[0])
                      .join('')}
                  </span>
                  <span className="user-chip__meta">
                    <span className="user-chip__name">{user.name}</span>
                    <span className="user-chip__role">{user.role}</span>
                  </span>
                </div>
                <button
                  className="btn btn--secondary btn--small btn--logout"
                  type="button"
                  onClick={handleLogout}
                  title="Выйти из системы"
                >
                  Выйти
                </button>
              </>
            )}
          </div>
        </header>

        <main className="content">
          {loadError && (
            <div className="remote-error" role="alert">
              <div className="remote-error__title">Не удалось загрузить реестр сервисов</div>
              <p className="remote-error__text">{loadError}</p>
            </div>
          )}
          {!loadError && isHome && (
            <div className="home">
              <h1 className="home__title">
                Добрый день{user ? `, ${user.name.split(' ')[0]}` : ''}!
              </h1>
              <p className="home__sub">
                Выберите сервис, чтобы начать работу. Сейчас подключён сервис отпусков,
                остальные появятся по мере готовности.
              </p>
              <div className="home__grid">
                {services.map((s) => (
                  <div className="svc-card" key={s.key}>
                    <div className="svc-card__head">
                      <h2 className="svc-card__title">{s.title}</h2>
                      <span
                        className={
                          'svc-card__status ' +
                          (s.status === 'active'
                            ? 'svc-card__status--active'
                            : 'svc-card__status--planned')
                        }
                      >
                        {s.status === 'active' ? 'Подключён' : 'Скоро'}
                      </span>
                    </div>
                    <p className="svc-card__desc">{s.description}</p>
                    {s.status === 'active' ? (
                      <button
                        className="btn"
                        type="button"
                        onClick={() => setActive(s.key)}
                      >
                        {s.key === 'vacations' ? 'Оформить отпуск →' : 'Открыть →'}
                      </button>
                    ) : (
                      <button className="btn btn--secondary" type="button" disabled>
                        Недоступно
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {!loadError && !isHome && activeService && activeService.status === 'active' && (
            <>
              <button
                className="btn btn--secondary back-btn"
                type="button"
                onClick={() => setActive('home')}
              >
                ← На главную
              </button>
              <ErrorBoundary serviceName={activeService.title}>
                <Suspense
                  fallback={
                    <div className="loading">
                      <span className="loading__bar" />
                      Загрузка модуля «{activeService.title}»…
                    </div>
                  }
                >
                  {activeService.remote && <RemoteView remote={activeService.remote} />}
                </Suspense>
              </ErrorBoundary>
            </>
          )}
          {!loadError && !isHome && activeService && activeService.status === 'planned' && (
            <ServicePlaceholder service={activeService} />
          )}
        </main>
      </div>
    </div>
  );
}
