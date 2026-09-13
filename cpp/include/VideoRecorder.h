#pragma once

#include <opencv2/opencv.hpp>
#include <string>
#include <chrono>

// Records video to disk while motion is active, with a grace period
// after motion stops so brief pauses don't cut a clip into fragments.
class VideoRecorder {
public:
    // outputDirectory: folder recordings are saved into (created if missing).
    // graceSeconds: how long to keep recording after motion stops before
    //               closing the file, in case motion resumes shortly after.
    // fps: frame rate to encode the video at.
    explicit VideoRecorder(const std::string& outputDirectory = "recordings",
        double graceSeconds = 3.0,
        double fps = 20.0);

    ~VideoRecorder();

    VideoRecorder(const VideoRecorder&) = delete;
    VideoRecorder& operator=(const VideoRecorder&) = delete;

    // Call once per frame regardless of motion state.
    // motionActive: current motion state from MotionDetector.
    // frame: current camera frame to (potentially) write.
    void update(bool motionActive, const cv::Mat& frame);

    // Returns true if a recording is currently open (including grace period).
    bool isRecording() const;

    // Immediately closes any open recording, ignoring the grace period.
    // Call this on shutdown so the last clip isn't left corrupted.
    void stopImmediately();

    // Returns the file path of the most recently completed recording,
    // or an empty string if none has completed yet. Useful for verifying
    // a recording immediately after it closes.
    std::string getLastCompletedFilePath() const;

private:
    std::string outputDirectory_;
    double graceSeconds_;
    double fps_;

    cv::VideoWriter writer_;
    bool isRecording_;
    std::chrono::steady_clock::time_point lastMotionTime_;
    std::string currentFilePath_;
    std::string lastCompletedFilePath_;

    std::string generateFilename() const;
    void startRecording(const cv::Mat& frame);
    void stopRecording();
};