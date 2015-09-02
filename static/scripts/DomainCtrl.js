fluxmon.controller("DomainTreeCtrl", function($scope, $stateParams, $http){
    $http.get("/api/domains/tree/").then(function(response){
        $scope.tree = response.data;
    });
});

fluxmon.controller("DomainCtrl", function($scope, $stateParams, $http){
    $http.get("/api/domains/" + $stateParams.domId + "/").then(function(response){
        $scope.domain = response.data;
    });
});

fluxmon.controller("DomainAggregateListCtrl", function($scope, $stateParams, $http){
    $http.get("/api/domains/" + $stateParams.domId + "/aggregates/").then(function(response){
        $scope.domainAggregates = response.data;
    });
});

fluxmon.controller("DomainAggregateCtrl", function($scope, $stateParams, $http){
    $scope.check = null;
    $http.get("/api/domains/" + $stateParams.domId + "/aggregates/").then(function(response){
        $scope.variables = response.data.filter(function(item){
            if(item.name == $stateParams.name){
                return true;
            }
        });
    });
    $scope.graphState = {};
});
