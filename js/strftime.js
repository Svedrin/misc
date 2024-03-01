/**
 * This extends a JavaScript date object with a basic strftime function.
 *
 * The zpad function is inspired from here:
 * https://stackoverflow.com/questions/49330139/date-toisostring-but-local-time-instead-of-utc
 */

Date.prototype.strftime = function(fmt, utc) {
    var zpad = n =>  ('0' + n).slice(-2);
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
                case '%':
                    result += '%';
                    break;
            }
            replace = false;
        }
    }
    return result;
}
