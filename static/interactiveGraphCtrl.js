// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.service('GraphDataService', function($http){
    return {
        get_data: function(check_uuid, variable_name, params){
            return $http.get('/check/' + check_uuid + '/' + variable_name + '.json', {
                params: params
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
        selection: {
            mode: "x"
        }
    };

    $scope.flotCallback = function(plotObj){
        $scope.plot = plotObj;
        console.log("got it!", $scope);
    }

    $scope.$watchGroup(['check_uuid', 'variable_name'], function(){
        if( $scope.check_uuid && $scope.variable_name ){
            var params = {};
            if( $scope.start ) params.start = parseInt($scope.start / 1000, 10);
            if( $scope.end   ) params.end   = parseInt($scope.end   / 1000, 10);
            GraphDataService.get_data($scope.check_uuid, $scope.variable_name, params).then(function(result){
                var i, data = [];
                for( i = 0; i < result.data.length; i++ ){
                    data.push([ new Date(result.data[i][0]).valueOf(), result.data[i][1] ]);
                }
                $scope.chartData = [
                    { 'label': $scope.variable_name, 'data': data }
                ];
                $scope.start = new Date(result.data[0][0]).valueOf();
                $scope.end   = new Date(result.data[i - 1][0]).valueOf()
            });
        }
    });

    $scope.$watchGroup(['start', 'end'], function(){
        $.each($scope.plot.getXAxes(), function(_, axis) {
            var opts = axis.options;
            opts.min = $scope.start;
            opts.max = $scope.end;
        });
        $scope.plot.setupGrid();
        $scope.plot.draw();
        $scope.plot.clearSelection();
    });
});

fluxmon.directive("zoom", function(){
    return {
        restrict: "A",
        scope: false, // Trying to properly isolate this scope would break the <flot> directive
        link: function(scope, element, attr){
            var placeholder = $(element).children("div");
            var zoomIn = function(){
                var intv = scope.end - scope.start;
                scope.start += intv * 0.10;
                scope.end   -= intv * 0.10;
                scope.$apply();
            }
            var zoomOut = function(){
                var intv = scope.end - scope.start;
                scope.start -= intv * 0.10;
                scope.end   += intv * 0.10;
                scope.$apply();
            }
            // Bind hammer for mobile pinch (doubletap) zooming
            var mc = new Hammer.Manager(placeholder[0]);
            var pinch = new Hammer.Pinch();
            mc.add([pinch]);
            mc.on("pinchin", function(ev) {
                zoomOut();
            });
            mc.on("pinchout", function(ev) {
                zoomIn();
            });
            // Bind wheel for standard mouse wheel scrolling
            placeholder.bind("wheel", function(ev){
                if(ev.originalEvent.deltaY < 0){
                    zoomIn();
                }
                else{
                    zoomOut();
                }
            });
            // Bind plot selection events
            placeholder.bind("plotselected", function (event, ranges) {
                scope.start = ranges.xaxis.from;
                scope.end   = ranges.xaxis.to;
                scope.$apply();
            });
        }
    };
});
