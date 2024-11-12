CREATE TABLE IF NOT EXISTS server (
  id INTEGER PRIMARY KEY,
  active_category_id INTEGER NOT NULL,
  archive_category_id INTEGER NOT NULL,
  min_role_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ctf (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  server_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  text_channel_id INTEGER NOT NULL,
  event_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  msg_id INTEGER NOT NULL,
  FOREIGN KEY (server_id) REFERENCES server (id)
);