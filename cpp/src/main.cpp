#include "MotionDetector.h"
#include "SnapshotManager.h"
#include "VideoRecorder.h"
#include "RecordingVerifier.h"
#include "CameraManager.h"
#include "Config.h"
#include "Logger.h"
#include "EventLogger.h"
#include <opencv2/opencv.hpp>
#include <iostream>

int main() {
	Logger::init("security_camera_system.log");
	Logger::log(LogLevel::Info, "Application starting.");

	Config config("config.txt");
	EventLogger eventLogger("db/events.db", "db/schema.sql");

	MotionDetector motionDetector(config.motionMinContourArea());
	SnapshotManager snapshotManager("snapshots", config.snapshotCooldownSeconds());
	VideoRecorder videoRecorder("recordings", config.recordingGraceSeconds(), config.recordingFps());
	CameraManager camera(config.cameraDeviceIndex(), config.cameraRetryIntervalSeconds());

	if (!camera.open()) {
		std::cerr << "Failed to open camera.\n";
		return 1;
	}

	auto orphaned = RecordingVerifier::scanForOrphanedRecordings("recordings");
	for (const auto& path : orphaned) {
		std::cout << "Orphaned/corrupt recording found: " << path << "\n";
	}

	std::cout << "Camera opened successfully. Press 'q' to quit.\n";

	bool wasMotionActive = false;

	cv::Mat frame;
	while (true) {
		if (!camera.readFrame(frame)) {
			continue;
		}

		cv::Rect motionBox;
		bool motionActive = motionDetector.detectMotion(frame, &motionBox);

		if (motionActive) {
			cv::rectangle(frame, motionBox, cv::Scalar(0, 255, 0), 2);
			if (snapshotManager.captureIfReady(frame)) {
				eventLogger.logEvent("snapshot", snapshotManager.getLastSavedFilePath(), config.cameraDeviceIndex());
			}
		}

		bool wasRecordingBeforeUpdate = videoRecorder.isRecording();
		videoRecorder.update(motionActive, frame);
		if (wasRecordingBeforeUpdate && !videoRecorder.isRecording()) {
			std::string finishedPath = videoRecorder.getLastCompletedFilePath();
			if (!RecordingVerifier::verifyRecording(finishedPath)) {
				Logger::log(LogLevel::Warning, "Just-completed recording failed verification: " + finishedPath);
			}
			eventLogger.logEvent("recording_stop", finishedPath, config.cameraDeviceIndex());
		}
		if (!wasRecordingBeforeUpdate && videoRecorder.isRecording()) {
			eventLogger.logEvent("recording_start", "", config.cameraDeviceIndex());
		}

		if (motionActive && !wasMotionActive) {
			Logger::log(LogLevel::Info, "Motion detected.");
			eventLogger.logEvent("motion_start", "", config.cameraDeviceIndex());
		}
		else if (!motionActive && wasMotionActive) {
			Logger::log(LogLevel::Info, "Motion stopped.");
			eventLogger.logEvent("motion_stop", "", config.cameraDeviceIndex());
		}
		wasMotionActive = motionActive;

		cv::imshow("Camera Capture", frame);

		if (cv::waitKey(1) == 'q') {
			break;
		}
	}

	// If a recording is still open when the user quits, stopImmediately()
	// closes the file — log that final stop before shutting down.
	bool wasRecordingAtExit = videoRecorder.isRecording();
	videoRecorder.stopImmediately();
	if (wasRecordingAtExit) {
		eventLogger.logEvent("recording_stop", videoRecorder.getLastCompletedFilePath(), config.cameraDeviceIndex());
	}

	camera.release();
	cv::destroyAllWindows();
	Logger::log(LogLevel::Info, "Application shutting down.");
	Logger::shutdown();
	return 0;
}