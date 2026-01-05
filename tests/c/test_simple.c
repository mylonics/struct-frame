#include <stdio.h>
#include <stdlib.h>
#include "test_codec.h"

int main() {
    test_message_t messages[10];
    printf("Loading test messages...\n");
    size_t count = load_test_messages(messages, 10);
    printf("Loaded %zu messages\n", count);
    
    if (count > 0) {
        printf("First message: magic=%u, string='%s'\n", 
               messages[0].magic_number, messages[0].test_string);
    }
    
    return 0;
}
