#include "CameraCapture.h"
#include <iostream>

CameraCapture::CameraCapture(int deviceIndex)
    : deviceIndex_(deviceIndex) {}

CameraCapture::~CameraCapture() {
    release();
}

bool CameraCapture::open() {
    if (capture_.isOpened()) {
        return true; // already open, nothing to do
    }

    capture_.open(deviceIndex_);

    if (!capture_.isOpened()) {
        std::cerr << "CameraCapture: failed to open device index "
            << deviceIndex_ << "\n";
        return false;
    }

    return true;
}

bool CameraCapture::readFrame(cv::Mat& outFrame) {
    if (!capture_.isOpened()) {
        return false;
    }

    bool success = capture_.read(outFrame);
    if (!success || outFrame.empty()) {
        return false;
    }

    return true;
}

void CameraCapture::release() {
    if (capture_.isOpened()) {
        capture_.release();
    }
}

bool CameraCapture::isOpen() const {
    return capture_.isOpened();
}

int CameraCapture::getDeviceIndex() const {
    return deviceIndex_;
}