CREATE TABLE activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL
                CHECK(category IN ('email', 'task', 'moltbook', 'error', 'session', 'system')),
            summary TEXT NOT NULL,
            details TEXT,
            email_id TEXT,
            task_id INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
CREATE TABLE sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            to_addr TEXT NOT NULL,
            from_addr TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            message_id TEXT NOT NULL,
            in_reply_to TEXT
        );
CREATE TABLE state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK(priority IN ('high', 'normal', 'low')),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')),
            source_email_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            assigned_to TEXT,
            result TEXT
        );
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_activity_log_category ON activity_log(category);
CREATE INDEX idx_activity_log_timestamp ON activity_log(timestamp);
CREATE INDEX idx_sent_emails_to_addr ON sent_emails(to_addr);
CREATE INDEX idx_sent_emails_subject ON sent_emails(subject);
CREATE INDEX idx_sent_emails_message_id ON sent_emails(message_id);
CREATE INDEX idx_sent_emails_in_reply_to ON sent_emails(in_reply_to);
