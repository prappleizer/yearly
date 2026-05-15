import initSqlJs from 'sql.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const dataDir = join(__dirname, '../../data');
const dbPath = join(dataDir, 'yearview.db');

// Ensure data directory exists
mkdirSync(dataDir, { recursive: true });

let db = null;

export async function initDb() {
  const SQL = await initSqlJs();
  
  // Load existing database or create new one
  if (existsSync(dbPath)) {
    const fileBuffer = readFileSync(dbPath);
    db = new SQL.Database(fileBuffer);
  } else {
    db = new SQL.Database();
  }
  
  // Create tables
  db.run(`
    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      color TEXT NOT NULL DEFAULT '#6b7280',
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
  `);
  
  db.run(`
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      start_date TEXT NOT NULL,
      end_date TEXT NOT NULL,
      tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
      is_travel INTEGER NOT NULL DEFAULT 0,
      is_preliminary INTEGER NOT NULL DEFAULT 0,
      description TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
  `);
  
  db.run(`CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_events_tag ON events(tag_id)`);
  
  // Insert default tags if none exist
  const tagCount = db.exec('SELECT COUNT(*) as count FROM tags')[0];
  if (tagCount && tagCount.values[0][0] === 0) {
    db.run('INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)', ['Vacation', '#10b981', 0]);
    db.run('INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)', ['Conference', '#f59e0b', 1]);
    db.run('INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)', ['Observing Run', '#6366f1', 2]);
    db.run('INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)', ['Deadline', '#ef4444', 3]);
    saveDb();
  }
  
  return db;
}

export function saveDb() {
  if (db) {
    const data = db.export();
    const buffer = Buffer.from(data);
    writeFileSync(dbPath, buffer);
  }
}

export function getDb() {
  return db;
}

// Helper functions to work with sql.js results
export function queryAll(sql, params = []) {
  const stmt = db.prepare(sql);
  if (params.length) stmt.bind(params);
  
  const results = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject());
  }
  stmt.free();
  return results;
}

export function queryOne(sql, params = []) {
  const results = queryAll(sql, params);
  return results[0] || null;
}

export function run(sql, params = []) {
  db.run(sql, params);
  saveDb();
  return {
    lastInsertRowid: db.exec('SELECT last_insert_rowid()')[0]?.values[0][0],
    changes: db.getRowsModified()
  };
}
