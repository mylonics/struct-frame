/**
 * Test entry point for extended message ID and payload tests (C#).
 *
 * Usage:
 *   dotnet run -- encode <frame_format> <output_file>
 *   dotnet run -- decode <frame_format> <input_file>
 *
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */

using System;
using StructFrameTests;

class TestExtended
{
    public static int Main(string[] args)
    {
        return TestCodec.RunTestMain(
            args,
            ExtendedTestData.Config.SupportsFormat,
            ExtendedTestData.Config.FORMATS_HELP,
            ExtendedTestData.Config.TEST_NAME,
            TestCodec.EncodeExtendedMessages,
            TestCodec.DecodeExtendedMessages
        );
    }
}
