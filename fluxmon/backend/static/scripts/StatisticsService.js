// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.service('StatisticsService', function($http){
    return {
        get_ntile: function(x, n, data){
            data = data.sort();
            idx = parseInt( (x / n) * data.length );
            return data[idx];
        }
    }
});
