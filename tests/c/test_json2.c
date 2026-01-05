#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include "cJSON.h"

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
    
    cJSON* messages = cJSON_GetObjectItem(root, "SerializationTestMessage");
    cJSON* first_msg = cJSON_GetArrayItem(messages, 0);
    cJSON* magic_number = cJSON_GetObjectItem(first_msg, "magic_number");
    
    printf("magic_number valueint: %d\n", magic_number->valueint);
    printf("magic_number valuedouble: %f\n", magic_number->valuedouble);
    printf("cast to uint32_t: %u\n", (uint32_t)magic_number->valuedouble);
    printf("INT_MAX: %d\n", INT_MAX);
    
    cJSON_Delete(root);
    return 0;
}
