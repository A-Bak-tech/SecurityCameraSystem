#pragma once

#include <opencv2/opencv.hpp>
#include <opencv2/video/background_segm.hpp>

// Detects motion in a video stream using background subtraction.
// Feed it consecutive frames via detectMotion(); it maintains its own
// internal background model between calls.
class MotionDetector {
public:
    // minContourArea: smallest blob (in pixels) counted as real motion,
    // used to filter out sensor noise and tiny lighting flicker.
    explicit MotionDetector(double minContourArea = 500.0);

    // Analyzes a single frame against the running background model.
    // Returns true if motion above the area threshold was found.
    // If motionBoundingBox is non-null, it is set to the bounding
    // rectangle enclosing all detected motion (only when true is returned).
    bool detectMotion(const cv::Mat& frame, cv::Rect* motionBoundingBox = nullptr);

    // Resets the background model, e.g. after a camera reconnect
    // or a deliberate scene change (lights turned on/off, etc.).
    void reset();

private:
    cv::Ptr<cv::BackgroundSubtractorMOG2> backgroundSubtractor_;
    double minContourArea_;
};