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

fluxmon.directive('interactiveGraph', function($timeout, GraphDataService, isMobile, StatisticsService){
    return {
        restrict: 'E',
        template: '<flot dataset="chartData" options="chartOptions" height="300px" callback="flotCallback"></flot>',
        scope: {
            check:    '@',
            variable: '@',
            variableDisplay: '@',
            variableUnit: '@',
            graphState: '='
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
                },
                grid: {
                    hoverable: true
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
                    $scope.data_start = new Date(result.data[0][0]).valueOf();
                    $scope.data_end   = new Date(result.data[i - 1][0]).valueOf()
                    if( !$scope.start ) $scope.start = $scope.data_start;
                    if( !$scope.end   ) $scope.end   = $scope.data_end;

                    var i = 0, min = null, max = null, avg = null, last, visibleData = [];
                    for( i = 0; i < data.length; i++ ){
                        if( data[i][0] < $scope.start ||
                            data[i][0] > $scope.end   ){
                            continue;
                        }
                        last = data[i][1],
                        min = (min == null ? last : (last < min ? last : min));
                        max = (max == null ? last : (last > max ? last : max));
                        avg += last;
                        visibleData.push(last);
                    }
                    if(visibleData) avg /= visibleData.length;

                    $scope.graphState = {
                        start: new Date($scope.start),
                        end:   new Date($scope.end),
                        data_start: new Date($scope.data_start),
                        data_end:   new Date($scope.data_end),
                        min: min, max: max, avg: avg, last: last,
                        p95: StatisticsService.get_ntile(95, 100, visibleData),
                        p05: StatisticsService.get_ntile( 5, 100, visibleData)
                    };

                    $scope.chartData = [{
                        label:  $scope.variableDisplay,
                        data:   data,
                        lines:  { show: true, fill: true },
                        color: '#007400',
                        threshold: [{
                            below: $scope.graphState.max + 1,
                            color: '#740000'
                        }, {
                            below: $scope.graphState.p95,
                            color: '#007400'
                        }, {
                            below: $scope.graphState.p05,
                            color: '#747474'
                        }]
                    }];
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
            var zoomIn = function(zoomX, dirIn){
                var intv = scope.end - scope.start;
                dirIn = dirIn || 1;
                scope.start += dirIn * intv * 0.20 * zoomX;
                scope.end   -= dirIn * intv * 0.20 * (1 - zoomX);
                scope.$apply();
            }
            var zoomOut = function(zoomX){
                return zoomIn(zoomX, -1);
            }
            // Bind hammer for mobile pinch zooming
            var mc    = new Hammer.Manager(placeholder[0]);
            var pan   = new Hammer.Pan();
            var pinch = new Hammer.Pinch();
            pan.recognizeWith(pinch);
            mc.add([pan, pinch]);
            mc.on('pinchin', function(ev) {
                zoomOut(0.5);
            });
            mc.on('pinchout', function(ev) {
                var target = $(ev.target),
                    zoomX  = (ev.center.x - target.offset().left) / target.width();
                zoomIn(zoomX);
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
                var target = $(ev.target),
                    zoomX  = (ev.originalEvent.pageX - target.offset().left) / target.width();
                if(ev.originalEvent.deltaY < 0){
                    zoomIn(zoomX);
                }
                else{
                    zoomOut(0.5);
                }
            });
            // Bind plot selection events
            placeholder.bind('plotselected', function (event, ranges) {
                scope.start = ranges.xaxis.from;
                scope.end   = ranges.xaxis.to;
                scope.$apply();
            });
            placeholder.bind("plothover",  function (event, pos, item) {
                scope.graphState = scope.graphState || {};
                scope.graphState.hover = {pos: pos, item: item};
                scope.$apply();
            });
            placeholder.bind("mouseout", function(event){
                scope.graphState = scope.graphState || {};
                scope.graphState.hover = {pos: null, item: null};
                scope.$apply();
            });
        }
    };
});
