/**
 * This extends a JavaScript date object with a basic strftime function.
 * See https://www.man7.org/linux/man-pages/man3/strftime.3.html
 *
 * Implemented formatters:
 *
 *   Y - Full year
 *   y - last two digits of the year
 *   m - month as 01 - 12
 *   d - day of month as 01 - 31
 *   H - Hour as 01 - 24
 *   M - Minute as 01 - 60
 *   S - Second as 01 - 60
 *   F - Date as %Y-%m-%d
 *   R - Time as %H:%M
 *   T - Time as %H:%M:%S
 *   a - Weekday as Mon-Sun in current locale
 *   A - Weekday as Monday-Sunday in current locale
 *   b - Month as Jan-Dec in current locale
 *   B - Month as January-December in current locale
 *   c - Date and time string in current locale
 *   s - seconds since the epoch
 *   % - a literal % sign
 *
 * Example:
 *
 *   > var a = new Date()
 *   undefined
 *   > a.strftime("%Y-%m-%d %H:%M")            // local time
 *   '2024-03-01 21:45'
 *   > a.strftime("%Y-%m-%d %H:%M", true)      // utc
 *   '2024-03-01 20:45'
 *   > a.strftime("%F %T")
 *   '2024-03-01 21:45:26'
 *   > a.strftime("%F %T", true)
 *   '2024-03-01 20:45:26'
 *
 * The zpad function is inspired from here:
 * https://stackoverflow.com/questions/49330139/date-toisostring-but-local-time-instead-of-utc
 */

Date.prototype.strftime = function(fmt, utc) {
    var zpad = n =>  ('0' + n).slice(-2);
    var locale = (process.env["LANG"] || "en_US.UTF-8").split(".")[0].replace("_", "-");
    var replace = false;
    var result  = '';
    var formatters = {
        'Y': date => (utc ? date.getUTCFullYear() : date.getFullYear()),
        'y': date => (utc ? date.getUTCFullYear() : date.getFullYear()).toString().slice(-2),
        'm': date => zpad((utc ? date.getUTCMonth() : date.getMonth()) + 1),
        'd': date => zpad(utc ? date.getUTCDate() : date.getDate()),
        'H': date => zpad(utc ? date.getUTCHours() : date.getHours()),
        'M': date => zpad(utc ? date.getUTCMinutes() : date.getMinutes()),
        'S': date => zpad(utc ? date.getUTCSeconds() : date.getSeconds()),
        'F': date => date.strftime('%Y-%m-%d', utc),
        'R': date => date.strftime('%H:%M', utc),
        'T': date => date.strftime('%H:%M:%S', utc),
        'a': date => date.toLocaleDateString(locale, { weekday: "short" }),
        'A': date => date.toLocaleDateString(locale, { weekday: "long" }),
        'b': date => date.toLocaleDateString(locale, { month: "short" }),
        'B': date => date.toLocaleDateString(locale, { month: "long" }),
        'c': date => date.toLocaleString(locale),
        's': date => parseInt(date.getTime() / 1000).toString(),
        '%': date => '%',
    }
    for (var chr of fmt) {
        if (replace) {
            result += formatters[chr](this);
            replace = false;
        } else if (chr == '%') {
            replace = true;
        } else {
            result += chr;
        }
    }
    return result;
}
