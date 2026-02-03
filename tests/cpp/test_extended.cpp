#include "include/extended_messages.hpp"
#include "include/test_harness.hpp"

static constexpr char TEST_NAME[] = "ExtendedMessages";
static constexpr char PROFILES[] = "bulk, network";

int main(int argc, char* argv[]) {
  return TestHarness<ExtendedMessages, FrameParsers::get_message_info, TEST_NAME, PROFILES>::run(argc, argv);
}
