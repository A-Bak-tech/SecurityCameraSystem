#pragma once

#include <opencv2/opencv.hpp>
#include <string>
#include <chrono>

// Saves motion-triggered snapshots to disk, throttled by a cooldown
// so continuous motion doesn't flood the disk with near-identical frames.
class SnapshotManager {
public:
    // outputDirectory: folder snapshots are saved into (created if missing).
    // cooldownSeconds: minimum time between saved snapshots.
    explicit SnapshotManager(const std::string& outputDirectory = "snapshots",
        double cooldownSeconds = 2.0);

    // Call this once per frame when motion is active. Internally enforces
    // the cooldown — returns true if a snapshot was actually written,
    // false if skipped due to cooldown or a write failure.
    bool captureIfReady(const cv::Mat& frame);

    // Returns the path of the most recently saved snapshot, or an
    // empty string if none has been saved yet.
    std::string getLastSavedFilePath() const { return lastSavedFilePath_; }

private:
    std::string outputDirectory_;
    double cooldownSeconds_;
    std::chrono::steady_clock::time_point lastSnapshotTime_;
    bool hasSavedBefore_;
    std::string lastSavedFilePath_;

    // Builds a timestamped filename like snapshot_2026-09-09_14-32-05.jpg
    std::string generateFilename() const;
};