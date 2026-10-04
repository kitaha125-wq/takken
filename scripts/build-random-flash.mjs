#!/usr/bin/env node
/**
 * weakness-daily.html と index.source.html から
 * data/random-flash.json を再生成する。
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

const html = fs.readFileSync(path.join(root, 'weakness-daily.html'), 'utf8');
const m = html.match(/const DATA = (\{[\s\S]*?\});\n\nconst CHECK_KEY/);
if (!m) {
  console.error('DATA not found in weakness-daily.html');
  process.exit(1);
}
const DATA = JSON.parse(m[1]);

const notes = [];
for (const cat of DATA.categories) {
  cat.items.forEach((it, j) => {
    notes.push({
      id: `${cat.cat}:${j}`,
      cat: cat.cat,
      field: cat.field,
      source: it.source || cat.source || 'weakness',
      wasWrong: !!it.wasWrong,
      weakPoint: it.weakPoint || '',
      memoryHook: it.memoryHook || '',
      keywords: it.keywords || [],
      summary: it.summary || '',
      comparisonTitle: it.comparisonTitle || '',
      comparisonTable: it.comparisonTable || [],
    });
  });
}

const src = fs.readFileSync(path.join(root, 'index.source.html'), 'utf8');
function extractArr(name) {
  const re = new RegExp(`const ${name} = (\\[[\\s\\S]*?\\]);`);
  const mm = src.match(re);
  if (!mm) return [];
  return Function(`"use strict"; return (${mm[1]});`)();
}

const past = extractArr('PAST_STYLE_QB');
const based = extractArr('PAST_BASED_QB');
const quizzes = [
  ...past.map((q, i) => ({ ...q, id: `past:${i}`, bank: '過去問風' })),
  ...based.map((q, i) => ({ ...q, id: `based:${i}`, bank: '過去問ベース' })),
];

const out = {
  generatedAt: new Date().toISOString(),
  notes,
  quizzes,
};
const outPath = path.join(root, 'data', 'random-flash.json');
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(`Wrote ${outPath} (${notes.length} notes, ${quizzes.length} quizzes)`);
