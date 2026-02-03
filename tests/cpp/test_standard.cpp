#include "include/standard_messages.hpp"
#include "include/test_harness.hpp"

static constexpr char TEST_NAME[] = "StandardMessages";
static constexpr char PROFILES[] = "standard, sensor, ipc, bulk, network";

int main(int argc, char* argv[]) {
  return TestHarness<StandardMessages, FrameParsers::get_message_info, TEST_NAME, PROFILES>::run(argc, argv);
}
