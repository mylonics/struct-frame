#include "include/test_harness.hpp"
#include "include/variable_flag_messages.hpp"

static constexpr char TEST_NAME[] = "VariableFlagMessages";
static constexpr char PROFILES[] = "standard, sensor, ipc, bulk, network";

int main(int argc, char* argv[]) {
  return TestHarness<VariableFlagMessages, structframe::serialization_test::get_message_info, TEST_NAME, PROFILES>::run(argc, argv);
}
