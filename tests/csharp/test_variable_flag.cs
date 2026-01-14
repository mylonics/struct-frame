/**
 * Test entry point for variable flag truncation tests (C#).
 *
 * This test validates that messages with option variable = true properly
 * truncate unused array space, while non-variable messages do not.
 *
 * Usage:
 *   dotnet run -- encode <frame_format> <output_file>
 *   dotnet run -- decode <frame_format> <input_file>
 *
 * Frame formats: profile_bulk (only profile that supports extended features)
 */

using System;
using StructFrameTests;

class TestVariableFlag
{
    public static int Main(string[] args)
    {
        return TestCodec.RunTestMain(
            args,
            VariableFlagTestData.Config.SupportsFormat,
            VariableFlagTestData.Config.FORMATS_HELP,
            VariableFlagTestData.Config.TEST_NAME,
            TestCodec.EncodeVariableFlagMessages,
            TestCodec.DecodeVariableFlagMessages
        );
    }
}
