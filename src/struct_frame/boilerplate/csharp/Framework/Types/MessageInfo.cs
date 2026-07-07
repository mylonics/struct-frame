#nullable enable

namespace StructFrame
{
    /// <summary>
    /// Message info structure - unified type for size and magic numbers lookup.
    /// </summary>
    public readonly struct MessageInfo
    {
        public int Size { get; }
        public byte Magic1 { get; }
        public byte Magic2 { get; }
        public int BaseSize { get; }  // Non-extension portion size (== Size when no extensions)
        public int MinSize { get; }   // Minimum valid payload size: BaseSize for fixed messages,
                                      // MinSize for variable messages

        public MessageInfo(int size, byte magic1 = 0, byte magic2 = 0)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
            BaseSize = size;
            MinSize = size;
        }

        public MessageInfo(int size, byte magic1, byte magic2, int baseSize)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
            BaseSize = baseSize;
            MinSize = baseSize;
        }

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
