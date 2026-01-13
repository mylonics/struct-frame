/**
 * Test entry point for basic message tests (C#).
 *
 * Usage:
 *   dotnet run -- encode <frame_format> <output_file>
 *   dotnet run -- decode <frame_format> <input_file>
 *
 * Frame formats: profile_basic, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

using System;
using StructFrameTests;

class TestBasic
{
    public static int Main(string[] args)
    {
        return TestCodec.RunTestMain(
            args,
            BasicTestData.Config.SupportsFormat,
            BasicTestData.Config.FORMATS_HELP,
            BasicTestData.Config.TEST_NAME,
            TestCodec.EncodeBasicMessages,
            TestCodec.DecodeBasicMessages
        );
    }
}
