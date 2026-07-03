/**
 * Compile-only test: the public C++ SDK umbrella header must compile standalone.
 *
 * The umbrella headers (sdk.hpp / sdk_embedded.hpp) are the documented entry
 * points for SDK users, but no runtime test includes them — which once let
 * serial_transport.hpp ship in an uncompilable state. This TU instantiates the
 * embedded umbrella (transport + serial_transport + observer + struct_frame_sdk;
 * the full sdk.hpp additionally needs the vendored ASIO include path, so it is
 * exercised separately by user builds).
 */

#include "struct_frame_sdk/sdk_embedded.hpp"

int main() {
  // Touch a couple of symbols so the headers are actually instantiated.
  structframe::sdk::TransportConfig config;
  (void)config;

  structframe::sdk::BaseTransport transport;
  (void)transport.IsConnected();

  return 0;
}
