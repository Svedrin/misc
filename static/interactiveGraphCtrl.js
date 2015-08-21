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

    $scope.zoomIn = function(){
        alert("in");
    }

    $scope.zoomOut = function(){
        alert("out");
    }

    $scope.$watchGroup(['check_uuid', 'variable_name'], function(){
        if( $scope.check_uuid && $scope.variable_name ){
            GraphDataService.get_data($scope.check_uuid, $scope.variable_name).then(function(result){
                var data = [];
                for( var i = 0; i < result.data.length; i++ ){
                    data.push([ new Date(result.data[i][0]).valueOf(), result.data[i][1] ]);
                }
                $scope.chartData = [
                    { 'label': $scope.variable_name, 'data': data }
                ];
            });
        }
    });
});

fluxmon.directive("zoom", function(){
    return {
        restrict: "A",
        scope: false, // Trying to properly isolate this scope would break the <flot> directive
        link: function(scope, element, attr){
            var mc = new Hammer.Manager($(element).children("div")[0]);
            var pinch = new Hammer.Pinch();
            mc.add([pinch]);
            mc.on("pinchin", function(ev) {
                scope.zoomIn({});
            });
            mc.on("pinchout", function(ev) {
                scope.zoomOut({});
            });
            $(element).children("div").bind("wheel", function(ev){
                if(ev.originalEvent.deltaY < 0){
                    scope.zoomIn({});
                }
                else{
                    scope.zoomOut({});
                }
            });
        }
    };
});
