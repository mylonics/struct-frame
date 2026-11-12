// @ts-check
const esbuild = require('esbuild');

const production = process.argv.includes('--production');
const watch = process.argv.includes('--watch');

async function build() {
  /** @type {import('esbuild').BuildOptions} */
  const sharedOptions = {
    bundle: true,
    format: /** @type {const} */ ('cjs'),
    minify: production,
    sourcemap: !production,
    sourcesContent: false,
    platform: /** @type {const} */ ('node'),
    logLevel: 'silent',
  };

  const clientCtx = await esbuild.context({
    ...sharedOptions,
    entryPoints: ['client/src/extension.ts'],
    outfile: 'client/out/extension.js',
    // vscode is provided by the host; do not bundle it
    external: ['vscode'],
  });

  const serverCtx = await esbuild.context({
    ...sharedOptions,
    entryPoints: ['server/src/server.ts'],
    outfile: 'server/out/server.js',
    // vscode-languageserver uses node built-ins only; bundle everything else
    external: ['vscode'],
  });

  if (watch) {
    await Promise.all([clientCtx.watch(), serverCtx.watch()]);
    console.log('Watching for changes...');
  } else {
    await clientCtx.rebuild();
    await clientCtx.dispose();
    await serverCtx.rebuild();
    await serverCtx.dispose();
    console.log('Build complete.');
  }
}

build().catch(e => {
  console.error(e);
  process.exit(1);
});
