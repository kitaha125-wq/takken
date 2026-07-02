import fs from 'fs';
import path from 'path';
import { transformSync } from '@babel/core';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const htmlPath = path.join(root, 'index.source.html');
const outPath = path.join(root, 'app.js');

const html = fs.readFileSync(htmlPath, 'utf8');
const m = html.match(/<script type="text\/babel">\s*([\s\S]*?)\s*<\/script>/);
if (!m) {
  console.error('No <script type="text/babel"> block found');
  process.exit(1);
}

const source = m[1];
console.log('Source size:', (source.length / 1024 / 1024).toFixed(2), 'MB');

const { code } = transformSync(source, {
  filename: 'app.jsx',
  presets: [['@babel/preset-react', { runtime: 'classic' }]],
  compact: true,
  comments: false,
});

const banner = '/* Precompiled for mobile — run: npm run build */\n';
fs.writeFileSync(outPath, banner + code);
console.log('Wrote', outPath, '(' + (code.length / 1024 / 1024).toFixed(2) + ' MB)');
