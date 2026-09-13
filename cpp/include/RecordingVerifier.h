#pragma once

#include <opencv2/opencv.hpp>
#include <string>
#include <vector>

// Verifies recorded video files are valid (non-empty, readable, contain
// at least one decodable frame), and scans for orphaned recordings left
// behind by a crash or unclean shutdown.
class RecordingVerifier {
public:
    // Checks a single recording file for basic validity.
    // Returns true if the file opens and yields at least one readable frame.
    static bool verifyRecording(const std::string& filePath);

    // Scans outputDirectory for .avi files that appear incomplete or
    // unreadable (zero-byte, or fails verifyRecording). Returns the list
    // of suspect file paths found; does not delete or modify anything.
    static std::vector<std::string> scanForOrphanedRecordings(const std::string& outputDirectory);
};