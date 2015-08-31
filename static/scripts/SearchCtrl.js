fluxmon.controller("SearchCtrl", function($scope, $http){
    $scope.submit = function(){
        console.log("Go!");
        $http.get("/api/checks/", {params: {
            search: $scope.query
        }}).then(function(response){
            $scope.foundChecks = response.data.results;
        });
    };
});
