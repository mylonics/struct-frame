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

}
