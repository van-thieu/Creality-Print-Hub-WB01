/* LD_PRELOAD shim: feed H.264 Annex-B data into uvc_stream's frame buffer.
   Self-contained memcpy (no dlsym) so it works with this uClibc build. */
typedef unsigned int u32;

extern int open(const char *path, int flags);
extern int read(int fd, void *buf, u32 count);
extern int close(int fd);
extern int lseek(int fd, int offset, int whence);

#define GLOBAL_BUF_PTR ((void **)0x008f6158)
#define FEED_PATH "/tmp/h264feed"
#define BLOCK 36000

static int feed_fd = -1;
static int ring_initialized = 0;

typedef int (*init_fn)(void);
#define RTSPSRV_INIT ((init_fn)0x0043435c)

void *memcpy(void *dest, const void *src, u32 n) {
    void *framebuf = *GLOBAL_BUF_PTR;
    if (framebuf && dest == (char *)framebuf + 0x10 && n > 0) {
        if (!ring_initialized) {
            ring_initialized = 1;
            RTSPSRV_INIT();   /* Rbuffer_init + rtsp_startService */
        }
        if (feed_fd < 0)
            feed_fd = open(FEED_PATH, 0);
        if (feed_fd >= 0) {
            u32 got = 0;
            while (got < BLOCK) {
                int r = read(feed_fd, (char *)dest + got, BLOCK - got);
                if (r <= 0) {
                    lseek(feed_fd, 0, 0);
                    if (got == 0) return dest;
                    got = 0;
                } else {
                    got += (u32)r;
                }
            }
            /* pad to the caller's requested size with zeros after the AU */
            while (got < n) { ((char *)dest)[got++] = 0; }
            return dest;
        }
    }
    {
        char *d = (char *)dest;
        const char *s = (const char *)src;
        u32 i;
        for (i = 0; i < n; i++) d[i] = s[i];
    }
    return dest;
}
