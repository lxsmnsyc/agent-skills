import Database from "better-sqlite3";

export const db = new Database("gallery.db");
db.exec(`CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  size INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)`);
