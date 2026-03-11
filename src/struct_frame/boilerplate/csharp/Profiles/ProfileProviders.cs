#nullable enable

using System;
using StructFrame;
using StructFrame.Framing;

namespace StructFrame.Profiles
{
    // ============================================================================
    // Profile Providers - Compile-time profile selection using generics
    // ============================================================================

    /// <summary>
    /// Interface for profile providers - enables compile-time profile selection.
    /// </summary>
    public interface IProfileProvider
    {
        static abstract ProfileConfig Profile { get; }
    }

    public struct StandardProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Standard;
    }

    public struct SensorProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Sensor;
    }

    public struct IPCProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.IPC;
    }

    public struct BulkProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Bulk;
    }

    public struct NetworkProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Network;
    }

    // ============================================================================
    // Type Aliases for Backwards Compatibility
    // ============================================================================

    // FrameEncoder aliases
    public class ProfileStandardEncoder : FrameEncoder<StandardProfile> { }
    public class ProfileSensorEncoder : FrameEncoder<SensorProfile> { }
    public class ProfileIPCEncoder : FrameEncoder<IPCProfile> { }
    public class ProfileBulkEncoder : FrameEncoder<BulkProfile> { }
    public class ProfileNetworkEncoder : FrameEncoder<NetworkProfile> { }

    // BufferParser aliases
    public class ProfileStandardParser : BufferParser<StandardProfile> { public ProfileStandardParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileSensorParser : BufferParser<SensorProfile> { public ProfileSensorParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileIPCParser : BufferParser<IPCProfile> { public ProfileIPCParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileBulkParser : BufferParser<BulkProfile> { public ProfileBulkParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileNetworkParser : BufferParser<NetworkProfile> { public ProfileNetworkParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }

    // BufferReader aliases
    public class ProfileStandardReader : BufferReader<StandardProfile> { public ProfileStandardReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileSensorReader : BufferReader<SensorProfile> { public ProfileSensorReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileIPCReader : BufferReader<IPCProfile> { public ProfileIPCReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileBulkReader : BufferReader<BulkProfile> { public ProfileBulkReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileNetworkReader : BufferReader<NetworkProfile> { public ProfileNetworkReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }

    // BufferWriter aliases
    public class ProfileStandardWriter : BufferWriter<StandardProfile> { }
    public class ProfileSensorWriter : BufferWriter<SensorProfile> { }
    public class ProfileIPCWriter : BufferWriter<IPCProfile> { }
    public class ProfileBulkWriter : BufferWriter<BulkProfile> { }
    public class ProfileNetworkWriter : BufferWriter<NetworkProfile> { }

    // AccumulatingReader aliases
    public class ProfileStandardAccumulatingReader : AccumulatingReader<StandardProfile> { public ProfileStandardAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileSensorAccumulatingReader : AccumulatingReader<SensorProfile> { public ProfileSensorAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileIPCAccumulatingReader : AccumulatingReader<IPCProfile> { public ProfileIPCAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileBulkAccumulatingReader : AccumulatingReader<BulkProfile> { public ProfileBulkAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileNetworkAccumulatingReader : AccumulatingReader<NetworkProfile> { public ProfileNetworkAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
}
