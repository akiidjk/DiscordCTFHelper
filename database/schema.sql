CREATE TABLE IF NOT EXISTS 'ctf' (
  'id' INTEGER PRIMARY KEY AUTOINCREMENT,
  'name' TEXT NOT NULL,
  'description' TEXT NOT NULL,
  'text_channel_id' INTEGER NOT NULL,
  'event_id' INTEGER NOT NULL,
  'role_id' INTEGER NOT NULL,
  'msg_id' INTEGER NOT NULL
);