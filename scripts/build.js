// Сборка всех фронтендов независимо от того, как npm разместил webpack
// (hoisted в корень workspaces или вложенно в пакет) — резолвим ближайшую копию.
const { execFileSync } = require('child_process');
const path = require('path');

const workspaces = ['services/shell', 'services/vacations/frontend', 'services/structure/frontend'];

for (const ws of workspaces) {
  const wsDir = path.resolve(__dirname, '..', ws);
  const webpackBin = require.resolve('webpack/bin/webpack.js', { paths: [wsDir] });
  console.log(`\n=== build ${ws} (webpack: ${webpackBin}) ===`);
  execFileSync(process.execPath, [webpackBin, '--mode', 'production'], {
    cwd: wsDir,
    stdio: 'inherit',
    env: { ...process.env, NODE_ENV: 'production' },
  });
}
