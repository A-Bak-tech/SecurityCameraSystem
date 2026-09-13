#include "Logger.h"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <ctime>
#include <iostream>

namespace {
    std::ofstream g_logFile;
    bool g_initialized = false;
}

void Logger::init(const std::string& logFilePath) {
    // Open in append mode so restarting the program doesn't erase history —
    // useful for a security system where past logs matter after a crash/reboot.
    g_logFile.open(logFilePath, std::ios::app);

    if (!g_logFile.is_open()) {
        std::cerr << "Logger: failed to open '" << logFilePath
            << "', logging to console only.\n";
    }

    g_initialized = true;
    log(LogLevel::Info, "===== Logger initialized =====");
}

void Logger::log(LogLevel level, const std::string& message) {
    std::string line = "[" + currentTimestamp() + "] [" + levelToString(level) + "] " + message;

    // Always echo to console so existing behavior (watching the terminal
    // live) still works, in addition to persisting to disk.
    if (level == LogLevel::Error) {
        std::cerr << line << "\n";
    }
    else {
        std::cout << line << "\n";
    }

    if (g_logFile.is_open()) {
        g_logFile << line << "\n";
        g_logFile.flush(); // flush immediately so a crash doesn't lose recent lines
    }
}

void Logger::shutdown() {
    if (g_logFile.is_open()) {
        log(LogLevel::Info, "===== Logger shutting down =====");
        g_logFile.close();
    }
}

std::string Logger::levelToString(LogLevel level) {
    switch (level) {
    case LogLevel::Info:    return "INFO";
    case LogLevel::Warning: return "WARN";
    case LogLevel::Error:   return "ERROR";
    }
    return "UNKNOWN";
}

std::string Logger::currentTimestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t nowTimeT = std::chrono::system_clock::to_time_t(now);

    std::tm localTime{};
    localtime_s(&localTime, &nowTimeT);

    std::ostringstream oss;
    oss << std::put_time(&localTime, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}