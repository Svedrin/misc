fluxmon.filter('i18ndate', function($filter){
    return function(input, format_type){
        // Translate the Django datetime format extensions into stuff that AngularJS actually understands.
        var fmt = get_format(format_type || 'SHORT_DATETIME_FORMAT'),
            res = "",
            esc = false;
        for( var i = 0; i < fmt.length; i++ ){
            if(esc){
                res += fmt[i];
                esc = false;
            }
            else if(fmt[i] === '\\'){
                esc = true;
            }
            else{
                res += ({
                    A: 'a',
                    b: 'MMM',
                    B: '', // "Not implemented" dfq
                    c: 'yyyy-MM-ddTHH:mm:ss.sssZ',
                    d: 'dd',
                    D: 'EEE',
                    e: '', // Timezone name
                    E: 'MMMM',
                    f: 'h:mm',
                    F: 'MMMM',
                    g: 'h',
                    G: 'H',
                    h: 'hh',
                    H: 'HH',
                    i: 'mm',
                    I: '', // Daylight Savings
                    j: 'd',
                    l: 'EEEE',
                    L: '', // leap year
                    m: 'MM',
                    M: 'MMM',
                    n: 'm',
                    N: 'MMM',
                    o: 'yyyy',
                    O: 'Z',
                    P: 'h:mm a',
                    r: 'EEE, dd MMM yyyy HH:mm:ss Z',
                    s: 'ss',
                    S: '', // 1st, 2nd, 3rd
                    t: '', // days in the month
                    T: '', // time zone
                    u: '', // Microseconds
                    U: '', // epoch
                    w: '', // day in week
                    W: 'w',
                    y: 'yy',
                    Y: 'yyyy',
                    z: '', // day of year
                    Z: ''  // time zone offset in seconds
                }[fmt[i]] || fmt[i]);
            }
        }
        return $filter('date')(input, res);
    };
});
