/* Modified copy of timemodule.c from Python 2.7
 * https://github.com/python/cpython/blob/2.7/Modules/timemodule.c
 */

/* Subset of the Time module */

#ifdef __APPLE__
#if defined(HAVE_GETTIMEOFDAY) && defined(HAVE_FTIME)
  /*
   * floattime falls back to ftime when getttimeofday fails because the latter
   * might fail on some platforms. This fallback is unwanted on MacOSX because
   * that makes it impossible to use a binary build on OSX 10.4 on earlier
   * releases of the OS. Therefore claim we don't support ftime.
   */
# undef HAVE_FTIME
#endif
#endif

#include <ctype.h>

#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif /* HAVE_SYS_TYPES_H */

#ifdef QUICKWIN
#include <io.h>
#endif

#ifdef HAVE_FTIME
#include <sys/timeb.h>
#if !defined(MS_WINDOWS) && !defined(PYOS_OS2)
extern int ftime(struct timeb *);
#endif /* MS_WINDOWS */
#endif /* HAVE_FTIME */

#if defined(__WATCOMC__) && !defined(__QNX__)
#include <i86.h>
#else
#ifdef MS_WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "pythread.h"

/* helper to allow us to interrupt sleep() on Windows*/
static HANDLE hInterruptEvent = NULL;
static BOOL WINAPI PyCtrlHandler(DWORD dwCtrlType)
{
    SetEvent(hInterruptEvent);
    /* allow other default handlers to be called.
       Default Python handler will setup the
       KeyboardInterrupt exception.
    */
    return FALSE;
}
static long main_thread;


#if defined(__BORLANDC__)
/* These overrides not needed for Win32 */
#define timezone _timezone
#define tzname _tzname
#define daylight _daylight
#endif /* __BORLANDC__ */
#endif /* MS_WINDOWS */
#endif /* !__WATCOMC__ || __QNX__ */

#if defined(MS_WINDOWS) && !defined(__BORLANDC__)
/* Win32 has better clock replacement; we have our own version below. */
#undef HAVE_CLOCK
#endif /* MS_WINDOWS && !defined(__BORLANDC__) */

#if defined(PYOS_OS2)
#define INCL_DOS
#define INCL_ERRORS
#include <os2.h>
#endif

#if defined(PYCC_VACPP)
#include <sys/time.h>
#endif

#ifdef __BEOS__
#include <time.h>
/* For bigtime_t, snooze(). - [cjh] */
#include <support/SupportDefs.h>
#include <kernel/OS.h>
#endif

#ifdef RISCOS
extern int riscos_sleep(double);
#endif


/* Implement floattime() for various platforms */

static double
floattime(void)
{
    /* There are three ways to get the time:
      (1) gettimeofday() -- resolution in microseconds
      (2) ftime() -- resolution in milliseconds
      (3) time() -- resolution in seconds
      In all cases the return value is a float in seconds.
      Since on some systems (e.g. SCO ODT 3.0) gettimeofday() may
      fail, so we fall back on ftime() or time().
      Note: clock resolution does not imply clock accuracy! */
#ifdef HAVE_GETTIMEOFDAY
    {
        struct timeval t;
#ifdef GETTIMEOFDAY_NO_TZ
        if (gettimeofday(&t) == 0)
            return (double)t.tv_sec + t.tv_usec*0.000001;
#else /* !GETTIMEOFDAY_NO_TZ */
        if (gettimeofday(&t, (struct timezone *)NULL) == 0)
            return (double)t.tv_sec + t.tv_usec*0.000001;
#endif /* !GETTIMEOFDAY_NO_TZ */
    }

#endif /* !HAVE_GETTIMEOFDAY */
    {
#if defined(HAVE_FTIME)
        struct timeb t;
        ftime(&t);
        return (double)t.time + (double)t.millitm * (double)0.001;
#else /* !HAVE_FTIME */
        time_t secs;
        time(&secs);
        return (double)secs;
#endif /* !HAVE_FTIME */
    }
}


/* Implement floatsleep() for various platforms.
   When interrupted (or when another error occurs), return -1 and
   set an exception; else return 0. */

static int
floatsleep(double secs)
{
/* XXX Should test for MS_WINDOWS first! */
#if defined(HAVE_SELECT) && !defined(__BEOS__) && !defined(__EMX__)
    struct timeval t;
    double frac;
    frac = fmod(secs, 1.0);
    secs = floor(secs);
    t.tv_sec = (long)secs;
    t.tv_usec = (long)(frac*1000000.0);
    //Py_BEGIN_ALLOW_THREADS
    if (select(0, (fd_set *)0, (fd_set *)0, (fd_set *)0, &t) != 0) {
#ifdef EINTR
        if (errno != EINTR) {
#else
        if (1) {
#endif
            //Py_BLOCK_THREADS
            //PyErr_SetFromErrno(PyExc_IOError);
            return -1;
        }
    }
    //Py_END_ALLOW_THREADS
#elif defined(__WATCOMC__) && !defined(__QNX__)
    /* XXX Can't interrupt this sleep */
    //Py_BEGIN_ALLOW_THREADS
    delay((int)(secs * 1000 + 0.5));  /* delay() uses milliseconds */
    //Py_END_ALLOW_THREADS
#elif defined(MS_WINDOWS)
    {
        double millisecs = secs * 1000.0;
        unsigned long ul_millis;

        if (millisecs > (double)ULONG_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                            "sleep length is too large");
            return -1;
        }
        //Py_BEGIN_ALLOW_THREADS
        /* Allow sleep(0) to maintain win32 semantics, and as decreed
         * by Guido, only the main thread can be interrupted.
         */
        ul_millis = (unsigned long)millisecs;
        if (ul_millis == 0 ||
            main_thread != PyThread_get_thread_ident())
            Sleep(ul_millis);
        else {
            DWORD rc;
            ResetEvent(hInterruptEvent);
            rc = WaitForSingleObject(hInterruptEvent, ul_millis);
            if (rc == WAIT_OBJECT_0) {
                /* Yield to make sure real Python signal
                 * handler called.
                 */
                Sleep(1);
                //Py_BLOCK_THREADS
                errno = EINTR;
                //PyErr_SetFromErrno(PyExc_IOError);
                return -1;
            }
        }
        //Py_END_ALLOW_THREADS
    }
#elif defined(PYOS_OS2)
    /* This Sleep *IS* Interruptable by Exceptions */
    //Py_BEGIN_ALLOW_THREADS
    if (DosSleep(secs * 1000) != NO_ERROR) {
        Py_BLOCK_THREADS
        PyErr_SetFromErrno(PyExc_IOError);
        return -1;
    }
    //Py_END_ALLOW_THREADS
#elif defined(__BEOS__)
    /* This sleep *CAN BE* interrupted. */
    {
        if( secs <= 0.0 ) {
            return;
        }

        //Py_BEGIN_ALLOW_THREADS
        /* BeOS snooze() is in microseconds... */
        if( snooze( (bigtime_t)( secs * 1000.0 * 1000.0 ) ) == B_INTERRUPTED ) {
            //Py_BLOCK_THREADS
            //PyErr_SetFromErrno( PyExc_IOError );
            return -1;
        }
        //Py_END_ALLOW_THREADS
    }
#elif defined(RISCOS)
    if (secs <= 0.0)
        return 0;
    //Py_BEGIN_ALLOW_THREADS
    /* This sleep *CAN BE* interrupted. */
    if ( riscos_sleep(secs) )
        return -1;
    //Py_END_ALLOW_THREADS
#elif defined(PLAN9)
    {
        double millisecs = secs * 1000.0;
        if (millisecs > (double)LONG_MAX) {
            PyErr_SetString(PyExc_OverflowError, "sleep length is too large");
            return -1;
        }
        /* This sleep *CAN BE* interrupted. */
        //Py_BEGIN_ALLOW_THREADS
        if(sleep((long)millisecs) < 0){
            //Py_BLOCK_THREADS
            //PyErr_SetFromErrno(PyExc_IOError);
            return -1;
        }
        //Py_END_ALLOW_THREADS
    }
#else
    /* XXX Can't interrupt this sleep */
    //Py_BEGIN_ALLOW_THREADS
    sleep((int)secs);
    //Py_END_ALLOW_THREADS
#endif

    return 0;
}
