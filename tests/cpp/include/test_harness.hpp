#pragma once

#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "profile_runner.hpp"

// TestHarness - High-level test setup, CLI parsing, file I/O, and test execution
//
// Template parameters:
//   - MessageProvider: struct with MessageVariant, MESSAGE_COUNT, get_message()
//   - GetMsgInfo: function pointer to get_message_info for the message set
//   - TestName: constexpr char[] for test output labeling
//   - ProfileHelp: constexpr char[] listing available profiles

template <typename MessageProvider, GetMessageInfoFn GetMsgInfo, const char* TestName, const char* ProfileHelp>
class TestHarness {
 public:
  // Profile runners for each frame profile
  using Standard = ProfileRunner<MessageProvider, FrameParsers::ProfileStandardConfig, GetMsgInfo>;
  using Sensor = ProfileRunner<MessageProvider, FrameParsers::ProfileSensorConfig, GetMsgInfo>;
  using IPC = ProfileRunner<MessageProvider, FrameParsers::ProfileIPCConfig, GetMsgInfo>;
  using Bulk = ProfileRunner<MessageProvider, FrameParsers::ProfileBulkConfig, GetMsgInfo>;
  using Network = ProfileRunner<MessageProvider, FrameParsers::ProfileNetworkConfig, GetMsgInfo>;

  static constexpr size_t BUFFER_SIZE = 16384;

  // Main entry point - parses CLI and runs appropriate test
  static int run(int argc, char* argv[]) {
    if (argc < 3) {
      print_usage(argv[0]);
      return 1;
    }

    std::string mode = argv[1];
    std::string profile = argv[2];
    std::string file_path = (argc > 3) ? argv[3] : "";

    if (mode != "encode" && mode != "decode" && mode != "both") {
      printf("Unknown mode: %s\n", mode.c_str());
      print_usage(argv[0]);
      return 1;
    }

    if ((mode == "encode" || mode == "decode") && file_path.empty()) {
      printf("Mode '%s' requires a file argument\n", mode.c_str());
      print_usage(argv[0]);
      return 1;
    }

    ProfileOps ops = get_profile_ops(profile);
    if (!ops.encode) {
      printf("Unknown profile: %s\n", profile.c_str());
      print_usage(argv[0]);
      return 1;
    }

    printf("\n[TEST START] %s %s %s\n", TestName, profile.c_str(), mode.c_str());

    int result;
    if (mode == "encode")
      result = run_encode(ops, file_path);
    else if (mode == "decode")
      result = run_decode(ops, file_path);
    else
      result = run_both(ops);

    printf("[TEST END] %s %s %s: %s\n\n", TestName, profile.c_str(), mode.c_str(), result == 0 ? "PASS" : "FAIL");
    return result;
  }

 private:
  static void print_usage(const char* program_name) {
    printf("Usage:\n");
    printf("  %s encode <profile> <output_file>\n", program_name);
    printf("  %s decode <profile> <input_file>\n", program_name);
    printf("  %s both <profile>\n", program_name);
    printf("\nProfiles: %s\n", ProfileHelp);
  }

  static ProfileOps get_profile_ops(const std::string& profile) {
    if (profile == "standard") return {Standard::encode, Standard::parse};
    if (profile == "sensor") return {Sensor::encode, Sensor::parse};
    if (profile == "ipc") return {IPC::encode, IPC::parse};
    if (profile == "bulk") return {Bulk::encode, Bulk::parse};
    if (profile == "network") return {Network::encode, Network::parse};
    return {nullptr, nullptr};
  }

  static bool write_file(const std::string& path, const uint8_t* data, size_t size) {
    std::ofstream file(path, std::ios::binary);
    if (!file) return false;
    file.write(reinterpret_cast<const char*>(data), size);
    return true;
  }

  static size_t read_file(const std::string& path, uint8_t* buffer, size_t buffer_size) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return 0;
    file.read(reinterpret_cast<char*>(buffer), buffer_size);
    return file.gcount();
  }

  static int run_encode(const ProfileOps& ops, const std::string& output_file) {
    std::vector<uint8_t> buffer(BUFFER_SIZE);
    size_t bytes = ops.encode(buffer.data(), buffer.size());
    if (bytes == 0 || !write_file(output_file, buffer.data(), bytes)) {
      printf("[ENCODE] FAILED\n");
      return 1;
    }
    printf("[ENCODE] SUCCESS: Wrote %zu bytes to %s\n", bytes, output_file.c_str());
    return 0;
  }

  static int run_decode(const ProfileOps& ops, const std::string& input_file) {
    std::vector<uint8_t> buffer(BUFFER_SIZE);
    size_t size = read_file(input_file, buffer.data(), buffer.size());
    if (size == 0) {
      printf("[DECODE] FAILED: Cannot read file\n");
      return 1;
    }
    size_t count = ops.parse(buffer.data(), size);
    if (count != MessageProvider::MESSAGE_COUNT) {
      printf("[DECODE] FAILED: %zu of %zu messages validated\n", count, MessageProvider::MESSAGE_COUNT);
      return 1;
    }
    printf("[DECODE] SUCCESS: %zu messages validated\n", count);
    return 0;
  }

  static int run_both(const ProfileOps& ops) {
    std::vector<uint8_t> buffer(BUFFER_SIZE);
    size_t bytes = ops.encode(buffer.data(), buffer.size());
    if (bytes == 0) {
      printf("[BOTH] FAILED: Encoding error\n");
      return 1;
    }
    printf("[BOTH] Encoded %zu bytes\n", bytes);

    size_t count = ops.parse(buffer.data(), bytes);
    if (count != MessageProvider::MESSAGE_COUNT) {
      printf("[BOTH] FAILED: %zu of %zu messages validated\n", count, MessageProvider::MESSAGE_COUNT);
      return 1;
    }
    printf("[BOTH] SUCCESS: %zu messages round-trip validated\n", count);
    return 0;
  }
};
