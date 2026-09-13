#pragma once

#include "CameraCapture.h"
#include <memory>
#include <chrono>

// Wraps a CameraCapture with automatic reconnect handling. If the camera
// disconnects mid-run, this keeps retrying at a fixed interval instead of
// letting the program crash or exit — intended for unattended operation.
class CameraManager {
public:
    // deviceIndex: which camera to manage.
    // retryIntervalSeconds: how long to wait between reconnect attempts.
    explicit CameraManager(int deviceIndex, double retryIntervalSeconds = 2.0);

    // Opens the camera for the first time. Returns false only if the
    // very first attempt fails (subsequent failures are handled via
    // automatic retry inside readFrame()).
    bool open();

    // Reads a frame. If the camera has disconnected, this returns false
    // for that call but internally starts attempting reconnects on a
    // timer — call it every loop iteration same as before, no special
    // handling needed by the caller beyond checking the return value.
    bool readFrame(cv::Mat& outFrame);

    // True if the underlying camera is currently connected and readable.
    bool isConnected() const;

    void release();

private:
    int deviceIndex_;
    double retryIntervalSeconds_;
    std::unique_ptr<CameraCapture> camera_;
    std::chrono::steady_clock::time_point lastReconnectAttempt_;
    bool hasAttemptedReconnect_;

    void attemptReconnect();
};