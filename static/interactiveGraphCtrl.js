// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.service('GraphDataService', function($http){
    return {
        get_data: function(check, variable, params){
            return $http.get('/check/' + check + '/' + variable + '.json', {
                params: params
            });
        }
    }
});

fluxmon.directive('interactiveGraph', function($timeout, GraphDataService, isMobile){
    return {
        restrict: 'E',
        template: '<flot dataset="chartData" options="chartOptions" height="300px" callback="flotCallback"></flot>',
        scope: {
            check:    '@',
            variable: '@'
        },
        controller: function($scope){
            var plot, query, maybeRequery, requeryTimer = null;

            $scope.chartData    = [];
            $scope.chartOptions = {
                xaxis: {
                    mode: 'time',
                    timezone: 'browser'
                },
                selection: {
                    mode: 'x'
                }
            };

            $scope.flotCallback = function(plotObj){
                plot = plotObj;
            }

            $scope.$watchGroup(['check', 'variable'], function(){
                if( $scope.check && $scope.variable ){
                    query();
                }
            });

            $scope.$watchGroup(['start', 'end'], function(){
                $.each(plot.getXAxes(), function(_, axis) {
                    var opts = axis.options;
                    opts.min = $scope.start;
                    opts.max = $scope.end;
                });
                plot.setupGrid();
                plot.draw();
                plot.clearSelection();
                maybeRequery();
            });

            query = function(){
                var params = {};
                if( $scope.start ) params.start = parseInt($scope.start / 1000, 10);
                if( $scope.end   ) params.end   = parseInt($scope.end   / 1000, 10);
                GraphDataService.get_data($scope.check, $scope.variable, params).then(function(result){
                    var i, data = [];
                    for( i = 0; i < result.data.length; i++ ){
                        data.push([ new Date(result.data[i][0]).valueOf(), result.data[i][1] ]);
                    }
                    $scope.chartData = [
                        {
                            label:  $scope.variable,
                            data:   data,
                            lines:  { show: true, fill: true }
                        }
                    ];
                    $scope.data_start = new Date(result.data[0][0]).valueOf();
                    $scope.data_end   = new Date(result.data[i - 1][0]).valueOf()
                    if( !$scope.start ) $scope.start = $scope.data_start;
                    if( !$scope.end   ) $scope.end   = $scope.data_end;
                });
            }

            maybeRequery = function(){
                if( requeryTimer ){
                    $timeout.cancel(requeryTimer);
                    requeryTimer = null;
                }
                if( $scope.start < $scope.data_start || $scope.end > $scope.data_end ){
                    requeryTimer = $timeout(query, 100);
                }
            }
        },
        link: function(scope, element, attr){
            var placeholder = $(element).children('flot').children('div');
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
            var mc    = new Hammer.Manager(placeholder[0]);
            var pan   = new Hammer.Pan();
            var pinch = new Hammer.Pinch();
            pan.recognizeWith(pinch);
            mc.add([pan, pinch]);
            mc.on('pinchin', function(ev) {
                zoomOut();
            });
            mc.on('pinchout', function(ev) {
                zoomIn();
            });
            if( isMobile.any() ){
                // Binding these events on a non-mobile client would break the selection
                mc.on('panleft', function(ev) {
                    var intv = scope.end - scope.start;
                    scope.start += intv * 0.04;
                    scope.end   += intv * 0.04;
                    scope.$apply();
                });
                mc.on('panright', function(ev) {
                    var intv = scope.end - scope.start;
                    scope.start -= intv * 0.04;
                    scope.end   -= intv * 0.04;
                    scope.$apply();
                });
            }
            // Bind wheel for standard mouse wheel scrolling
            placeholder.bind('wheel', function(ev){
                if(ev.originalEvent.deltaY < 0){
                    zoomIn();
                }
                else{
                    zoomOut();
                }
            });
            // Bind plot selection events
            placeholder.bind('plotselected', function (event, ranges) {
                scope.start = ranges.xaxis.from;
                scope.end   = ranges.xaxis.to;
                scope.$apply();
            });
        }
    };
});
