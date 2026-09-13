#include "MotionDetector.h"

MotionDetector::MotionDetector(double minContourArea)
    : minContourArea_(minContourArea) {
    // history=500 frames, varThreshold=16 (default sensitivity),
    // detectShadows=true so shadows get labeled gray (127) instead of
    // white (255) and can be filtered out below.
    backgroundSubtractor_ = cv::createBackgroundSubtractorMOG2(
        /*history=*/500,
        /*varThreshold=*/16.0,
        /*detectShadows=*/true
    );
}

bool MotionDetector::detectMotion(const cv::Mat& frame, cv::Rect* motionBoundingBox) {
    if (frame.empty()) {
        return false;
    }

    cv::Mat foregroundMask;
    backgroundSubtractor_->apply(frame, foregroundMask);

    // Shadows are marked 127 by detectShadows=true; threshold them out
    // so only strong foreground pixels (255) count as motion.
    cv::threshold(foregroundMask, foregroundMask, 200, 255, cv::THRESH_BINARY);

    // Clean up small noise specks left over from the mask.
    cv::morphologyEx(foregroundMask, foregroundMask, cv::MORPH_OPEN,
        cv::getStructuringElement(cv::MORPH_RECT, cv::Size(3, 3)));

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(foregroundMask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

    bool motionFound = false;
    cv::Rect combinedBox;

    for (const auto& contour : contours) {
        double area = cv::contourArea(contour);
        if (area < minContourArea_) {
            continue; // too small, treat as noise
        }

        cv::Rect box = cv::boundingRect(contour);
        combinedBox = motionFound ? (combinedBox | box) : box; // union of all motion regions
        motionFound = true;
    }

    if (motionFound && motionBoundingBox != nullptr) {
        *motionBoundingBox = combinedBox;
    }

    return motionFound;
}

void MotionDetector::reset() {
    backgroundSubtractor_ = cv::createBackgroundSubtractorMOG2(500, 16.0, true);
}