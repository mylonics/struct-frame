#nullable enable

using System;
using StructFrame;
using StructFrame.Framing;

namespace StructFrame.Profiles
{
    /// <summary>
    /// Pre-defined profile configurations.
    /// </summary>
    public static class Profiles
    {
        /// <summary>
        /// ProfileStandard: Basic + Default
        /// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Standard = new ProfileConfig(
            "ProfileStandard",
            HeaderConfigs.Basic,
            PayloadConfigs.Default
        );

        /// <summary>
        /// ProfileSensor: Tiny + Minimal
        /// Frame: [0x70] [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly ProfileConfig Sensor = new ProfileConfig(
            "ProfileSensor",
            HeaderConfigs.Tiny,
            PayloadConfigs.Minimal
        );

        /// <summary>
        /// ProfileIPC: None + Minimal
        /// Frame: [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly ProfileConfig IPC = new ProfileConfig(
            "ProfileIPC",
            HeaderConfigs.None,
            PayloadConfigs.Minimal
        );

        /// <summary>
        /// ProfileBulk: Basic + Extended
        /// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Bulk = new ProfileConfig(
            "ProfileBulk",
            HeaderConfigs.Basic,
            PayloadConfigs.Extended
        );

        /// <summary>
        /// ProfileNetwork: Basic + ExtendedMultiSystemStream
        /// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Network = new ProfileConfig(
            "ProfileNetwork",
            HeaderConfigs.Basic,
            PayloadConfigs.ExtendedMultiSystemStream
        );

        /// <summary>
        /// Get a profile by name.
        /// </summary>
        public static ProfileConfig GetByName(string name)
        {
            return name.ToLowerInvariant() switch
            {
                "profile_standard" or "profilestandard" or "standard" => Standard,
                "profile_sensor" or "profilesensor" or "sensor" => Sensor,
                "profile_ipc" or "profileipc" or "ipc" => IPC,
                "profile_bulk" or "profilebulk" or "bulk" => Bulk,
                "profile_network" or "profilenetwork" or "network" => Network,
                _ => throw new ArgumentException($"Unknown profile: {name}")
            };
        }

        /// <summary>
        /// Create a BufferWriter for the specified profile name.
        /// </summary>
        public static BufferWriter CreateWriter(string profileName)
        {
            return new BufferWriter(GetByName(profileName));
        }

        /// <summary>
        /// Create a BufferReader for the specified profile name.
        /// </summary>
        public static BufferReader CreateReader(string profileName, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            return new BufferReader(GetByName(profileName), getMessageInfo);
        }

        /// <summary>
        /// Create a FrameEncoder for the specified profile name.
        /// </summary>
        public static FrameEncoder CreateEncoder(string profileName)
        {
            return new FrameEncoder(GetByName(profileName));
        }

        /// <summary>
        /// Create a BufferParser for the specified profile name.
        /// </summary>
        public static BufferParser CreateParser(string profileName, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            return new BufferParser(GetByName(profileName), getMessageInfo);
        }
    }
}
