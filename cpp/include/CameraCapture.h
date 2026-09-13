#pragma once

#include <opencv2/opencv.hpp>
#include <string>

class CameraCapture {
public:
	explicit CameraCapture(int deviceIndex);
	~CameraCapture();

	CameraCapture(const CameraCapture&) = delete;
	CameraCapture& operator=(const CameraCapture&) = delete;

	bool open();

	bool readFrame(cv::Mat& outFrame);

	void release();

	bool isOpen() const;
	int getDeviceIndex() const;

private:
	int deviceIndex_;
	cv::VideoCapture capture_;
};