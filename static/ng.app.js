// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

var fluxmon = angular.module('FluxmonApp', []);

fluxmon.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[');
    $interpolateProvider.endSymbol(']}');
});

fluxmon.controller("GraphDurationCtrl", function($scope, $timeout){
    $scope.profiles = [
        {title:  "4h", duration:      6*60*60, tiny: true },
        {title: "24h", duration:     24*60*60, tiny: true },
        {title: "48h", duration:     48*60*60, tiny: true },
        {title:  "1w", duration:   7*24*60*60, tiny: true },
        {title:  "2w", duration:  14*24*60*60, tiny: false},
        {title:  "1m", duration:  30*24*60*60, tiny: true },
        {title:  "3m", duration:  90*24*60*60, tiny: false},
        {title:  "6m", duration: 180*24*60*60, tiny: false},
        {title:  "1y", duration: 365*24*60*60, tiny: true },
    ];
    $scope.active_profile = $scope.profiles[1]; // 24h
    $scope.set_active_profile = function(val){
        $scope.active_profile = val;
    }
    var update_start = function(){
        $scope.start = $scope.end - $scope.active_profile.duration;
    };
    $scope.$watch("active_profile", update_start);
    $scope.$watch("end", update_start);

    var update_end = function(){
        while( new Date() > ($scope.end + 300) * 1000 ){
            $scope.end += 300;
        }
        $timeout(update_end, 1);
    }
    update_end();
})
