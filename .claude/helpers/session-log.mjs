#!/usr/bin/env node
// Session log writer — invoked by SessionEnd / PreCompact hooks.
// Captures branch, commits since last session-log entry, and writes a
// dated markdown file under docs/session-logs/ for /update-notion to
// pick up on the next sync.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, sep } from 'node:path';

const cwd = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const LOG_DIR = resolve(cwd, 'docs', 'session-logs');

function git(args) {
  try {
    return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
  } catch {
    return '';
  }
}

function isoDate() {
  return new Date().toISOString().slice(0, 10);
}

function isoTime() {
  return new Date().toISOString().slice(0, 19).replace('T', ' ');
}

function commitsSince(sinceRef) {
  if (sinceRef === '') return '';
  return git(['log', '--pretty=format:%h\t%s', `${sinceRef}..HEAD`]);
}

function readLastSeenSha() {
  const stateFile = resolve(LOG_DIR, '.last-seen-sha');
  if (!existsSync(stateFile)) return '';
  try {
    return readFileSync(stateFile, 'utf8').trim();
  } catch {
    return '';
  }
}

function writeLastSeenSha(sha) {
  const stateFile = resolve(LOG_DIR, '.last-seen-sha');
  mkdirSync(dirname(stateFile), { recursive: true });
  writeFileSync(stateFile, sha + '\n', 'utf8');
}

function refExists(ref) {
  if (ref === '') return false;
  try {
    execFileSync('git', ['cat-file', '-e', `${ref}^{commit}`], { cwd, stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function main() {
  if (!existsSync(resolve(cwd, '.git'))) {
    console.log('[session-log] not a git repo — skipping');
    return;
  }

  const branch = git(['rev-parse', '--abbrev-ref', 'HEAD']) || 'detached';
  const head = git(['rev-parse', 'HEAD']);
  const lastSeen = readLastSeenSha();
  const sinceRef = lastSeen !== '' && refExists(lastSeen) ? lastSeen : `origin/${branch}`;
  const commits = commitsSince(sinceRef);
  const dirty = git(['status', '--porcelain']);

  if (commits === '' && dirty === '' && lastSeen === head) {
    console.log('[session-log] nothing new to log');
    return;
  }

  const today = isoDate();
  const safeBranch = branch.replace(/[\\/:]/g, '-');
  const file = resolve(LOG_DIR, `${today}-${safeBranch}.md`);

  mkdirSync(LOG_DIR, { recursive: true });

  const isNew = !existsSync(file);
  const lines = [];
  if (isNew) {
    lines.push(`# Session log — ${today} — ${branch}`);
    lines.push('');
  }
  lines.push(`## Entry @ ${isoTime()} UTC`);
  lines.push('');
  lines.push(`**HEAD:** \`${head.slice(0, 12)}\``);
  if (commits !== '') {
    lines.push('');
    lines.push('**Commits:**');
    lines.push('');
    for (const row of commits.split('\n')) {
      if (row.trim() === '') continue;
      const [sha, ...msgParts] = row.split('\t');
      lines.push(`- \`${sha}\` ${msgParts.join('\t')}`);
    }
  } else {
    lines.push('');
    lines.push('_No new commits since last log._');
  }
  if (dirty !== '') {
    lines.push('');
    lines.push('**Working tree (uncommitted):**');
    lines.push('');
    lines.push('```');
    lines.push(dirty);
    lines.push('```');
  }
  lines.push('');

  if (isNew) {
    writeFileSync(file, lines.join('\n'), 'utf8');
  } else {
    const existing = readFileSync(file, 'utf8');
    writeFileSync(file, `${existing}\n${lines.join('\n')}`, 'utf8');
  }
  writeLastSeenSha(head);
  const display = file.split(sep).slice(-3).join('/');
  console.log(`[session-log] wrote ${display}`);
}

main();
