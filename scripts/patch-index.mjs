import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(__dirname, '..', 'index.html');
let html = fs.readFileSync(htmlPath, 'utf8');
const startTag = '<script type="text/babel">';
const start = html.indexOf(startTag);
if (start < 0) {
  console.log('index.html already patched (no text/babel block)');
  process.exit(0);
}
const end = html.indexOf('</script>', start + startTag.length);
const before = html.slice(0, start).replace(
  /<script src="https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/babel-standalone[^"]*"><\/script>\s*/,
  ''
);
const after = html.slice(end + '</script>'.length);
html = before + '<script src="./app.js"></script>' + after;
fs.writeFileSync(htmlPath, html);
console.log('Patched index.html → uses app.js');
