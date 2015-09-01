fluxmon.controller("ProfileCtrl", function($scope, $stateParams, $http){
    $http.get("/api/users/self/").then(function(response){
        $scope.user = response.data;
    });
    $http.get("/api/checks/most_viewed/").then(function(response){
        $scope.mostViewedChecks = response.data;
    });
});
