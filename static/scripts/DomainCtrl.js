fluxmon.controller("DomainTreeCtrl", function($scope, $stateParams, $http){
    $http.get("/api/domains/tree/").then(function(response){
        $scope.tree = response.data;
    });
});
