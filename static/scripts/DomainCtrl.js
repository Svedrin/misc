fluxmon.controller("DomainTreeCtrl", function($scope, $stateParams, $http, $rootScope){
    $rootScope.titlePrefix = "Hosts";
    $http.get("/api/domains/tree/").then(function(response){
        $scope.tree = response.data;
    });
});

fluxmon.controller("DomainCtrl", function($scope, $stateParams, $http, $rootScope){
    $http.get("/api/domains/" + $stateParams.domId + "/").then(function(response){
        $scope.domain = response.data;
        $rootScope.titlePrefix = $scope.domain.fqdn;
    });
});

fluxmon.controller("DomainAggregateListCtrl", function($scope, $stateParams, $http){
});

fluxmon.controller("DomainAggregateCtrl", function($scope, $stateParams, $http){
    $scope.check = null;
    $scope.$watch('domain', function(){
        if(!$scope.domain) return;
        $scope.variables = $scope.domain.aggregates_set.filter(function(item){
            if(item.name == $stateParams.name){
                return true;
            }
        });
    });
    $scope.graphState = {};
});
