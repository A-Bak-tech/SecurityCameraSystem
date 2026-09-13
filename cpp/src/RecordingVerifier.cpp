#include "RecordingVerifier.h"
#include "Logger.h"
#include <filesystem>

namespace fs = std::filesystem;

bool RecordingVerifier::verifyRecording(const std::string& filePath) {
    std::error_code errorCode;
    auto fileSize = fs::file_size(filePath, errorCode);

    if (errorCode || fileSize == 0) {
        Logger::log(LogLevel::Warning, "RecordingVerifier: '" + filePath + "' is missing or empty.");
        return false;
    }

    cv::VideoCapture testReader(filePath);
    if (!testReader.isOpened()) {
        Logger::log(LogLevel::Warning, "RecordingVerifier: '" + filePath + "' could not be opened.");
        return false;
    }

    cv::Mat frame;
    bool readFrame = testReader.read(frame);
    testReader.release();

    if (!readFrame || frame.empty()) {
        Logger::log(LogLevel::Warning, "RecordingVerifier: '" + filePath + "' has no readable frames.");
        return false;
    }

    return true;
}

std::vector<std::string> RecordingVerifier::scanForOrphanedRecordings(const std::string& outputDirectory) {
    std::vector<std::string> suspectFiles;

    if (!fs::exists(outputDirectory)) {
        return suspectFiles;
    }

    for (const auto& entry : fs::directory_iterator(outputDirectory)) {
        if (!entry.is_regular_file()) {
            continue;
        }

        if (entry.path().extension() != ".avi") {
            continue;
        }

        std::string filePath = entry.path().string();
        if (!verifyRecording(filePath)) {
            suspectFiles.push_back(filePath);
        }
    }

    if (!suspectFiles.empty()) {
        Logger::log(LogLevel::Warning, "RecordingVerifier: found " + std::to_string(suspectFiles.size()) + " suspect recording(s) in '" + outputDirectory + "'.");
    }

    return suspectFiles;
}