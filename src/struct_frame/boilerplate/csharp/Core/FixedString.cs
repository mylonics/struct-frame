using System;

namespace StructFrame
{
    /// <summary>
    /// A fixed-size string buffer stored as bytes.
    /// </summary>
    public struct FixedString
    {
        public byte Length { get; set; }
        public byte[] Data { get; set; }

        public FixedString()
        {
            Length = 0;
            Data = Array.Empty<byte>();
        }

        public FixedString(int maxLength)
        {
            Length = 0;
            Data = new byte[maxLength];
        }

        public FixedString(string value, int maxLength)
        {
            Data = new byte[maxLength];
            if (string.IsNullOrEmpty(value))
            {
                Length = 0;
            }
            else
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(value);
                Length = (byte)Math.Min(bytes.Length, maxLength);
                Array.Copy(bytes, Data, Length);
            }
        }

        public override readonly string ToString()
        {
            if (Data == null || Length == 0)
                return string.Empty;
            return System.Text.Encoding.UTF8.GetString(Data, 0, Length);
        }

        public static implicit operator string(FixedString fs) => fs.ToString();
    }
}
