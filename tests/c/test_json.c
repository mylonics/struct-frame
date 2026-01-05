#include <stdio.h>
#include <stdlib.h>
#include "cJSON.h"

int main() {
    FILE* file = fopen("../test_messages.json", "r");
    if (!file) {
        printf("Failed to open file\n");
        return 1;
    }
    
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    char* json_str = (char*)malloc(file_size + 1);
    size_t read_size = fread(json_str, 1, file_size, file);
    json_str[read_size] = '\0';
    fclose(file);
    
    printf("Read %zu bytes\n", read_size);
    printf("First 100 chars: %.100s\n", json_str);
    
    cJSON* root = cJSON_Parse(json_str);
    free(json_str);
    
    if (!root) {
        printf("Failed to parse JSON: %s\n", cJSON_GetErrorPtr());
        return 1;
    }
    
    printf("Parsed JSON successfully\n");
    
    cJSON* messages = cJSON_GetObjectItem(root, "SerializationTestMessage");
    if (!messages) {
        printf("No SerializationTestMessage key\n");
        messages = cJSON_GetObjectItem(root, "messages");
    }
    
    if (messages && cJSON_IsArray(messages)) {
        int count = cJSON_GetArraySize(messages);
        printf("Found %d messages\n", count);
    } else {
        printf("messages is not an array\n");
    }
    
    cJSON_Delete(root);
    return 0;
}
