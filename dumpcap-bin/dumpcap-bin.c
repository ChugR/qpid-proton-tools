#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define ARRAY_NAME rewrite_bytes
#include "data.c"

// Return the big-endian int32 pointed to by *pptr.
int get_long(char *buf, int offset)
{
    unsigned char *ptr = (unsigned char *)buf;
    int res = 0;
    int v;
    v = *(ptr + offset + 0);
    res += (v & 0xFF) << 24;
    v = *(ptr + offset + 1);
    res += (v & 0xFF) << 16;
    v = *(ptr + offset + 2);
    res += (v & 0xFF) << 8;
    v = *(ptr + offset + 3);
    res += (v & 0xFF) << 0;
    return res;
}

void dump_bytes(char *ptr, int n_bytes)
{
    for (; n_bytes > 0; n_bytes--, ptr++) {
        printf("%02x", *ptr);
    }
}

void print_bytes(char *ptr, int n_bytes)
{
    for (; n_bytes > 0; n_bytes--, ptr++) {
        char c = *ptr;
        if (isprint(c)) {
            printf ("%c", c);
        } else {
            printf("0x%02x", c);
        }
    }
}

// define this if the file all transfers and the sequence numbers
// should be consecutive
//#define CHECK_SEQ 1

// define this to write to files
//#define WRITE_FILES 1

// define this to print all-hex characters
//#define DUMP_BYTES 1

// define this to print printable characters
//#define PRINT_BYTES 1

int main(int argc, char** argv)
{
    size_t n_bytes = sizeof(ARRAY_NAME);
    //printf("Array ARRAY_NAME is %d bytes\n", n_bytes);

#ifdef WRITE_FILES
    // write all file
    char fname[100];
    sprintf(fname, "raw-files/all.dat");
    FILE * fptr;
    fptr = fopen(fname, "wb");
    if (!fptr) {
        printf("Can't open file\n");
        return 1;
    }
    fwrite(ARRAY_NAME, n_bytes, 1, fptr);
    fclose(fptr);
#endif
    
    int expected_seq = 0;
    char * ptr = ARRAY_NAME;
    char * pend = ptr + n_bytes;
    int offset = 0;
    while (ptr < pend) {
        int transfer_size = get_long(ARRAY_NAME, offset);
#ifdef CHECK_SEQ
        int seq_no = get_long(ARRAY_NAME, offset + 23);
        if (expected_seq == 0) {
            expected_seq = seq_no + 1;
        } else {
            if (expected_seq != seq_no) {
                printf ("seq_no error expected %08d but got %08d\n", expected_seq, seq_no);
                return 1;
            }
            expected_seq = seq_no + 1;
        }
        printf("Transfer seq %08d starts at %d, size=%d, offset=%d\n", seq_no, ptr, transfer_size, offset);
#else
        printf("Performative starts at %d, size=%d, offset=%d\n", ptr, transfer_size, offset);
#endif

#ifdef DUMP_BYTES        
        dump_bytes(ptr, transfer_size);
        printf("\n");
#endif
        
#ifdef PRINT_BYTES
        print_bytes(ptr, transfer_size);
        printf("\n");
#endif

#ifdef WRITE_FILES    
        // write a file
        char fname[100];
        sprintf(fname, "raw-files/d_%08x.dat", seq_no);
        FILE * fptr;
        fptr = fopen(fname, "wb");
        if (!fptr) {
            printf("Can't open file\n");
            return 1;
        }
        fwrite(ptr, transfer_size, 1, fptr);
        fclose(fptr);
#endif

        ptr += transfer_size;
        offset += transfer_size;
    }
    return 0;
}
