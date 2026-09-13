#include "Config.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cctype>

namespace {
    // Trims leading/trailing whitespace from a string.
    std::string trim(const std::string& s) {
        size_t start = s.find_first_not_of(" \t\r\n");
        size_t end = s.find_last_not_of(" \t\r\n");
        if (start == std::string::npos) {
            return "";
        }
        return s.substr(start, end - start + 1);
    }
}

Config::Config(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        std::cout << "Config: '" << filePath << "' not found, using default settings.\n";
        return;
    }

    std::string line;
    while (std::getline(file, line)) {
        std::string trimmedLine = trim(line);

        // Skip blank lines and comments.
        if (trimmedLine.empty() || trimmedLine[0] == '#') {
            continue;
        }

        size_t equalsPos = trimmedLine.find('=');
        if (equalsPos == std::string::npos) {
            std::cerr << "Config: ignoring malformed line: " << trimmedLine << "\n";
            continue;
        }

        std::string key = trim(trimmedLine.substr(0, equalsPos));
        std::string value = trim(trimmedLine.substr(equalsPos + 1));
        applyKeyValue(key, value);
    }

    std::cout << "Config: loaded settings from '" << filePath << "'.\n";
}

void Config::applyKeyValue(const std::string& key, const std::string& value) {
    try {
        if (key == "camera_device_index") {
            cameraDeviceIndex_ = std::stoi(value);
        }
        else if (key == "camera_retry_interval_seconds") {
            cameraRetryIntervalSeconds_ = std::stod(value);
        }
        else if (key == "motion_min_contour_area") {
            motionMinContourArea_ = std::stod(value);
        }
        else if (key == "snapshot_cooldown_seconds") {
            snapshotCooldownSeconds_ = std::stod(value);
        }
        else if (key == "recording_grace_seconds") {
            recordingGraceSeconds_ = std::stod(value);
        }
        else if (key == "recording_fps") {
            recordingFps_ = std::stod(value);
        }
        else {
            std::cerr << "Config: unknown key '" << key << "', ignoring.\n";
        }
    }
    catch (const std::exception&) {
        std::cerr << "Config: invalid value for '" << key << "': '" << value << "', keeping default.\n";
    }
}