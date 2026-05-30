namespace StructFrame
{
    /// <summary>
    /// Diagnostic counters for AccumulatingReader (stream mode).
    ///
    /// All counters accumulate over the reader's lifetime.
    /// Call <see cref="Framing.AccumulatingReader.ResetDiagnostics"/> to clear them.
    /// </summary>
    public struct ParserDiagnostics
    {
        /// <summary>
        /// Number of complete frames received with a bad CRC.
        /// Indicates noise or corruption on the line.
        /// </summary>
        public int CntCrcFailures;

        /// <summary>
        /// Number of times the parser discarded bytes and re-searched for a frame start.
        /// Indicates lost bytes or buffer overflows.
        /// </summary>
        public int CntSyncRecoveries;

        /// <summary>
        /// Number of frames where the header length field does not match the expected
        /// message-struct size from the message-info callback.
        /// Vital for detecting mismatched definitions on profiles that carry an explicit length.
        /// </summary>
        public int CntLenErrors;

        /// <summary>
        /// Number of sequence-number gaps detected.
        /// Only incremented on profiles that carry a sequence field (e.g. ProfileNetwork).
        /// Indicates dropped packets.
        /// </summary>
        public int CntSeqGaps;
    }
}
