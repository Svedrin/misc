// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.service('GraphDataService', function($http){
    return {
        get_data: function(check_uuid, variable_name){
            return $http.get('/check/' + check_uuid + '/' + variable_name + '.json', {
                params_should_be: {
                    start: 1234,
                    end:   5678
                }
            });
        }
    }
});

fluxmon.controller("InteractiveGraphCtrl", function($scope, GraphDataService){
    $scope.chartData    = [];
    $scope.chartOptions = {
        xaxis: {
            mode: 'time',
            timezone: 'browser'
        },
    };
    $scope.$watchGroup(['check_uuid', 'variable_name'], function(){
        if( $scope.check_uuid && $scope.variable_name )
            GraphDataService.get_data($scope.check_uuid, $scope.variable_name).then(function(result){
                var data = [];
                for( var i = 0; i < result.data.length; i++ ){
                    data.push([ new Date(result.data[i][0]).valueOf(), result.data[i][1] ]);
                }
                $scope.chartData = [
                    { 'label': $scope.variable_name, 'data': data }
                ];
            });
    });
});
