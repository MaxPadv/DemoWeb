import React from 'react';

interface Props {
  children: React.ReactNode;
  serviceName: string;
}
interface State {
  hasError: boolean;
}

// Если remote недоступен или упал — показываем заглушку,
// портал при этом продолжает работать.
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error(`[shell] remote "${this.props.serviceName}" failed:`, error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="remote-error" role="alert">
          <div className="remote-error__title">Сервис «{this.props.serviceName}» недоступен</div>
          <p className="remote-error__text">
            Модуль не загрузился или вернул ошибку. Остальные сервисы портала работают.
          </p>
          <button
            className="btn btn--secondary"
            onClick={() => this.setState({ hasError: false })}
          >
            Повторить
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
