using System;

namespace StructFrame
{
    /// <summary>
    /// A bounded array type for variable-length arrays in structs.
    /// This is used for arrays with a count field followed by data.
    /// </summary>
    public struct BoundedArray<T> where T : unmanaged
    {
        public int Count { get; set; }
        public T[] Data { get; set; }

        public BoundedArray(int capacity)
        {
            Count = 0;
            Data = new T[capacity];
        }

        public BoundedArray(T[]? data)
        {
            Count = data?.Length ?? 0;
            Data = data ?? Array.Empty<T>();
        }

        public T this[int index]
        {
            get => Data[index];
            set => Data[index] = value;
        }

        public void Add(T item)
        {
            if (Data == null)
                Data = new T[16]; // Default capacity
            if (Count >= Data.Length)
            {
                var data = Data;
                Array.Resize(ref data, data.Length * 2);
                Data = data;
            }
            Data[Count++] = item;
        }

        public Span<T> AsSpan() => new Span<T>(Data, 0, Count);
        public ReadOnlySpan<T> AsReadOnlySpan() => new ReadOnlySpan<T>(Data, 0, Count);
    }
}
