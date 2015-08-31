
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
