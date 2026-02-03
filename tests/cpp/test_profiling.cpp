/**
 * Struct-Frame-Generic Profiling Test
 *
 * Compares packed vs unpacked struct performance for struct-frame encode/decode.
 * Core structs and functions are in profiling_generic.hpp.
 */

#include <chrono>
#include <cstdio>
#include <functional>

#include "profiling_generic.hpp"

using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

// Time an operation and return duration in milliseconds
template<typename Func>
Duration time_operation(Func&& func) {
  auto start = Clock::now();
  func();
  return Clock::now() - start;
}

// Calculate percentage difference (positive = packed slower)
double calc_diff_pct(double packed_ms, double unpacked_ms) {
  return unpacked_ms > 0 ? ((packed_ms - unpacked_ms) / unpacked_ms) * 100.0 : 0.0;
}

// Print performance comparison
void print_diff(const char* operation, double diff_pct) {
  printf("\n  %s Performance Difference:\n", operation);
  if (diff_pct > 0) {
    printf("    Packed is %.1f%% SLOWER than unpacked\n", diff_pct);
  } else if (diff_pct < 0) {
    printf("    Packed is %.1f%% FASTER than unpacked\n", -diff_pct);
  } else {
    printf("    No significant difference\n");
  }
}

int main() {
  constexpr size_t ITERATIONS = GenericTests::DEFAULT_ITERATIONS;

  printf("\n");
  printf("=============================================================\n");
  printf("STRUCT-FRAME-GENERIC PROFILING TEST\n");
  printf("=============================================================\n");
  printf("\nTest configuration:\n");
  printf("  Messages: %zu | Packed size: %zu bytes | Unpacked size: %zu bytes\n",
         ITERATIONS, sizeof(GenericTests::TestMessagePacked), sizeof(GenericTests::TestMessageUnpacked));

  GenericTests::init_all_messages();

  // ---- ENCODE ----
  printf("\n-------------------------------------------------------------\n");
  printf("ENCODE TESTS\n");
  printf("-------------------------------------------------------------\n");

  GenericTests::EncodeDecodeResult packed_enc, unpacked_enc;
  auto packed_encode_time = time_operation([&] { packed_enc = GenericTests::encode_packed(); });
  GenericTests::do_not_optimize_packed_buffer();
  
  auto unpacked_encode_time = time_operation([&] { unpacked_enc = GenericTests::encode_unpacked(); });
  GenericTests::do_not_optimize_unpacked_buffer();

  if (!packed_enc.success || !unpacked_enc.success) {
    printf("  [FAIL] Encode failed\n");
    return 1;
  }

  printf("  Packed:   %8.3f ms (%zu bytes)\n", packed_encode_time.count(), packed_enc.total_bytes);
  printf("  Unpacked: %8.3f ms (%zu bytes)\n", unpacked_encode_time.count(), unpacked_enc.total_bytes);
  
  double encode_diff = calc_diff_pct(packed_encode_time.count(), unpacked_encode_time.count());
  print_diff("Encode", encode_diff);

  // ---- DECODE ----
  printf("\n-------------------------------------------------------------\n");
  printf("DECODE TESTS\n");
  printf("-------------------------------------------------------------\n");

  GenericTests::EncodeDecodeResult packed_dec, unpacked_dec;
  auto packed_decode_time = time_operation([&] { packed_dec = GenericTests::decode_packed(); });
  GenericTests::do_not_optimize_decoded_packed();
  
  auto unpacked_decode_time = time_operation([&] { unpacked_dec = GenericTests::decode_unpacked(); });
  GenericTests::do_not_optimize_decoded_unpacked();

  if (!packed_dec.success || !unpacked_dec.success) {
    printf("  [FAIL] Decode failed\n");
    return 1;
  }

  printf("  Packed:   %8.3f ms\n", packed_decode_time.count());
  printf("  Unpacked: %8.3f ms\n", unpacked_decode_time.count());
  
  double decode_diff = calc_diff_pct(packed_decode_time.count(), unpacked_decode_time.count());
  print_diff("Decode", decode_diff);

  // ---- SUMMARY ----
  printf("\n=============================================================\n");
  printf("SUMMARY\n");
  printf("=============================================================\n\n");
  printf("  %-10s %10s %10s %10s\n", "Operation", "Packed", "Unpacked", "Diff");
  printf("  %-10s %10s %10s %10s\n", "----------", "----------", "----------", "----------");
  printf("  %-10s %8.3f ms %8.3f ms %+9.1f%%\n", "Encode", packed_encode_time.count(), unpacked_encode_time.count(), encode_diff);
  printf("  %-10s %8.3f ms %8.3f ms %+9.1f%%\n", "Decode", packed_decode_time.count(), unpacked_decode_time.count(), decode_diff);

  double total_packed = packed_encode_time.count() + packed_decode_time.count();
  double total_unpacked = unpacked_encode_time.count() + unpacked_decode_time.count();
  double total_diff = calc_diff_pct(total_packed, total_unpacked);

  printf("\n  Overall: Packed is %.1f%% %s than unpacked\n",
         total_diff > 0 ? total_diff : -total_diff,
         total_diff > 1.0 ? "SLOWER" : (total_diff < -1.0 ? "FASTER" : "~EQUAL"));

  // ---- VERIFY ----
  bool verified = GenericTests::verify_packed_results();
  printf("\n%s\n\n", verified 
         ? "[TEST PASSED] All messages verified successfully." 
         : "[TEST FAILED] Data integrity check failed.");

  return verified ? 0 : 1;
}
