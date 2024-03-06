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
    for (var chr of fmt) {
        if (!replace) {
            if (chr == '%') {
                replace = true;
            } else {
                result += chr;
            }
        } else {
            switch (chr) {
                case 'Y':
                    result += (utc ? this.getUTCFullYear() : this.getFullYear());
                    break;
                case 'y':
                    result += (utc ? this.getUTCFullYear() : this.getFullYear()).toString().slice(-2);
                    break;
                case 'm':
                    result += zpad((utc ? this.getUTCMonth() : this.getMonth()) + 1);
                    break;
                case 'd':
                    result += zpad(utc ? this.getUTCDate() : this.getDate());
                    break;
                case 'H':
                    result += zpad(utc ? this.getUTCHours() : this.getHours());
                    break;
                case 'M':
                    result += zpad(utc ? this.getUTCMinutes() : this.getMinutes());
                    break;
                case 'S':
                    result += zpad(utc ? this.getUTCSeconds() : this.getSeconds());
                    break;
                case 'F':
                    result += this.strftime('%Y-%m-%d', utc);
                    break;
                case 'R':
                    result += this.strftime('%H:%M', utc);
                    break;
                case 'T':
                    result += this.strftime('%H:%M:%S', utc);
                    break;
                case 'a':
                    result += this.toLocaleDateString(locale, { weekday: "short" });
                    break;
                case 'A':
                    result += this.toLocaleDateString(locale, { weekday: "long" });
                    break;
                case 'b':
                    result += this.toLocaleDateString(locale, { month: "short" });
                    break;
                case 'B':
                    result += this.toLocaleDateString(locale, { month: "long" });
                    break;
                case 'c':
                    result += this.toLocaleString(locale);
                    break;
                case 's':
                    result += parseInt(a.getTime() / 1000).toString();
                    break;
                case '%':
                    result += '%';
                    break;
            }
            replace = false;
        }
    }
    return result;
}
