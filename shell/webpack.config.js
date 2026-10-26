const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('@module-federation/enhanced/webpack');
const deps = require('./package.json').dependencies;

module.exports = {
  context: __dirname,
  entry: './src/index.ts',
  mode: process.env.NODE_ENV === 'development' ? 'development' : 'production',
  output: {
    path: path.resolve(__dirname, 'dist'),
    publicPath: '/',
    clean: true,
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js'],
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loader: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new ModuleFederationPlugin({
      dts: false,
      name: 'shell',
      // remotes не прописаны: shell берёт их из реестра /api/services в рантайме
      shared: {
        react: { singleton: true, requiredVersion: deps.react },
        'react-dom': { singleton: true, requiredVersion: deps['react-dom'] },
      },
    }),
    new HtmlWebpackPlugin({
      template: './src/index.html',
    }),
  ],
  devServer: {
    port: 3001,
    historyApiFallback: true,
  },
};
