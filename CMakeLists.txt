cmake_minimum_required(VERSION 3.16)
project(SlideApp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(SlideApp
  src/main.cpp
  src/HomeWindow.cpp
  src/HomeWindow.h
)

target_link_libraries(SlideApp PRIVATE Qt6::Widgets)
