#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int32_t bkit_int;

static const int FLOAT_PRECISION = 2;
// +-d.[FLOAT_PRECISION]de+-dd
static const int STR_FLOAT_RANGE = 8 + FLOAT_PRECISION;
// ceil(log10(2 ^ 32)) + 1
static const int STR_INT_RANGE = 11;
static const char *TRUE = "True";
static const char *FALSE = "False";

void printStrLn(const char *str) { puts(str); }

void printLn() { putchar('\n'); }

void print(const char *str) { fputs(str, stdout); }

bkit_int int_of_float(float val) { return val; }

float float_of_int(bkit_int val) { return val; }

bkit_int int_of_string(const char *str) { return strtol(str, NULL, 10); }

float float_of_string(const char *str) { return strtof(str, NULL); }

bool bool_of_string(const char *str) { return strncmp(str, TRUE, 4) == 0; }

const char *string_of_bool(bool val) { return val ? TRUE : FALSE; }

const char *string_of_int(bkit_int val) {
  char *str = malloc(STR_INT_RANGE);
  sprintf(str, "%d", val);
  return str;
}

const char *string_of_float(float val) {
  char *str = malloc(STR_FLOAT_RANGE);
  sprintf(str, "%.2e", val);
  return str;
}

bool *alloc_BoolType_array(bkit_int size) {
  return malloc(sizeof(bool) * size);
}

bkit_int *alloc_IntType_array(bkit_int size) {
  return malloc(sizeof(bkit_int) * size);
}

float *alloc_FloatType_array(bkit_int size) {
  return malloc(sizeof(float) * size);
}

const char **alloc_StringType_array(bkit_int size) {
  return malloc(sizeof(void *));
}
