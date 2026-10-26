// Async boundary — обязательный паттерн для Module Federation host:
// динамический import даёт рантайму время инициализировать shared-зависимости.
import('./bootstrap');
export {};
