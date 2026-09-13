#include "VideoRecorder.h"
#include "Logger.h"
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace fs = std::filesystem;

VideoRecorder::VideoRecorder(const std::string& outputDirectory, double graceSeconds, double fps)
    : outputDirectory_(outputDirectory),
    graceSeconds_(graceSeconds),
    fps_(fps),
    isRecording_(false) {
    std::error_code errorCode;
    fs::create_directories(outputDirectory_, errorCode);
    if (errorCode) {
        Logger::log(LogLevel::Error, "VideoRecorder: failed to create directory '" + outputDirectory_ + "': " + errorCode.message());
    }
}

VideoRecorder::~VideoRecorder() {
    stopImmediately();
}

void VideoRecorder::update(bool motionActive, const cv::Mat& frame) {
    if (frame.empty()) {
        return;
    }

    if (motionActive) {
        lastMotionTime_ = std::chrono::steady_clock::now();

        if (!isRecording_) {
            startRecording(frame);
        }
    }

    if (isRecording_) {
        writer_.write(frame);

        double secondsSinceMotion =
            std::chrono::duration<double>(std::chrono::steady_clock::now() - lastMotionTime_).count();

        if (!motionActive && secondsSinceMotion > graceSeconds_) {
            stopRecording();
        }
    }
}

bool VideoRecorder::isRecording() const {
    return isRecording_;
}

void VideoRecorder::stopImmediately() {
    if (isRecording_) {
        stopRecording();
    }
}

void VideoRecorder::startRecording(const cv::Mat& frame) {
    currentFilePath_ = outputDirectory_ + "/" + generateFilename();

    int fourcc = cv::VideoWriter::fourcc('M', 'J', 'P', 'G');
    cv::Size frameSize(frame.cols, frame.rows);

    bool opened = writer_.open(currentFilePath_, fourcc, fps_, frameSize, /*isColor=*/true);
    if (!opened) {
        Logger::log(LogLevel::Error, "VideoRecorder: failed to open writer for " + currentFilePath_);
        isRecording_ = false;
        return;
    }

    isRecording_ = true;
    Logger::log(LogLevel::Info, "VideoRecorder: started recording " + currentFilePath_);
}

void VideoRecorder::stopRecording() {
    writer_.release();
    isRecording_ = false;
    lastCompletedFilePath_ = currentFilePath_;
    Logger::log(LogLevel::Info, "VideoRecorder: stopped recording " + currentFilePath_);
}

std::string VideoRecorder::getLastCompletedFilePath() const {
    return lastCompletedFilePath_;
}

std::string VideoRecorder::generateFilename() const {
    auto now = std::chrono::system_clock::now();
    std::time_t nowTimeT = std::chrono::system_clock::to_time_t(now);

    std::tm localTime{};
    localtime_s(&localTime, &nowTimeT);

    std::ostringstream oss;
    oss << "recording_"
        << std::put_time(&localTime, "%Y-%m-%d_%H-%M-%S")
        << ".avi";

    return oss.str();
}