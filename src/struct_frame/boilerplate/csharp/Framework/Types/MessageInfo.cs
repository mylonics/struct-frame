#nullable enable

namespace StructFrame
{
    /// <summary>
    /// Message info structure - unified type for size and magic numbers lookup.
    /// </summary>
    public readonly struct MessageInfo
    {
        /// <summary>Maximum payload size in bytes.</summary>
        public int Size { get; }
        /// <summary>First checksum magic byte.</summary>
        public byte Magic1 { get; }
        /// <summary>Second checksum magic byte.</summary>
        public byte Magic2 { get; }
        /// <summary>Size of the non-extension fields.</summary>
        public int BaseSize { get; }  // Non-extension portion size (== Size when no extensions)
        /// <summary>Minimum valid payload size.</summary>
        public int MinSize { get; }   // Minimum valid payload size: BaseSize for fixed messages,
                                      // MinSize for variable messages

        /// <summary>Creates fixed-size message information.</summary>
        public MessageInfo(int size, byte magic1 = 0, byte magic2 = 0)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
            BaseSize = size;
            MinSize = size;
        }

        /// <summary>Creates message information with an extension-aware base size.</summary>
        public MessageInfo(int size, byte magic1, byte magic2, int baseSize)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
            BaseSize = baseSize;
            MinSize = baseSize;
        }

        /// <summary>Creates message information with base and minimum sizes.</summary>
        public MessageInfo(int size, byte magic1, byte magic2, int baseSize, int minSize)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
            BaseSize = baseSize;
            MinSize = minSize;
        }
    }
}
