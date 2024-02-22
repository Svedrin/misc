fluxmon.controller("ProfileCtrl", function($scope, $stateParams, $http, $rootScope){
    $http.get("/api/users/self/").then(function(response){
        $scope.user = response.data;
        $rootScope.titlePrefix = $scope.user.username;
    });
    $http.get("/api/checks/most_viewed/").then(function(response){
        $scope.mostViewedChecks = response.data;
    });
});
