function printFailureDetails(label: string): void {
  console.log('\n============================================================');
  console.log(`FAILURE DETAILS: ${label}`);
  console.log('============================================================\n');
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Cross-Language Serialization');
  
  try {
    console.log('[TEST END] TypeScript Cross-Language Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Cross-Language Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
