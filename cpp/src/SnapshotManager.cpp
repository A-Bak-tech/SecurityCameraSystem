#include "SnapshotManager.h"
#include "Logger.h"
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace fs = std::filesystem;

SnapshotManager::SnapshotManager(const std::string& outputDirectory, double cooldownSeconds)
    : outputDirectory_(outputDirectory),
    cooldownSeconds_(cooldownSeconds),
    hasSavedBefore_(false) {
    std::error_code errorCode;
    fs::create_directories(outputDirectory_, errorCode);
    if (errorCode) {
        Logger::log(LogLevel::Error, "SnapshotManager: failed to create directory '" + outputDirectory_ + "': " + errorCode.message());
    }
}

bool SnapshotManager::captureIfReady(const cv::Mat& frame) {
    if (frame.empty()) {
        return false;
    }

    auto now = std::chrono::steady_clock::now();

    if (hasSavedBefore_) {
        double secondsSinceLastSnapshot =
            std::chrono::duration<double>(now - lastSnapshotTime_).count();

        if (secondsSinceLastSnapshot < cooldownSeconds_) {
            return false;
        }
    }

    std::string filename = generateFilename();
    std::string fullPath = outputDirectory_ + "/" + filename;

    bool success = cv::imwrite(fullPath, frame);
    if (!success) {
        Logger::log(LogLevel::Error, "SnapshotManager: failed to write " + fullPath);
        return false;
    }

    lastSnapshotTime_ = now;
    hasSavedBefore_ = true;
    lastSavedFilePath_ = fullPath;

    Logger::log(LogLevel::Info, "SnapshotManager: saved " + fullPath);
    return true;
}

std::string SnapshotManager::generateFilename() const {
    auto now = std::chrono::system_clock::now();
    std::time_t nowTimeT = std::chrono::system_clock::to_time_t(now);

    std::tm localTime{};
    localtime_s(&localTime, &nowTimeT);

    std::ostringstream oss;
    oss << "snapshot_"
        << std::put_time(&localTime, "%Y-%m-%d_%H-%M-%S")
        << ".jpg";

    return oss.str();
}