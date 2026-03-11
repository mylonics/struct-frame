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

        public MessageInfo(int size, byte magic1 = 0, byte magic2 = 0)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
        }
    }
}
