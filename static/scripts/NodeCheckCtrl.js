
fluxmon.controller("NodeCheckListCtrl", function($scope, $stateParams, $http){
    $http.get("/api/checks/", {params: {
      target_host: $stateParams.nodeId
    }}).then(function(response){
        $scope.hostChecks = response.data.results;
    });
});

fluxmon.controller("NodeCheckCtrl", function($scope, $stateParams, $http){
    $http.get("/api/checks/" + $stateParams.check + "/").then(function(response){
        $scope.check = response.data;
    });
});

fluxmon.controller("NodeCheckVarCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.$watch("check", function(){
        if(!$scope.check) return;
        $scope.variables = $scope.check.sensor.sensorvariable_set.filter(function(item){
            if(item.name == $stateParams.name){
                return true;
            }
        }).map(function(item){
            item.sensor = $scope.check.sensor.name;
            return item;
        });
    });
    $scope.graphState = {};
});
