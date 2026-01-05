-- Wireshark Dissector for Struct Frame Protocol
-- This dissector supports all standard frame format profiles
--
-- Installation:
--   1. Copy this file to your Wireshark plugins directory:
--      - Windows: %APPDATA%\Wireshark\plugins\
--      - Linux: ~/.local/lib/wireshark/plugins/
--      - macOS: ~/.wireshark/plugins/
--   2. Restart Wireshark
--
-- Usage:
--   The dissector will automatically decode struct-frame protocols
--   based on the start bytes (0x90 for Basic, 0x70-0x78 for Tiny)

-- Protocol definition
local struct_frame_proto = Proto("struct_frame", "Struct Frame Protocol")

-- Field definitions
local f_start1 = ProtoField.uint8("struct_frame.start1", "Start Byte 1", base.HEX)
local f_start2 = ProtoField.uint8("struct_frame.start2", "Start Byte 2", base.HEX)
local f_header_type = ProtoField.string("struct_frame.header_type", "Header Type")
local f_payload_type = ProtoField.string("struct_frame.payload_type", "Payload Type")
local f_profile_name = ProtoField.string("struct_frame.profile_name", "Profile Name")

-- Payload fields
local f_sequence = ProtoField.uint8("struct_frame.sequence", "Sequence Number", base.DEC)
local f_system_id = ProtoField.uint8("struct_frame.system_id", "System ID", base.DEC)
local f_component_id = ProtoField.uint8("struct_frame.component_id", "Component ID", base.DEC)
local f_length = ProtoField.uint16("struct_frame.length", "Length", base.DEC)
local f_length_lo = ProtoField.uint8("struct_frame.length_lo", "Length Low", base.DEC)
local f_length_hi = ProtoField.uint8("struct_frame.length_hi", "Length High", base.DEC)
local f_package_id = ProtoField.uint8("struct_frame.package_id", "Package ID", base.DEC)
local f_message_id = ProtoField.uint8("struct_frame.message_id", "Message ID", base.DEC)
local f_payload = ProtoField.bytes("struct_frame.payload", "Payload Data")
local f_crc1 = ProtoField.uint8("struct_frame.crc1", "CRC Byte 1", base.HEX)
local f_crc2 = ProtoField.uint8("struct_frame.crc2", "CRC Byte 2", base.HEX)
local f_crc_status = ProtoField.string("struct_frame.crc_status", "CRC Status")

struct_frame_proto.fields = {
    f_start1, f_start2, f_header_type, f_payload_type, f_profile_name,
    f_sequence, f_system_id, f_component_id, f_length, f_length_lo, f_length_hi,
    f_package_id, f_message_id, f_payload, f_crc1, f_crc2, f_crc_status
}

-- Payload type mapping (offset from 0x70 base)
local payload_types = {
    [0] = "Minimal",
    [1] = "Default",
    [2] = "ExtendedMsgIds",
    [3] = "ExtendedLength",
    [4] = "Extended",
    [5] = "SysComp",
    [6] = "Seq",
    [7] = "MultiSystemStream",
    [8] = "ExtendedMultiSystemStream"
}

-- Profile name mapping for common combinations
local profile_names = {
    ["BasicDefault"] = "Standard (General Serial/UART)",
    ["TinyMinimal"] = "Sensor (Low-Bandwidth)",
    ["NoneMinimal"] = "IPC (Trusted Inter-Process)",
    ["BasicExtended"] = "Bulk (Large Data Transfers)",
    ["BasicExtendedMultiSystemStream"] = "Network (Multi-Node Mesh)"
}

-- Payload structure definitions
local payload_structures = {
    [0] = { -- Minimal
        has_sequence = false,
        has_system_id = false,
        has_component_id = false,
        has_length = false,
        length_bytes = 0,
        has_package_id = false,
        has_crc = false
    },
    [1] = { -- Default
        has_sequence = false,
        has_system_id = false,
        has_component_id = false,
        has_length = true,
        length_bytes = 1,
        has_package_id = false,
        has_crc = true
    },
    [2] = { -- ExtendedMsgIds
        has_sequence = false,
        has_system_id = false,
        has_component_id = false,
        has_length = true,
        length_bytes = 1,
        has_package_id = true,
        has_crc = true
    },
    [3] = { -- ExtendedLength
        has_sequence = false,
        has_system_id = false,
        has_component_id = false,
        has_length = true,
        length_bytes = 2,
        has_package_id = false,
        has_crc = true
    },
    [4] = { -- Extended
        has_sequence = false,
        has_system_id = false,
        has_component_id = false,
        has_length = true,
        length_bytes = 2,
        has_package_id = true,
        has_crc = true
    },
    [5] = { -- SysComp
        has_sequence = false,
        has_system_id = true,
        has_component_id = true,
        has_length = true,
        length_bytes = 1,
        has_package_id = false,
        has_crc = true
    },
    [6] = { -- Seq
        has_sequence = true,
        has_system_id = false,
        has_component_id = false,
        has_length = true,
        length_bytes = 1,
        has_package_id = false,
        has_crc = true
    },
    [7] = { -- MultiSystemStream
        has_sequence = true,
        has_system_id = true,
        has_component_id = true,
        has_length = true,
        length_bytes = 1,
        has_package_id = false,
        has_crc = true
    },
    [8] = { -- ExtendedMultiSystemStream
        has_sequence = true,
        has_system_id = true,
        has_component_id = true,
        has_length = true,
        length_bytes = 2,
        has_package_id = true,
        has_crc = true
    }
}

-- Fletcher-16 checksum calculation
function fletcher16(data)
    local sum1 = 0
    local sum2 = 0
    
    for i = 0, data:len() - 1 do
        local byte = data:get_index(i)
        sum1 = (sum1 + byte) % 256
        sum2 = (sum2 + sum1) % 256
    end
    
    return sum1, sum2
end

-- Main dissector function
function struct_frame_proto.dissector(buffer, pinfo, tree)
    local length = buffer:len()
    if length == 0 then return end
    
    pinfo.cols.protocol = "STRUCT_FRAME"
    
    local offset = 0
    
    -- Detect frame type by examining start bytes
    local first_byte = buffer(0, 1):uint()
    local header_type = nil
    local payload_type_offset = nil
    local start_bytes = 0
    
    if first_byte == 0x90 then
        -- Basic frame (2 start bytes)
        if length < 2 then return end
        header_type = "Basic"
        start_bytes = 2
        payload_type_offset = buffer(1, 1):uint() - 0x70
    elseif first_byte >= 0x70 and first_byte <= 0x78 then
        -- Tiny frame (1 start byte)
        header_type = "Tiny"
        start_bytes = 1
        payload_type_offset = first_byte - 0x70
    else
        -- Could be None frame (no start bytes) or unknown
        -- TODO: None frames cannot be auto-detected since they have no start bytes.
        -- They would require manual configuration or external context.
        return
    end
    
    -- Validate payload type
    if payload_type_offset < 0 or payload_type_offset > 8 then
        return
    end
    
    local payload_type_name = payload_types[payload_type_offset]
    if not payload_type_name then
        return
    end
    
    local structure = payload_structures[payload_type_offset]
    if not structure then
        return
    end
    
    -- Create protocol tree
    local subtree = tree:add(struct_frame_proto, buffer(), "Struct Frame Protocol")
    
    -- Determine profile name
    local profile_name = header_type .. payload_type_name
    local display_name = profile_names[profile_name] or profile_name
    
    -- Add header information
    if header_type == "Basic" then
        subtree:add(f_start1, buffer(0, 1))
        subtree:add(f_start2, buffer(1, 1))
        offset = 2
    elseif header_type == "Tiny" then
        subtree:add(f_start1, buffer(0, 1)):append_text(" (Tiny frame)")
        offset = 1
    end
    
    subtree:add(f_header_type, header_type)
    subtree:add(f_payload_type, payload_type_name)
    subtree:add(f_profile_name, display_name)
    
    -- Parse payload header fields according to structure
    local payload_length = nil
    local crc_start_offset = nil
    
    -- Sequence number
    if structure.has_sequence then
        if offset + 1 > length then return end
        subtree:add(f_sequence, buffer(offset, 1))
        offset = offset + 1
    end
    
    -- System ID and Component ID
    if structure.has_system_id then
        if offset + 1 > length then return end
        subtree:add(f_system_id, buffer(offset, 1))
        offset = offset + 1
    end
    
    if structure.has_component_id then
        if offset + 1 > length then return end
        subtree:add(f_component_id, buffer(offset, 1))
        offset = offset + 1
    end
    
    -- Length field
    if structure.has_length then
        if structure.length_bytes == 1 then
            if offset + 1 > length then return end
            payload_length = buffer(offset, 1):uint()
            subtree:add(f_length, buffer(offset, 1))
            offset = offset + 1
        elseif structure.length_bytes == 2 then
            if offset + 2 > length then return end
            local len_lo = buffer(offset, 1):uint()
            local len_hi = buffer(offset + 1, 1):uint()
            payload_length = len_lo + (len_hi * 256)
            subtree:add(f_length_lo, buffer(offset, 1))
            subtree:add(f_length_hi, buffer(offset + 1, 1))
            local combined_length = subtree:add(f_length, payload_length)
            combined_length:set_generated()
            offset = offset + 2
        end
    end
    
    -- Package ID
    if structure.has_package_id then
        if offset + 1 > length then return end
        subtree:add(f_package_id, buffer(offset, 1))
        offset = offset + 1
    end
    
    -- Message ID
    if offset + 1 > length then return end
    local msg_id = buffer(offset, 1):uint()
    subtree:add(f_message_id, buffer(offset, 1))
    offset = offset + 1
    
    -- Payload data
    local expected_payload_len = payload_length or (length - offset)
    if structure.has_crc then
        expected_payload_len = expected_payload_len - 2
    end
    
    if payload_length then
        crc_start_offset = start_bytes
        if offset + payload_length > length then
            -- Incomplete frame
            pinfo.cols.info = string.format("%s (incomplete)", display_name)
            return
        end
        
        if payload_length > 0 then
            subtree:add(f_payload, buffer(offset, payload_length))
            offset = offset + payload_length
        end
    else
        -- Minimal format - payload extends to end (minus CRC if present)
        local remaining = length - offset
        if structure.has_crc then
            remaining = remaining - 2
        end
        
        if remaining > 0 then
            subtree:add(f_payload, buffer(offset, remaining))
            offset = offset + remaining
        end
    end
    
    -- CRC
    if structure.has_crc then
        if offset + 2 > length then return end
        
        subtree:add(f_crc1, buffer(offset, 1))
        subtree:add(f_crc2, buffer(offset + 1, 1))
        
        local received_crc1 = buffer(offset, 1):uint()
        local received_crc2 = buffer(offset + 1, 1):uint()
        
        -- Calculate CRC over the data (excluding start bytes and CRC itself)
        if crc_start_offset then
            local crc_data_len = offset - crc_start_offset
            local crc_data = buffer(crc_start_offset, crc_data_len)
            local calc_crc1, calc_crc2 = fletcher16(crc_data)
            
            if calc_crc1 == received_crc1 and calc_crc2 == received_crc2 then
                subtree:add(f_crc_status, "Valid"):set_generated()
            else
                subtree:add(f_crc_status, string.format("Invalid (expected: 0x%02X 0x%02X)", calc_crc1, calc_crc2)):set_generated()
            end
        end
        
        offset = offset + 2
    end
    
    -- Update info column
    pinfo.cols.info = string.format("%s - Msg ID: %d", display_name, msg_id)
end

-- Register the dissector
-- Register on a custom DLT for PCAP files
-- User DLT 0 = 147 in Wireshark (fixed mapping, see Wireshark documentation)
local wtap_encap_table = DissectorTable.get("wtap_encap")
local USER_DLT = 147  -- User DLT 0
wtap_encap_table:add(USER_DLT, struct_frame_proto)

-- Also register as a heuristic dissector for UDP
function heuristic_checker(buffer, pinfo, tree)
    -- Check if this looks like a struct-frame packet
    if buffer:len() < 2 then
        return false
    end
    
    local first_byte = buffer(0, 1):uint()
    
    -- Check for Basic frame (0x90 followed by 0x70-0x78)
    if first_byte == 0x90 then
        if buffer:len() < 2 then return false end
        local second_byte = buffer(1, 1):uint()
        if second_byte >= 0x70 and second_byte <= 0x78 then
            struct_frame_proto.dissector(buffer, pinfo, tree)
            return true
        end
    end
    
    -- Check for Tiny frame (0x70-0x78)
    if first_byte >= 0x70 and first_byte <= 0x78 then
        struct_frame_proto.dissector(buffer, pinfo, tree)
        return true
    end
    
    return false
end

-- Register heuristic dissector for UDP
struct_frame_proto:register_heuristic("udp", heuristic_checker)

-- Also register for TCP
struct_frame_proto:register_heuristic("tcp", heuristic_checker)

-- Optional: Register on specific UDP/TCP ports
-- Uncomment and modify the port number as needed for your application
-- local udp_port = DissectorTable.get("udp.port")
-- udp_port:add(YOUR_PORT_NUMBER, struct_frame_proto)

print("Struct Frame dissector loaded successfully")
