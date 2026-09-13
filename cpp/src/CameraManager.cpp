#include "CameraManager.h"
#include "Logger.h"

CameraManager::CameraManager(int deviceIndex, double retryIntervalSeconds)
    : deviceIndex_(deviceIndex),
    retryIntervalSeconds_(retryIntervalSeconds),
    hasAttemptedReconnect_(false) {
    camera_ = std::make_unique<CameraCapture>(deviceIndex_);
}

bool CameraManager::open() {
    return camera_->open();
}

bool CameraManager::readFrame(cv::Mat& outFrame) {
    if (!camera_->isOpen()) {
        attemptReconnect();
        return false;
    }

    bool success = camera_->readFrame(outFrame);
    if (!success) {
        Logger::log(LogLevel::Warning, "CameraManager: lost connection to device " + std::to_string(deviceIndex_) + ".");
        camera_->release();
        attemptReconnect();
        return false;
    }

    return true;
}

bool CameraManager::isConnected() const {
    return camera_->isOpen();
}

void CameraManager::release() {
    camera_->release();
}

void CameraManager::attemptReconnect() {
    auto now = std::chrono::steady_clock::now();

    if (hasAttemptedReconnect_) {
        double secondsSinceLastAttempt =
            std::chrono::duration<double>(now - lastReconnectAttempt_).count();
        if (secondsSinceLastAttempt < retryIntervalSeconds_) {
            return;
        }
    }

    lastReconnectAttempt_ = now;
    hasAttemptedReconnect_ = true;

    Logger::log(LogLevel::Info, "CameraManager: attempting to reconnect to device " + std::to_string(deviceIndex_) + "...");

    camera_ = std::make_unique<CameraCapture>(deviceIndex_);

    if (camera_->open()) {
        Logger::log(LogLevel::Info, "CameraManager: reconnected to device " + std::to_string(deviceIndex_) + ".");
    }
}