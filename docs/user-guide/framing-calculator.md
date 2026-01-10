# Frame Profile Calculator

Use this interactive tool to select the features you need and discover which frame profile matches your requirements.

<div id="calculator-app">

<div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">

**Frame Type**
<div style="margin: 10px 0;">
  <label style="display: block; margin: 5px 0;">
    <input type="radio" name="frameType" value="basic" checked onchange="updateCalculator()"> 
    <strong>Basic (2 start bytes)</strong> - Better sync recovery, recommended for noisy links
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="radio" name="frameType" value="tiny" onchange="updateCalculator()"> 
    <strong>Tiny (1 start byte)</strong> - Lower overhead, good for clean links
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="radio" name="frameType" value="none" onchange="updateCalculator()"> 
    <strong>None (0 start bytes)</strong> - No framing, external sync required
  </label>
</div>

**Features**
<div style="margin: 10px 0;">
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasCrc" checked onchange="updateCalculator()"> 
    <strong>CRC Error Detection</strong> - Detect corrupted frames (recommended)
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasLength" checked onchange="updateCalculator()"> 
    <strong>Length Field</strong> - Variable-length messages (recommended)
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasLargePayload" onchange="updateCalculator()"> 
    <strong>Large Payloads (&gt;255 bytes)</strong> - Support up to 64KB messages
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasPackageId" onchange="updateCalculator()"> 
    <strong>Package ID</strong> - Namespace separation for many message types
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasSequence" onchange="updateCalculator()"> 
    <strong>Sequence Number</strong> - Detect packet loss
  </label>
  <label style="display: block; margin: 5px 0;">
    <input type="checkbox" id="hasRouting" onchange="updateCalculator()"> 
    <strong>Multi-Node Routing</strong> - System ID + Component ID for distributed systems
  </label>
</div>

</div>

<div id="results" style="background: #e8f5e9; padding: 20px; border-radius: 8px; border: 2px solid #4caf50; margin-top: 20px;">
  <h3 style="margin-top: 0; color: #2e7d32;">Selected Frame Format</h3>
  <div id="frameFormatName" style="font-size: 24px; font-weight: bold; color: #1b5e20; margin: 10px 0;">
    BasicDefault
  </div>
  <div id="frameFormatDetails" style="margin: 15px 0; font-size: 16px;">
    <div><strong>Profile:</strong> <span id="profileName">Profile.Standard</span></div>
    <div><strong>Total Overhead:</strong> <span id="overhead">6</span> bytes</div>
    <div><strong>Maximum Payload:</strong> <span id="maxPayload">255</span> bytes</div>
    <div><strong>Start Bytes:</strong> <span id="startBytes">0x90, 0x71</span></div>
  </div>
  <div id="frameStructure" style="background: white; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 14px; overflow-x: auto;">
    <strong>Frame Structure:</strong><br>
    <span id="structureDisplay">[0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]</span>
  </div>
</div>

</div>

<script>
// Frame format definitions
const frameFormats = {
  // Basic frames
  basic_minimal: {
    name: 'BasicMinimal',
    profile: 'Custom',
    overhead: 3,
    maxPayload: 255,
    startBytes: '0x90, 0x70',
    structure: '[0x90] [0x70] [MSG_ID] [PAYLOAD]'
  },
  basic_default: {
    name: 'BasicDefault',
    profile: 'Profile.Standard',
    overhead: 6,
    maxPayload: 255,
    startBytes: '0x90, 0x71',
    structure: '[0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_extended_msg_ids: {
    name: 'BasicExtendedMsgIds',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 255,
    startBytes: '0x90, 0x72',
    structure: '[0x90] [0x72] [LEN] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_extended_length: {
    name: 'BasicExtendedLength',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 65535,
    startBytes: '0x90, 0x73',
    structure: '[0x90] [0x73] [LEN_LO] [LEN_HI] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_extended: {
    name: 'BasicExtended',
    profile: 'Profile.Bulk',
    overhead: 8,
    maxPayload: 65535,
    startBytes: '0x90, 0x74',
    structure: '[0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_sys_comp: {
    name: 'BasicSysComp',
    profile: 'Custom',
    overhead: 8,
    maxPayload: 255,
    startBytes: '0x90, 0x75',
    structure: '[0x90] [0x75] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_seq: {
    name: 'BasicSeq',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 255,
    startBytes: '0x90, 0x76',
    structure: '[0x90] [0x76] [SEQ] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_multi_system_stream: {
    name: 'BasicMultiSystemStream',
    profile: 'Custom',
    overhead: 9,
    maxPayload: 255,
    startBytes: '0x90, 0x77',
    structure: '[0x90] [0x77] [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  basic_extended_multi_system_stream: {
    name: 'BasicExtendedMultiSystemStream',
    profile: 'Profile.Network',
    overhead: 11,
    maxPayload: 65535,
    startBytes: '0x90, 0x78',
    structure: '[0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  
  // Tiny frames
  tiny_minimal: {
    name: 'TinyMinimal',
    profile: 'Profile.Sensor',
    overhead: 2,
    maxPayload: 255,
    startBytes: '0x70',
    structure: '[0x70] [MSG_ID] [PAYLOAD]'
  },
  tiny_default: {
    name: 'TinyDefault',
    profile: 'Custom',
    overhead: 5,
    maxPayload: 255,
    startBytes: '0x71',
    structure: '[0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_extended_msg_ids: {
    name: 'TinyExtendedMsgIds',
    profile: 'Custom',
    overhead: 6,
    maxPayload: 255,
    startBytes: '0x72',
    structure: '[0x72] [LEN] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_extended_length: {
    name: 'TinyExtendedLength',
    profile: 'Custom',
    overhead: 6,
    maxPayload: 65535,
    startBytes: '0x73',
    structure: '[0x73] [LEN_LO] [LEN_HI] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_extended: {
    name: 'TinyExtended',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 65535,
    startBytes: '0x74',
    structure: '[0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_sys_comp: {
    name: 'TinySysComp',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 255,
    startBytes: '0x75',
    structure: '[0x75] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_seq: {
    name: 'TinySeq',
    profile: 'Custom',
    overhead: 6,
    maxPayload: 255,
    startBytes: '0x76',
    structure: '[0x76] [SEQ] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_multi_system_stream: {
    name: 'TinyMultiSystemStream',
    profile: 'Custom',
    overhead: 8,
    maxPayload: 255,
    startBytes: '0x77',
    structure: '[0x77] [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  tiny_extended_multi_system_stream: {
    name: 'TinyExtendedMultiSystemStream',
    profile: 'Custom',
    overhead: 10,
    maxPayload: 65535,
    startBytes: '0x78',
    structure: '[0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  
  // None frames
  none_minimal: {
    name: 'NoneMinimal',
    profile: 'Profile.IPC',
    overhead: 1,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[MSG_ID] [PAYLOAD]'
  },
  none_default: {
    name: 'NoneDefault',
    profile: 'Custom',
    overhead: 4,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_extended_msg_ids: {
    name: 'NoneExtendedMsgIds',
    profile: 'Custom',
    overhead: 5,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[LEN] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_extended_length: {
    name: 'NoneExtendedLength',
    profile: 'Custom',
    overhead: 5,
    maxPayload: 65535,
    startBytes: 'None',
    structure: '[LEN_LO] [LEN_HI] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_extended: {
    name: 'NoneExtended',
    profile: 'Custom',
    overhead: 6,
    maxPayload: 65535,
    startBytes: 'None',
    structure: '[LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_sys_comp: {
    name: 'NoneSysComp',
    profile: 'Custom',
    overhead: 6,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_seq: {
    name: 'NoneSeq',
    profile: 'Custom',
    overhead: 5,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[SEQ] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_multi_system_stream: {
    name: 'NoneMultiSystemStream',
    profile: 'Custom',
    overhead: 7,
    maxPayload: 255,
    startBytes: 'None',
    structure: '[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  },
  none_extended_multi_system_stream: {
    name: 'NoneExtendedMultiSystemStream',
    profile: 'Custom',
    overhead: 9,
    maxPayload: 65535,
    startBytes: 'None',
    structure: '[SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]'
  }
};

function updateCalculator() {
  // Get selected frame type
  const frameType = document.querySelector('input[name="frameType"]:checked').value;
  
  // Get selected features
  const hasCrc = document.getElementById('hasCrc').checked;
  const hasLength = document.getElementById('hasLength').checked;
  const hasLargePayload = document.getElementById('hasLargePayload').checked;
  const hasPackageId = document.getElementById('hasPackageId').checked;
  const hasSequence = document.getElementById('hasSequence').checked;
  const hasRouting = document.getElementById('hasRouting').checked;
  
  // Determine format key
  let formatKey = frameType + '_';
  
  // Determine payload type
  if (!hasCrc && !hasLength) {
    formatKey += 'minimal';
  } else if (hasSequence && hasRouting && hasLargePayload && hasPackageId) {
    formatKey += 'extended_multi_system_stream';
  } else if (hasSequence && hasRouting) {
    formatKey += 'multi_system_stream';
  } else if (hasRouting) {
    formatKey += 'sys_comp';
  } else if (hasSequence) {
    formatKey += 'seq';
  } else if (hasLargePayload && hasPackageId) {
    formatKey += 'extended';
  } else if (hasLargePayload) {
    formatKey += 'extended_length';
  } else if (hasPackageId) {
    formatKey += 'extended_msg_ids';
  } else {
    formatKey += 'default';
  }
  
  // Get format details
  const format = frameFormats[formatKey];
  
  // Update display
  document.getElementById('frameFormatName').textContent = format.name;
  document.getElementById('profileName').textContent = format.profile;
  document.getElementById('overhead').textContent = format.overhead;
  document.getElementById('maxPayload').textContent = format.maxPayload;
  document.getElementById('startBytes').textContent = format.startBytes;
  document.getElementById('structureDisplay').textContent = format.structure;
}

// Initialize calculator on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', updateCalculator);
} else {
  updateCalculator();
}
</script>

---

## Understanding the Results

### Frame Format Names

The frame format name tells you exactly what features are included:

- **Frame Type Prefix**: `Basic`, `Tiny`, or `None`
- **Payload Type Suffix**: `Default`, `Extended`, `MultiSystemStream`, etc.

### Overhead Calculation

The overhead is calculated as:

```
Overhead = Start Bytes + Header Fields + CRC Bytes

Basic frames: +2 bytes (0x90, 0x7X)
Tiny frames:  +1 byte  (0x7X)
None frames:  +0 bytes

Header fields:
- Length (8-bit):  +1 byte
- Length (16-bit): +2 bytes
- Message ID:      +1 byte (always present)
- Package ID:      +1 byte (if enabled)
- Sequence:        +1 byte (if enabled)
- System ID:       +1 byte (if routing enabled)
- Component ID:    +1 byte (if routing enabled)

Footer:
- CRC:             +2 bytes (if enabled)
```

### Next Steps

1. **Use a standard profile** that matches your needs (recommended)
2. **Use it in your code** when initializing the frame parser

### Using Standard Profiles

For most use cases, use one of the 5 standard profiles:

```python
# For general serial/UART:
ProfileStandard  # Basic header + Default payload

# For low-bandwidth sensors:
ProfileSensor    # Tiny header + Minimal payload

# For trusted inter-process communication:
ProfileIPC       # No header + Minimal payload

# For large file transfers:
ProfileBulk      # Basic header + Extended payload

# For multi-node mesh networks:
ProfileNetwork   # Basic header + ExtendedMultiSystemStream payload
```

### Contributing New Headers/Payloads

If you need a new header or payload type that doesn't exist, please submit a PR to the 
[struct-frame repository](https://github.com/mylonics/struct-frame).

### Example Usage

=== "Python"

    ```python
    from frame_profiles import (
        ProfileStandardConfig,
        BufferWriter,
        BufferReader
    )
    
    # Encode a message
    writer = BufferWriter(ProfileStandardConfig, 1024)
    writer.write(my_message)
    encoded = writer.data()
    
    # Decode messages
    reader = BufferReader(ProfileStandardConfig, encoded)
    for result in reader:
        if result.valid:
            print(f"Message ID: {result.msg_id}")
    ```

=== "TypeScript"

    ```typescript
    import {
        ProfileStandardConfig,
        BufferWriter,
        BufferReader
    } from './frame_profiles';
    
    // Encode a message
    const writer = new BufferWriter(ProfileStandardConfig, 1024);
    writer.write(myMessage);
    const encoded = writer.data();
    
    // Decode messages
    const reader = new BufferReader(ProfileStandardConfig, encoded);
    for (const result of reader) {
        if (result.valid) {
            console.log(`Message ID: ${result.msg_id}`);
        }
    }
    ```

=== "C++"

    ```cpp
    #include "FrameProfiles.hpp"
    
    // Encode a message
    uint8_t buffer[1024];
    StructFrame::BufferWriter<StructFrame::ProfileStandardConfig> writer(buffer, sizeof(buffer));
    writer.write(msg_id, &msg, sizeof(msg));
    
    // Decode messages
    StructFrame::BufferReader<StructFrame::ProfileStandardConfig> reader(buffer, writer.size());
    while (auto result = reader.next()) {
        // Process result->msg_id, result->msg_data
    }
    ```

---

## Additional Resources

- [Complete Framing Guide](framing.md)
- [Framing Architecture](framing-architecture.md)
- [SDK Overview](sdk-overview.md)
