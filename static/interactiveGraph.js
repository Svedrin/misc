// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.service('GraphDataService', function($http){
    return {
        get_data: function(params){
            return $http.get('/check.json', {
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
            variables: '@',
            graphState: '='
        },
        controller: function($scope){
            var plot, query, maybeRequery, requeryTimer = null;

            $scope.variables = $.parseJSON($scope.variables);

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
                var vars = $scope.variables;
                if( !vars.map ) vars = $.parseJSON(vars);
                var params = {
                    check: $scope.check,
                    variables: vars.map(function(v){ return v.name })
                };
                if( $scope.start ) params.start = parseInt($scope.start / 1000, 10);
                if( $scope.end   ) params.end   = parseInt($scope.end   / 1000, 10);
                GraphDataService.get_data(params).then(function(response){
                    var result = response.data, i, v, respdata, data;
                    var min, max, avg, last, visibleData;

                    $scope.chartData = [];

                    $scope.data_start = new Date(result.data_window.start).valueOf();
                    $scope.data_end   = new Date(result.data_window.end).valueOf();
                    if( !$scope.start ) $scope.start = $scope.data_start;
                    if( !$scope.end   ) $scope.end   = $scope.data_end;

                    $scope.graphState = {
                        start: new Date($scope.start),
                        end:   new Date($scope.end),
                        data_start: new Date($scope.data_start),
                        data_end:   new Date($scope.data_end),
                        stats: []
                    };

                    for( v = 0; v < vars.length; v++ ){
                        respdata = result.metrics[vars[v].name].data;
                        min = null;
                        max = null;
                        avg = null;
                        visibleData = [];
                        data = [];

                        for( i = 0; i < respdata.length; i++ ){
                            // if( respdata[i][0] < $scope.start ||
                            //     respdata[i][0] > $scope.end   ){
                            //     continue;
                            // }
                            data.push([ new Date(respdata[i][0]).valueOf(), respdata[i][1] ]);
                            last = respdata[i][1];
                            min = (min == null ? last : (last < min ? last : min));
                            max = (max == null ? last : (last > max ? last : max));
                            avg += last;
                            visibleData.push(last);
                        }
                        if(visibleData) avg /= visibleData.length;

                        $scope.graphState.stats.push({
                            variable: vars[v],
                            min: min, max: max, avg: avg, last: last,
                            p95: StatisticsService.get_ntile(95, 100, visibleData),
                            p05: StatisticsService.get_ntile( 5, 100, visibleData)
                        });

                        $scope.chartData.push({
                            label:  vars[v].display,
                            data:   data,
                            lines:  { show: true, fill: false},
                            //color: '#007400',
                        });
                        if( false && min != max ){
                            $scope.chartData[0].threshold = [{
                                below: $scope.graphState.max + 1,
                                color: '#740000'
                            }, {
                                below: $scope.graphState.p95,
                                color: '#007400'
                            }, {
                                below: $scope.graphState.p05,
                                color: '#747474'
                            }];
                        }
                    }
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

            query();
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
