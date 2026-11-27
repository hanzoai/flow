cmake_minimum_required(VERSION 3.16)
project(hanzo_flow_sdk VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(CURL REQUIRED)
find_package(Threads REQUIRED)

# Header-only 1:1 C++20 flow-core DAG engine
add_library(hanzo_flow_core INTERFACE)
target_include_directories(hanzo_flow_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(hanzo_flow_core INTERFACE cxx_std_20)

# Native C++20 REST SDK for /v1/flow/*
add_library(hanzo_flow_sdk STATIC
    src/client.cpp
)
target_link_libraries(hanzo_flow_sdk PUBLIC
    hanzo_flow_core
    CURL::libcurl
)
target_compile_features(hanzo_flow_sdk PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(hanzo_flow_sdk PRIVATE /W4 /WX)
else()
    target_compile_options(hanzo_flow_sdk PRIVATE -Wall -Wextra -Werror)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(test_flow tests/test_flow.cpp)
    target_link_libraries(test_flow PRIVATE hanzo_flow_sdk Threads::Threads)
    if(MSVC)
        target_compile_options(test_flow PRIVATE /W4 /WX)
    else()
        target_compile_options(test_flow PRIVATE -Wall -Wextra -Werror)
    endif()
    add_test(NAME hanzo_flow_tests COMMAND test_flow)
endif()
