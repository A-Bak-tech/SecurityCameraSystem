#include "EventLogger.h"
#include "Logger.h"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <ctime>

EventLogger::EventLogger(const std::string& dbPath, const std::string& schemaPath)
    : db_(nullptr) {
    int result = sqlite3_open(dbPath.c_str(), &db_);
    if (result != SQLITE_OK) {
        Logger::log(LogLevel::Error, "EventLogger: failed to open database '" + dbPath + "'.");
        db_ = nullptr;
        return;
    }

    if (!applySchema(schemaPath)) {
        Logger::log(LogLevel::Error, "EventLogger: failed to apply schema from '" + schemaPath + "'.");
    }
}

EventLogger::~EventLogger() {
    if (db_) {
        sqlite3_close(db_);
    }
}

bool EventLogger::applySchema(const std::string& schemaPath) {
    std::ifstream file(schemaPath);
    if (!file.is_open()) {
        return false;
    }

    std::ostringstream buffer;
    buffer << file.rdbuf();
    std::string schemaSql = buffer.str();

    char* errorMessage = nullptr;
    int result = sqlite3_exec(db_, schemaSql.c_str(), nullptr, nullptr, &errorMessage);
    if (result != SQLITE_OK) {
        Logger::log(LogLevel::Error, std::string("EventLogger: schema error: ") + errorMessage);
        sqlite3_free(errorMessage);
        return false;
    }

    return true;
}

long long EventLogger::logEvent(const std::string& eventType,
    const std::string& filePath,
    int cameraDeviceIndex) {
    if (!db_) {
        return -1;
    }

    const char* sql =
        "INSERT INTO events (event_type, file_path, camera_device_index, created_at) "
        "VALUES (?, ?, ?, ?);";

    sqlite3_stmt* statement = nullptr;
    if (sqlite3_prepare_v2(db_, sql, -1, &statement, nullptr) != SQLITE_OK) {
        Logger::log(LogLevel::Error, "EventLogger: failed to prepare insert statement.");
        return -1;
    }

    std::string timestamp = currentTimestamp();

    sqlite3_bind_text(statement, 1, eventType.c_str(), -1, SQLITE_TRANSIENT);
    if (filePath.empty()) {
        sqlite3_bind_null(statement, 2);
    }
    else {
        sqlite3_bind_text(statement, 2, filePath.c_str(), -1, SQLITE_TRANSIENT);
    }
    sqlite3_bind_int(statement, 3, cameraDeviceIndex);
    sqlite3_bind_text(statement, 4, timestamp.c_str(), -1, SQLITE_TRANSIENT);

    int stepResult = sqlite3_step(statement);
    sqlite3_finalize(statement);

    if (stepResult != SQLITE_DONE) {
        Logger::log(LogLevel::Error, "EventLogger: failed to insert event.");
        return -1;
    }

    return sqlite3_last_insert_rowid(db_);
}

std::string EventLogger::currentTimestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t nowTimeT = std::chrono::system_clock::to_time_t(now);

    std::tm localTime{};
    localtime_s(&localTime, &nowTimeT);

    std::ostringstream oss;
    oss << std::put_time(&localTime, "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}