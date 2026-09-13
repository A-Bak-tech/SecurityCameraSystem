#pragma once

#include <string>
#include <sqlite3.h>

// Writes system events (motion, snapshots, recordings) to a SQLite
// database so they can be queried later or picked up by the Python
// AI layer for classification.
class EventLogger {
public:
    // dbPath: path to the SQLite database file (created if missing).
    // schemaPath: path to schema.sql, executed once at startup to
    //             ensure tables exist.
    explicit EventLogger(const std::string& dbPath = "db/events.db",
        const std::string& schemaPath = "db/schema.sql");
    ~EventLogger();

    EventLogger(const EventLogger&) = delete;
    EventLogger& operator=(const EventLogger&) = delete;

    // Logs an event. filePath may be empty for events with no
    // associated file (e.g. motion_start/motion_stop).
    // Returns the new row's id, or -1 on failure.
    long long logEvent(const std::string& eventType,
        const std::string& filePath,
        int cameraDeviceIndex);

private:
    sqlite3* db_;
    bool applySchema(const std::string& schemaPath);
    static std::string currentTimestamp();
};