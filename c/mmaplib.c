#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>

typedef struct {
    int    valid;
    FILE*  file;
    void*  addr;
    size_t size;
} mmap_t;

mmap_t mmap_open(const char* filepath, const char* mode, size_t extra_space){
    mmap_t mmapped;
    mmapped.valid = 0;

    FILE* filep = fopen(filepath, mode);
    struct stat filestat;
    if( fstat(fileno(filep), &filestat) == -1 ){
        fclose(filep);
        return mmapped;
    }


    int mmapprot = 0;
    if( strcmp(mode, "r") == 0 ){
        mmapprot = PROT_READ;
        mmapped.size = filestat.st_size;
    }
    else if( strcmp(mode, "w+") == 0 ){
        mmapprot = PROT_READ | PROT_WRITE;
        mmapped.size = extra_space;
        fallocate(fileno(filep), 0, 0, mmapped.size);
    }
    else{
        fprintf(stderr, "Invalid mode '%s' (use either r or w+)\n", mode);
        fclose(filep);
        return mmapped;
    }

    void* addr = mmap(
        0,
        mmapped.size,
        mmapprot,
        MAP_SHARED,
        fileno(filep),
        0
    );


    if( addr == MAP_FAILED ){
        fclose(filep);
        return mmapped;
    }

    mmapped.file = filep;
    mmapped.addr = addr;
    mmapped.valid = 1;

    return mmapped;
}

void mmap_close(mmap_t mapped){
    if( mapped.valid == 1 ){
        munmap(mapped.addr, mapped.size);
        fclose(mapped.file);
    }
}

