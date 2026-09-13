#pragma once

#include <string>

// Loads runtime settings from a plain-text key=value config file
// (e.g. config.txt). Missing file or missing keys fall back to
// sensible defaults so the program still runs out of the box.
class Config {
public:
    // Attempts to load settings from filePath. If the file doesn't
    // exist, all values stay at their defaults and this still succeeds
    // (a missing config file is not treated as an error).
    explicit Config(const std::string& filePath = "config.txt");

    int cameraDeviceIndex() const { return cameraDeviceIndex_; }
    double cameraRetryIntervalSeconds() const { return cameraRetryIntervalSeconds_; }
    double motionMinContourArea() const { return motionMinContourArea_; }
    double snapshotCooldownSeconds() const { return snapshotCooldownSeconds_; }
    double recordingGraceSeconds() const { return recordingGraceSeconds_; }
    double recordingFps() const { return recordingFps_; }

private:
    int cameraDeviceIndex_ = 1;
    double cameraRetryIntervalSeconds_ = 2.0;
    double motionMinContourArea_ = 500.0;
    double snapshotCooldownSeconds_ = 2.0;
    double recordingGraceSeconds_ = 3.0;
    double recordingFps_ = 20.0;

    void applyKeyValue(const std::string& key, const std::string& value);
};