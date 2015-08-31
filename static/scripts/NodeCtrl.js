fluxmon.controller("NodeCtrl", function($scope, $stateParams, $http){
    $http.get("/api/hosts/" + $stateParams.nodeId + "/").then(function(response){
        $scope.host = response.data;
    });
});
