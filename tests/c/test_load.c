#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <limits.h>
#include <string.h>
#include "cJSON.h"

#define MAX_STRING_LENGTH 100
#define MAX_ARRAY_LENGTH 20

typedef struct {
  uint32_t magic_number;
  char test_string[MAX_STRING_LENGTH];
  float test_float;
  bool test_bool;
  int32_t test_array[MAX_ARRAY_LENGTH];
  size_t test_array_count;
} test_message_t;

int main() {
    FILE* file = fopen("../test_messages.json", "r");
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    char* json_str = (char*)malloc(file_size + 1);
    size_t read_size = fread(json_str, 1, file_size, file);
    json_str[read_size] = '\0';
    fclose(file);
    
    cJSON* root = cJSON_Parse(json_str);
    free(json_str);
    
    cJSON* message_array = cJSON_GetObjectItem(root, "SerializationTestMessage");
    
    size_t count = 0;
    test_message_t messages[10];
    cJSON* msg_item = NULL;
    cJSON_ArrayForEach(msg_item, message_array) {
        printf("Processing message %zu\n", count);
        
        cJSON* magic_number = cJSON_GetObjectItem(msg_item, "magic_number");
        cJSON* test_string = cJSON_GetObjectItem(msg_item, "test_string");
        cJSON* test_float = cJSON_GetObjectItem(msg_item, "test_float");
        cJSON* test_bool = cJSON_GetObjectItem(msg_item, "test_bool");
        
        printf("  magic_number: %p\n", magic_number);
        printf("  test_string: %p\n", test_string);
        printf("  test_float: %p\n", test_float);
        printf("  test_bool: %p\n", test_bool);
        
        if (magic_number && test_string && test_float && test_bool) {
            messages[count].magic_number = (uint32_t)magic_number->valuedouble;
            strncpy(messages[count].test_string, cJSON_GetStringValue(test_string), MAX_STRING_LENGTH - 1);
            messages[count].test_string[MAX_STRING_LENGTH - 1] = '\0';
            messages[count].test_float = (float)test_float->valuedouble;
            messages[count].test_bool = cJSON_IsTrue(test_bool);
            
            printf("  Parsed: magic=%u, string='%s'\n", messages[count].magic_number, messages[count].test_string);
            count++;
        } else {
            printf("  Skipping message (missing fields)\n");
        }
    }
    
    printf("Total messages: %zu\n", count);
    
    cJSON_Delete(root);
    return 0;
}
