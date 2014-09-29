var fluxmon = angular.module('FluxmonApp', []);

fluxmon.config(function($interpolateProvider) {
	$interpolateProvider.startSymbol('{[');
	$interpolateProvider.endSymbol(']}');
});

fluxmon.controller("GraphDurationCtrl", function($scope){
	$scope.profiles = [
		{title: "4h", duration:      6*60*60},
		{title:"24h", duration:     24*60*60},
		{title:"48h", duration:     48*60*60},
		{title: "1w", duration:   7*24*60*60},
		{title: "2w", duration:  14*24*60*60},
		{title: "1m", duration:  30*24*60*60},
		{title: "3m", duration:  90*24*60*60},
		{title: "6m", duration: 180*24*60*60},
		{title: "1y", duration: 365*24*60*60},
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

})

