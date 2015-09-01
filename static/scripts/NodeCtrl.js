fluxmon.controller("NodeCtrl", function($scope, $stateParams, $http){
    $http.get("/api/hosts/" + $stateParams.nodeId + "/").then(function(response){
        $scope.host = response.data;
    });
});

fluxmon.controller("NodeCheckListCtrl", function($scope, $stateParams, $http){
    $http.get("/api/checks/", {params: {
      target_host: $stateParams.nodeId
    }}).then(function(response){
        $scope.hostChecks = response.data.results;
    });
});

fluxmon.controller("NodeCheckCtrl", function($scope, $stateParams, $http, $timeout){
    $http.get("/api/checks/" + $stateParams.check + "/").then(function(response){
        $scope.check = response.data;
        $scope.editing = false;
        $scope.startEdit = function(){
          $scope.editing = true;
          $timeout(function(){
            $('#id_display').focus();
          }, 50);
        };
        $scope.submit = function(){
          $http.patch("/api/checks/" + $stateParams.check + "/", {
            display: $scope.check.display
          });
          $scope.editing = false;
        };
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
        });
    });
    $scope.graphState = {};
});

fluxmon.controller("NodeCheckViewCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.$watch("check", function(){
        if(!$scope.check) return;
        $scope.variables = $scope.check.views_set.reduce(function(prev, item){
            if(item.name == $stateParams.name){
                return item.variables;
            }
            return prev;
        }, []);
    });
    $scope.graphState = {};
});
