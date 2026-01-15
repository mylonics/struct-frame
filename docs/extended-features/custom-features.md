# Extended Features

This page covers advanced scenarios for special use cases.

## Package IDs for Extended Addressing

Package IDs enable 16-bit message addressing for large systems.

**When to use:**
- Systems with more than 255 messages
- Multi-package systems requiring namespace separation

**Frame compatibility:**
Use Extended or ExtendedMultiSystemStream payload types with package IDs.

**Message ID encoding:**
- Without pkgid: 8-bit (0-255)
- With pkgid: 16-bit = `(package_id << 8) | msg_id`

See [Message Definitions](../basic-usage/message-definitions.md#message-options) for usage details.

## Minimal Frames (Bandwidth-Limited Scenarios)

Minimal frames remove length and checksum fields for lowest overhead.

**Requirements:**
- All messages must be fixed-size (no max_size, only size)
- Parser needs message length lookup function

The generator creates a `get_msg_info` function automatically:

=== "Python"
    ```python
    from struct_frame.frame_profiles import get_profile, Profile
    from messages import get_msg_info
    
    # Get minimal profile
    profile = get_profile(Profile.SENSOR)  # TinyMinimal
    
    # Parser uses auto-generated get_msg_info
    parser = profile.create_parser(get_msg_info)
    ```

=== "C++"
    ```cpp
    #include "FrameProfiles.hpp"
    #include "messages.structframe.hpp"
    
    // Use sensor profile with minimal frames
    ProfileSensorAccumulatingReader reader(get_msg_info);
    ```

See [Framing](../basic-usage/framing.md) for more on minimal frames.

## Large Messages

For messages > 255 bytes, use Extended payload type:

```bash
python -m struct_frame large.proto --build_c
```

Use BasicExtended or Network frame profile when encoding.

## Variable-Length Encoding

Use `option variable = true;` for efficient encoding of messages with variable-length arrays or strings:

```proto
message LogEntry {
  option msgid = 10;
  option variable = true;
  uint64 timestamp = 1;
  string message = 2 [max_size=256];
  repeated uint8 data = 3 [max_size=128];
}
```

Only used bytes are transmitted instead of full max_size. See [Message Definitions](../basic-usage/message-definitions.md#message-options) for details.

