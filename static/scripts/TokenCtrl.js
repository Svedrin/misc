fluxmon.controller("TokenCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.check  = null;
    $scope.graphState = {};
    $http.get("/api/tokens/" + $stateParams.token + "/").then(function(response){
        $scope.check = response.data.check;
        $scope.domain = response.data.domain;
        if(response.data.view != null){
            $scope.variables = response.data.view.variables;
        }
        else{
            $scope.variables = [response.data.variable];
        }
    });
});
