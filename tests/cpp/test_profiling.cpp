/**
 * Struct-Frame-Generic Profiling Test
 *
 * Compares packed vs unpacked struct performance for struct-frame encode/decode.
 * Core structs and functions are in profiling_generic.hpp.
 */

#include <chrono>
#include <cstdio>

#include "profiling_generic.hpp"

// Timing function using std::chrono
double get_current_time_seconds() {
  return std::chrono::duration<double>(
      std::chrono::high_resolution_clock::now().time_since_epoch()).count();
}

int main() {
  constexpr size_t ITERATIONS = GenericTests::DEFAULT_ITERATIONS;
  constexpr size_t RUNS = GenericTests::DEFAULT_RUNS;

  printf("\n");
  printf("=============================================================\n");
  printf("STRUCT-FRAME-GENERIC PROFILING TEST\n");
  printf("=============================================================\n");
  printf("\nTest configuration:\n");
  printf("  Messages per run: %zu | Runs: %zu | Total messages: %zu\n", 
         ITERATIONS, RUNS, ITERATIONS * RUNS);
  printf("  Packed size: %zu bytes | Unpacked size: %zu bytes\n",
         sizeof(GenericTests::TestMessagePacked), sizeof(GenericTests::TestMessageUnpacked));

  // Run the profiling test
  auto results = GenericTests::run_test(get_current_time_seconds);

  if (!results.success) {
    printf("\n[TEST FAILED] Encode/decode or verification failed.\n\n");
    return 1;
  }

  // Convert seconds to milliseconds for display
  double packed_encode_ms = results.packed_encode_seconds * 1000.0;
  double unpacked_encode_ms = results.unpacked_encode_seconds * 1000.0;
  double packed_decode_ms = results.packed_decode_seconds * 1000.0;
  double unpacked_decode_ms = results.unpacked_decode_seconds * 1000.0;
  
  // Convert per-message timings to microseconds for display
  double packed_encode_us_per_msg = results.packed_encode_per_msg_seconds * 1000000.0;
  double unpacked_encode_us_per_msg = results.unpacked_encode_per_msg_seconds * 1000000.0;
  double packed_decode_us_per_msg = results.packed_decode_per_msg_seconds * 1000000.0;
  double unpacked_decode_us_per_msg = results.unpacked_decode_per_msg_seconds * 1000000.0;

  // Print encode performance
  printf("\n  Encode Performance Difference:\n");
  if (results.encode_diff_percent > 0) {
    printf("    Packed is %.1f%% SLOWER than unpacked\n", results.encode_diff_percent);
  } else if (results.encode_diff_percent < 0) {
    printf("    Packed is %.1f%% FASTER than unpacked\n", -results.encode_diff_percent);
  } else {
    printf("    No significant difference\n");
  }

  // ---- SUMMARY ----
  printf("\n=============================================================\n");
  printf("SUMMARY (Total Time for %zu messages)\n", results.total_messages);
  printf("=============================================================\n\n");
  printf("  %-10s %10s %10s %10s\n", "Operation", "Packed", "Unpacked", "Diff");
  printf("  %-10s %10s %10s %10s\n", "----------", "----------", "----------", "----------");
  printf("  %-10s %8.3f ms %8.3f ms %+9.1f%%\n", "Encode", 
         packed_encode_ms, unpacked_encode_ms, results.encode_diff_percent);
  printf("  %-10s %8.3f ms %8.3f ms %+9.1f%%\n", "Decode", 
         packed_decode_ms, unpacked_decode_ms, results.decode_diff_percent);

  printf("\n  Overall: Packed is %.1f%% %s than unpacked\n", 
         results.total_diff_percent > 0 ? results.total_diff_percent : -results.total_diff_percent,
         results.total_diff_percent > 1.0 ? "SLOWER" : 
         (results.total_diff_percent < -1.0 ? "FASTER" : "~EQUAL"));

  printf("\n=============================================================\n");
  printf("PER-MESSAGE TIMING\n");
  printf("=============================================================\n\n");
  printf("  %-10s %12s %12s\n", "Operation", "Packed", "Unpacked");
  printf("  %-10s %12s %12s\n", "----------", "------------", "------------");
  printf("  %-10s %9.3f us %9.3f us\n", "Encode", 
         packed_encode_us_per_msg, unpacked_encode_us_per_msg);
  printf("  %-10s %9.3f us %9.3f us\n", "Decode", 
         packed_decode_us_per_msg, unpacked_decode_us_per_msg);

  printf("\n[TEST PASSED] All messages verified successfully.\n\n");

  return 0;
}
