/**
 * Unified test runner for C# struct-frame tests.
 *
 * Routes to the appropriate test suite based on the executable name or first argument.
 * This allows a single compiled executable to handle both standard and extended tests.
 */

using System;
using System.IO;
using System.Reflection;

class TestRunner
{
    static int Main(string[] args)
    {
        // Determine which test suite to run based on:
        // 1. --runner argument (e.g., "--runner test_extended")
        // 2. Executable name (e.g., "test_standard.exe" or "test_extended.exe")
        // 3. Default to test_standard

        string testSuite = "test_standard";
        string[] filteredArgs = args;

        // Check for --runner argument
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == "--runner")
            {
                testSuite = args[i + 1];
                // Remove --runner and its value from args
                filteredArgs = new string[args.Length - 2];
                Array.Copy(args, 0, filteredArgs, 0, i);
                if (i + 2 < args.Length)
                {
                    Array.Copy(args, i + 2, filteredArgs, i, args.Length - i - 2);
                }
                break;
            }
        }

        // If not specified via --runner, check the executable name
        if (testSuite == "test_standard" && filteredArgs.Length == args.Length)
        {
            string exeName = Path.GetFileNameWithoutExtension(Assembly.GetExecutingAssembly().Location);
            if (exeName.Contains("test_extended") || exeName.Contains("extended"))
            {
                testSuite = "test_extended";
            }
            else if (exeName.Contains("test_negative") || exeName.Contains("negative"))
            {
                testSuite = "test_negative";
            }
            else if (exeName.Contains("pkg_test_messages"))
            {
                testSuite = "test_roundtrip_pkg_test_messages";
            }
        }

        // Route to the appropriate test suite
        if (testSuite == "test_extended")
        {
            return TestExtended.Main(filteredArgs);
        }
        else if (testSuite == "test_variable_flag")
        {
            return TestVariableFlag.Main(filteredArgs);
        }
        else if (testSuite == "test_negative")
        {
            return TestNegative.Main(filteredArgs);
        }
        else if (testSuite == "test_envelope_sdk")
        {
            return TestEnvelopeSdk.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_subscribe")
        {
            return TestSdkSubscribe.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_strict_ordering")
        {
            return TestSdkStrictOrdering.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_lifecycle")
        {
            return TestSdkLifecycle.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_client_wrapper")
        {
            return TestSdkClientWrapper.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_profiles")
        {
            return TestSdkProfiles.Main(filteredArgs);
        }
        else if (testSuite == "test_base_transport")
        {
            return TestBaseTransport.Main(filteredArgs);
        }
        else if (testSuite == "test_sdk_request_response")
        {
            return TestSdkRequestResponse.Main(filteredArgs);
        }
        else if (testSuite == "test_wire_evolution")
        {
            return TestWireEvolution.Main(filteredArgs);
        }
        else if (testSuite == "test_wire_evolution_interop")
        {
            return TestWireEvolutionInterop.Main(filteredArgs);
        }
        else if (testSuite == "test_roundtrip_pkg_test_messages")
        {
            return StructFrame.PkgTestMessages.TestRoundtripPkgTestMessages.Main(filteredArgs);
        }
        else
        {
            return TestStandard.Main(filteredArgs);
        }
    }
}
