cmake_minimum_required(VERSION 3.20)
project(SecurityCameraSystem)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)
find_package(unofficial-sqlite3 CONFIG REQUIRED)

add_executable(SecurityCameraSystem
    cpp/src/main.cpp
    cpp/src/CameraCapture.cpp
    cpp/src/MotionDetector.cpp
    cpp/src/SnapshotManager.cpp
    cpp/src/VideoRecorder.cpp
    cpp/src/RecordingVerifier.cpp
    cpp/src/CameraManager.cpp
    cpp/src/Config.cpp
    cpp/src/Logger.cpp
    cpp/src/EventLogger.cpp
)

target_include_directories(SecurityCameraSystem PRIVATE
    cpp/include
)

target_link_libraries(SecurityCameraSystem PRIVATE
    ${OpenCV_LIBS}
    unofficial::sqlite3::sqlite3
)

add_custom_command(TARGET SecurityCameraSystem POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_SOURCE_DIR}/config.txt
        $<TARGET_FILE_DIR:SecurityCameraSystem>/config.txt
)