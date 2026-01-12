/**
 * Test entry point for standard message tests (C#).
 *
 * Usage:
 *   dotnet run -- encode <frame_format> <output_file>
 *   dotnet run -- decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

using System;
using StructFrameTests;

class TestStandard
{
    public static int Main(string[] args)
    {
        return TestCodec.RunTestMain(
            args,
            StandardTestData.Config.SupportsFormat,
            StandardTestData.Config.FORMATS_HELP,
            StandardTestData.Config.TEST_NAME,
            TestCodec.EncodeStandardMessages,
            TestCodec.DecodeStandardMessages
        );
    }
}
