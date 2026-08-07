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
        /// <summary>Gets the profile configuration.</summary>
        static abstract ProfileConfig Profile { get; }
    }

    /// <summary>Compile-time provider for the standard profile.</summary>
    public struct StandardProfile : IProfileProvider
    {
        /// <summary>Gets the standard profile.</summary>
        public static ProfileConfig Profile => Profiles.Standard;
    }

    /// <summary>Compile-time provider for the sensor profile.</summary>
    public struct SensorProfile : IProfileProvider
    {
        /// <summary>Gets the sensor profile.</summary>
        public static ProfileConfig Profile => Profiles.Sensor;
    }

    /// <summary>Compile-time provider for the IPC profile.</summary>
    public struct IPCProfile : IProfileProvider
    {
        /// <summary>Gets the IPC profile.</summary>
        public static ProfileConfig Profile => Profiles.IPC;
    }

    /// <summary>Compile-time provider for the bulk profile.</summary>
    public struct BulkProfile : IProfileProvider
    {
        /// <summary>Gets the bulk profile.</summary>
        public static ProfileConfig Profile => Profiles.Bulk;
    }

    /// <summary>Compile-time provider for the network profile.</summary>
    public struct NetworkProfile : IProfileProvider
    {
        /// <summary>Gets the network profile.</summary>
        public static ProfileConfig Profile => Profiles.Network;
    }

}
