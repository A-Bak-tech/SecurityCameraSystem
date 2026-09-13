#pragma once

#include <string>

enum class LogLevel {
    Info,
    Warning,
    Error
};

// Simple static file logger. Call Logger::init() once at program startup,
// then Logger::log(...) from anywhere — no need to pass a Logger instance
// around. Falls back to console-only output if the log file can't be opened.
class Logger {
public:
    // logFilePath: where to write the log. Call this once, early in main().
    static void init(const std::string& logFilePath = "security_camera_system.log");

    // Writes a single timestamped line to the log file (and echoes to console).
    static void log(LogLevel level, const std::string& message);

    // Closes the log file cleanly. Call at program shutdown.
    static void shutdown();

private:
    static std::string levelToString(LogLevel level);
    static std::string currentTimestamp();
};