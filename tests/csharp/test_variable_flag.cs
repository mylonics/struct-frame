/**
 * Test entry point for variable flag tests (C#).
 */

using System;
using StructFrame.SerializationTest;
using StructFrameTests;

class TestVariableFlag
{
    private const string TEST_NAME = "VariableFlagMessages";
    private const string PROFILES = "bulk";

    public static int Main(string[] args)
    {
        return TestHarness.Run(
            args,
            VariableFlagMessages.MESSAGE_COUNT,
            VariableFlagMessages.GetMessage,
            VariableFlagMessages.CheckMessage,
            (msgId) => MessageDefinitions.GetMessageInfo(msgId),
            TEST_NAME,
            PROFILES
        );
    }
}
